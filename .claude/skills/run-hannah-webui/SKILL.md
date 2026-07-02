---
name: run-hannah-webui
description: Build, run, and drive hannah-webui (the Flask admin UI for Hannah Core). Use when asked to start hannah-webui, run its tests, take a screenshot of a page, or verify a UI change works end-to-end — without needing a real Hannah Core gRPC backend.
---

hannah-webui is a server-rendered Flask app (Jinja2 + Tailwind CDN, no
SPA framework) that normally talks to Hannah Core over gRPC. There is
no real Core in this environment, so the driver boots the app against
`tests/fake_hannah_client.py` (the same in-memory stand-in the test
suite uses) on a real HTTP port, then drives it with Playwright.
Drive it via `.claude/skills/run-hannah-webui/driver.py`.

All paths below are relative to the repo root.

## Setup

```sh
python -m venv venv
venv/Scripts/pip install -r requirements.txt -r tests/requirements-test.txt
venv/Scripts/pip install playwright
venv/Scripts/python -m playwright install chromium
```

No `config.yaml` needed for the agent path — `serve_fake.py` builds
the app directly with `create_app()`, bypassing `main.py`/`config.py`
and the real gRPC connection entirely.

## Run (agent path)

1. Start the fake-backed dev server in the background and wait for it
   to answer:

   ```sh
   venv/Scripts/python .claude/skills/run-hannah-webui/serve_fake.py --port 5099 > /tmp/webui_serve.log 2>&1 &
   timeout 30 bash -c 'until curl -sf http://127.0.0.1:5099/login >/dev/null; do sleep 1; done'
   ```

2. Drive it:

   ```sh
   venv/Scripts/python .claude/skills/run-hannah-webui/driver.py --base-url http://127.0.0.1:5099
   ```

   This logs in as `admin`/`admin` (trust_level 10, sees every nav
   item), screenshots all eight main pages, then does one real write
   flow — create a group via the form, assert it appears, delete it,
   assert it's gone — and prints any browser console errors.
   Screenshots land in `.claude/skills/run-hannah-webui/screenshots/`,
   numbered in click order (`00_me.png` … `09_group_deleted.png`).

3. Stop the server. **On Windows, `kill $(cat pid)` from Git Bash does
   not reach the real `python.exe` process** (see Gotchas) — use
   `taskkill`:

   ```sh
   tasklist //FI "IMAGENAME eq python.exe"
   taskkill //F //PID <pid-from-above>
   ```

   On Linux/macOS, plain `kill $(cat /tmp/webui_serve.pid)` works.

Other logins: `claude`/`claude` (trust_level 7 — a regular roomie, no
admin nav items). Both come from `tests/fake_hannah_client.py`.

To hit a single page manually without the full driver script:

```sh
curl -s -c /tmp/c.txt -b /tmp/c.txt -X POST http://127.0.0.1:5099/login -d "username=admin&password=admin"
curl -s -b /tmp/c.txt http://127.0.0.1:5099/groups
```

## Run (agent path) — against a real Hannah Core

Same driver, but the server is started with `main.py` (the real
entrypoint) against a `config.yaml` pointing at a live Hannah Core
instead of `serve_fake.py`. Verified working end-to-end in this
session against the real Core at `192.168.8.69:50051` — login and
gRPC round-trip confirmed against real household data (`/rooms`
showed real room names, not the fake seed data).

**Which pages actually render depends on the logged-in user's
`trust_level`** (`TRUST_LEVELS` in `hannah_webui/app.py`) — routes
below the threshold don't 403, they redirect to `/me` with a "Zugriff
verweigert" flash. The driver now detects this (compares the URL
after `goto()` to the URL it asked for) and prints `ACCESS DENIED` per
page plus a summary — don't assume 8/8 "successful" screenshots
means 8 distinct pages actually rendered; check the driver's own
output. In this session's live test, the `claude` login (trust 7)
correctly got `/groups`, `/settings`, `/users` bounced (those need
trust_level 10) while `/me`, `/rooms`, `/satellites`, `/routines`,
`/triggers` rendered for real.

1. Create `config.yaml` in the repo root (gitignored, never commit
   it — see `config.example.yaml` for the shape) with the real
   `grpc.host`/`grpc.port` and a stable `secret_key`. Note: `host`/
   `port` in `config.yaml` are the WebUI's own bind address — not
   necessarily `5000`, check what's actually in the file. Login
   credentials are **not** stored there — they're real user
   credentials on your Hannah Core, entered per-run (see step 3).

2. Start the app against it and wait for it to answer — check the
   actual `port:` value in `config.yaml` first (it's whatever the
   file says, e.g. `5050`, not necessarily the `5000` default from
   `config.example.yaml`):

   ```sh
   venv/Scripts/python main.py --config config.yaml > /tmp/webui_live.log 2>&1 &
   timeout 30 bash -c 'until curl -sf http://127.0.0.1:<port-from-config.yaml>/login >/dev/null; do sleep 1; done'
   ```

   The log line `gRPC channel to Hannah at <host>:<port> created`
   confirms the channel was built (not that Core is reachable — gRPC
   channels connect lazily). If the curl poll times out, it's more
   likely no route to Core than a WebUI bug — check
   `grpc.host:grpc.port` reachability first, e.g.
   `timeout 5 bash -c 'exec 3<>/dev/tcp/<grpc.host>/<grpc.port> && echo CONNECTED'`.

3. Drive it **read-only** — never run the default write flow against
   real data:

   ```sh
   export HANNAH_WEBUI_DRIVER_USER=<a real username on your Hannah Core>
   export HANNAH_WEBUI_DRIVER_PASSWORD=<their password>
   venv/Scripts/python .claude/skills/run-hannah-webui/driver.py --base-url http://127.0.0.1:<port-from-config.yaml> --read-only
   ```

   `--read-only` skips the create/delete-group flow — it only logs in
   and screenshots the eight pages listed above.

4. **Screenshots now contain real household data** (residents, room
   names, satellite device IDs, users) — treat
   `.claude/skills/run-hannah-webui/screenshots/` as sensitive, don't
   paste its contents anywhere outside this conversation without
   checking first. It's already gitignored (see below), so it won't
   land in a commit.

5. Stop the same way as the fake-backend server (`tasklist` /
   `taskkill` — see below).

Wrong username/password and "can't reach Core" look identical from
the browser: `HannahClient.login()` catches `grpc.RpcError` and
returns "not found," which the login page renders as the same
"Ungültige Zugangsdaten." as a wrong password. If login fails
immediately after starting the server, suspect connectivity before
suspecting the credentials.

## Run (human path)

`python main.py` needs a real Hannah Core gRPC endpoint (`config.yaml`
→ `grpc.host`/`grpc.port`, default `127.0.0.1:50051`) — same command
as the live agent path above, just opened in a browser instead of
driven by Playwright.

## Test

```sh
venv/Scripts/python -m pytest tests/ -v
```

53 tests pass against `FakeHannahClient`, no network/Core needed —
this is the fastest way to check route/template logic without going
through Playwright at all.

## Gotchas

- **`kill $(cat pidfile)` doesn't stop the server on Windows.** Git
  Bash's `&`/`$!` capture a bash job number, not the actual
  `python.exe` PID launched under MSYS. Find the real PID with
  `tasklist //FI "IMAGENAME eq python.exe"` and `taskkill //F //PID
  <pid>` instead.
- **Tailwind loads from `cdn.tailwindcss.com`** (see `base.html`) — if
  the environment has no outbound internet, pages render unstyled
  (still functionally testable, just ugly in screenshots).
- **`create_app()` takes the fake client directly** — don't route
  through `main.py`/`config.py` for the fake-backend path. `main.py`
  needs a `config.yaml` and every route that touches Hannah data will
  fail (or hang until gRPC's deadline) without a reachable Core behind
  it — fine for the live path, pointless overhead for the fake one.
- **`FakeHannahClient` is stateful and shared for the process
  lifetime** of `serve_fake.py`. The driver's group-create/delete flow
  cleans up after itself; if you add new write-flow checks, delete
  what you created or restart `serve_fake.py` between driver runs to
  get a clean slate (`tests/fake_hannah_client.py` reseeds one
  `erdgeschoss` group, one `kueche-esp` satellite, etc. — see its
  `__init__`).
- **A "successful" screenshot doesn't mean the real page rendered.**
  `trust_level_required()` (`hannah_webui/app.py`) redirects
  under-privileged users to `/me` instead of returning a 403 — `goto()`
  + `screenshot()` both "succeed" on the bounce page. Only trust with
  the `admin`/`admin` fake login (trust 10) or a real trust-10 account;
  otherwise check the driver's `ACCESS DENIED` output before trusting
  a screenshot's filename.
