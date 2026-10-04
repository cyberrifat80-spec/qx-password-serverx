import os
import time
import secrets
import string
import hmac
import hashlib
import base64
import requests

from flask import Flask, request, jsonify


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.environ["8850298235:AAHN7H6OKapbqPby6uHUL5XHHGnXkAou4PI"]

SERVER_SECRET = os.environ["QX9x7K2mP8v4R6t1Z3n5"]

PUBLIC_URL = os.environ["PUBLIC_URL"].rstrip("/")

ADMIN_ID = os.environ.get("7130116597", "")


app = Flask(__name__)


# =========================================================
# PASSWORD SYSTEM
# =========================================================

def make_password():

    random_part = "".join(
        secrets.choice(
            string.ascii_uppercase + string.digits
        )
        for _ in range(10)
    )

    expires = int(time.time()) + 86400

    payload = f"{random_part}|{expires}"

    signature = hmac.new(
        SERVER_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()[:16]

    raw = f"{payload}|{signature}"

    encoded = base64.urlsafe_b64encode(
        raw.encode()
    ).decode().rstrip("=")

    return "QX-" + encoded


def verify_password(password):

    if not password.startswith("QX-"):
        return False

    try:

        encoded = password[3:]

        encoded += "=" * (
            4 - len(encoded) % 4
        ) % 4

        raw = base64.urlsafe_b64decode(
            encoded
        ).decode()

        random_part, expires, signature = raw.split("|")

        expires = int(expires)

        if time.time() > expires:
            return False

        payload = f"{random_part}|{expires}"

        expected = hmac.new(
            SERVER_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()[:16]

        return hmac.compare_digest(
            signature,
            expected
        )

    except Exception:

        return False


# =========================================================
# TELEGRAM
# =========================================================

def telegram(method, data):

    url = (
        "https://api.telegram.org/"
        f"bot{BOT_TOKEN}/{method}"
    )

    return requests.post(
        url,
        json=data,
        timeout=20
    )


def send_message(chat_id, text):

    telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text
        }
    )


# =========================================================
# TELEGRAM WEBHOOK
# =========================================================

@app.post("/telegram")
def telegram_webhook():

    update = request.get_json(silent=True) or {}

    message = update.get("message", {})

    chat = message.get("chat", {})

    chat_id = chat.get("id")

    text = message.get("text", "").strip()

    if not chat_id:
        return jsonify(ok=True)


    # -----------------------------------------------
    # START
    # -----------------------------------------------

    if text == "/start":

        send_message(
            chat_id,
            "🔐 QX ACCESS BOT\n\n"
            "/newpass - Generate 24H password\n"
            "/status - Check bot status\n"
            "/id - Show your Telegram ID"
        )


    # -----------------------------------------------
    # TELEGRAM ID
    # -----------------------------------------------

    elif text == "/id":

        send_message(
            chat_id,
            f"🆔 Your Telegram ID:\n\n{chat_id}"
        )


    # -----------------------------------------------
    # NEW PASSWORD
    # -----------------------------------------------

    elif text == "/newpass":

        # If ADMIN_ID is configured,
        # only that Telegram account can generate passwords.

        if ADMIN_ID:

            if str(chat_id) != str(ADMIN_ID):

                send_message(
                    chat_id,
                    "⛔ You are not authorized."
                )

                return jsonify(ok=True)


        password = make_password()

        send_message(
            chat_id,
            "✅ NEW 24H PASSWORD\n\n"
            f"{password}\n\n"
            "⏳ Valid for 24 hours."
        )


    # -----------------------------------------------
    # STATUS
    # -----------------------------------------------

    elif text == "/status":

        send_message(
            chat_id,
            "🟢 Bot is online.\n\n"
            "Use /newpass to generate a new password."
        )


    return jsonify(ok=True)


# =========================================================
# PASSWORD VERIFY API
# =========================================================

@app.get("/verify")
def verify():

    password = request.args.get(
        "password",
        ""
    )

    if verify_password(password):

        return jsonify({
            "ok": True
        })

    return jsonify({
        "ok": False
    }), 401


# =========================================================
# HOME / HEALTH CHECK
# =========================================================

@app.get("/")
def home():

    return "QX Password Server Online"


# =========================================================
# SET TELEGRAM WEBHOOK
# =========================================================

def set_webhook():

    webhook_url = PUBLIC_URL + "/telegram"

    result = telegram(
        "setWebhook",
        {
            "url": webhook_url
        }
    )

    print(
        "Webhook:",
        result.text
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    set_webhook()

    port = int(
        os.environ.get(
            "PORT",
            "10000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )