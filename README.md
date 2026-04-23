# wg-ocd

一个用于实现 **一键部署 WireGuard VPN** 的 Python CLI 项目（CLI MVP）。

> 当前阶段先完成 CLI MVP：命令入口、子命令职责、模块边界、日志与错误处理。

## 目录结构

```text
.
├── app
│   ├── __init__.py
│   └── main.py                  # MVP 命令入口（python -m app.main）
├── pyproject.toml
├── README.md
└── src
    └── wg_ocd
        ├── __init__.py
        ├── app.py               # 业务编排层
        ├── cli.py               # 兼容入口（保留）
        ├── exceptions.py
        ├── clients
        │   ├── __init__.py
        │   └── service.py
        ├── firewall
        │   ├── __init__.py
        │   └── service.py
        ├── installer
        │   ├── __init__.py
        │   └── service.py
        ├── utils
        │   ├── __init__.py
        │   ├── command.py
        │   └── logging_utils.py
        └── wireguard
            ├── __init__.py
            └── service.py
```

## CLI MVP 命令

按以下方式运行：

```bash
python -m app.main install
python -m app.main add-client --name alice
python -m app.main remove-client --name alice
python -m app.main status
python -m app.main uninstall
```

### 子命令职责

- `install`：完成完整部署（安装、规则、服务配置）。
- `add-client`：新建客户端配置。
- `remove-client`：删除客户端。
- `status`：查看服务状态和配置摘要。
- `uninstall`：移除服务和规则。

## 本地开发

### 1) 直接运行（推荐）

无需安装，直接执行：

```bash
python -m app.main --help
```

### 2) 可选安装方式

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

安装后可使用：

```bash
wg-ocd --help
```

## 设计说明

- CLI 采用 `argparse`。
- 模块按 `installer` / `wireguard` / `firewall` / `clients` / `utils` 拆分。
- 统一日志初始化：`utils/logging_utils.py`。
- 统一错误处理：`WGOCDError` 及其子类。
- 当前实现为 MVP stub，后续逐步接入真实系统命令（`wg`, `wg-quick`, `ip`, `nft/iptables`）。
