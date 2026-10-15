# V0.1 验证报告 · 2026-10-15

本次在 MacBook Air M2 本机执行，不含远程部署或真机安装声明。

| 项目 | 结果 |
|---|---|
| Codex 真实查询 | PASS：本机 codex app-server 初始化及 account/rateLimits/read，返回 2 个真实窗口；不在开源包包含账号值 |
| Mac 真实客户端 | PASS：--plugin codex --once 推送本机 8017 服务 |
| 真实 HTTP 闭环 | PASS：规范化快照→POST→SQLite→只读 GET，Codex ok，ChatGPT unavailable |
| 演示客户端闭环 | PASS：demo --once，两个来源均显式 demo |
| Python | 16 passed；1 个 Starlette TestClient/httpx 弃用警告，无失败 |
| 前端 | 4 passed；Vue/Vite 生产构建成功（最终 JS 约 76 KB / gzip 30 KB） |
| 静态资源 | 首页、manifest、worker、192/512 图标 HTTP 200；worker 语法检查成功 |
| 权限 | 无 token 返回 401；读写隔离、空值、过期、持久化、回放/未来值、超限测试通过 |
| 浏览器 | 内置浏览器实际连接演示、共享开关隐藏额度并清除输入、375×812 竖屏和 812×375 横屏检查、Kiosk 进入成功；修正横屏时钟换行 |
| Compose | docker compose config --quiet 通过 |
| Docker 构建/容器运行 | 未完成：本机 Docker daemon 未启动；未实际运行容器，CI 保留 docker build 检查 |
| Android / iPhone / iPad PWA | manifest/图标/worker 已实现；尚未真机验收安装、长期常亮和旧系统兼容 |
| PVE / 日本 VPS | 未部署，无需购买 VPS；提供自托管配置和部署指南 |

真实采集依据：[官方 Codex App Server](https://learn.chatgpt.com/docs/app-server)。额度是 Codex 的账户限额快照，不代表 ChatGPT 全模型个人额度。ChatGPT 真实来源始终不可用。

共享模式为本机显示过滤，首版只有单信任域共享只读令牌，没有服务端逐设备 ACL。PWA 离线只缓存公共壳，不缓存 API 与 token，重启需重新输入 token。
