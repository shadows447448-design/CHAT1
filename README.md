# wg-ocd

合法远程访问场景的一键部署 WireGuard 工具（CLI MVP）。

## 技术拆分

- `installer.py`：root/发行版检查、安装包、内核转发、systemd。
- `wireguard.py`：服务端/客户端密钥、配置渲染、peer 管理。
- `firewall.py`：检测后端（iptables/nftables/ufw）、NAT、端口放行、卸载移除。
- `clients.py`：新增/删除/列出/导出客户端配置。
- `utils.py`：命令执行、备份、模板渲染、日志、路径辅助。

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

1. `status` 无输出：检查 `wg` 命令是否存在。
2. `install` 失败：查看异常里的 `stderr`。
3. 客户端配置缺失：检查 `clients/` 目录权限。
4. 防火墙未生效：确认系统使用的后端（nft/iptables/ufw）。

## 测试

```bash
PYTHONPATH=src pytest -q
```
