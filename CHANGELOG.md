# Changelog
<!--
    Placeholder for the next version (at the beginning of the line):
    ## **WORK IN PROGRESS**
-->


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
