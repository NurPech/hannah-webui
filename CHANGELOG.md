# Changelog
<!--
    Placeholder for the next version (at the beginning of the line):
    ## **WORK IN PROGRESS**
-->

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
