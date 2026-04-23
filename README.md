# wg-ocd

一个用于实现 **一键部署 WireGuard VPN** 的 Python CLI 项目骨架。

> 当前版本为初始化脚手架，核心命令与模块已就位，实际系统配置逻辑为 stub，便于后续逐步实现。

## 目录结构

```text
.
├── pyproject.toml
├── README.md
└── src
    └── wg_ocd
        ├── __init__.py
        ├── app.py
        ├── cli.py
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

## 本地开发

### 1) 创建虚拟环境并安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

### 2) 查看 CLI 帮助

```bash
wg-ocd --help
```

或不安装脚本时：

```bash
PYTHONPATH=src python -m wg_ocd.cli --help
```

### 3) 可用子命令（已预留）

- `install`
- `add-client <name>`
- `remove-client <name>`
- `status`
- `uninstall`

示例：

```bash
PYTHONPATH=src python -m wg_ocd.cli install -v
PYTHONPATH=src python -m wg_ocd.cli add-client alice
PYTHONPATH=src python -m wg_ocd.cli status
```

## 设计说明

- 使用 `argparse` 构建 CLI，便于后续扩展命令参数。
- 采用模块化拆分：`installer` / `wireguard` / `firewall` / `clients` / `utils`。
- 基础日志由 `utils/logging_utils.py` 统一配置。
- 错误处理采用统一异常基类 `WGOCDError`，CLI 层集中处理并返回非 0 退出码。

## 后续建议

1. 在 `utils/command.py` 中补齐 sudo、重试、超时与命令白名单能力。
2. 在各 `service.py` 中替换 stub 为真实系统调用（`wg`, `wg-quick`, `ip`, `nft/iptables`）。
3. 增加测试：参数解析测试、服务编排单测、集成 smoke test。
