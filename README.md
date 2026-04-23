# CHAT1 工具集合

本仓库当前包含两个独立工具：

1. 外贸客服中转站（Telegram ↔ Feishu）
2. 本地离线加密密码记事本（Cold Vault）

---

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

## 二、本地运行桥接服务

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

---

# 本地离线加密密码记事本（Cold Vault）

这是一个完全离线、独立运作的密码记事本示例，面向关键账号凭据的本地安全保存场景。

## 目标

- 不依赖云端，不做联网同步。
- 数据仅加密保存在本地文件。
- 可以复制到 U 盘进行移动存储（文件始终为密文）。
- 使用主口令解锁，类似冷钱包思路（离线 + 强加密 + 最小暴露）。

## 安全模型（简化版）

- 加密算法：`AES-256-GCM`（提供机密性和完整性校验）。
- 密钥派生：`Argon2id`（抗暴力破解）。
- 每次写入使用随机 `salt` 与 `nonce`。
- 仓库文件、临时文件和导出文件会显式设置为 owner-only 权限（`0600`）。
- 从磁盘读取的 KDF 参数会先校验范围，避免被篡改为极端资源消耗值。

> 注意：本项目是一个实用起点，不是经过第三方审计的商业级密码管理器。

## 如何安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

离线环境可以先在联网机器下载 wheel：

```bash
mkdir -p wheels
pip download -r requirements.txt -d wheels
```

然后把 `wheels/` 和项目文件拷到离线机器：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --no-index --find-links=./wheels -r requirements.txt
```

## 如何使用

假设你的 U 盘挂载路径是 `/media/usb`。

### 1. 初始化加密仓库

```bash
python3 password_notebook.py init --vault /media/usb/myvault.vlt
```

### 2. 添加一个账号条目

```bash
python3 password_notebook.py add --vault /media/usb/myvault.vlt --title "邮箱主账号"
```

依次输入：`username`、`password`、`url`、`notes`。

### 3. 查看某个条目

```bash
python3 password_notebook.py get --vault /media/usb/myvault.vlt --title "邮箱主账号"
```

### 4. 列出全部条目标题

```bash
python3 password_notebook.py list --vault /media/usb/myvault.vlt
```

### 5. 导出密文备份（仍加密）

```bash
python3 password_notebook.py export --vault /media/usb/myvault.vlt --out /media/usb/myvault_backup.vlt
```

## 常见问题

### Q1：我把 `.vlt` 文件复制到另一台机器，能直接打开吗？

可以，只要那台机器安装了 Python + 依赖，并且你记得主口令。

### Q2：忘记主口令怎么办？

无法恢复。该工具不保存明文密钥，也没有后门重置机制。

### Q3：是否会上传云端？

不会。工具本身没有任何联网同步逻辑。

## 关键实践建议

1. 主口令必须足够强（建议 16+ 位，且非复用）。
2. U 盘建议至少准备两份离线备份，分开存放。
3. 不要在不可信电脑上解锁仓库。
4. 定期轮换关键账号密码。
5. 重要数据建议纸质应急恢复信息（如主口令提示策略）单独保存。
