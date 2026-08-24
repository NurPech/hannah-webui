# Nutzung

Login mit dem eigenen Hannah-Core-Account (Username + Passwort). Was danach sichtbar ist, hängt vom **Trust-Level** des Accounts ab (von einem Admin in der [User-Verwaltung](#user-verwaltung-users--ab-trust-level-10) gesetzt) — Self-Service-Seiten (`/me`, `/messages`, `/activity-log` ohne Filter) sind für jeden eingeloggten User offen, alles andere gestaffelt.

Kurzüberblick als Tabelle: siehe [README](../README.md#seiten-übersicht--berechtigungen). Hier die Langfassung je Seite.

---

## Self-Service (`/me`) — für jeden

Ersetzt die alte Index-Seite, wirkt nur auf den eigenen Account:

- **Passwort ändern**
- **Telegram verknüpfen** — Button startet das [Telegram Login Widget](https://core.telegram.org/widgets/login); Voraussetzung ist ein in der Config hinterlegter Bot, der beim [@BotFather](https://t.me/BotFather) per `/setdomain` auf diese WebUI-Domain freigeschaltet ist (Admin-Aufgabe, siehe [README](../README.md#konfiguration)). Trennen jederzeit möglich.
- **Wecker** — Uhrzeit + Satellit sind Pflicht (ein Wecker klingelt immer auf genau einem Satelliten, nie auf allen gleichzeitig), dazu wahlweise einmalig (Datum) oder wiederkehrend (Wochentage), optionales Label. Einzeln an-/ausschaltbar und löschbar.

## Nachrichten (`/messages`)

Passive Mailbox für Nutzer-zu-Nutzer-Nachrichten:

- Liste der eigenen Nachrichten (empfangen + selbst gesendet), neueste zuerst; Absendername oder „System" bei automatischen Nachrichten
- Antworten geht nur bei Nachrichten mit echtem Absender, nicht bei System-Benachrichtigungen
- Neue Nachricht an einen beliebigen aktiven User senden
- Einzeln löschen
- Die Navigation zeigt einen Badge mit der Anzahl offener Nachrichten

Der Absender bekommt aktuell keine Kopie der eigenen gesendeten Nachricht — das ist eine Inbox-Sicht, kein vollständiger beidseitiger Chat-Verlauf.

## Verlauf (`/activity-log`)

Eigene geloggte Interaktionen: Transkript, aufgelöster Kanal (z. B. welcher Satellit oder Telegram), erkannter Intent, Antworttext. Cursor-basierte Pagination (vor **und** zurück), Audio-Wiedergabe inline wo vorhanden.

Ab Trust-Level 10: Filter, um den Verlauf eines anderen Users einzusehen.

## Räume (`/rooms`) — ab Trust-Level 3

Read-only Liste aller Räume.

## Satelliten (`/satellites`) — ab Trust-Level 5

- Satellit einem Raum zuordnen, Anzeigenamen setzen
- FollowUp-Listening (ob der Satellit nach einer Smalltalk-Antwort automatisch auf eine Folgefrage lauscht) togglen
- Unterhalb Trust-Level 10 sieht man nur den eigenen Satelliten (per Besitzer-Zuweisung), ab Trust-Level 10 alle
- Ab Trust-Level 10 zusätzlich: Besitzer zuweisen, Firmware-Update anstoßen, Satellit löschen

## Gruppen (`/groups`) — ab Trust-Level 10

Gruppen anlegen (Anzeigename → automatisch daraus abgeleitete ID), bearbeiten, löschen. Beim Bearbeiten werden der Gruppe direkt Satelliten zugewiesen (seit v2.0.0 — vorher Räume).

## Trigger (`/triggers`) — Anzeigen ab Trust-Level 5, Anlegen/Bearbeiten/Löschen ab Trust-Level 7

Wenn/Und/Außer-wenn/Dann-Regelbuilder, löste die frühere separate Routinen-Verwaltung ab:

- **Wenn** — eine oder mehrere Bedingungen (ODER-verknüpft), Typ `state` (Gerätezustand), `time` (Uhrzeit) oder `phrase` (Sprachphrase-Substring-Match)
- **Und** — zusätzliche Zustandsbedingungen (UND/ODER wählbar), die parallel erfüllt sein müssen
- **Außer wenn** — Ausschlussbedingungen; der Trigger feuert nicht, wenn eine davon zutrifft
- **Dann** — eine oder mehrere Aktionen auf schreibbaren Geräten

Dazu konfigurierbar: Rückfrage („Ask"), Raum-Scope, Cooldown (Sekunden, Default 3600), Delay. Ein „Erweitert"-Feld nimmt rohes JSON für komplexere Antwortregeln (`on_response_json`) entgegen.

## Settings (`/settings`) — ab Trust-Level 10

Kein JSON-Textfeld, sondern No-Code-Editor: der Render-Typ pro Setting wird automatisch aus der Form des aktuellen Werts abgeleitet — String → Text-Editor mit echten Zeilenumbrüchen, Liste → Zeilen-Builder, Objekt → Key-Value-Grid, alles andere → rohes JSON als „Erweitert".

## BLE-Tags (`/ble-tags`) — ab Trust-Level 10

CRUD: MAC-Adresse (Pflicht), Label, optional einem User zugewiesen.

## Fahrzeuge (`/cars`) — ab Trust-Level 10

CRUD: MQTT-Topic-Prefix (Pflicht), Name, Heimatadresse, mehrere Besitzer zuweisbar.

## User-Verwaltung (`/users`) — ab Trust-Level 10

- User anlegen (Username, Passwort, E-Mail Pflicht, Typ z. B. „roomie"), bearbeiten, aktivieren/deaktivieren
- **Trust-Level setzen** — steuert den Zugriff auf alle oben genannten Admin-Seiten
- System-Nachrichten an-/abschalten
- Mit einem Resident verknüpfen/trennen (Resident = Core-seitige Bewohner-Identität, z. B. relevant für Sprechererkennung)
