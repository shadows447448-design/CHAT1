# 外贸客服中转站（Telegram ↔ Feishu）

## 功能

1. Telegram 客户消息通过 Webhook 转发到飞书群。
2. 飞书线程回复后，自动回发给 Telegram 客户。
3. 非英文内容会走 AI 翻译层（支持任意 OpenAI 兼容 API），并在消息末尾追加翻译。
4. 提供操作界面 `/admin`，可在页面绑定 Telegram、飞书与模型配置（无需改代码）。

## 一、配置方式

### 方式 A：在 `/admin` 操作界面配置（推荐）

启动服务后打开：

```text
http://<your-host>:8080/admin
```

在页面中填写并保存以下项目：

- `TELEGRAM_BOT_TOKEN`
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_TARGET_CHAT_ID`
- `LLM_API_BASE`（例如 `https://api.openai.com/v1`）
- `LLM_API_KEY`
- `LLM_MODEL`（例如 `gpt-4o-mini`，也可以填你接入平台上的其它模型）

### 方式 B：环境变量配置

```bash
export TELEGRAM_BOT_TOKEN="<telegram_bot_token>"
export FEISHU_APP_ID="<lark_app_id>"
export FEISHU_APP_SECRET="<lark_app_secret>"
export FEISHU_TARGET_CHAT_ID="<target_group_chat_id>"

export LLM_API_BASE="https://api.openai.com/v1"
export LLM_API_KEY="<your_api_key>"
export LLM_MODEL="gpt-4o-mini"

export PORT="8080"
export CONFIG_DB_PATH="bridge_config.db"
```

> `/admin` 保存后的配置优先于环境变量。

## 二、本地运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## 三、Webhook 配置

### Telegram

Webhook URL：

```text
POST https://<your-domain>/webhook/telegram
```

设置命令：

```bash
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d "url=https://<your-domain>/webhook/telegram"
```

### Feishu (Lark)

事件订阅配置：

- Request URL: `https://<your-domain>/webhook/feishu`
- 订阅事件：`im.message.receive_v1`
- 机器人加入目标群并授予发消息权限。

## 四、协议转换说明

- Telegram 入站：解析 `message.text/caption`。
- 飞书出站：发送 `msg_type=text`，`content` 是 JSON 字符串。
- 飞书回复回传：通过 `parent_id/root_id` 找到原消息，解析 `[TG_REF:chat_id:message_id]` 路由回 Telegram。

## 五、生产建议

- `MESSAGE_BRIDGE` 仅作演示，建议改为 Redis 持久化。
- 增加 Telegram/飞书签名校验。
- 增加重试、幂等与告警。
