# CLI MVP 设计

## 目标
实现合法远程访问场景的一键部署 WireGuard CLI MVP，满足：模块化、模板化配置、命令封装、自动备份、dry-run、敏感信息保护、卸载回滚。

## 架构
- `app/main.py`：CLI 入口与参数解析。
- `src/wg_ocd/app.py`：应用编排。
- `installer/service.py`：安装/卸载流程。
- `clients/service.py`：客户端增删与配置生成。
- `wireguard/service.py`：WireGuard 状态与配置应用。
- `firewall/service.py`：防火墙开关。
- `utils/command.py`：统一命令执行封装。
- `utils/backup.py`：自动备份与安装清单。
- `config/templates.py` + `templates/*.tpl`：模板渲染。

## 安全与回滚
- 密钥字段使用占位符写入模板，不进日志。
- 修改前自动备份原文件。
- 安装创建项写入 manifest，卸载按 manifest 尽量回滚。
- 命令失败保留 stdout/stderr 便于排查。
