# Pixora 架构

[English](ARCHITECTURE.md) | [简体中文](ARCHITECTURE.zh-CN.md)

单体仓库、软件优先。Mac 可信连接器 → 写令牌 / FastAPI → SQLite WAL → 只读设备 API → Vue 3 + Vue I18n → Widget / 浏览器与手机 PWA。未来 ESP32 使用同一版本化读接口，五大模式是扩展分类而非五套已完成应用。

连接器实现 `Collector.collect() -> list[Snapshot | Observation]`，目前注册 Codex、demo 和 Linux system，不加载任意外部代码。v1 数据模型包含 provider/source/mode/status/observed_at/windows/reason_code；采集时间可用 collected_at 写入，读取同时返回两种名称，附接收时间、年龄、过期。当前明确限定额度来源，不把系统指标塞进额度字段。

Widget 注册字段为 titleKey/mode/sensitivity，组件输入 data/clock/connected，展示与语言解耦。UTC 存储、Intl 按区域和本机时区格式化。时钟、额度、同步状态和三套布局已实现；名称/主题/布局/共享配置只存当前浏览器。共享清除令牌与未完成请求，不是服务端 ACL。

SQLite 保留 v1 最新额度，并新增 v2 有限历史（每流最多 1000 条），提供分页查询；迁移先备份，再回填现有额度。事务拒绝旧观测覆盖新值，操作后关闭连接。令牌区分读写，但仍是单用户、单信任域。

PWA 只缓存公共壳与资源，不缓存 API、令牌或观测，HTTPS 独立设备可用 Secure HttpOnly 会话恢复；本机手动令牌仍仅在内存。HTTPS/localhost 才支持完整能力，全屏与常亮视浏览器支持。无已完成的拖拽编辑器、服务端设备注册或 ESP32 模拟器。

已实现数值型 Observation v2，包含 connector/entity ID、category、mode、metrics/value/unit、采集/失效时间、source 和 sensitivity，提供迁移和旧读接口兼容；见 [V0.2](V0.2.md)。五大模式可混合布局；PVE/NAS、CI、日历/待办/天气、个人摘要、Home Assistant 尚待实现。控制需独立授权、审计与幂等命令通道。

服务端逐设备来源/模式权限、期限和撤销已实现；字段权限与公共数据裁剪仍待实现。Mac 可独立运行；PVE Linux VM 可常驻服务，Mac 休眠则采集过期，VPS 可选。多尺寸 ESP32、NFC、MagSafe、自研 PCB 后续探索。

V0.3 adds optional bounded plain-text entries to Observation v2, independent github/rss/tasks scopes, and read-only configured collectors. SQLite remains v2; old device grants do not expand. See [V0.3 implementation, limits and acceptance](V0.3.md). Calendar/weather/editor remain future tasks.

## V0.4 device profiles / 设备配置

设备端新增只读 `/api/v2/device-config`，管理员本地 CLI 发布推荐布局和收紧策略。SQLite 新增独立 device_profiles 表，旧令牌默认保持原范围；实体/连接器/指标/额度窗口及条目投影在 v1/v2/历史 API 服务端过滤，并对已存在 Cookie 会话即时生效。浏览器 Orbit 编辑器仅保存本地布局覆盖，可恢复服务端推荐；不增加数据权限。详细契约与回退隐私边界见 [V0.4](V0.4.md)。
