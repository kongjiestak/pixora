# Scoped display tokens / 逐设备只读令牌

EN: Provision on the server, never from an unauthenticated HTTP endpoint. Each screen gets an independent 256-bit random bearer token. SQLite stores only its SHA-256 digest. Provider and real/demo scope are enforced on every API request; expiry and revocation take effect on the next request without a restart. A revoked screen may retain previously rendered information: clear/disconnect it locally as well. Tokens authorize whole provider observations, not individual fields/widgets. No multi-tenant or command permissions are claimed.

中文：在服务端本机操作，不提供网络管理入口。每块屏幕获得独立随机令牌，数据库仅存摘要；每次读取强制检查数据源、真实/演示权限、期限和撤销状态。撤销阻止后续请求，无法远程擦除已经显示的数据。权限粒度为完整数据源观测，不是逐字段或 Widget，也不是多租户或控制权限。

## Create / 创建

From the repository root (or use the installed `pixora-device` command):

```sh
python -m pixora.devices create --name desk --provider codex --mode real --days 30
```

Docker Compose uses the same SQLite volume as the server:

```sh
docker compose exec monitor python -m pixora.devices create --name public-screen --provider codex --mode demo --days 7
```

The JSON response contains `id`, `token`, `expires_at`. Save the token privately once and enter it into the existing dashboard read-token field. Do not paste it into issues, URLs or screenshots. The CLI output is sensitive; the token cannot be retrieved later. Default mode is **demo only** if `--mode` is omitted. Repeat `--provider` / `--mode` for multiple scopes. Supported providers are currently codex and chatgpt; chatgpt real quotas remain unavailable.

输出含 id、token 和 expires_at。令牌只显示这一次，私下保存并填入网页已有的只读令牌框；不要贴到 Issue、URL、截图或日志。省略 --mode 时默认仅演示权限。可重复 --provider/--mode。网页须选择获授权的真实或演示模式；无权限返回 403，未知/到期/撤销令牌返回 401。共享模式仍会清除令牌；如需持续演示，可使用独立 demo 令牌，不授予 real。

## List / revoke / 列表与撤销

```sh
python -m pixora.devices list
python -m pixora.devices revoke DEVICE_ID
```

In Docker prefix with `docker compose exec monitor`. List never returns tokens or digests. To rotate, create a replacement, update the screen and revoke the old id. Existing snapshots remain unchanged. Back up SQLite including the devices table and retain server filesystem access as an administrator privilege.

容器中加前缀 docker compose exec monitor。列表不返回令牌或摘要。轮换流程：创建替代令牌、更新屏幕、撤销旧 id。不会修改现有观测数据；SQLite 备份也包含设备授权，服务端文件访问等同管理权限。

## Migration / 迁移

Existing global `PIXORA_READ_TOKEN` remains a broad compatibility credential by default; it does not acquire device restrictions. After provisioning and switching every display, set `PIXORA_ALLOW_LEGACY_READ_TOKEN=false` in .env and recreate the service (`docker compose up -d`). This disables the broad read credential without affecting the collector write credential. Keep distinct read/write values configured for compatibility with startup validation. A stale or malformed legacy-enable value fails closed (only `true` enables it).

旧全局只读令牌默认继续有效且可读全部数据。为所有屏幕配置独立令牌后，设置上述开关为 false 并重建服务，关闭宽权限入口；采集写令牌不受影响。启动校验仍要求独立读写配置。设备管理网页、自动配对、逐字段权限与服务端布局同步留待后续。
