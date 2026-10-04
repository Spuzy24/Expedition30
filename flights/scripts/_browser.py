"""Headless-Chromium helper (Playwright) for sites that need a real browser
(AWS-WAF / JS challenges): Aviasales, Booking.com flights, FlightConnections.

Usage:
    from _browser import browser_page
    with browser_page(capture=lambda url: "/api/" in url) as (page, captured):
        page.goto(url); ...; captured -> list of {"url", "status", "post", "json"}

Environment setup (Claude Code sandbox, tested 2026-10-04):
  * pip install playwright==1.56.0  (matches the preinstalled Chromium build 1194 in
    /opt/pw-browsers; do NOT run `playwright install`). Override the binary with
    PW_CHROMIUM=/path/to/chrome if a different Playwright version is used.
  * HTTPS goes through the agent proxy (HTTPS_PROXY). Chromium validates TLS with the NSS
    store, which must trust the proxy CA. If pages fail with ERR_CERT_AUTHORITY_INVALID run:
        apt-get install -y libnss3-tools
        certutil -A -d sql:$HOME/.pki/nssdb -n ccr-agent-proxy -t "C,," -i /root/.ccr/agent-proxy-ca.crt
    (this ADDS trust for the proxy CA; never disable certificate checking).
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
import time
from typing import Callable

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
CONSENT_SELECTORS = [
    "#onetrust-accept-btn-handler", "button:has-text('Accept all')", "button:has-text('Accept All')",
    "button:has-text('Accept')", "button:has-text('I agree')", "button:has-text('Agree')",
    "button:has-text('Allow all')", "button:has-text('OK')", "button:has-text('Got it')",
]


@contextlib.contextmanager
def browser_page(capture: Callable[[str], bool] | None = None, locale: str = "en-GB",
                 headless: bool = True, max_body: int = 8_000_000):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("playwright missing: pip install playwright==1.56.0")
    captured: list[dict] = []
    with sync_playwright() as p:
        kw = dict(headless=headless, args=["--disable-blink-features=AutomationControlled"])
        if os.environ.get("HTTPS_PROXY"):
            kw["proxy"] = {"server": os.environ["HTTPS_PROXY"]}
        if os.environ.get("PW_CHROMIUM"):
            kw["executable_path"] = os.environ["PW_CHROMIUM"]
        b = p.chromium.launch(**kw)
        ctx = b.new_context(user_agent=UA, viewport={"width": 1440, "height": 900},
                            locale=locale, timezone_id="Europe/Zagreb")
        ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
        page = ctx.new_page()

        def on_resp(r):
            if not capture or not capture(r.url):
                return
            rec = {"url": r.url, "status": r.status,
                   "post": (r.request.post_data_buffer or b"").decode("utf-8", "replace")}
            try:
                body = r.text()
                rec["json"] = json.loads(body) if len(body) < max_body else None
            except Exception:
                rec["json"] = None
            captured.append(rec)

        page.on("response", on_resp)
        try:
            yield page, captured
        finally:
            b.close()


def click_consent(page, tries: int = 1) -> bool:
    for _ in range(tries):
        for sel in CONSENT_SELECTORS:
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=300):
                    loc.click(timeout=2000)
                    return True
            except Exception:
                pass
        time.sleep(1)
    return False


def wait_until(pred: Callable[[], bool], timeout: float, step: float = 1.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        if pred():
            return True
        time.sleep(step)
    return False
