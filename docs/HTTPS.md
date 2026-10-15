# Private LAN HTTPS / 局域网 HTTPS

A domain with a publicly trusted certificate can serve a private LAN address. DNS-01 validation proves domain control without opening inbound WAN HTTP ports. The hostname must resolve to the correct LAN server on every display; VPN fake-IP DNS can require a narrowly scoped hostname mapping and exact DIRECT rule. Keep all other proxy policies intact. Back up the active proxy configuration before changes.

中文：域名可指向局域网地址，并通过DNS-01获得受信证书，无需向公网转发端口。每台显示设备都须能正确解析/路由；启用fake-IP的VPN可能需要精确域名Hosts映射及DIRECT规则。不要为此关闭全局VPN或TLS校验。

## Certificate and proxy

Use a real domain you control. Obtain a certificate with a DNS authenticator, then mount the full certificate directory read-only (including archive/live symlink targets) into a reverse proxy. Bind the proxy host port to the intended LAN interface; keep the API container private on its Compose network or loopback. Expose HTTPS only, retain bearer authentication and exclude credential headers from logs. No mandatory cloud hosting is involved.

Caddy example (replace the example hostname and certificate paths):

```caddyfile
{
    admin off
    auto_https off
}
https://display.example.com {
    tls /certs/live/display.example.com/fullchain.pem /certs/live/display.example.com/privkey.pem
    reverse_proxy monitor:8000
}
```

With the official Caddy binary, a deployment dropping all capabilities may need to add only NET_BIND_SERVICE, including for execution of its file capability. Keep no-new-privileges and resource/log limits. Do not remove isolation wholesale to fix startup.

## Renewal is an explicit requirement

A manually entered DNS-01 TXT challenge does not by itself automate future renewal. Keep the private key private, record the actual notAfter date in the operator timezone and renew before expiry. For manual renewal, obtain a new challenge, publish/verify its TXT record, complete issuance and restart/reload only the TLS proxy. Do not reuse a stale challenge or approval flag. A certificate renewed on disk is not proof the running proxy has loaded it: verify the served certificate afterward.

中文：手工TXT验证不会自动续期。须记录证书准确到期时间，提前重新验证并仅重载TLS代理，再核对实际服务证书。不要重用旧验证值/批准标志。若需要自动DNS续期，应由用户明确授权最小DNS权限凭据；本项目不默认为用户创建长期域名API密钥。

## Acceptance

Validate normal hostname HTTPS with default certificate and hostname checks. Check public page/PWA assets, 401 without a device token, 200 with an authorized scoped token and 403 for forbidden modes. In the browser verify a secure context, active registered service worker and actual quota provenance. Browser checks do not prove installation, wake lock, background/resume or old-OS compatibility on physical phones.

2026-10-16: actual LAN target passed the checks above over TLS 1.3 with a publicly trusted domain certificate and live Codex observations. Physical phone installation/resume and automated renewal remain separate unaccepted gates. Operational domain/IP, token values, certificate private key and account quota screenshots are excluded from this repository.

References: [Let's Encrypt challenges](https://letsencrypt.org/docs/challenge-types/), [Certbot manual and renewal](https://eff-certbot.readthedocs.io/en/stable/using.html#manual), [Caddy TLS](https://caddyserver.com/docs/caddyfile/directives/tls).
