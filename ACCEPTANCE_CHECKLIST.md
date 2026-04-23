# 真实目标机验收清单（WireGuard 一键部署）

> 适用对象：在真实 Linux 服务器（具备 sudo/root、systemd、外网）上验收 `wg-ocd`。

## 验收前准备
- [ ] 目标机具备 `sudo` 权限
- [ ] 目标机可访问互联网（安装依赖、探测公网 IP）
- [ ] 已开放 UDP 51820（若自定义端口，请按实际值）
- [ ] 本地已安装 WireGuard 客户端（手机/电脑）

---

## 1) 安装成功

### 执行
```bash
python -m app.main install
```

### 通过标准
- [ ] 命令退出码为 0
- [ ] 生成服务端配置文件：`/etc/wg-ocd/server/wg0.conf`
- [ ] 生成状态文件：`/etc/wg-ocd/state/server_keys.json`、`/etc/wg-ocd/state/server_meta.json`
- [ ] `systemctl status wg-quick@wg0` 显示 active（running）

### 记录
- 验收结果：通过 / 不通过
- 备注：

---

## 2) 客户端握手成功

### 执行
```bash
python -m app.main add-client --name qa-client
cat /etc/wg-ocd/clients/qa-client.conf
```

将生成的配置导入客户端后，在服务端执行：
```bash
wg show
```

### 通过标准
- [ ] 成功生成客户端配置：`/etc/wg-ocd/clients/qa-client.conf`
- [ ] `wg show` 能看到对应 peer
- [ ] peer 的 `latest handshake` 在近期时间内（例如 2 分钟内）
- [ ] `transfer` 收发字节非 0（或有增长）

### 记录
- 验收结果：通过 / 不通过
- 最新握手时间：
- 流量统计：
- 备注：

---

## 3) 开机自启成功

### 执行
```bash
systemctl is-enabled wg-quick@wg0
sudo reboot
# 重启后
systemctl status wg-quick@wg0
```

### 通过标准
- [ ] `systemctl is-enabled wg-quick@wg0` 返回 `enabled`
- [ ] 重启后服务自动拉起，状态为 active（running）

### 记录
- 验收结果：通过 / 不通过
- 备注：

---

## 4) 卸载清理成功

### 执行
```bash
python -m app.main remove-client --name qa-client
python -m app.main uninstall
```

### 通过标准
- [ ] `systemctl status wg-quick@wg0` 显示 stopped / not found / inactive
- [ ] 主要托管文件被清理（按 manifest）：
  - `/etc/wg-ocd/server/wg0.conf`
  - `/etc/wg-ocd/state/peers.json`
  - `/etc/wg-ocd/state/server_keys.json`
  - `/etc/wg-ocd/state/server_meta.json`
- [ ] 客户端配置已删除：`/etc/wg-ocd/clients/qa-client.conf`

### 记录
- 验收结果：通过 / 不通过
- 备注：

---

## 总结
- 安装成功：通过 / 不通过
- 客户端握手成功：通过 / 不通过
- 开机自启成功：通过 / 不通过
- 卸载清理成功：通过 / 不通过
- 最终结论：可上线 / 不可上线
