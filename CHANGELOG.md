# Changelog

All notable changes are documented here, in the [Keep a Changelog](https://keepachangelog.com/) style, English only.

<!--
    Placeholder for the next version (at the beginning of the line):
    ## **WORK IN PROGRESS**

    ### Added
    - ...

    ### Changed
    - ...

    ### Fixed
    - ...

    ### Removed
    - ...

    Only include the categories actually used. Breaking changes get a
    `**BREAKING:**` prefix within their category. Every entry ends with `Refs #ID`.
-->


## 1.13.6
### Fixed
- `deploy/install.sh` was tracked in git without the executable bit — `curl | bash` worked regardless, but running the extracted script directly (e.g. `--uninstall`) failed with `Permission denied`.

## 1.13.5
### Fixed
- `deploy/install.sh` no longer hard-fails when `UPDATE_SERVER_TOKEN` is unset, same fix as Core.

### Added
- `deploy/install.sh` now checks it's running as root before attempting any privileged operation, instead of failing partway through with a confusing permission error

## 1.13.4
### Changed
- Trigger editor's "Wenn" label and a new hint under the days picker now explain that a time condition acts as an additional AND-gate over the rest of the (still OR-connected) "Wenn" group — previously implied everything was plain OR, which pointed users toward the "Und" block instead of just adding a second "Wenn" row. Refs #36

## 1.13.3
### Fixed
- "Und" condition on a trigger's time-type "Wenn" row was silently dropped instead of being sent to Core — `_attach_also_unless()` only attached it to conditions with a `state` key. Core now evaluates `also` for time conditions too (time acts as an additional AND-gate), so the webui no longer needs the restriction. Refs #35

## 1.13.2
### Fixed
- Trigger list showed a blank pill for phrase-only conditions (the former Routinen, e.g. `nachtlicht`/`gute_nacht`/`regenbogen`) — the pill template only handled `time`/`state`, not `phrase`. Now shows the quoted phrase, and a condition with no label at all no longer renders an empty pill. Refs #34

## 1.13.1
* Changed: CI now uses the shared `test-changelog` component from `hannah-components` instead of its own inline job — same discipline, now covers any source change instead of the previous fixed file pattern
* Changed: CI now uses the shared `upload-base`/`upload-notes` components from `hannah-components` instead of its own inline `upload` job's notes-upload block
* Changed: Trigger-Editor's "Dann"-Geräte-Dropdown blendet States aus, die laut `DeviceInfo.state_writable` (neu in `hannah-proto>=0.5.2`) nicht beschreibbar sind — z.B. Fenster-/Tür-/Temperatursensoren, die ohnehin nicht gesetzt werden können. "Wenn"/"Und"/"Außer wenn" zeigen weiterhin alle States, da nicht-schreibbare Sensoren dort als Bedingung sinnvoll sind. Refs #32

## 1.13.0
* **Breaking:** Routinen-Verwaltung (`/routines`) entfernt — Routinen und Trigger waren zwei separate Systeme mit stark überlappendem Aktionsmodell (siehe `gessinger/voice/hannah#139`). Core hat Routinen zugunsten eines neuen Trigger-Bedingungstyps `phrase` (Sprachphrase, Substring-Match) aufgelöst und die `GetRoutines`/`CreateRoutine`/`UpdateRoutine`/`DeleteRoutine`-RPCs entfernt. Bestehende Routinen migriert Core serverseitig in Trigger — kein WebUI-seitiger Migrationsschritt nötig. Refs #28
* Added: Trigger-Editor's "Wenn"-Zeilen bekommen einen dritten Bedingungstyp "Phrase" neben "Zustand"/"Uhrzeit" — deckt ab, was vorher die Routinen-Verwaltung konnte (gesprochener Text löst den Trigger aus, Actions/Und/Außer-wenn funktionieren unverändert mit). Refs #28
* Changed: Trigger-Editor's "Dann"-Zeilen bekommen die gleiche No-Code-Behandlung wie #16 — "Gerät setzen"-Aktionen nutzen jetzt die Geräte-Dropdown-Kette (Auslöser + typgefiltertes Wert-Widget, Freitext-Fallback) statt State-ID/Wert-Freitext, "Ansage"-Aktionen bekommen einen Raum-Dropdown (`GetRooms`) statt Freitext-Raum. Der Trigger-weite "Raum"-Dropdown (unten im Editor) wurde aus Konsistenzgründen ebenfalls auf denselben Dropdown umgestellt. "Dann"-Zeilen zeigen jetzt außerdem nur die zum gewählten Aktions-Typ passenden Felder (analog #29). Formularfeldnamen/Parsing unverändert. Refs #30

## 1.12.1
* Changed: Trigger-Editor's "Wenn"-Zeilen zeigen jetzt nur noch die Felder, die zum gewählten Typ passen — Geräte-Auslöser/Vergleich/Wert bei "Zustand", Uhrzeit/Tage bei "Uhrzeit" — statt immer alle gleichzeitig. Refs #29

## 1.12.0
* Added: Trigger-Editor's "Wenn"/"Und"/"Außer wenn"-Zustandsbedingungen bekommen eine Dropdown-Kette (Gerät → Vergleich → Wert) statt einer freien ioBroker-State-ID — Vergleichsoperatoren und Werteingabe passen sich clientseitig an den Typ des gewählten States an (Boolean → An/Aus, Numeric → Zahl + größer/kleiner, Enum/Color → Dropdown aus den erlaubten Werten). Der bisherige Freitext-Modus bleibt pro Zeile per Toggle erhalten (Fallback für States, die zu keinem bekannten Gerät gehören) und ist weiterhin das, was tatsächlich gespeichert wird — keine Änderung am `when`/`also`/`unless`-JSON-Format. Braucht `hannah-proto>=0.4.0` (`StateType`/`EnumValues` in `shared.proto`, `DeviceInfo.state_types`/`state_enum_values` in `device_control_menu.proto`). Refs #16

## 1.11.1
* Changed: proto stubs now come from the published [`hannah-proto`](https://pypi.org/project/hannah-proto/) package instead of the git-submodule/local-codegen pattern — `.gitmodules`, `proto/` submodule, `hannah_webui/proto/*` generated stubs and `scripts/gen_proto.sh` removed; imports moved from `hannah_webui.proto` to `hannah_proto`. Refs #27

## 1.11.0
* Changed: bumped `proto` submodule to v0.3.0 (adds the `PROTO_VERSION` file/CI gate upstream; no `.proto` schema changes). `gen_proto.sh` now also copies `proto/PROTO_VERSION` into `gen/hannah/PROTO_VERSION` for embedding (#4)
* Added: gRPC client interceptor attaches the current `PROTO_VERSION` as `x-proto-version` metadata on every outgoing call to Hannah, so a protocol version mismatch can be rejected at runtime (#4)

## 1.10.1
* Fix: on the Cars card, "Bearbeiten"/"Löschen" sat top-right next to the title and looked stranded whenever the home address wrapped to multiple lines, growing the card below them. Moved into their own footer row below the owner pills, with a divider — stays put regardless of text length. Refs #26

## 1.10.0
* Internal: `app.py` (1059 lines, every route as a nested function inside `create_app`) split into Flask Blueprints — one module per route group under `hannah_webui/blueprints/` (`auth`, `me`, `rooms`, `groups`, `satellites`, `settings`, `ble_tags`, `cars`, `routines`, `triggers`, `users`), plus `extensions.py` (`TRUST_LEVELS`, `login_required`/`trust_level_required`, `current_app`-based `hannah` access instead of closure capture) and `route_helpers.py` (the No-Code parsing/formatting helpers). `app.py` is now 93 lines. No user-visible change — endpoint names changed internally (e.g. `rooms` → `rooms.rooms`), all templates updated accordingly. Refs #10

## 1.9.4
* Changed: `proto/*.proto` replaced with a git submodule pointing to [hannah-proto](https://dev.kernstock.net/gessinger/voice/hannah-proto) (pinned to a release tag), instead of a manually synced copy. `scripts/gen_proto.sh` needs no path change — `proto/` is now the submodule itself, same location as before. Added `tests/test_proto_reexport.py`, a regression test walking every scope-split `*_pb2` module and asserting nothing is missing from `hannah_pb2` (Refs #24)

## 1.9.3
* Fix `scripts/gen_proto.sh` after Core split `hannah.proto` into multiple scope files (`proto/*.proto` synced from `gessinger/voice/hannah#44`): two quoting bugs left the glob unexpanded and broke stub generation entirely. Also ports Core's `hannah/proto/__init__.py` re-export patch to `hannah_webui/proto/__init__.py`, so `hannah_pb2.Car`/`hannah_pb2.User`/etc. keep working even though those messages now live in `control_pb2`/`user_registry_pb2`/etc. — no call sites in `app.py`/`grpc_client.py` needed to change. Refs #23

## 1.9.2
* Cars get their own `name` field instead of showing the technical `topic_prefix` (e.g. `javascript/0/virtualDevice/Auto/Leonie/Auto1`) as the card title — display name now on top, `topic_prefix` as a small mono line below. New name field in `car_edit.html` and the "New Car" form. Requires Core's new `Car.name` field (`proto/hannah.proto` synced, `gessinger/voice/hannah#123`). Refs #22

## 1.9.1
* Settings bekommen typspezifische No-Code-Editoren statt eines rohen JSON-Textareas: der Render-Typ wird rein clientseitig aus der Form des JSON-decodierten Werts abgeleitet (kein neues Core-Feld) — ein String wird zum Text-Editor mit echten Zeilenumbrüchen (behebt das kaputte `\n`-Escaping bei `llm.system_prompt`), eine Liste von Strings zum Zeilen-Builder (`nlu.*`), ein Objekt mit String-Values zum Key-Value-Grid (`iobroker.state_names`). Alles andere fällt weiterhin auf das rohe JSON-Textarea zurück ("Erweitert"). Refs #21

## 1.9.0
* Responsive Design (Teil 1): `/rooms`, `/users` und `/ble-tags` zeigen auf Mobile jetzt gestapelte Karten statt der breiten Tabelle (`hidden sm:table` / `sm:hidden` Dual-View, kein JS). `/groups` und `/cars` waren als Card-Grid bereits responsive. Satelliten/Routinen/Trigger/Settings folgen in eigenen Tickets. Refs #19
* Responsive Design (Teil 2): `/satellites` bekommt das gleiche Dual-View — letzte verbliebene Tabelle mit mehreren Inline-Forms pro Zeile (Anzeigename, Raum, Besitzer). Routinen, Trigger und Settings sind bereits Card-basiert und brauchen aktuell keine Anpassung. Refs #20

## 1.8.1
* Friendly error pages instead of Flask's default 500: an unreachable Hannah Core (`grpc.RpcError`) now renders a dark-theme "Core nicht erreichbar" page (503), unknown routes get a themed 404, and any other unhandled exception gets a generic 500 page instead of a raw traceback/default error text. Also fixes `HannahClient.login()` swallowing `grpc.RpcError` into a misleading "Ungültige Zugangsdaten" — Core being down now shows the "not reachable" page instead of looking like a wrong password. Refs #18

## 1.8.0
* Fix: the alarm creation form on `/me` (#13) offered an "Alle" (all satellites) option for the satellite dropdown — Core's `CreateAlarm` RPC requires a concrete `satellite_id` and rejects that. Dropdown is now required with no empty option; `create_alarm()` also validates server-side since the browser's `required` isn't the only line of defense. Refs #15
* BLE-Tags and Cars get their own admin pages (`/ble-tags`, `/cars`) instead of the generic Settings JSON-textarea, backed by Core's new dedicated models (Core #115): `GetBleTags`/`CreateBleTag`/`UpdateBleTag`/`DeleteBleTag` and `GetCars`/`CreateCar`/`UpdateCar`/`DeleteCar`. BLE-Tags are a single-page row list (MAC/label/owner); Cars are a card list + a dedicated edit page for the owner checkboxes (`owner_user_ids` is a list). Both admin-only (trust level 10), same as Settings. **Breaking (internal only):** `CreateSetting`/`DeleteSetting` were removed from Core along with this — the generic "create a new setting" and "delete a setting" UI in `/settings` is gone, since `ble.tags`/`cars` were the only settings ever created/deleted that way; the remaining settings (`nlu`, `iobroker.state_names`, `llm.system_prompt`) are always pre-seeded. Refs #12

## 1.7.1
* The WebUI now knows its own version: CI stamps a `VERSION` file at build time (both the Docker image and the systemd tarball, next to `main.py`) instead of committing it to git history — `release.js` bumps the changelog before the tag exists, so it can't be the source of truth. New `/version` JSON endpoint and a small version badge next to the "Hannah" logo in the header; local dev without a CI-stamped file shows "dev". Refs #14

## 1.7.0
* CI: new `test:changelog` job fails MR pipelines that touch `hannah_webui/`, `proto/`, or the deploy/entrypoint files without also touching `CHANGELOG.md` — enforces git workflow rule 2 (CLAUDE.md) instead of relying on remembering it.
* Alarm/Wecker management: `/me` now has a third card listing the logged-in user's own alarms (time, weekdays or one-off date, label, satellite, enable/disable toggle, delete) plus a form to create new ones (one-off vs. recurring), backed by the new `GetAlarms`/`CreateAlarm`/`UpdateAlarm`/`DeleteAlarm` RPCs (Core #4). Personal data scoped to `session['user_id']` like the rest of `/me` — no trust-level gate, no new nav entry. Refs #13

## 1.6.2
* Fix: `oauth.telegram.org`'s link-based auth flow (introduced in 1.6.1) appends the signed result as a URL fragment (`#tgAuthResult=...`), not a query string — fragments never reach the server, so every Telegram (re-)linking failed with "ungültige oder abgelaufene Signatur." `/me` now has a small inline script that decodes the fragment client-side and forwards it to the callback as a proper query string. Refs #11

## 1.6.1
* Fix: the Telegram Login Widget's `data-auth-url` rendered as `http://` instead of `https://` in production (gunicorn behind a TLS-terminating reverse proxy, no `ProxyFix`/`X-Forwarded-Proto` handling) — Telegram silently rejects non-HTTPS auth-urls for public domains, so linking looked like it worked but never actually called back. Forces `https` explicitly on that one URL now. Refs #9
* `/me`'s password-change and linked-accounts cards moved into a two-column grid instead of full-width stacked cards; password inputs no longer stretch edge to edge. Replaced the default Telegram Login Widget (a cross-origin iframe with no color control) with Telegram's link-based auth flow (`oauth.telegram.org/auth`) so the trigger button can be styled to match the dark theme. Refs #7

## 1.6.0
* Account linking: `/me` now has a "Verknüpfte Konten" section to link/unlink a Telegram account via the [Telegram Login Widget](https://core.telegram.org/widgets/login). The WebUI verifies the HMAC signature itself (new `telegram_bot_token`/`telegram_bot_username` config) and only reports the already-verified `account_id` to Core via `LinkAccount` — replaces the insecure bot-side `/verknuepfen <name>` trust model (gessinger/voice/hannah#70) for Telegram. Refs #7

## 1.5.0
* New `/me` page replaces the old index page as the logged-in landing page: greeting plus self-service password change (`/me/password`), no trust-level gate — only affects the logged-in user's own account. `/` now redirects to `/me`. First step towards hosting account-linking (Telegram/OAuth) there too. Refs #8

## 1.4.0
* Role-based access control: pages and actions are now gated by the logged-in user's `trust_level`. Regular users (trust ≥ 5) see Index, Rooms, Routines and Triggers (editing routines/triggers requires trust ≥ 7); everything else (Groups, Settings, Users, satellite ownership/deletion) requires trust ≥ 10 ("Admin"). Nav links and list/detail action buttons are hidden client-side to match; enforcement itself is server-side via a new `trust_level_required` decorator. Refs #6
* Satellites: regular users (trust ≥ 5) can now open the Satellites page, but only see satellites they own and can only reassign the room — deleting a satellite or changing its owner still requires trust ≥ 10. `SetSatelliteRoom`/`SetSatelliteDisplayName`/`SetSatelliteOwner`/`DeleteSatellite` now send a `requestor_id`, validated against ownership/trust-level by Core. Refs #6

## 1.3.1
* Adjust page width for better alignment

## 1.3.0
* Satellite management: delete a satellite from the database — new "Löschen" button (with confirmation dialog) in `satellites.html`, backed by the new `DeleteSatellite` RPC. Flash message on success/failure. Refs #5

## 1.2.0
* Satellite management: assign a satellite to a Person (User) as its owner, independent of its room — new "Besitzer" dropdown in `satellites.html`, backed by the new `SetSatelliteOwner` RPC (Core #31). Refs #4

## 1.1.1
* Delete links (`Löschen`) in `groups.html`, `routines.html`, `triggers.html` and `users.html` are now red by default instead of only on hover, for better visibility.
* Trigger editor: the "Tage" field of a "Wenn"-row (Uhrzeit type) is now a checkbox group (Montag–Sonntag) instead of a comma-separated text input — easier and more reliable on mobile. Form contract unchanged (still submits `when_days` as a comma-joined string via a small JS sync), no backend changes. Refs #3

## 1.1.0
* Redesigned `base.html` and `settings.html` with a dark-theme Tailwind look (CDN, no build step) instead of Bootstrap 5, modeled on the Hannah Update Server UI. First template migrated as part of the broader redesign; remaining templates still use Bootstrap until migrated. Refs #1
* Redesigned `rooms.html` with the same dark-theme Tailwind look. Refs #1
* Redesigned `satellites.html` with the same dark-theme Tailwind look. Refs #1
* Redesigned `groups.html` and `group_edit.html` with the same dark-theme Tailwind look. Refs #1
* Redesigned `login.html` and `index.html` with the same dark-theme Tailwind look. Refs #1
* Redesigned `users.html`, `user_create.html` and `user_edit.html` with the same dark-theme Tailwind look. Refs #1
* Redesigned `routines.html`, `routine_edit.html`, `triggers.html` and `trigger_edit.html` with the same dark-theme Tailwind look — last templates of the redesign. Refs #1
* Extracted the pill/badge markup into a `pill()` Jinja macro (`_macros.html`), used by `rooms.html`, `groups.html`, `users.html`, `routines.html` and `triggers.html` instead of copy-pasted markup. Closes #1

## 1.0.0
* Extracted from the Hannah monorepo (`gessinger/voice/hannah`, directory `webui/`) into its own repository — no functional changes. History before this point (the WebUI service skeleton from #27 through v0.46.1) lives in the monorepo's `CHANGELOG.md`. Refs gessinger/voice/hannah#106
* Added: Docker image build (Kaniko, multi-arch amd64/arm64) pushed to this repo's own Container Registry, as an alternative deployment path alongside the existing systemd/`install.sh` flow. No auto-update for the container path — versioning happens via the image tag. Refs gessinger/voice/hannah#105
