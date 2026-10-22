# Third-party components

Pixora client source is covered by the repository MIT license. No VibePulse code/assets are incorporated.

Dependencies are obtained from upstream by ESP-IDF Component Manager; `dependencies.lock` pins exact versions/hashes. Upstream copyright and notices remain applicable, independently of Pixora's license:

- ESP-IDF v5.5.5: Apache-2.0 and bundled third-party component notices, including cJSON (MIT).
- Waveshare `esp32_s3_touch_amoled_2_16` 2.0.1 and panel/touch BSP dependencies: retain their supplied licenses/notices (BSP Apache-2.0).
- LVGL 9.3.0: MIT; retain applicable font notices supplied under `demos/widgets/assets/fonts/license` and the LVGL source tree when distributing those fonts.
- Additional transitive graphics/codec/utility components: retain their individual license files from the exact managed-component versions. Do not infer their licensing from the BSP or Pixora license.

Local review bundles collect upstream license/notice files. A distributable firmware release needs a final linked-component/font notice review; no stable binary Release is claimed at this prototype stage. Do not publish private NVS, original flash backups or account data as part of a firmware bundle.

Primary sources:
https://github.com/espressif/esp-idf/tree/v5.5.5
https://github.com/waveshareteam/Waveshare-ESP32-components
https://github.com/lvgl/lvgl/tree/v9.3.0
