import json
import os
import re
import time
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


TELEGRAM_BOT_TOKEN = require_env("TELEGRAM_BOT_TOKEN")
FEISHU_APP_ID = require_env("FEISHU_APP_ID")
FEISHU_APP_SECRET = require_env("FEISHU_APP_SECRET")
FEISHU_TARGET_CHAT_ID = require_env("FEISHU_TARGET_CHAT_ID")
CLAUDE_API_KEY = require_env("CLAUDE_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-latest")
PORT = int(os.getenv("PORT", "8080"))

# In production you should switch this to Redis or DB.
# key: feishu_message_id -> value: (telegram_chat_id, telegram_message_id)
MESSAGE_BRIDGE: Dict[str, Tuple[int, int]] = {}


class TokenCache:
    def __init__(self) -> None:
        self.value: Optional[str] = None
        self.expire_at: float = 0


TOKEN_CACHE = TokenCache()


@lru_cache(maxsize=1)
def telegram_api_base() -> str:
    return f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def is_non_english(text: str) -> bool:
    if not text:
        return False
    # Heuristic: contains CJK or many non-ASCII characters.
    if re.search(r"[\u4e00-\u9fff]", text):
        return True
    non_ascii = sum(1 for c in text if ord(c) > 127)
    return non_ascii / max(len(text), 1) > 0.2


def translate_to_english(text: str) -> Optional[str]:
    if not is_non_english(text):
        return None

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": CLAUDE_MODEL,
        "max_tokens": 400,
        "temperature": 0,
        "system": "You are a professional customer-support translator. Translate the input into concise natural English.",
        "messages": [{"role": "user", "content": text}],
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    for block in data.get("content", []):
        if block.get("type") == "text":
            return block.get("text", "").strip()
    return None


def get_feishu_tenant_access_token() -> str:
    now = time.time()
    if TOKEN_CACHE.value and now < TOKEN_CACHE.expire_at - 30:
        return TOKEN_CACHE.value

    resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        headers={"content-type": "application/json"},
        json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Feishu token error: {data}")

    TOKEN_CACHE.value = data["tenant_access_token"]
    TOKEN_CACHE.expire_at = now + int(data.get("expire", 7200))
    return TOKEN_CACHE.value


def send_to_feishu_group(text: str) -> str:
    token = get_feishu_tenant_access_token()
    resp = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        params={"receive_id_type": "chat_id"},
        json={
            "receive_id": FEISHU_TARGET_CHAT_ID,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Feishu send error: {data}")
    return data["data"]["message_id"]


def send_to_telegram(chat_id: int, text: str, reply_to_message_id: Optional[int] = None) -> None:
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
    }
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id

    resp = requests.post(
        f"{telegram_api_base()}/sendMessage",
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()


def get_feishu_message_text(message_id: str) -> str:
    token = get_feishu_tenant_access_token()
    resp = requests.get(
        f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        return ""

    content = data.get("data", {}).get("items", [{}])[0].get("body", {}).get("content", "")
    if not content:
        return ""

    try:
        return json.loads(content).get("text", "")
    except json.JSONDecodeError:
        return content


def format_telegram_forward(message: Dict[str, Any]) -> str:
    text = message.get("text") or message.get("caption") or "[非文本消息]"
    customer = message.get("from", {})
    name = " ".join(filter(None, [customer.get("first_name"), customer.get("last_name")])) or customer.get("username", "Unknown")
    chat_id = message["chat"]["id"]
    msg_id = message["message_id"]

    translated = translate_to_english(text)
    lines = [
        "📨 New Telegram Inquiry",
        f"From: {name}",
        f"Chat ID: {chat_id}",
        f"Message ID: {msg_id}",
        f"Content: {text}",
        f"[TG_REF:{chat_id}:{msg_id}]",
    ]
    if translated:
        lines.append(f"Translation: {translated}")
    return "\n".join(lines)


@app.get("/healthz")
def healthz() -> Any:
    return jsonify({"ok": True})


@app.post("/webhook/telegram")
def telegram_webhook() -> Any:
    payload = request.get_json(force=True, silent=True) or {}
    message = payload.get("message")
    if not message:
        return jsonify({"ok": True, "ignored": True})

    text = format_telegram_forward(message)
    feishu_message_id = send_to_feishu_group(text)
    MESSAGE_BRIDGE[feishu_message_id] = (message["chat"]["id"], message["message_id"])

    return jsonify({"ok": True})


@app.post("/webhook/feishu")
def feishu_webhook() -> Any:
    payload = request.get_json(force=True, silent=True) or {}

    # URL verification handshake.
    if payload.get("type") == "url_verification":
        return jsonify({"challenge": payload.get("challenge")})

    event = payload.get("event", {})
    message = event.get("message", {})
    if message.get("message_type") != "text":
        return jsonify({"ok": True, "ignored": "non-text"})

    reply_text = ""
    try:
        reply_text = json.loads(message.get("content", "{}")).get("text", "")
    except json.JSONDecodeError:
        reply_text = message.get("content", "")

    parent_id = message.get("parent_id") or message.get("root_id")
    if not parent_id:
        return jsonify({"ok": True, "ignored": "not a reply"})

    parent_text = get_feishu_message_text(parent_id)
    match = re.search(r"\[TG_REF:(-?\d+):(\d+)\]", parent_text)
    if not match:
        return jsonify({"ok": True, "ignored": "no tg ref"})

    chat_id = int(match.group(1))
    telegram_msg_id = int(match.group(2))
    send_to_telegram(chat_id, f"客服回复: {reply_text}", reply_to_message_id=telegram_msg_id)

    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
