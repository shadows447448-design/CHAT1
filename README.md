# wg-ocd

合法远程访问场景的一键部署 WireGuard 工具（CLI MVP）。

## 1. 快速说明

`wg-ocd` 当前提供以下命令：

- `install`：安装并初始化服务端
- `add-client --name <name>`：新增客户端配置
- `remove-client --name <name>`：删除客户端
- `status`：查看服务状态摘要
- `uninstall`：卸载并清理托管内容

---

## 2. 权限与环境要求

- 真实安装/卸载需 root（或 sudo）权限。
- 需要 systemd 环境（`wg-quick@wg0` 服务管理）。
- 需要外网访问能力以自动探测公网 endpoint（可回退到本机 IP）。
- 需要开放 UDP 监听端口（默认 51820）。

---

## 3. 安装与开发环境

### 3.1 克隆并进入项目

```bash
git clone <your-repo-url>
cd CHAT1
```

### 3.2 创建虚拟环境并安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

### 3.3 查看帮助

```bash
python -m app.main --help
```

---

### 3.4 EXE 安装模式（无 Python 运行项目）

如果你希望以单文件可执行程序方式使用：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .[build]
./scripts/build_exe.sh
```

构建产物：

- `dist/wg-ocd`

安装到系统路径（需要 root）：

```bash
sudo ./scripts/install_exe.sh
wg-ocd --help
```

之后可以直接使用：

```bash
sudo wg-ocd install
sudo wg-ocd add-client --name alice
wg-ocd status
sudo wg-ocd remove-client --name alice
sudo wg-ocd uninstall
```

---

## 4. 详细使用教程（从 0 到 1）

## 4.1 第一步：安装服务端

### 演练模式（不改系统）

```bash
python -m app.main install --dry-run
```

### 真实安装

```bash
sudo python -m app.main install
```

### 安装后你应看到

- `/etc/wg-ocd/server/wg0.conf`
- `/etc/wg-ocd/state/server_keys.json`
- `/etc/wg-ocd/state/server_meta.json`
- `systemctl status wg-quick@wg0` 为 active（running）

---

## 4.2 第二步：新增客户端并导入配置

```bash
sudo python -m app.main add-client --name alice
sudo cat /etc/wg-ocd/clients/alice.conf
```

把 `alice.conf` 导入手机或电脑的 WireGuard 客户端后，开启连接。

---

## 4.3 第三步：验证连接握手

在服务端执行：

```bash
sudo wg show
```

重点看：
- 对应 peer 是否存在
- `latest handshake` 是否是近期时间
- `transfer` 收发字节是否增长

---

## 4.4 第四步：查看状态

```bash
python -m app.main status
```

该命令输出服务摘要（接口名、状态、摘要信息）。

---

## 4.5 第五步：删除客户端

```bash
sudo python -m app.main remove-client --name alice
```

删除后再次 `wg show`，应看不到对应 peer。

---

## 4.6 第六步：卸载

### 演练模式

```bash
python -m app.main uninstall --dry-run
```

### 真实卸载

```bash
sudo python -m app.main uninstall
```

卸载后应完成：
- 停止并禁用 `wg-quick@wg0`
- 清理 manifest 托管的主要文件

---

## 5. 真实目标机验收清单

请使用单独文档：

- `ACCEPTANCE_CHECKLIST.md`

该清单已逐条对应：
- 安装成功
- 客户端握手成功
- 开机自启
- 卸载清理

---

## 6. 一键真实验收脚本（目标机）

```bash
./scripts/e2e_smoke.sh
```

脚本串联流程：

- install
- add-client
- status
- remove-client
- uninstall

基础验收检查脚本（安装产物/自启/服务状态）：

```bash
./scripts/acceptance_check.sh
```

---

## 7. 工程验收映射

- README：本文件
- 配置模板：`src/wg_ocd/templates/*.tpl`
- 测试：`tests/`
- 错误处理：`src/wg_ocd/exceptions.py` + CLI 捕获
- dry-run：`install --dry-run`、`uninstall --dry-run`
- 日志：`src/wg_ocd/utils/logging_utils.py`
- 备份：`SystemUtils.backup_file`
- Git 提交：见仓库历史

---

## 8. 测试

```bash
PYTHONPATH=src pytest -q
```
