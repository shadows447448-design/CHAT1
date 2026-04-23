# wg-ocd

合法远程访问场景的一键部署 WireGuard 工具（CLI MVP）。

## 功能验收映射

- 一键安装：`python -m app.main install`。
- 至少 1 个客户端配置：`python -m app.main add-client --name alice`。
- 开机自启：安装流程执行 `systemctl enable wg-quick@wg0`。
- 客户端新增/删除：`add-client` / `remove-client`。
- 卸载清理：`python -m app.main uninstall` 清理服务与主要托管文件。
- 连通性验证：在真实服务器执行 `wg show` + 客户端握手验证（见“故障排查”）。

## 工程验收映射

- README：本文件。
- 配置模板：`src/wg_ocd/templates/*.tpl`。
- 测试：`tests/`。
- 错误处理：`src/wg_ocd/exceptions.py` + CLI 捕获。
- dry-run：`install --dry-run`、`uninstall --dry-run`。
- 日志：`src/wg_ocd/utils/logging_utils.py`。
- 备份：`SystemUtils.backup_file`。
- Git 提交：见仓库历史。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## 使用

```bash
python -m app.main install --dry-run
python -m app.main install
python -m app.main add-client --name alice
python -m app.main status
python -m app.main remove-client --name alice
```

## 卸载

```bash
python -m app.main uninstall --dry-run
python -m app.main uninstall
```

## 故障排查

1. 服务状态：`python -m app.main status`。
2. 服务自启：`systemctl status wg-quick@wg0`。
3. 连接验证：服务端 `wg show` 看最新握手时间与流量。
4. 客户端连接失败：检查端口 UDP/51820、防火墙后端、配置导入是否最新。

## 测试

```bash
PYTHONPATH=src pytest -q
```
