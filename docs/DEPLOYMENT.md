# 部署与运行指南

## 1. 本机先验收
按 README 创建虚拟环境、生成 .env、构建网页并启动服务。demo 只写模拟流；网页要选择模拟演示。真实数据需要安装并登录 Codex CLI。

## 2. 家中 PVE
PVE 宿主建议保持管理用途，在 Debian/Ubuntu Linux VM 中安装 Docker Engine + Compose 插件；不要直接在 PVE 管理宿主安装应用栈。将仓库复制到 VM，生成 .env 后 `docker compose up -d --build`。本次未取得用户 PVE 访问，不声称已经部署家中服务器。

服务默认绑定 VM 回环 127.0.0.1。先在 VM 用 `/healthz` 检查，再配置私有入口。

## 3. 无 VPS 的异地连接
推荐在 PVE 的 VM 与 Mac 安装并加入同一个私有 VPN（例如用户已有的组网服务）。私有 VPN 的厂商控制面/中继可能是外部依赖，但无需租 VPS；也可使用已有路由器 VPN，后者是否能入站取决于公网地址/CGNAT。

将 VM 的 VPN 地址放入 `.env`：

```sh
APM_BIND=100.x.y.z
```

这只是示例，必须换成实际 VM 地址。重启 Compose 后仅在 VPN 网卡提供服务，并用防火墙只允许自己的 VPN 成员。Mac 设置：

```sh
export APM_SERVER=http://100.x.y.z:8000
# 仅在确认经加密的可信私网承载时使用
apm-collect --plugin codex --allow-private-http
```

Mac 所在 Wi-Fi 不必能从家中入站；Mac 主动访问服务器。但 VPN、防火墙与家中在线状态必须正常。IPv4 地址不是自动安全边界。公开 HTTPS 入口才适合不具备 VPN 网关的独立 ESP32，这属于后续可选部署；首版不替用户开公网端口。

ESP32 不能直接照搬 Mac 的 VPN 软件。未来跨 Wi-Fi 使用可选：旅行路由器/VPN 网关，或安全公开 HTTPS 反代（可在家中，或选用 VPS/隧道）。在这些条件未满足之前，不保证任意 Wi-Fi 可读。

## 4. 可选 HTTPS 反向代理
可在现有家庭网关/反向代理上为 8000 配 HTTPS，正确配置证书与访问控制。服务仍回环绑定或内网绑定。代理不得记录 Authorization，设置请求体上限、限流和连接限制。客户端 `APM_SERVER=https://实际域名`，禁止跳过证书验证。当前网页只使用同源 API，不需开启 CORS。

## 5. Mac 后台启动（可选，先完成前台验证）
复制 `examples/com.ai-pocket-monitor.collector.plist` 到 `~/Library/LaunchAgents/`，修改绝对路径。创建一个仅含 `APM_SERVER` 和 `APM_WRITE_TOKEN` 的本机配置文件，权限 0600；不要把 PVE 的读写全量 .env 无谓复制给其他设备。编辑 wrapper 中路径。plist 不包含凭据，wrapper 从本地文件读取。不要把示例直接加载；确认路径后再 `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.ai-pocket-monitor.collector.plist`。停止用 `launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.ai-pocket-monitor.collector.plist`。失败退避最多约一小时。休眠时不采集，唤醒后在下一周期恢复。

## 6. 备份、升级、撤销
停止应用后复制数据卷中的 apm.sqlite（或用 sqlite 在线备份 API，不能只复制运行中主文件而忽略 WAL）。凭据单独备份。更新代码后重新 build/up，保留卷。替换泄漏 token 后重新创建服务并更新对应客户端；首版所有读设备共享一个读 token，不支持逐设备撤销。

同一服务只对应一个账户。切换 Codex 登录账户需使用新的服务实例/数据卷，防止不同账号读数混杂。日志不打印服务器响应体或凭据。排障先看 `docker compose logs --tail 50`、健康检查和客户端泛化错误，不要上传 .env 或 Codex 认证目录。
