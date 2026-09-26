# -*- coding: utf-8 -*-
import asyncio
import os
from flask import Flask, request, jsonify
from playwright.async_api import async_playwright

app = Flask(__name__)

API_KEY = "vanta-ff-2026-secret"

BROWSER = None
PLAYWRIGHT = None

async def start_browser():
    global BROWSER, PLAYWRIGHT
    if BROWSER is not None:
        return BROWSER
    PLAYWRIGHT = await async_playwright().start()
    BROWSER = await PLAYWRIGHT.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-gpu",
        ]
    )
    return BROWSER

async def do_send(email):
    browser = await start_browser()
    ctx = await browser.new_context(
        user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36",
        viewport={"width": 393, "height": 873},
        locale="en-US",
    )
    page = await ctx.new_page()
    try:
        await page.goto(
            "https://sso.garena.com/universal/register?locale=en-US&app_id=100067",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        await page.wait_for_timeout(3000)

        selectors = [
            'input[name="email"]',
            'input[type="email"]',
            'input[placeholder*="mail"]',
            'input[placeholder*="Mail"]',
            'input[placeholder*="Email"]',
        ]
        filled = False
        for sel in selectors:
            try:
                await page.wait_for_selector(sel, timeout=5000)
                await page.fill(sel, email)
                filled = True
                break
            except:
                continue

        if not filled:
            return {"ok": False, "reason": "no_email_field"}

        buttons = [
            'button:has-text("Send")',
            'button:has-text("Continue")',
            'button:has-text("Next")',
            'button:has-text("Submit")',
            'button[type="submit"]',
        ]
        clicked = False
        for bsel in buttons:
            try:
                await page.click(bsel, timeout=3000)
                clicked = True
                break
            except:
                continue

        if not clicked:
            try:
                await page.keyboard.press("Enter")
                clicked = True
            except:
                pass

        await page.wait_for_timeout(5000)
        html = (await page.content()).lower()
        url_after = page.url.lower()

        if "too many" in html or "rate" in html:
            return {"ok": False, "reason": "429"}
        if "error" in html and "invalid" in html:
            return {"ok": False, "reason": "invalid_email"}
        if "sent" in html or "success" in html or "verify" in html:
            return {"ok": True, "reason": "sent"}
        if "code" in html or "otp" in html:
            return {"ok": True, "reason": "otp_page"}

        return {"ok": False, "reason": "unknown", "url": url_after}
    except Exception as e:
        return {"ok": False, "reason": "err", "msg": str(e)[:120]}
    finally:
        await ctx.close()

@app.route("/send", methods=["POST"])
def send():
    data = request.get_json() or {}
    if data.get("key") != API_KEY:
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    email = data.get("email", "").strip()
    if not email or "@" not in email:
        return jsonify({"ok": False, "error": "invalid_email"}), 400
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(do_send(email))
    return jsonify(result)

@app.route("/", methods=["GET"])
def home():
    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
