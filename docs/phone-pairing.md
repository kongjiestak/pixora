# Private phone pairing / 手机私密配对

Administrators may encode an HTTPS dashboard URL with `#token=DEVICE_READ_TOKEN` in a locally generated QR code. Only scoped read-only device tokens belong here. Treat the QR as a credential: never publish it, send it to an online QR service, or place it in Git.

The app consumes the fragment on initial page load, removes it with history.replaceState, selects real observations and connects. Fragments are excluded from HTTP requests; scanners and browser extensions may still read the original URL. Tokens and observations remain memory-only. Reloading requires pairing again. This is a basic private onboarding bridge, not one-time exchange or persistent login. Revoke the device locally if a QR is exposed.

管理员本地生成手机专用只读二维码；默认网址不会自动获得私密数据。扫码后应看到 Codex、真实来源及采集时间；离线/过期提示不等于实时成功。二维码是可重复使用的凭据，不能公开，刷新后需重新扫码。真机安装及持续显示需单独验收。
