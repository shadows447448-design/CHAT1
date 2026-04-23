import importlib
import os
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _FakeResponse:
    def __init__(self, payload=None):
        self._payload = payload or {}
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeRequests(types.SimpleNamespace):
    def post(self, *_args, **_kwargs):
        return _FakeResponse()

    def get(self, *_args, **_kwargs):
        return _FakeResponse()


def _install_fake_dependencies():
    if "requests" not in sys.modules:
        sys.modules["requests"] = _FakeRequests()

    if "flask" not in sys.modules:
        flask_mod = types.ModuleType("flask")
        _request_state = {"json": None}

        class FakeRequest:
            @staticmethod
            def get_json(force=True, silent=True):
                return _request_state["json"]

        class FakeClient:
            def __init__(self, app):
                self._app = app

            def post(self, path, json=None):
                _request_state["json"] = json
                fn = self._app._routes[("POST", path)]
                body = fn()
                return _FakeResponse(body)

        class FakeFlask:
            def __init__(self, _name):
                self._routes = {}

            def get(self, path):
                def decorator(fn):
                    self._routes[("GET", path)] = fn
                    return fn

                return decorator

            def post(self, path):
                def decorator(fn):
                    self._routes[("POST", path)] = fn
                    return fn

                return decorator

            def test_client(self):
                return FakeClient(self)

            def run(self, host, port):
                return None

        def jsonify(obj):
            return obj

        flask_mod.Flask = FakeFlask
        flask_mod.jsonify = jsonify
        flask_mod.request = FakeRequest()
        sys.modules["flask"] = flask_mod


def load_app_module():
    _install_fake_dependencies()
    os.environ.setdefault("TELEGRAM_BOT_TOKEN", "t")
    os.environ.setdefault("FEISHU_APP_ID", "a")
    os.environ.setdefault("FEISHU_APP_SECRET", "s")
    os.environ.setdefault("FEISHU_TARGET_CHAT_ID", "c")
    os.environ.setdefault("CLAUDE_API_KEY", "k")
    if "app" in sys.modules:
        del sys.modules["app"]
    return importlib.import_module("app")


def test_is_non_english_detection():
    app = load_app_module()
    assert app.is_non_english("你好，想了解报价") is True
    assert app.is_non_english("Hello, I need pricing details") is False


def test_format_telegram_forward_appends_translation(monkeypatch):
    app = load_app_module()
    monkeypatch.setattr(app, "translate_to_english", lambda _text: "Hello, I want a quote")

    message = {
        "message_id": 12,
        "text": "你好，我想要报价",
        "chat": {"id": 10001},
        "from": {"first_name": "Zhang", "last_name": "San"},
    }

    out = app.format_telegram_forward(message)
    assert "[TG_REF:10001:12]" in out
    assert "Translation: Hello, I want a quote" in out


def test_telegram_webhook_forwards_to_feishu(monkeypatch):
    app = load_app_module()
    monkeypatch.setattr(app, "format_telegram_forward", lambda _msg: "formatted")
    monkeypatch.setattr(app, "send_to_feishu_group", lambda _text: "om_123")

    client = app.app.test_client()
    resp = client.post(
        "/webhook/telegram",
        json={"message": {"message_id": 7, "chat": {"id": 9}}},
    )

    assert resp.status_code == 200
    assert app.MESSAGE_BRIDGE["om_123"] == (9, 7)


def test_send_to_telegram_rejects_logical_api_failures(monkeypatch):
    app = load_app_module()
    calls = []

    def fake_post(url, json, timeout):
        calls.append((url, json, timeout))
        return _FakeResponse({"ok": False, "description": "Bad Request: chat not found"})

    monkeypatch.setattr(app.requests, "post", fake_post)
    monkeypatch.setattr(app, "telegram_api_base", lambda: "https://api.telegram.org/bottoken")

    with pytest.raises(RuntimeError, match="Telegram send error"):
        app.send_to_telegram(10001, "hello", reply_to_message_id=12)

    assert calls == [
        (
            "https://api.telegram.org/bottoken/sendMessage",
            {"chat_id": 10001, "text": "hello", "reply_to_message_id": 12},
            10,
        )
    ]


def test_feishu_webhook_prefers_root_id_for_nested_replies(monkeypatch):
    app = load_app_module()
    lookups = []
    sent_messages = []

    def fake_get_feishu_message_text(message_id):
        lookups.append(message_id)
        if message_id == "om_root":
            return "Original Telegram inquiry\n[TG_REF:10001:12]"
        if message_id == "om_parent":
            return "Intermediate Feishu reply without a marker"
        return ""

    def fake_send_to_telegram(chat_id, text, reply_to_message_id=None):
        sent_messages.append((chat_id, text, reply_to_message_id))

    monkeypatch.setattr(app, "get_feishu_message_text", fake_get_feishu_message_text)
    monkeypatch.setattr(app, "send_to_telegram", fake_send_to_telegram)

    client = app.app.test_client()
    resp = client.post(
        "/webhook/feishu",
        json={
            "event": {
                "message": {
                    "message_type": "text",
                    "content": '{"text": "We can help with that"}',
                    "parent_id": "om_parent",
                    "root_id": "om_root",
                }
            }
        },
    )

    assert resp.status_code == 200
    assert lookups == ["om_root"]
    assert sent_messages == [(10001, "客服回复: We can help with that", 12)]
