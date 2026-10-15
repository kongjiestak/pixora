# AI Pocket Monitor · V0.1

自托管、硬件无关的个人信息与监控平台。Mac 采集 → FastAPI + SQLite → Vue 3 / PWA；旧 Android、iPhone、iPad 与浏览器都是第一类显示终端。**不依赖 VPS，不需要购买硬件。**

状态：可运行原型；真实 Codex 查询路径已在开发 Mac 实测。ChatGPT 真实额度未接入。硬件固件不在本版范围，见更新路线图。

## 5 分钟本机运行

需要 Python 3.11+、Node 20.19+ 或 22.12+。在仓库根目录执行：

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-lock.txt
pip install --no-deps .
python scripts/setup_env.py
set -a
source .env
set +a
npm --prefix web ci
npm --prefix web run build
uvicorn apm.server:create_app --factory --host 127.0.0.1 --port 8000
```

打开 http://127.0.0.1:8000 ，从本地 `.env` 复制 **APM_READ_TOKEN** 填入网页。Token 仅保存在该页内存。网页每 30 秒刷新。

第二个终端，在同一目录：

```sh
source .venv/bin/activate
set -a
source .env
set +a
# 无需 Codex 即可体验，网页切换到“模拟演示”
apm-collect --plugin demo --once
# 已安装并登录 Codex 的 Mac：真实额度（网页选择“真实观测”）
apm-collect --plugin codex --once
# 持续采集，默认每 120 秒，失败指数退避，Ctrl-C 停止
apm-collect --plugin codex
```

未找到 `codex` 时设置 `APM_CODEX_BIN` 为实际可执行文件的绝对路径。客户端沿用 Codex CLI 当前登录；需先自行完成 Codex 登录。可只在本机检验：`apm-collect --plugin codex --print-only`，不会推送。

首次数据为空是正常状态。Demo 固定值有显著标签，不能证明账号额度。真实模式不自动回退 demo。CLI 查询失败时上传 error 状态、清除该来源当前窗口；Mac 休眠或无法连接服务器时则保留旧快照并标为过期。

## Docker / PVE

```sh
python3 scripts/setup_env.py  # 已存在 .env 则跳过，不会覆盖
# 服务及已编译网页使用同一端口
 docker compose up -d --build
 docker compose ps
```

默认仅监听宿主 127.0.0.1。SQLite 使用 `apm-data` 命名卷，`docker compose down` 保留数据，**down -v 会删除数据**。完整步骤、异地联网与 Mac 后台运行见 [DEPLOYMENT](docs/DEPLOYMENT.md)。

## 数据与 API

- 写：`POST /api/v1/snapshots`，仅采集 token。
- 读：`GET /api/v1/device?mode=real`，仅设备 token；演示用 `mode=demo`。
- 健康：`GET /healthz`。交互规范 `/docs`，OpenAPI `/openapi.json`。
- 使用 `Authorization: Bearer <token>`；不要将 token 放查询参数。
- 服务端读数含原采集时间、接收时间、年龄、过期标志。默认 600 秒过期；窗口重置时间已到也视为过期，不自动猜测新额度。
- 多桶/多窗口原样区分，剩余百分比为 `100-usedPercent`；不是 API 账单余额，也不是精确剩余请求次数。

## 真实采集可行性与限制

内置插件使用本机 `codex app-server --stdio` 的 `account/rateLimits/read`。优先多桶 `rateLimitsByLimitId`，兼容单桶；nullable 值表示不可用。本机测试见 [验证报告](docs/VERIFICATION.md)。

这是 Codex 服务提供的账户额度视图，**不能据此推断 ChatGPT 网页里所有模型的额度**。查询受 CLI 版本、账号、网络和上游可用性影响，不保证永久兼容。不会通过会话 token 计数反推额度，也不抓取未公开网页接口。

官方依据：[Codex App Server](https://learn.chatgpt.com/docs/app-server)，其中说明额度查询方法及窗口字段。实验性 CLI 接口应随版本复核。ChatGPT 独立 provider 首版保持不可用；不索取浏览器 Cookie。

## 开发与测试

```sh
pytest -q
npm --prefix web test
npm --prefix web run build
# UI 热更新；需另启 8000 服务
npm --prefix web run dev
```

新增采集器：实现 `Collector.collect()`、返回 `Snapshot`，在 `apm/plugins.py` 的 `PLUGINS` 显式注册，并补边界测试。当前协议固定两个 provider，新增服务时同步扩展 schema、API 和 UI；不是任意不可信插件加载器。

## 手机与显示模式

浏览器打开服务，设置设备名称、明暗主题与总览/专注/公共布局；可进入全屏显示，或使用 `/?kiosk`。全屏与屏幕常亮尽力调用平台能力，不支持时仍可浏览。系统的自动锁屏需自行设置，iOS 可使用引导式访问。

HTTPS（或本机 localhost）下可安装 PWA。Android Chrome 使用安装菜单，iPhone/iPad Safari 使用“分享→添加到主屏幕”。局域网 HTTP 可打开网页，但无法保证安装/离线壳。首次在线访问后缓存公共壳，不缓存 API；重开需要重新输入只读 token。旧手机实际兼容范围尚待真机验收，建议先用可更新的系统浏览器。

共享屏幕选项会断开、清除内存令牌并隐藏私密额度 Widget；这是本机保护，首版不含服务器设备 ACL。设备名称、主题、预设布局只保存在当前浏览器。

当前 Widget：本机时钟、AI 额度、同步状态。五大模式扩展接口已规划；完整个人信息和自动化功能留待后续版本。

[总体架构](docs/ARCHITECTURE.md) · [V0.1–V1.0 路线图](docs/ROADMAP.md) · [详细实现任务](docs/CODEX_TASK.md) · [验证结果](docs/VERIFICATION.md)

文档：[技术需求](docs/REQUIREMENTS.md) · [Codex 主任务书](docs/CODEX_TASK.md) · [安全边界](docs/SECURITY.md) · [贡献说明](CONTRIBUTING.md)

MIT License。欢迎先从数据插件、界面和市售开发板适配参与。
