> Current direction / 当前方向（2026-10-22）：V0.4 owner accepted; V0.5 first ESP32 + phone onboarding; V0.6 activity/minimal alerts + Watch 8 notification trial; V0.7 novice usability; V1.0 stable delivery. Old personal-information expansion is cancelled. See [V0.5](V0.5.md) / [中文](V0.5.zh-CN.md). Older milestone rows below are historical context, not the current plan.

# Pixora 路线图

[English](ROADMAP.md) | [简体中文](ROADMAP.zh-CN.md)

按验收推进，无固定日期。当前 Early Development；0.3.0.dev1 只是开发元数据，不是正式版本完成声明。

| 里程碑 | 工作 | 验收 / 状态 |
|---|---|---|
| V0.1 | Codex → API → Web、英中文、Widget、PWA/Kiosk、本机隐私 | 已部署；iPhone PWA、家庭采集恢复已验收，未创建稳定 Release |
| V0.2 | 通用 Observation v2、迁移、PVE/主机只读指标、历史 | main 已实现：迁移回滚、Linux 系统与历史；iPhone/安卓显示已验收，PVE 专用 API 延后 |
| V0.3 | CI/GitHub、日历/待办/天气/RSS | 开发中：GitHub公开状态、RSS/Atom、本地待办已实现；本地月历/天气/圆环已实现；日历账号同步延后、待办编辑暂停 |
| V0.4 | 布局编辑器、服务端设备配置、逐设备令牌/撤销 | 开发中：Orbit 约束式布局编辑、管理员发布设备推荐配置、实体/指标/额度窗口/条目策略；网页设备管理与远程发布待做 |
| V0.5 | 邮件摘要、生活/账单提醒、出行、预算、目标 | 规划；最小留存、撤销、屏幕锁 |
| V0.7 | Home Assistant、自动化交互控制 | 规划；独立权限、审计、确认、幂等 |
| V0.9 | ESP32 多尺寸/墨水屏、低性能优化 | 规划；硬件与协议兼容、恢复和更新 |
| V1.0 | 稳定 SDK/协议、迁移、权限、可复现发布 | 规划；真机矩阵、恢复演练、安全检查 |

NFC、MagSafe、自研 PCB 为独立后续探索。保留旧 APM v0.1.0 预发布用于历史追溯，不作为 Pixora 验收证据。

## 2026-10-15 progress / 进度更新

Provider/mode scoped device tokens, digest-only storage, expiry and live revocation are implemented ahead of the V0.4 milestone. Local CLI administration only; pairing UI, field-level policies and server layout synchronization remain planned. Linux Docker runtime CI passed for the previous baseline; this increment is subject to its own CI. Physical-phone/PVE acceptance remains open.


## V0.2 development update / 开发进度

Observation v2, additive migration with private backup, v1 quota backfill, Linux CPU/memory/root-disk metrics, private system Widget and bounded paginated history are implemented on the V0.2 development branch. Dedicated PVE API integration is deferred; the first connector is Linux host read-only collection. Existing device scopes remain unchanged. See [contracts and rollback](V0.2.md). Deployment and phone acceptance are separate gates; no stable V0.2 Release is claimed.

V0.1 operations now include VPS HTTPS, independent home collection, verified recovery, certificate renewal and isolated SQLite restore. User iPhone installation/session/rotation/continued-display checks passed; Android 13 portrait/landscape display passed owner acceptance; Android installation remains untested. Earlier status rows above are historical baseline descriptions.

## V0.4 first increment / 首轮增量

See [device profiles, restrictive policies and rollback boundary](V0.4.md). V0.3 Orbit/settings were accepted on iPhone; V0.4 has its own acceptance gate. No stable Release is claimed.


## V0.4 dev3 update / 更新

Implemented: administrator-only web device inventory, per-device pairing/revocation, restrictive policy editing and atomic batch profile publication. Local overrides keep precedence; arbitrary widget composition, online presence and one-use invitations remain future work. See [administrator guide](ADMIN.md) / [管理员指南](ADMIN.zh-CN.md). Deployment and owner acceptance are separate from automated checks. Package version 0.4.0.dev3 remains Early Development.
