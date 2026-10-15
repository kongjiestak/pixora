# Pixora 路线图

[English](ROADMAP.md) | [简体中文](ROADMAP.zh-CN.md)

按验收推进，无固定日期。当前 Early Development；0.1.0.dev1 只是开发元数据，不是正式版本完成声明。

| 里程碑 | 工作 | 验收 / 状态 |
|---|---|---|
| V0.1 | Codex → API → Web、英中文、Widget、PWA/Kiosk、本机隐私 | 基础已实现，真机安装、部署运行、长期恢复验收仍待完成，本轮不创建 Pixora Release |
| V0.2 | 通用 Observation v2、迁移、PVE/主机只读指标、历史 | 规划；迁移可回滚、首个真实系统 Widget |
| V0.3 | CI/GitHub、日历/待办/天气/RSS | 规划；来源时间、隐私和真实终端矩阵 |
| V0.4 | 布局编辑器、服务端设备配置、逐设备令牌/撤销 | 规划；公共设备 API 无法读到私密字段 |
| V0.5 | 邮件摘要、生活/账单提醒、出行、预算、目标 | 规划；最小留存、撤销、屏幕锁 |
| V0.7 | Home Assistant、自动化交互控制 | 规划；独立权限、审计、确认、幂等 |
| V0.9 | ESP32 多尺寸/墨水屏、低性能优化 | 规划；硬件与协议兼容、恢复和更新 |
| V1.0 | 稳定 SDK/协议、迁移、权限、可复现发布 | 规划；真机矩阵、恢复演练、安全检查 |

NFC、MagSafe、自研 PCB 为独立后续探索。保留旧 APM v0.1.0 预发布用于历史追溯，不作为 Pixora 验收证据。

## 2026-10-15 progress / 进度更新

Provider/mode scoped device tokens, digest-only storage, expiry and live revocation are implemented ahead of the V0.4 milestone. Local CLI administration only; pairing UI, field-level policies and server layout synchronization remain planned. Linux Docker runtime CI passed for the previous baseline; this increment is subject to its own CI. Physical-phone/PVE acceptance remains open.
