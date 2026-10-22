# Native LVGL UI smoke test

Runs the production `screen_ui.c` in LVGL 9.3 with a synthetic pointer, local in-memory NVS and a synchronous software display. ASan/UBSan cover repeated settings/theme navigation, language persistence and the per-second digital-clock colon. This does not validate the ESP touch controller, panel DMA, Wi-Fi or physical rotation.

With ESP-IDF's host CMake on PATH and `IDF_PATH` set (not an ESP cross compiler):

```sh
cmake -S firmware/esp32/host-tests/ui -B /tmp/pixora-ui-smoke
cmake --build /tmp/pixora-ui-smoke -j 4
/tmp/pixora-ui-smoke/ui-smoke
```

The executable also writes synthetic framebuffer PPMs under `/tmp/pixora-ui-*`. These contain test time/status, not production data or proof of physical-device acceptance.

The regression now skips hidden cached controls, traverses the visible three-face carousel 18 times, checks activity expiry and verifies first-tap settings after idle.
