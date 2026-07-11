"""In-memory stand-in for grpc_client.HannahClient — same method surface, no network,
no real Hannah Core needed. Built from real hannah_pb2 messages so route/template code
is exercised against the exact wire types Core actually sends."""
import json

from hannah_proto import hannah_pb2


class FakeHannahClient:
    def __init__(self):
        self._rooms = {
            "kueche": "Küche",
            "wohnzimmer": "Wohnzimmer",
            "bad": "Bad",
        }
        self._groups = {
            "erdgeschoss": {"display_name": "Erdgeschoss", "room_ids": ["kueche", "wohnzimmer"]},
        }
        self._satellites = {
            "kueche-esp": {
                "display_name": "Küche01",
                "room_id": "kueche",
                "live_room": "kueche",
                "last_seen": "2026-06-27 12:00:00",
                "connected": True,
                "owner_user_id": 0,
            },
        }
        self._users = {"claude": "claude", "admin": "admin"}
        self._user_records = {
            1: {
                "user_name": "leonie", "display_name": "Leonie", "email": "leonie@example.com",
                "trust_level": 8, "active": True, "system_messages": True, "type": "roomie",
                "linked_accounts": {},
            },
        }
        self._next_user_id = 2
        self._residents = {
            "leonie_roomie": {"roomie_id": "leonie", "display_name": "Leonie", "type": "roomie", "home": True},
        }
        self._categories = {1: "nlu", 2: "llm", 3: "iobroker"}
        self._settings = {
            1: {"category_id": 1, "name": "turn_on_words", "value": ["an", "einschalten"]},
            2: {"category_id": 2, "name": "system_prompt", "value": "Du bist Hannah.\nDeine Antworten werden per Sprachausgabe vorgelesen."},
            3: {"category_id": 3, "name": "state_names", "value": {"on": "on", "level": "level"}},
        }
        self._triggers = {
            "aussentuer_abend": {
                "when": {"time": "23:00", "days": ["mon", "tue", "wed", "thu", "fri"]},
                "cancel_when": None, "on_response": [], "actions": [],
                "say": "Leonie, denk an die Außentüren.", "ask": "", "rephrase": True,
                "room": "all", "cooldown": 3600, "delay": "",
            },
        }
        self._alarms = {
            1: {
                "satellite_id": "kueche-esp", "time": "06:30", "weekdays": [0, 1, 2, 3, 4],
                "skip_dates": [], "one_shot_date": "", "enabled": True, "label": "Aufstehen", "user_id": 1,
            },
        }
        self._next_alarm_id = 2
        self._ble_tags = {
            1: {"mac_address": "aa:bb:cc:dd:ee:ff", "label": "Schlüsselanhänger", "user_id": 1},
        }
        self._next_ble_tag_id = 2
        self._cars = {
            1: {"topic_prefix": "vwconnect/golf", "home_address": "Musterstraße 1", "owner_user_ids": [1], "name": "Golf"},
        }
        self._next_car_id = 2

    def connect(self) -> None:
        pass

    def close(self) -> None:
        pass

    def login(self, username, password):
        if self._users.get(username) != password:
            return False, None
        if username == "admin":
            user = hannah_pb2.User(id=2, user_name=username, display_name="Admin", trust_level=10, active=True)
        else:
            user = hannah_pb2.User(id=1, user_name=username, display_name=username, trust_level=7, active=True)
        return True, user

    def get_rooms(self):
        return [hannah_pb2.Room(room_id=rid, display_name=name) for rid, name in self._rooms.items()]

    def get_groups(self):
        result = []
        for group_id, g in self._groups.items():
            rooms = [
                hannah_pb2.Room(room_id=rid, display_name=self._rooms[rid])
                for rid in g["room_ids"] if rid in self._rooms
            ]
            result.append(hannah_pb2.Group(group_id=group_id, display_name=g["display_name"], rooms=rooms))
        return result

    def get_group(self, group_id):
        return next((g for g in self.get_groups() if g.group_id == group_id), None)

    def create_group(self, group_id, display_name):
        if group_id in self._groups:
            return False
        self._groups[group_id] = {"display_name": display_name, "room_ids": []}
        return True

    def update_group(self, group_id, display_name):
        if group_id not in self._groups:
            return False
        self._groups[group_id]["display_name"] = display_name
        return True

    def delete_group(self, group_id):
        return self._groups.pop(group_id, None) is not None

    def set_group_rooms(self, group_id, room_ids):
        if group_id not in self._groups:
            return False
        self._groups[group_id]["room_ids"] = list(room_ids)
        return True

    def get_devices(self):
        licht = hannah_pb2.DeviceInfo(
            id="javascript.0.virtualDevice.Licht.EG.Wohnzimmer.DeckeSeite",
            name="DeckeSeite", category="Licht",
            states=["on", "level", "color"],
            current={"on": "true", "level": "75", "color": "warm"},
            state_types={
                "on": hannah_pb2.BOOLEAN, "level": hannah_pb2.NUMERIC, "color": hannah_pb2.ENUM,
            },
            state_enum_values={
                "color": hannah_pb2.EnumValues(values={"warm": "Warmweiß", "kalt": "Kaltweiß"}),
            },
        )
        fenster = hannah_pb2.DeviceInfo(
            id="fenster.wz.open", name="Fenster", category="Fenster",
            states=["open"], current={"open": "false"},
            state_types={"open": hannah_pb2.BOOLEAN},
        )
        return [
            hannah_pb2.RoomInfo(key="wohnzimmer", name="Wohnzimmer", devices=[licht, fenster]),
        ]

    def get_satellites(self):
        result = []
        for device_id, sat in self._satellites.items():
            room_id = sat.get("room_id") or ""
            live_room = sat.get("live_room", "")
            owner_user_id = sat.get("owner_user_id") or 0
            owner = self._user_records.get(owner_user_id)
            result.append(hannah_pb2.Satellite(
                device_id=device_id,
                room=live_room,
                display_name=sat.get("display_name") or "",
                room_id=room_id,
                room_display_name=self._rooms.get(room_id, ""),
                last_seen=sat.get("last_seen") or "",
                connected=sat.get("connected", False),
                room_mismatch=sat.get("connected", False) and live_room != room_id,
                owner_user_id=owner_user_id,
                owner_display_name=owner["display_name"] if owner else "",
            ))
        return result

    def set_satellite_room(self, device_id, room_id, requestor_id):
        if device_id not in self._satellites:
            return False, "satellite not found"
        self._satellites[device_id]["room_id"] = room_id or ""
        return True, "updated"

    def set_satellite_display_name(self, device_id, display_name, requestor_id):
        if device_id not in self._satellites:
            return False, "satellite not found"
        self._satellites[device_id]["display_name"] = display_name
        return True, "updated"

    def set_satellite_owner(self, device_id, user_id, requestor_id):
        if device_id not in self._satellites:
            return False, "satellite not found"
        self._satellites[device_id]["owner_user_id"] = user_id or 0
        return True, "updated"

    def delete_satellite(self, device_id, requestor_id):
        return (True, "deleted") if self._satellites.pop(device_id, None) is not None else (False, "satellite not found")

    def get_settings(self):
        categories = [hannah_pb2.Category(id=cid, name=name) for cid, name in self._categories.items()]
        settings = [
            hannah_pb2.Setting(id=sid, category_id=s["category_id"], name=s["name"], value=json.dumps(s["value"]))
            for sid, s in self._settings.items()
        ]
        return categories, settings

    def update_setting(self, setting_id, value_json):
        if setting_id not in self._settings:
            return False, "setting not found"
        try:
            value = json.loads(value_json)
        except json.JSONDecodeError as e:
            return False, f"invalid JSON for setting {setting_id}: {e}"
        self._settings[setting_id]["value"] = value
        return True, "updated"

    def get_users(self, include_inactive=True):
        users = []
        for uid, u in self._user_records.items():
            if not include_inactive and not u["active"]:
                continue
            users.append(hannah_pb2.User(
                id=uid, user_name=u["user_name"], display_name=u["display_name"],
                trust_level=u["trust_level"], active=u["active"], system_messages=u["system_messages"],
                email=u["email"], type=u["type"], linked_accounts=u["linked_accounts"],
            ))
        return users

    def get_residents(self):
        return [
            hannah_pb2.Resident(id=rid, roomie_id=r["roomie_id"], display_name=r["display_name"], type=r["type"], home=r["home"])
            for rid, r in self._residents.items()
        ]

    def create_user(self, username, password, email, display_name, user_type):
        if any(u["user_name"] == username for u in self._user_records.values()):
            return False, "username oder email existiert bereits"
        user_id = self._next_user_id
        self._next_user_id += 1
        self._user_records[user_id] = {
            "user_name": username, "display_name": display_name or username, "email": email,
            "trust_level": 5, "active": True, "system_messages": False, "type": user_type or "roomie",
            "linked_accounts": {},
        }
        return True, "created"

    def update_user(self, user_id, display_name, email, user_type, is_active, password=""):
        if user_id not in self._user_records:
            return False, "User nicht gefunden."
        u = self._user_records[user_id]
        u["display_name"] = display_name.strip() or u["user_name"]
        u["email"] = email.strip() or u["email"]
        u["type"] = user_type or u["type"]
        u["active"] = bool(is_active)
        return True, "updated"

    def delete_user(self, user_id):
        return self._user_records.pop(user_id, None) is not None

    def set_trust_level(self, user_id, level):
        if user_id not in self._user_records:
            return False
        self._user_records[user_id]["trust_level"] = level
        return True

    def set_system_messages(self, user_id, enabled):
        if user_id not in self._user_records:
            return False
        self._user_records[user_id]["system_messages"] = bool(enabled)
        return True

    def link_account(self, user_id, service, account_id, provider_payload=""):
        if user_id not in self._user_records:
            return False
        self._user_records[user_id]["linked_accounts"][service] = account_id
        return True

    def unlink_account(self, user_id, service, requestor_id):
        if user_id not in self._user_records:
            return False
        self._user_records[user_id]["linked_accounts"].pop(service, None)
        return True

    def get_triggers(self):
        return [
            hannah_pb2.Trigger(
                id=tid, when_json=json.dumps(t["when"]),
                cancel_when_json=json.dumps(t["cancel_when"]) if t["cancel_when"] else "",
                on_response_json=json.dumps(t["on_response"]), actions_json=json.dumps(t["actions"]),
                say=t["say"], ask=t["ask"], rephrase=t["rephrase"], room=t["room"],
                cooldown=t["cooldown"], delay=t["delay"],
            )
            for tid, t in self._triggers.items()
        ]

    def create_trigger(self, trigger_id, when, cancel_when, on_response, actions, say, ask, rephrase, room, cooldown, delay):
        if trigger_id in self._triggers:
            return False, "id existiert bereits"
        self._triggers[trigger_id] = {
            "when": when, "cancel_when": cancel_when, "on_response": on_response, "actions": actions,
            "say": say, "ask": ask, "rephrase": rephrase, "room": room, "cooldown": cooldown, "delay": delay,
        }
        return True, "created"

    def update_trigger(self, trigger_id, when, cancel_when, on_response, actions, say, ask, rephrase, room, cooldown, delay):
        if trigger_id not in self._triggers:
            return False, "not found"
        self._triggers[trigger_id] = {
            "when": when, "cancel_when": cancel_when, "on_response": on_response, "actions": actions,
            "say": say, "ask": ask, "rephrase": rephrase, "room": room, "cooldown": cooldown, "delay": delay,
        }
        return True, "updated"

    def delete_trigger(self, trigger_id):
        return self._triggers.pop(trigger_id, None) is not None

    def get_alarms(self, user_id=None):
        alarms = [
            hannah_pb2.Alarm(
                id=aid, satellite_id=a["satellite_id"], time=a["time"], weekdays=a["weekdays"],
                skip_dates=a["skip_dates"], one_shot_date=a["one_shot_date"], enabled=a["enabled"],
                label=a["label"], user_id=a["user_id"],
            )
            for aid, a in self._alarms.items()
        ]
        if user_id is not None:
            alarms = [a for a in alarms if a.user_id == user_id]
        return alarms

    def create_alarm(self, satellite_id, time, weekdays, one_shot_date, label, user_id):
        alarm_id = self._next_alarm_id
        self._next_alarm_id += 1
        self._alarms[alarm_id] = {
            "satellite_id": satellite_id, "time": time, "weekdays": list(weekdays),
            "skip_dates": [], "one_shot_date": one_shot_date, "enabled": True,
            "label": label, "user_id": user_id,
        }
        return True, "created"

    def update_alarm(self, alarm_id, satellite_id, time, weekdays, skip_dates, one_shot_date, enabled, label):
        if alarm_id not in self._alarms:
            return False, "not found"
        self._alarms[alarm_id] = {
            "satellite_id": satellite_id, "time": time, "weekdays": list(weekdays),
            "skip_dates": list(skip_dates), "one_shot_date": one_shot_date, "enabled": enabled,
            "label": label, "user_id": self._alarms[alarm_id]["user_id"],
        }
        return True, "updated"

    def delete_alarm(self, alarm_id):
        return self._alarms.pop(alarm_id, None) is not None

    def get_ble_tags(self):
        return [
            hannah_pb2.BleTag(id=tid, mac_address=t["mac_address"], label=t["label"], user_id=t["user_id"])
            for tid, t in self._ble_tags.items()
        ]

    def create_ble_tag(self, mac_address, label, user_id):
        tag_id = self._next_ble_tag_id
        self._next_ble_tag_id += 1
        self._ble_tags[tag_id] = {"mac_address": mac_address, "label": label, "user_id": user_id}
        return True, "created"

    def update_ble_tag(self, tag_id, mac_address, label, user_id):
        if tag_id not in self._ble_tags:
            return False, "not found"
        self._ble_tags[tag_id] = {"mac_address": mac_address, "label": label, "user_id": user_id}
        return True, "updated"

    def delete_ble_tag(self, tag_id):
        return self._ble_tags.pop(tag_id, None) is not None

    def get_cars(self):
        return [
            hannah_pb2.Car(id=cid, topic_prefix=c["topic_prefix"], home_address=c["home_address"],
                            owner_user_ids=c["owner_user_ids"], name=c.get("name", ""))
            for cid, c in self._cars.items()
        ]

    def create_car(self, topic_prefix, home_address, owner_user_ids, name=""):
        car_id = self._next_car_id
        self._next_car_id += 1
        self._cars[car_id] = {
            "topic_prefix": topic_prefix, "home_address": home_address, "owner_user_ids": list(owner_user_ids),
            "name": name,
        }
        return True, "created"

    def update_car(self, car_id, topic_prefix, home_address, owner_user_ids, name=""):
        if car_id not in self._cars:
            return False, "not found"
        self._cars[car_id] = {
            "topic_prefix": topic_prefix, "home_address": home_address, "owner_user_ids": list(owner_user_ids),
            "name": name,
        }
        return True, "updated"

    def delete_car(self, car_id):
        return self._cars.pop(car_id, None) is not None
