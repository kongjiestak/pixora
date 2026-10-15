# PVE deployment acceptance / PVE 部署验收

Observed 2026-10-15, Asia/Shanghai. Application image built from commit `993ac502d03472fac70966539a96ca2a68432e5e` on an actual Debian 13 Docker VM hosted on PVE 9.2.2 / N100. This is a specific environment result, not a compatibility guarantee for all PVE installations.

| Check / 检查 | Observed / 实测 |
|---|---|
| Image build and non-root container | Passed on actual target |
| Isolation | Independent Compose project, volume, directory, 512 MiB / 1 CPU limit; existing services remained running |
| Transport | Server binds loopback; Mac uses two host-key-verified SSH hops to the VM loopback port. No public ingress or LAN plaintext bearer-token endpoint opened |
| Real roundtrip | Mac Codex collector → SSH tunnel → FastAPI → persistent SQLite → scoped read API; two real Codex windows, fresh at test time; values withheld |
| ChatGPT | Unavailable, no invented real quota |
| Demo browser | Target-served Vue dashboard rendered labeled demo data in browser; real view also connected |
| Credentials | Random server tokens, global broad read disabled, independent 90-day private screen and 30-day demo-only screen; raw values excluded from repository and reports |
| Persistence | Only Pixora container restarted; observations and scoped-device authentication survived |
| Backup | SQLite online backup with integrity_check=ok; copied outside volume and a private copy transferred to Mac; SHA256 matched |
| Restore | Offline isolated disposable container restored backup to a different SQLite file; real/demo reads and demo-scope rejection passed; production DB not replaced |

中文：已在真实PVE上的Debian VM部署并验证真实采集闭环、独立令牌、容器重启持久化、SQLite在线备份和隔离恢复。原有影音服务持续运行。截图仅演示数据，账户数值与凭据不公开。

Remaining gates: physical Android/iPhone/iPad installation, trusted LAN HTTPS for phones, long-running wake/sleep/recovery, Mac login autostart and full VM/host reboot acceptance. Mac LaunchAgent trial stalled during file access; trial jobs were unloaded, tunnel/collector run in the current session. Prepared launch files are not evidence of successful autostart. Existing PVE boot/network settings were not changed. No new release is justified by these partial gates.

尚未完成：真实旧手机、手机可信HTTPS入口、长时间睡眠恢复、Mac登录自启动及VM/宿主整体重启验收。仅重启Pixora容器；未改PVE启动与网络配置。备份本次为手动执行，未宣称自动备份计划。原历史旧SHA缓存问题仍独立未解决。

Operational private addresses, credentials, VM SSH keys and database backups belong outside the source checkout. Use `DEVICES.md` to provision/revoke screens. A copied online-backup file may retain WAL journal mode; for a read-only immutable backup mount, use SQLite URI `mode=ro&immutable=1` or copy it into a writable scratch directory before opening. Never use `immutable=1` against a live changing database.
