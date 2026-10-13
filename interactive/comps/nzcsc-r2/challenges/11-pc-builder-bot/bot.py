import os
import time
import traceback

import requests
from playwright.sync_api import sync_playwright

WEB_URL = os.environ.get("WEB_URL", "https://web:5000")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "adminpass")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "bottoken")
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "10"))
VISIT_TIMEOUT_MS = int(os.environ.get("VISIT_TIMEOUT_MS", "8000"))

HEADERS = {"X-Bot-Token": BOT_TOKEN}


def get_pending():
    resp = requests.get(f"{WEB_URL}/internal/pending", headers=HEADERS, timeout=10, verify=False)
    resp.raise_for_status()
    return resp.json()


def review_one(playwright, req):
    browser = playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()

    try:
        page.goto(f"{WEB_URL}/login", timeout=VISIT_TIMEOUT_MS)
        page.fill('input[name="username"]', ADMIN_USERNAME)
        page.fill('input[name="password"]', ADMIN_PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle", timeout=VISIT_TIMEOUT_MS)
        page.goto(req["proof_url"], timeout=VISIT_TIMEOUT_MS)        
        page.wait_for_timeout(3000)

        page.goto(f"{WEB_URL}/dashboard", timeout=VISIT_TIMEOUT_MS)
        
    finally:
        page.evaluate(
                    """
                    async (reqId) => {
                        await fetch(`/review/${reqId}`, {
                            method: "POST",
                            headers: {"Content-Type": "application/x-www-form-urlencoded"},
                            body: "decision=deny",
                        });
                    }
                    """,
                    req["id"],
                )
        
        context.close()
        browser.close()


def main():
    print(f"[bot] starting, target={WEB_URL}", flush=True)
    with sync_playwright() as playwright:
        while True:
            try:
                pending = get_pending()
                for req in pending:
                    print(f"[bot] reviewing request #{req['id']} -> {req['proof_url']}", flush=True)
                    try:
                        review_one(playwright, req)
                    except Exception:
                        print(f"[bot] error visiting request #{req['id']}:", flush=True)
                        traceback.print_exc()
            except Exception:
                print("[bot] error polling pending requests:", flush=True)
                traceback.print_exc()

            time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()