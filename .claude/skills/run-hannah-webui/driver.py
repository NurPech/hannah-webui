"""Playwright driver for hannah-webui — logs in and walks the admin nav, screenshotting
each page. Requires a server already running: either serve_fake.py (fake backend) or
main.py against a real config.yaml (live Hannah Core) — see SKILL.md for both.

Usage:
    venv/Scripts/python .claude/skills/run-hannah-webui/driver.py [--base-url http://127.0.0.1:5099]
                                                                    [--user admin] [--password admin]
                                                                    [--read-only]

--user/--password default to the HANNAH_WEBUI_DRIVER_USER / HANNAH_WEBUI_DRIVER_PASSWORD
env vars if set, else "admin"/"admin" (the seeded fake-backend admin login).

--read-only skips the create/delete-group write flow at the end — use this against a
live Hannah Core so the driver never mutates real data, only screenshots existing pages.

Screenshots land in .claude/skills/run-hannah-webui/screenshots/, numbered in click order.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

SHOT_DIR = Path(__file__).resolve().parent / "screenshots"

# path -> (screenshot filename, nav link text used to reach it — None for direct nav)
PAGES = [
    ("/me", "00_me.png"),
    ("/rooms", "01_rooms.png"),
    ("/groups", "02_groups.png"),
    ("/satellites", "03_satellites.png"),
    ("/settings", "04_settings.png"),
    ("/triggers", "05_triggers.png"),
    ("/users", "06_users.png"),
]


def run(base_url: str, username: str, password: str, read_only: bool) -> None:
    SHOT_DIR.mkdir(exist_ok=True)
    errors: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        page.goto(f"{base_url}/login")
        page.fill("input[name=username]", username)
        page.fill("input[name=password]", password)
        page.click("button[type=submit]")
        page.wait_for_url(f"{base_url}/me")

        denied = []
        for path, filename in PAGES:
            expected_url = f"{base_url}{path}"
            page.goto(expected_url)
            page.wait_for_load_state("networkidle")
            page.screenshot(path=str(SHOT_DIR / filename), full_page=True)
            if page.url != expected_url:
                # trust_level_required() bounces to /me with a flash instead of a 403 —
                # the screenshot exists but shows the access-denied /me page, not `path`.
                denied.append(path)
                print(f"{path} -> {filename}  ACCESS DENIED (redirected to {page.url}, logged-in user's trust level is too low for this page)")
            else:
                print(f"{path} -> {filename}")

        if read_only:
            print("--read-only: skipping create/delete-group write flow")
        else:
            # one representative write path: create a group, see it appear, delete it again
            page.goto(f"{base_url}/groups")
            page.fill("input[name=display_name]", "Testgruppe")
            page.click("button:has-text('Anlegen')")
            page.wait_for_load_state("networkidle")
            assert page.locator("text=Testgruppe").count() > 0, "created group not shown in list"
            page.screenshot(path=str(SHOT_DIR / "07_group_created.png"), full_page=True)

            page.once("dialog", lambda dialog: dialog.accept())
            card = page.locator("div.rounded-xl", has_text="Testgruppe")
            card.locator("button:has-text('Löschen')").click()
            page.wait_for_load_state("networkidle")
            assert page.locator("text=Testgruppe").count() == 0, "group still present after delete"
            page.screenshot(path=str(SHOT_DIR / "08_group_deleted.png"), full_page=True)

        browser.close()

    if denied:
        print(f"NOTE: {len(denied)}/{len(PAGES)} page(s) were access-denied for this login, not actually rendered: {', '.join(denied)}")
        print("Use an account with trust_level 10 (see hannah_webui/app.py TRUST_LEVELS) to see them.")

    if errors:
        print("CONSOLE ERRORS:")
        for e in errors:
            print(" -", e)
    else:
        print("No console errors.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5099")
    parser.add_argument("--user", default=os.environ.get("HANNAH_WEBUI_DRIVER_USER", "admin"))
    parser.add_argument("--password", default=os.environ.get("HANNAH_WEBUI_DRIVER_PASSWORD", "admin"))
    parser.add_argument("--read-only", action="store_true")
    args = parser.parse_args()
    run(args.base_url, args.user, args.password, args.read_only)
