# Display mode / 显示模式

Display mode has its own **Clock + quota** and **Quota only** layouts. It keeps the configured theme, real/demo labels, source, collection time, stale/offline state and a compact sync footer. Landscape phone screens place quota windows side by side. Display settings are tucked into a small toolbar; Exit display restores the configuration screen without clearing the current in-memory connection.

The layout choice is saved locally; credentials and observations are not. Shared-screen privacy still overrides display layouts and hides quota. Returning from a hidden tab attempts to reacquire Screen Wake Lock; the toolbar reports requesting, active, paused, unsupported or failed. An active lock is a browser signal, not a guarantee against device sleep. A retry button is available under Display settings. Fullscreen is best effort; iPhone users can open the installed home-screen app to reduce browser chrome. No browser security or OS power policy is bypassed.

显示模式 → 显示设置，可选择“时钟＋额度”或“仅额度”。手机横屏自动并排展示额度窗口，竖屏纵向排布。状态、来源、采集时间仍可见。常亮提示反映浏览器授权情况，不保证系统不会休眠。iPhone 可通过 Safari 分享菜单添加到主屏幕。

Validation: desktop Chromium viewport checks at 390×844 and 844×390, live Codex observations, layout switching and no horizontal overflow. Real iPhone/Android wake lock, sleep recovery and installed PWA still require separate device acceptance. Reloading clears the memory-only token: rescan your private pairing QR to reconnect.
