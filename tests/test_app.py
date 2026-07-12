class TestLogin:
    def test_protected_route_redirects_to_login(self, client):
        resp = client.get("/rooms")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_login_success_redirects_to_me(self, client):
        resp = client.post("/login", data={"username": "claude", "password": "claude"})
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/me")

    def test_login_failure_shows_error(self, client):
        resp = client.post("/login", data={"username": "claude", "password": "wrong"})
        assert resp.status_code == 200
        assert "Ungültige Zugangsdaten" in resp.get_data(as_text=True)


import hashlib
import hmac as hmac_mod
import time

from tests.conftest import TELEGRAM_BOT_TOKEN


def _sign_telegram_data(data, bot_token=TELEGRAM_BOT_TOKEN):
    data = dict(data)
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    data["hash"] = hmac_mod.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    return data


class TestTelegramAuthVerification:
    def test_valid_signature_accepted(self):
        from hannah_webui.route_helpers import _verify_telegram_auth
        data = _sign_telegram_data({"id": "123", "first_name": "Claude", "auth_date": str(int(time.time()))})
        assert _verify_telegram_auth(data, TELEGRAM_BOT_TOKEN) is True

    def test_tampered_payload_rejected(self):
        from hannah_webui.route_helpers import _verify_telegram_auth
        data = _sign_telegram_data({"id": "123", "first_name": "Claude", "auth_date": str(int(time.time()))})
        data["id"] = "999"
        assert _verify_telegram_auth(data, TELEGRAM_BOT_TOKEN) is False

    def test_expired_auth_date_rejected(self):
        from hannah_webui.route_helpers import _verify_telegram_auth
        data = _sign_telegram_data({"id": "123", "first_name": "Claude", "auth_date": "1000000000"})
        assert _verify_telegram_auth(data, TELEGRAM_BOT_TOKEN) is False

    def test_wrong_bot_token_rejected(self):
        from hannah_webui.route_helpers import _verify_telegram_auth
        data = _sign_telegram_data({"id": "123", "first_name": "Claude", "auth_date": str(int(time.time()))})
        assert _verify_telegram_auth(data, "other-secret") is False


class TestTelegramLinking:
    def test_callback_with_invalid_hash_shows_error(self, telegram_client):
        resp = telegram_client.get("/me/telegram/callback?id=123&first_name=Claude&auth_date=1&hash=bogus")
        body = telegram_client.get(resp.headers["Location"]).get_data(as_text=True)
        assert "ungültige oder abgelaufene Signatur" in body

    def test_callback_with_valid_hash_links_account(self, telegram_client):
        data = _sign_telegram_data({"id": "555", "first_name": "Claude", "auth_date": str(int(time.time()))})
        resp = telegram_client.get("/me/telegram/callback", query_string=data)
        assert resp.status_code == 302
        body = telegram_client.get("/me").get_data(as_text=True)
        assert "Trennen" in body
        assert "telegram-widget.js" not in body

    def test_login_link_uses_https_return_to_me_page(self, telegram_client):
        """Telegram silently rejects non-HTTPS return_to urls on public domains — this must
        hold even though gunicorn itself serves plain HTTP behind a TLS-terminating
        reverse proxy that doesn't forward X-Forwarded-Proto. return_to must point at /me
        (not /me/telegram/callback) because Telegram appends the result as a URL *fragment*,
        which never reaches the server — only a real page with the tgAuthResult-decoding
        script (below) can pick it up client-side."""
        body = telegram_client.get("/me").get_data(as_text=True)
        assert "oauth.telegram.org/auth?" in body
        assert "return_to=https%3A%2F%2Flocalhost%2Fme" in body

    def test_me_page_decodes_tg_auth_result_fragment(self, telegram_client):
        body = telegram_client.get("/me").get_data(as_text=True)
        assert "tgAuthResult" in body
        assert "/me/telegram/callback" in body

    def test_unlink_removes_account(self, telegram_client):
        data = _sign_telegram_data({"id": "555", "first_name": "Claude", "auth_date": str(int(time.time()))})
        telegram_client.get("/me/telegram/callback", query_string=data)

        telegram_client.post("/me/telegram/unlink")
        body = telegram_client.get("/me").get_data(as_text=True)
        assert "Trennen" not in body


class TestMe:
    def test_me_shows_display_name(self, logged_in_client):
        body = logged_in_client.get("/me").get_data(as_text=True)
        assert "Hallo" in body

    def test_change_password_success(self, logged_in_client):
        resp = logged_in_client.post("/me/password", data={"password": "newpass123", "password_confirm": "newpass123"})
        assert resp.status_code == 302
        body = logged_in_client.get("/me").get_data(as_text=True)
        assert "Passwort geändert" in body

    def test_change_password_mismatch_rejected(self, logged_in_client):
        resp = logged_in_client.post("/me/password", data={"password": "abc12345", "password_confirm": "different"})
        body = logged_in_client.get(resp.headers["Location"]).get_data(as_text=True)
        assert "stimmen nicht überein" in body


class TestAlarms:
    def test_me_lists_own_seeded_alarm(self, logged_in_client):
        body = logged_in_client.get("/me").get_data(as_text=True)
        assert "06:30" in body
        assert "Aufstehen" in body

    def test_create_recurring_alarm(self, logged_in_client, hannah):
        resp = logged_in_client.post("/me/alarms/create", data={
            "time": "07:00", "satellite_id": "kueche-esp", "label": "Test",
            "alarm_type": "recurring", "weekdays": ["0", "2"],
        })
        assert resp.status_code == 302
        alarms = hannah.get_alarms(1)
        created = next(a for a in alarms if a.label == "Test")
        assert created.time == "07:00"
        assert list(created.weekdays) == [0, 2]
        assert created.one_shot_date == ""

    def test_create_once_alarm(self, logged_in_client, hannah):
        logged_in_client.post("/me/alarms/create", data={
            "time": "08:00", "satellite_id": "kueche-esp", "alarm_type": "once", "one_shot_date": "2026-07-10",
        })
        alarms = hannah.get_alarms(1)
        created = next(a for a in alarms if a.time == "08:00")
        assert created.one_shot_date == "2026-07-10"
        assert list(created.weekdays) == []

    def test_create_alarm_without_time_is_rejected(self, logged_in_client, hannah):
        logged_in_client.post("/me/alarms/create", data={"satellite_id": "kueche-esp", "alarm_type": "once"})
        assert len(hannah.get_alarms(1)) == 1  # nur der geseedete Alarm, keiner angelegt

    def test_create_alarm_without_satellite_is_rejected(self, logged_in_client, hannah):
        resp = logged_in_client.post(
            "/me/alarms/create", data={"time": "09:00", "alarm_type": "once"}, follow_redirects=True
        )
        assert len(hannah.get_alarms(1)) == 1  # nur der geseedete Alarm, keiner angelegt
        assert "Satellit ist Pflicht" in resp.get_data(as_text=True)

    def test_toggle_alarm(self, logged_in_client, hannah):
        logged_in_client.post("/me/alarms/1/toggle")
        assert hannah._alarms[1]["enabled"] is False

    def test_delete_alarm(self, logged_in_client, hannah):
        logged_in_client.post("/me/alarms/1/delete")
        assert 1 not in hannah._alarms

    def test_cannot_toggle_or_delete_other_users_alarm(self, admin_client, hannah):
        """Alarme sind personenbezogen (user_id) — Alarm 1 gehört user_id 1 (claude),
        admin (user_id 2) darf ihn weder togglen noch löschen."""
        admin_client.post("/me/alarms/1/toggle")
        assert hannah._alarms[1]["enabled"] is True
        admin_client.post("/me/alarms/1/delete")
        assert 1 in hannah._alarms


class TestRooms:
    def test_rooms_lists_seeded_rooms_and_group_badge(self, logged_in_client):
        resp = logged_in_client.get("/rooms")
        body = resp.get_data(as_text=True)
        assert "Küche" in body
        assert "Erdgeschoss" in body  # group badge on a room that belongs to it


class TestGroups:
    def test_create_group_then_visible(self, admin_client):
        admin_client.post("/groups/create", data={"display_name": "Obergeschoss"})
        resp = admin_client.get("/groups")
        assert "Obergeschoss" in resp.get_data(as_text=True)

    def test_edit_group_renames_and_sets_rooms(self, admin_client):
        admin_client.post(
            "/groups/erdgeschoss/edit",
            data={"display_name": "EG", "room_ids": "bad"},
        )
        resp = admin_client.get("/groups")
        body = resp.get_data(as_text=True)
        assert "EG" in body
        assert "Bad" in body

    def test_delete_group(self, admin_client):
        admin_client.post("/groups/erdgeschoss/delete")
        resp = admin_client.get("/groups")
        # erdgeschoss is the only seeded group, so its removal should hit the empty state.
        # "Erdgeschoss" itself isn't a safe needle here: the create-form placeholder uses it as an example.
        assert "Noch keine Gruppen angelegt" in resp.get_data(as_text=True)


class TestSatellites:
    def test_satellites_lists_seeded_satellite(self, admin_client):
        resp = admin_client.get("/satellites")
        body = resp.get_data(as_text=True)
        assert "kueche-esp" in body
        assert "Küche01" in body

    def test_set_satellite_room(self, logged_in_client, hannah):
        logged_in_client.post("/satellites/kueche-esp/room", data={"room_id": "bad"})
        assert hannah._satellites["kueche-esp"]["room_id"] == "bad"

    def test_set_satellite_display_name(self, logged_in_client, hannah):
        logged_in_client.post("/satellites/kueche-esp/name", data={"display_name": "NeuerName"})
        assert hannah._satellites["kueche-esp"]["display_name"] == "NeuerName"

    def test_set_satellite_owner(self, admin_client, hannah):
        admin_client.post("/satellites/kueche-esp/owner", data={"user_id": "1"})
        assert hannah._satellites["kueche-esp"]["owner_user_id"] == 1

    def test_satellites_shows_owner_options(self, admin_client):
        resp = admin_client.get("/satellites")
        assert "Leonie" in resp.get_data(as_text=True)


class TestSatellitePermissions:
    """Row-level Sichtbarkeit: reguläre User (trust_level 7) sehen nur eigene
    Satelliten, Admins (trust_level 10) sehen alle."""

    def test_regular_user_only_sees_own_satellite(self, logged_in_client, hannah):
        hannah._satellites["kueche-esp"]["owner_user_id"] = 1  # == logged_in_client's session user_id
        hannah._satellites["wz-esp"] = {
            "display_name": "Wohnzimmer01", "room_id": "wohnzimmer", "live_room": "wohnzimmer",
            "last_seen": "", "connected": False, "owner_user_id": 99,
        }
        body = logged_in_client.get("/satellites").get_data(as_text=True)
        assert "kueche-esp" in body
        assert "wz-esp" not in body

    def test_admin_sees_all_satellites(self, admin_client, hannah):
        hannah._satellites["wz-esp"] = {
            "display_name": "Wohnzimmer01", "room_id": "wohnzimmer", "live_room": "wohnzimmer",
            "last_seen": "", "connected": False, "owner_user_id": 99,
        }
        body = admin_client.get("/satellites").get_data(as_text=True)
        assert "kueche-esp" in body
        assert "wz-esp" in body

    def test_regular_user_redirected_from_admin_only_route(self, logged_in_client):
        resp = logged_in_client.get("/users")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/me")


class TestSettings:
    def test_settings_lists_seeded_category_and_value(self, admin_client):
        resp = admin_client.get("/settings")
        body = resp.get_data(as_text=True)
        assert "nlu" in body
        assert "turn_on_words" in body
        assert "einschalten" in body

    def test_settings_renders_list_type_as_line_inputs(self, admin_client):
        resp = admin_client.get("/settings")
        body = resp.get_data(as_text=True)
        assert 'name="list_item" value="an"' in body
        assert 'name="list_item" value="einschalten"' in body

    def test_settings_renders_text_type_with_real_newline(self, admin_client):
        resp = admin_client.get("/settings")
        body = resp.get_data(as_text=True)
        assert "Du bist Hannah.\nDeine Antworten" in body

    def test_settings_renders_keyvalue_type_as_kv_inputs(self, admin_client):
        resp = admin_client.get("/settings")
        body = resp.get_data(as_text=True)
        assert 'name="kv_key" value="on"' in body
        assert 'name="kv_value" value="on"' in body

    def test_update_setting(self, admin_client, hannah):
        admin_client.post("/settings/1/update", data={"value": '["an"]'})
        assert hannah._settings[1]["value"] == ["an"]

    def test_update_setting_invalid_json_is_rejected(self, admin_client, hannah):
        resp = admin_client.post(
            "/settings/1/update", data={"value": "not json"}, follow_redirects=True
        )
        assert "invalid JSON" in resp.get_data(as_text=True)
        assert hannah._settings[1]["value"] == ["an", "einschalten"]

    def test_update_setting_list_type_drops_blank_rows(self, admin_client, hannah):
        admin_client.post(
            "/settings/1/update",
            data={"value_type": "list", "list_item": ["an", "", "aus", "  "]},
        )
        assert hannah._settings[1]["value"] == ["an", "aus"]

    def test_update_setting_text_type_normalizes_crlf(self, admin_client, hannah):
        admin_client.post(
            "/settings/2/update",
            data={"value_type": "text", "text_value": "Zeile 1\r\nZeile 2"},
        )
        assert hannah._settings[2]["value"] == "Zeile 1\nZeile 2"

    def test_update_setting_keyvalue_type_drops_blank_keys(self, admin_client, hannah):
        admin_client.post(
            "/settings/3/update",
            data={
                "value_type": "keyvalue",
                "kv_key": ["on", "", "level"],
                "kv_value": ["an", "ignored", "stufe"],
            },
        )
        assert hannah._settings[3]["value"] == {"on": "an", "level": "stufe"}


class TestBleTags:
    def test_ble_tags_lists_seeded_tag(self, admin_client):
        resp = admin_client.get("/ble-tags")
        body = resp.get_data(as_text=True)
        assert "aa:bb:cc:dd:ee:ff" in body
        assert "Schlüsselanhänger" in body

    def test_create_ble_tag_then_visible(self, admin_client, hannah):
        admin_client.post("/ble-tags/create", data={"mac_address": "11:22:33:44:55:66", "label": "Auto", "user_id": "1"})
        created = next(t for t in hannah._ble_tags.values() if t["mac_address"] == "11:22:33:44:55:66")
        assert created["label"] == "Auto"
        assert created["user_id"] == 1

    def test_edit_ble_tag(self, admin_client, hannah):
        admin_client.post("/ble-tags/1/edit", data={"mac_address": "aa:bb:cc:dd:ee:ff", "label": "Neu", "user_id": "0"})
        assert hannah._ble_tags[1]["label"] == "Neu"
        assert hannah._ble_tags[1]["user_id"] == 0

    def test_delete_ble_tag(self, admin_client, hannah):
        admin_client.post("/ble-tags/1/delete")
        assert 1 not in hannah._ble_tags

    def test_regular_user_redirected_from_ble_tags(self, logged_in_client):
        resp = logged_in_client.get("/ble-tags")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/me")


class TestCars:
    def test_cars_lists_seeded_car_and_owner(self, admin_client):
        resp = admin_client.get("/cars")
        body = resp.get_data(as_text=True)
        assert "vwconnect/golf" in body
        assert "Leonie" in body

    def test_cars_shows_name_as_title_and_topic_prefix_as_subline(self, admin_client):
        resp = admin_client.get("/cars")
        body = resp.get_data(as_text=True)
        assert "Golf" in body
        assert "vwconnect/golf" in body

    def test_create_car_then_visible(self, admin_client, hannah):
        admin_client.post("/cars/create", data={"topic_prefix": "vwconnect/id3", "home_address": "Musterweg 2"})
        created = next(c for c in hannah._cars.values() if c["topic_prefix"] == "vwconnect/id3")
        assert created["home_address"] == "Musterweg 2"
        assert created["owner_user_ids"] == []

    def test_create_car_with_name(self, admin_client, hannah):
        admin_client.post("/cars/create", data={
            "topic_prefix": "vwconnect/id4", "home_address": "Musterweg 3", "name": "Auto Leonie",
        })
        created = next(c for c in hannah._cars.values() if c["topic_prefix"] == "vwconnect/id4")
        assert created["name"] == "Auto Leonie"

    def test_edit_car_form_prefills_existing_data(self, admin_client):
        resp = admin_client.get("/cars/1/edit")
        body = resp.get_data(as_text=True)
        assert "vwconnect/golf" in body
        assert 'value="Golf"' in body
        assert 'checked' in body

    def test_save_car_updates_fields_and_owners(self, admin_client, hannah):
        admin_client.post("/cars/1/edit", data={
            "topic_prefix": "vwconnect/golf", "home_address": "Neue Adresse", "name": "Golf GTI", "owner_user_ids": [],
        })
        assert hannah._cars[1]["home_address"] == "Neue Adresse"
        assert hannah._cars[1]["owner_user_ids"] == []
        assert hannah._cars[1]["name"] == "Golf GTI"

    def test_delete_car(self, admin_client, hannah):
        admin_client.post("/cars/1/delete")
        assert 1 not in hannah._cars

    def test_regular_user_redirected_from_cars(self, logged_in_client):
        resp = logged_in_client.get("/cars")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/me")


class TestTriggers:
    """#101 Teil 2 — No-Code-Trigger-Editor. Seit #28 auch when.phrase (ersetzt die
    frühere separate Routinen-Verwaltung, siehe hannah#139)."""

    def test_triggers_lists_seeded_trigger(self, logged_in_client):
        resp = logged_in_client.get("/triggers")
        body = resp.get_data(as_text=True)
        assert "aussentuer_abend" in body
        assert "23:00" in body

    def test_new_trigger_form_renders(self, logged_in_client):
        resp = logged_in_client.get("/triggers/new")
        assert resp.status_code == 200

    def test_new_trigger_form_hides_non_writable_state_in_action_dropdown(self, logged_in_client):
        """state_writable (hannah-proto #8) blendet nicht beschreibbare States wie den
        Fenstersensor in der Dann-Auswahl aus, bleibt aber in Wenn/Und/Außer-wenn sichtbar."""
        resp = logged_in_client.get("/triggers/new")
        body = resp.get_data(as_text=True)
        # 2 Wenn- + 2 Und- + 2 Außer-wenn-Zeilen zeigen den State, die 2 Dann-Zeilen nicht
        # (8 Vorkommen wären es, würde die Action-Dropdown den Sensor nicht ausblenden).
        assert body.count('value="fenster.wz.open.open"') == 6

    def test_edit_trigger_form_prefills_time_condition(self, logged_in_client):
        resp = logged_in_client.get("/triggers/aussentuer_abend/edit")
        body = resp.get_data(as_text=True)
        assert 'value="23:00"' in body
        assert "mon,tue,wed,thu,fri" in body

    def _create_payload(self, **overrides):
        payload = {
            "id": "Fenster Kalt",
            "when_type": ["state"], "when_state": ["fenster.wz.open"], "when_cmp": ["value"],
            "when_value": ["true"], "when_time": [""], "when_days": [""],
            "also_op": "and", "also_state": [], "also_cmp": [], "also_value": [],
            "unless_state": [], "unless_cmp": [], "unless_value": [],
            "action_type": ["say"], "action_say": ["Fenster offen."], "action_room": ["all"],
            "action_state_id": [""], "action_state_value": [""],
            "room": "all", "cooldown": "3600", "delay": "", "ask": "", "on_response_json": "",
        }
        payload.update(overrides)
        return payload

    def test_create_trigger_with_or_when_and_also_and_unless(self, logged_in_client, hannah):
        logged_in_client.post("/triggers/create", data=self._create_payload(
            when_type=["state", "state"], when_state=["fenster.wz.open", "fenster.kueche.open"],
            when_cmp=["value", "value"], when_value=["true", "true"], when_time=["", ""], when_days=["", ""],
            also_op="or", also_state=["a", "b"], also_cmp=["value", "value"], also_value=["true", "true"],
            unless_state=["abwesend"], unless_cmp=["value"], unless_value=["true"],
        ))
        created = hannah._triggers["fenster-kalt"]
        assert len(created["when"]) == 2
        assert created["when"][0]["also"] == {"op": "or", "conditions": [
            {"state": "a", "value": "true"}, {"state": "b", "value": "true"},
        ]}
        assert created["when"][0]["unless"] == [{"state": "abwesend", "value": "true"}]
        assert created["when"][1]["also"] == created["when"][0]["also"]
        assert created["actions"] == [{"say": "Fenster offen.", "room": "all"}]

    def test_create_trigger_with_phrase_condition(self, logged_in_client, hannah):
        """#28 — ersetzt die frühere separate Routinen-Verwaltung (hannah#139)."""
        logged_in_client.post("/triggers/create", data=self._create_payload(
            id="gute-nacht",
            when_type=["phrase"], when_state=[""], when_cmp=["value"], when_value=[""],
            when_time=[""], when_days=[""], when_phrase=["gute nacht"],
        ))
        created = hannah._triggers["gute-nacht"]
        assert created["when"] == [{"phrase": "gute nacht"}]

    def test_edit_trigger_form_prefills_phrase_condition(self, logged_in_client, hannah):
        hannah._triggers["schlafenszeit"] = {
            "when": {"phrase": "schlafenszeit"}, "cancel_when": None, "on_response": [], "actions": [],
            "say": "Gute Nacht.", "ask": "", "rephrase": False, "room": "all", "cooldown": 0, "delay": "",
        }
        resp = logged_in_client.get("/triggers/schlafenszeit/edit")
        body = resp.get_data(as_text=True)
        assert 'value="schlafenszeit"' in body

    def test_create_trigger_with_time_condition_and_state_action(self, logged_in_client, hannah):
        logged_in_client.post("/triggers/create", data=self._create_payload(
            id="zeit-trigger",
            when_type=["time"], when_state=[""], when_cmp=["value"], when_value=[""],
            when_time=["07:00"], when_days=["mon,tue"],
            action_type=["state"], action_say=[""], action_room=[""],
            action_state_id=["javascript.0.virtualDevice.Licht.test"], action_state_value=["true"],
        ))
        created = hannah._triggers["zeit-trigger"]
        assert created["when"] == [{"time": "07:00", "days": ["mon", "tue"]}]
        assert created["actions"] == [{"set_state": {"id": "javascript.0.virtualDevice.Licht.test", "value": "true"}}]

    def test_update_trigger(self, logged_in_client, hannah):
        logged_in_client.post("/triggers/aussentuer_abend/edit", data=self._create_payload(
            when_type=["time"], when_state=[""], when_cmp=["value"], when_value=[""],
            when_time=["22:00"], when_days=[""], room="flur",
        ))
        updated = hannah._triggers["aussentuer_abend"]
        assert updated["when"] == [{"time": "22:00"}]
        assert updated["room"] == "flur"

    def test_delete_trigger(self, logged_in_client, hannah):
        logged_in_client.post("/triggers/aussentuer_abend/delete")
        assert "aussentuer_abend" not in hannah._triggers


class TestUsers:
    def test_users_lists_seeded_user(self, admin_client):
        resp = admin_client.get("/users")
        body = resp.get_data(as_text=True)
        assert "Leonie" in body
        assert "leonie" in body

    def test_create_user_then_visible(self, admin_client):
        admin_client.post("/users/create", data={
            "username": "hannah", "password": "secret", "email": "hannah@example.com",
            "display_name": "Hannah", "type": "roomie",
        })
        resp = admin_client.get("/users")
        assert "Hannah" in resp.get_data(as_text=True)

    def test_create_user_missing_fields_is_rejected(self, admin_client, hannah):
        before = len(hannah._user_records)
        resp = admin_client.post(
            "/users/create", data={"username": "", "password": "", "email": ""}, follow_redirects=True
        )
        assert "Pflicht" in resp.get_data(as_text=True)
        assert len(hannah._user_records) == before

    def test_edit_user_updates_fields(self, admin_client, hannah):
        admin_client.post("/users/1/edit", data={
            "display_name": "Leonie G.", "email": "leonie@neu.example.com", "type": "roomie",
            "is_active": "on", "trust_level": "9", "system_messages": "on", "password": "",
        })
        assert hannah._user_records[1]["display_name"] == "Leonie G."
        assert hannah._user_records[1]["trust_level"] == 9
        assert hannah._user_records[1]["system_messages"] is True

    def test_delete_user(self, admin_client, hannah):
        admin_client.post("/users/1/delete")
        assert 1 not in hannah._user_records

    def test_link_resident(self, admin_client, hannah):
        admin_client.post("/users/1/link-resident", data={"resident_id": "leonie_roomie"})
        assert hannah._user_records[1]["linked_accounts"]["residents"] == "leonie_roomie"

    def test_unlink_resident(self, admin_client, hannah):
        hannah._user_records[1]["linked_accounts"]["residents"] = "leonie_roomie"
        admin_client.post("/users/1/unlink-resident")
        assert "residents" not in hannah._user_records[1]["linked_accounts"]


class TestVersion:
    def test_version_endpoint_returns_json_without_login(self, client):
        resp = client.get("/version")
        assert resp.status_code == 200
        assert resp.get_json() == {"version": "dev"}

    def test_me_shows_version_badge(self, logged_in_client):
        body = logged_in_client.get("/me").get_data(as_text=True)
        assert "dev" in body


import grpc


class TestErrorPages:
    def test_grpc_error_shows_friendly_503_page(self, logged_in_client, hannah):
        hannah.get_rooms = lambda: (_ for _ in ()).throw(grpc.RpcError())
        resp = logged_in_client.get("/rooms")
        assert resp.status_code == 503
        assert "nicht erreichbar" in resp.get_data(as_text=True)

    def test_unknown_route_shows_friendly_404_page(self, client):
        resp = client.get("/this-route-does-not-exist")
        assert resp.status_code == 404
        assert "nicht gefunden" in resp.get_data(as_text=True)

    def test_login_when_core_down_shows_friendly_error_not_wrong_password(self, client, hannah):
        hannah.login = lambda username, password: (_ for _ in ()).throw(grpc.RpcError())
        resp = client.post("/login", data={"username": "claude", "password": "claude"})
        assert resp.status_code == 503
        body = resp.get_data(as_text=True)
        assert "nicht erreichbar" in body
        assert "Ungültige Zugangsdaten" not in body

    def test_unexpected_error_shows_friendly_500_page(self, logged_in_client, hannah):
        hannah.get_rooms = lambda: (_ for _ in ()).throw(ValueError("boom"))
        resp = logged_in_client.get("/rooms")
        assert resp.status_code == 500
        assert "schiefgelaufen" in resp.get_data(as_text=True)
