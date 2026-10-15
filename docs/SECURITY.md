# Pixora security / 安全

Single-user, single trust domain prototype. A stolen write token can forge observations; `source` is a trusted collector assertion, not cryptographic provenance. A read token grants all currently stored quota observations; there is no per-device scope/revocation or tenant isolation. Do not provision untrusted public displays. Shared-screen UI clears token, cancels requests and filters private widgets, but is not server ACL.

Use distinct random 32+ character `PIXORA_READ_TOKEN` and `PIXORA_WRITE_TOKEN`. Bearer header only, no query tokens; no CORS by default. Tokens/observations remain in page memory, settings/locale in localStorage. PWA caches only public assets, never API. Restart after token rotation; every device sharing that token is affected. No server control API is implemented.

Codex authentication stays with the installed CLI. Pixora does not open auth.json, collect cookies/prompts or send raw RPC. The query can cause normal CLI credential refresh. `--print-only` outputs account observations: keep private. Snapshot fields/body size and time ordering are validated; no account data is distributed. Backups and credentials must be separate. The legacy `APM_*` fallback is supported; avoid conflicting variables.

Default service binds loopback. HTTPS is required outside loopback, except an explicitly trusted encrypted private VPN with collector `--allow-private-http`. Use a reverse proxy with TLS, body/connection/rate limits, and logs that exclude Authorization. Do not expose Codex app-server. The app does not include internet-scale rate limiting, audit logging or endpoint isolation.

Vulnerability reporting: contact the owner via [GitHub profile](https://github.com/kongjiestak) first, without disclosing secrets. A dedicated confidential intake channel is not established and no SLA is promised. If no private contact is available, open a minimal issue requesting a private channel; do not include exploit credentials or sensitive data. Do not claim a security audit or production hardening from these checks.

中文：首版单信任域，只读令牌可读全部额度，共享界面不等于服务端权限。令牌泄漏后更换并重启，所有共享该令牌的设备都受影响。公网必须配置 TLS 与代理限流；不暴露 Codex 自身端口。不上传 Cookie、凭据、原始 RPC；打印观测也需保密。漏洞先通过维护者主页联系，尚无专用私密渠道与响应承诺，公开 Issue 不贴敏感细节。
