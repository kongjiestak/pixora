# Codex 实现任务与验收

最新范围以 ARCHITECTURE.md 和 ROADMAP.md 为准，替代仅 AI/ESP32 原型需求。

| ID | 工作 | 实现位置 | V0.1 验收 |
|---|---|---|---|
| T01 | 数据模型与来源/时间/过期 | apm/models.py, server.py | schema 严格校验、UTC、未来/回放拒绝 |
| T02 | Codex 真实额度验证 | apm/plugins.py | 本机 JSON-RPC initialize→account/rateLimits/read，多桶/空值兼容；不传凭据 |
| T03 | ChatGPT 边界 | models.py | 真实成功状态拒绝，不用 demo/消耗量猜额度 |
| T04 | Mac 采集客户端 | collector.py, examples/ | 单次/常驻、超时、退避、HTTPS、错误状态 |
| T05 | 存储与读取 | server.py | SQLite 重启保留、只读/写令牌隔离、请求限量 |
| T06 | Vue 响应式终端 | web/src/ | 手机横竖屏、断线/过期/来源/演示标签 |
| T07 | Widget 引擎 | widgets.js, Widget.vue | registry + 预设组合；三种组件可复用 |
| T08 | 设备设置与共享 | App.vue | 本机保存名称/布局/主题；共享清令牌/隐藏私人组件 |
| T09 | PWA/Kiosk | public/, App.vue | manifest、图标、Service Worker；无 API 缓存；全屏能力降级 |
| T10 | 自托管 | Dockerfile, compose.yaml | 多阶段构建、非 root、持久卷、健康检查 |
| T11 | 开源交付 | README/贡献/许可/示例环境 | 无凭据压缩包、启动步骤、验证报告 |
| T12 | 自动测试 | tests/, web/tests/ | API/模型/插件/隐私过滤/格式检查 + 前端生产构建 |

手工验收：真机 iPhone Safari 添加主屏幕；Android Chrome 安装；横竖屏/全屏退出/休眠恢复；PVE Docker 构建与卷恢复。当前无法验收项必须在 VERIFICATION.md 标明，不以 manifest 存在推断真机通过。

后续任务：Observation v2 migration、设备 ACL、通用插件配置、Widget 编辑器、服务端设备配置、个人信息连接器、审计控制，各依赖稳定版本化 schema 和权限设计。禁止悄悄复用采集 token 作为控制 token。
