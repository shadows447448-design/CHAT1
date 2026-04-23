# wg-ocd

合法远程访问场景的一键部署 WireGuard 工具（CLI MVP）。

## 设计概览

- **模块化结构**：`installer`、`wireguard`、`firewall`、`clients`、`utils`。
- **命令执行封装**：所有系统命令统一走 `CommandRunner`，返回 `returncode/stdout/stderr`。
- **模板化配置生成**：服务端与客户端配置均从模板文件渲染。
- **自动备份**：所有配置修改前自动备份到 `backup/`。
- **安全日志**：日志不输出密钥等敏感信息。

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

卸载会尝试回滚安装阶段记录的创建项（manifest 驱动）。

## 故障排查

1. `status` 显示 `stopped`：检查 `wg` 是否安装、接口名是否正确。
2. `install` 失败：查看错误里的 `stderr`（由 `CommandRunner` 捕获）。
3. 客户端操作失败：检查 `state/clients.json` 是否可写。
4. 权限问题：确保当前用户有执行系统命令与写配置目录权限。

## 测试

```bash
PYTHONPATH=src pytest -q
```
