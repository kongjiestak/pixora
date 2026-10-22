# Pixora UI CJK subset

`main/pixora_cjk_18.c` and `main/pixora_cjk_24.c` are 18px/24px bitmap subsets for the bilingual screen UI, generated from Noto Sans CJK SC Regular, tag **Sans2.004**. Original font copyright: **© 2014–2021 Adobe (http://www.adobe.com/).** The generated font remains under **SIL OFL 1.1**, independently of Pixora's MIT code license; see `OFL.txt`. The derivative identifiers are `pixora_cjk_18` / `pixora_cjk_24`.

Source: https://github.com/notofonts/noto-cjk/tree/Sans2.004

Original OTF SHA256: `2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b`.

Reproduce with the downloaded upstream `Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf`, `lv_font_conv@1.5.3` (MIT converter, build tool only), and this repository's `ui-zh.symbols.txt`:

```sh
lv_font_conv --font NotoSansCJKsc-Regular.otf --symbols "$(cat fonts/ui-zh.symbols.txt)" \
  --size 18 --bpp 4 --no-compress --format lvgl --lv-include lvgl.h -o main/pixora_cjk_18.c
```

Run from `firmware/esp32`. Montserrat remains the Latin/symbol font; LVGL's existing CJK fallback remains for characters outside the UI subset. Arbitrary names can still contain unsupported glyphs; this is not a full CJK font.

Repeat the conversion with `--size 24` and output `main/pixora_cjk_24.c` for the larger perimeter font.
