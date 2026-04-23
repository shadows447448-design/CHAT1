# 外贸客服中转站（Telegram ↔ Feishu）

该示例实现了：

1. Telegram 客户消息通过 Webhook 转发到飞书群。
2. 飞书在对应线程回复后，自动回发给 Telegram 客户。
3. 对非英文消息调用 Claude API 翻译，并在转发消息末尾附上翻译。

## 1) 环境变量

```bash
export TELEGRAM_BOT_TOKEN="<telegram_bot_token>"
export FEISHU_APP_ID="<lark_app_id>"
export FEISHU_APP_SECRET="<lark_app_secret>"
export FEISHU_TARGET_CHAT_ID="<target_group_chat_id>"
export CLAUDE_API_KEY="<anthropic_api_key>"
# 可选
export CLAUDE_MODEL="claude-3-5-sonnet-latest"
export PORT="8080"
```

## 2) 本地运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## 3) Webhook 配置

### Telegram

把 Telegram Webhook 指向：

```text
POST https://<your-domain>/webhook/telegram
```

设置命令示例：

```bash
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d "url=https://<your-domain>/webhook/telegram"
```

### Feishu (Lark)

在飞书应用事件订阅中配置：

- Request URL: `https://<your-domain>/webhook/feishu`
- 订阅事件：`im.message.receive_v1`
- 开启机器人入群并授予发消息权限。

## 4) 协议转换说明

- Telegram 入站：解析 `message.text/caption`。
- 飞书出站：发送 `msg_type=text`，`content` 为 JSON 字符串。
- 飞书回复回传：通过 `parent_id/root_id` 找到原消息，解析 `[TG_REF:chat_id:message_id]` 路由标记，回发 Telegram。

## 5) 生产建议

- 把 `MESSAGE_BRIDGE` 换成 Redis 或数据库，支持多实例与重启恢复。
- 为 webhook 增加签名校验（Telegram secret token、飞书签名）。
- 增加重试与死信队列，保障网络抖动下的实时性。
