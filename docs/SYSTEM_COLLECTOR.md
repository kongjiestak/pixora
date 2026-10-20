# Linux system collector / Linux 常驻系统采集

The connector reads CPU, available memory and root filesystem occupancy locally. It does not require root, PVE credentials, Codex login or a Mac. It sends numeric observations using the trusted backend write capability. Collection is read-only on the host; the backend credential can ingest data, not control the host. Provider-specific write capabilities are not implemented yet, so keep this trusted collector credential private.

连接器在 Linux 主机本机读取 CPU、内存、根文件系统，不需要 root 权限、PVE 管理凭据或 Mac 在线。若在容器中运行，只能视为容器所见的内核/文件系统，不宣称是完整主机/cgroup 指标。PVE 专用 API 连接器不是本增量功能。

## Install / 安装

Use Python 3.11+ and the OS venv package. On Debian/Ubuntu install the matching `python3-venv` package if venv reports ensurepip missing. Create a clean checkout of this repository at `/opt/pixora-system-collector/source`; never copy `.env`, private deployments or Codex credentials into it. As an administrator:

```sh
useradd --system --create-home --home-dir /var/lib/pixora-system-collector --shell /usr/sbin/nologin pixora-system
python3 -m venv /opt/pixora-system-collector/venv
/opt/pixora-system-collector/venv/bin/pip install -r /opt/pixora-system-collector/source/requirements-lock.txt
/opt/pixora-system-collector/venv/bin/pip install --no-deps /opt/pixora-system-collector/source
install -d -m 700 /etc/pixora
install -m 600 examples/system-collector.env.example /etc/pixora/system-collector.env
# Edit the private env file: actual write token, URL and an opaque entity ID.
# The service user needs read/execute access to the code and venv, not the env file.
install -m 644 deploy/pixora-system-collector.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now pixora-system-collector.service
systemctl status pixora-system-collector.service
```

Do not recreate an existing system user; reuse it after checking its identity. The root systemd manager reads the 0600 EnvironmentFile before dropping privileges. Keep `/opt` code/venv administrator-owned and readable by the service, with no writable source path. Use HTTPS for a remote server; loopback HTTP is allowed for the same host. No public listener or inbound firewall rule is required for collection.

服务采用独立用户、空 capability、NoNewPrivileges、只读系统、受限地址族、96MiB 内存和 10% CPU 限额。默认每 120 秒采集，网络失败退避最多 300 秒另加抖动及请求耗时；成功恢复正常间隔。服务重启策略处理进程异常，网络恢复由同一进程重试，不以整机重启代替。

## Acceptance and diagnostics / 验收排查

- `systemctl is-enabled/is-active pixora-system-collector` should report enabled/active.
- Logs should show `snapshot delivered`; failure details deliberately suppress tokens and raw observations.
- Check the v2 latest/history API using a separate `system` read-scoped device. Compare collection timestamps over two cycles, rather than inferring success from a green service state.
- Host startup/network scheduling and token validity remain prerequisites. No complete power-loss/whole-machine reboot test is implied.
- A recovery test must affect only this service and must establish an independent automatic restoration before injecting a fault. Do not disable the global network, proxies, firewall or other services. Only claim same-process recovery when the observed PID is unchanged after access is restored.

授予屏幕系统数据权限时创建新设备，不扩大旧的 Codex-only 令牌：

```sh
pixora-device create --name system-screen --provider codex --provider system --mode real --days 30
```

The provisioning output is private. Pair over HTTPS. Verify mode/source scope, history and sign-out; browser/PWA cookie storage can differ, so test the actual Home Screen app separately. System shared-screen widgets are hidden, but local UI hiding is not a replacement for server scopes.
