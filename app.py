import json
import os
import re
import sqlite3
import time
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
DB_PATH = os.getenv("CONFIG_DB_PATH", "bridge_config.db")

# In production you should switch this to Redis or DB.
# key: feishu_message_id -> value: (telegram_chat_id, telegram_message_id)
MESSAGE_BRIDGE: Dict[str, Tuple[int, int]] = {}


class TokenCache:
    def __init__(self) -> None:
        self.value: Optional[str] = None
        self.expire_at: float = 0


TOKEN_CACHE = TokenCache()


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        conn.commit()


def set_setting(key: str, value: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO settings(key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """,
            (key, value, int(time.time())),
        )
        conn.commit()


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def config_value(name: str, required: bool = False, default: Optional[str] = None) -> str:
    value = get_setting(name) or os.getenv(name) or default
    if required and not value:
        raise RuntimeError(f"Missing required config: {name}. Please configure in /admin or env.")
    return value or ""


@lru_cache(maxsize=1)
def telegram_api_base() -> str:
    token = config_value("TELEGRAM_BOT_TOKEN", required=True)
    return f"https://api.telegram.org/bot{token}"


def is_non_english(text: str) -> bool:
    if not text:
        return False
    if re.search(r"[\u4e00-\u9fff]", text):
        return True
    non_ascii = sum(1 for c in text if ord(c) > 127)
    return non_ascii / max(len(text), 1) > 0.2


def translate_to_english(text: str) -> Optional[str]:
    if not is_non_english(text):
        return None

    api_key = config_value("LLM_API_KEY")
    if not api_key:
        return None

    api_base = config_value("LLM_API_BASE", default="https://api.openai.com/v1")
    model = config_value("LLM_MODEL", default="gpt-4o-mini")
    endpoint = f"{api_base.rstrip('/')}/chat/completions"

    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": "You are a customer-support translator. Translate user content into concise natural English.",
            },
            {"role": "user", "content": text},
        ],
    }

    resp = requests.post(
        endpoint,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip() or None


def get_feishu_tenant_access_token() -> str:
    app_id = config_value("FEISHU_APP_ID", required=True)
    app_secret = config_value("FEISHU_APP_SECRET", required=True)

    now = time.time()
    if TOKEN_CACHE.value and now < TOKEN_CACHE.expire_at - 30:
        return TOKEN_CACHE.value

    resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        headers={"content-type": "application/json"},
        json={"app_id": app_id, "app_secret": app_secret},
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
    chat_id = config_value("FEISHU_TARGET_CHAT_ID", required=True)
    token = get_feishu_tenant_access_token()
    resp = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        params={"receive_id_type": "chat_id"},
        json={
            "receive_id": chat_id,
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
    payload: Dict[str, Any] = {"chat_id": chat_id, "text": text}
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id

    resp = requests.post(f"{telegram_api_base()}/sendMessage", json=payload, timeout=10)
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


def find_telegram_reference(*message_ids: str) -> Optional[Tuple[int, int]]:
    seen = set()
    for message_id in message_ids:
        if not message_id or message_id in seen:
            continue
        seen.add(message_id)
        message_text = get_feishu_message_text(message_id)
        match = re.search(r"\[TG_REF:(-?\d+):(\d+)\]", message_text)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None


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


@app.get("/admin")
def admin_page() -> str:
    keys = [
        "TELEGRAM_BOT_TOKEN",
        "FEISHU_APP_ID",
        "FEISHU_APP_SECRET",
        "FEISHU_TARGET_CHAT_ID",
        "LLM_API_BASE",
        "LLM_API_KEY",
        "LLM_MODEL",
    ]
    rows = []
    for key in keys:
        val = get_setting(key, "")
        show = val if key in ("LLM_API_BASE", "LLM_MODEL", "FEISHU_TARGET_CHAT_ID") else ("***" if val else "")
        rows.append(f"<tr><td>{key}</td><td><input name='{key}' value='{show}' style='width:460px'/></td></tr>")

    return (
        "<html><body><h2>Bridge Admin</h2>"
        "<p>绑定 Telegram / Feishu，并配置任意 OpenAI 兼容模型 API。</p>"
        "<form method='post' action='/admin'>"
        "<table>"
        + "".join(rows)
        + "</table><button type='submit'>保存配置</button></form>"
        "</body></html>"
    )


@app.post("/admin")
def admin_save() -> Any:
    form = request.form
    sensitive = {"TELEGRAM_BOT_TOKEN", "FEISHU_APP_ID", "FEISHU_APP_SECRET", "LLM_API_KEY"}
    for key in [
        "TELEGRAM_BOT_TOKEN",
        "FEISHU_APP_ID",
        "FEISHU_APP_SECRET",
        "FEISHU_TARGET_CHAT_ID",
        "LLM_API_BASE",
        "LLM_API_KEY",
        "LLM_MODEL",
    ]:
        val = (form.get(key) or "").strip()
        if key in sensitive and val == "***":
            continue
        if val:
            set_setting(key, val)
    telegram_api_base.cache_clear()
    TOKEN_CACHE.value = None
    return jsonify({"ok": True, "message": "saved"})


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
    if payload.get("type") == "url_verification":
        return jsonify({"challenge": payload.get("challenge")})

    event = payload.get("event", {})
    message = event.get("message", {})
    if message.get("message_type") != "text":
        return jsonify({"ok": True, "ignored": "non-text"})

    try:
        reply_text = json.loads(message.get("content", "{}")).get("text", "")
    except json.JSONDecodeError:
        reply_text = message.get("content", "")

    root_id = message.get("root_id")
    parent_id = message.get("parent_id")
    reference_source_ids = [message_id for message_id in (root_id, parent_id) if message_id]
    if not reference_source_ids:
        return jsonify({"ok": True, "ignored": "not a reply"})

    telegram_ref = find_telegram_reference(*reference_source_ids)
    if not telegram_ref:
        return jsonify({"ok": True, "ignored": "no tg ref"})

    chat_id, telegram_msg_id = telegram_ref
    send_to_telegram(chat_id, f"客服回复: {reply_text}", reply_to_message_id=telegram_msg_id)
    return jsonify({"ok": True})


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
