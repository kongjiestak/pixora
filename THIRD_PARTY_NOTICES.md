# Third-party notices

Project source is MIT; dependencies retain their own licenses. The following inventory is read from installed versions matching the lockfiles, not a legal opinion.

The pulse icons are original project-generated artwork. No downloaded logos, photos, or fonts are bundled; the UI uses system fonts.

## Python dependencies

pip retains each distribution’s original license. certifi (MPL-2.0) is installed unchanged; none of its source is copied into this repository. OpenTelemetry is Apache-2.0, typing_extensions PSF-2.0; these are not relicensed as MIT.

| Package | Version | License |
|---|---|---|
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.15.1 | MIT |
| certifi | 2026.7.22 | MPL-2.0 |
| click | 8.5.0 | BSD-3-Clause |
| fastapi | 0.143.1 | MIT |
| h11 | 0.16.0 | MIT |
| httpcore | 1.0.9 | BSD-3-Clause |
| httpx | 0.28.1 | BSD-3-Clause |
| idna | 3.20 | BSD-3-Clause |
| iniconfig | 2.3.1 | MIT |
| opentelemetry-api | 1.45.1 | Apache-2.0 |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pluggy | 1.6.0 | MIT |
| pydantic | 2.14.1 | MIT |
| pydantic_core | 2.50.1 | MIT |
| Pygments | 2.21.0 | BSD-2-Clause |
| pytest | 9.1.1 | MIT |
| starlette | 1.8.0 | BSD-3-Clause |
| typing-inspection | 0.4.4 | MIT |
| typing_extensions | 4.16.0 | PSF-2.0 |
| uvicorn | 0.54.0 | BSD-3-Clause |

## npm packages (runtime and build tools)

| Package | Version | License |
|---|---|---|
| @babel/helper-string-parser | 7.29.7 | MIT |
| @babel/helper-validator-identifier | 7.29.7 | MIT |
| @babel/parser | 7.29.9 | MIT |
| @babel/types | 7.29.8 | MIT |
| @esbuild/darwin-arm64 | 0.25.12 | MIT |
| @intlify/core-base | 11.4.14 | MIT |
| @intlify/devtools-types | 11.4.14 | MIT |
| @intlify/message-compiler | 11.4.14 | MIT |
| @intlify/shared | 11.4.14 | MIT |
| @jridgewell/sourcemap-codec | 1.6.0 | MIT |
| @rollup/rollup-darwin-arm64 | 4.64.7 | MIT |
| @types/estree | 1.0.9 | MIT |
| @vitejs/plugin-vue | 5.2.4 | MIT |
| @vue/compiler-core | 3.5.44 | MIT |
| @vue/compiler-dom | 3.5.44 | MIT |
| @vue/compiler-sfc | 3.5.44 | MIT |
| @vue/compiler-ssr | 3.5.44 | MIT |
| @vue/devtools-api | 6.6.4 | MIT |
| @vue/reactivity | 3.5.44 | MIT |
| @vue/runtime-core | 3.5.44 | MIT |
| @vue/runtime-dom | 3.5.44 | MIT |
| @vue/server-renderer | 3.5.44 | MIT |
| @vue/shared | 3.5.44 | MIT |
| csstype | 3.2.3 | MIT |
| entities | 7.0.1 | BSD-2-Clause |
| esbuild | 0.25.12 | MIT |
| estree-walker | 2.0.2 | MIT |
| fdir | 6.5.0 | MIT |
| fsevents | 2.3.3 | MIT |
| magic-string | 0.30.21 | MIT |
| nanoid | 3.3.20 | MIT |
| picocolors | 1.1.1 | ISC |
| picomatch | 4.0.7 | MIT |
| postcss | 8.5.30 | MIT |
| rollup | 4.64.7 | MIT |
| source-map-js | 1.2.2 | BSD-3-Clause |
| tinyglobby | 0.2.17 | MIT |
| vite | 6.4.4 | MIT |
| vue | 3.5.44 | MIT |
| vue-i18n | 11.4.14 | MIT |

Original npm runtime copyright/license texts are included in [docs/licenses/npm-runtime.txt](docs/licenses/npm-runtime.txt) for redistribution of the compiled web app. Platform-specific optional Rollup/esbuild binaries are MIT and retain their licenses in the installed packages. No third-party trademark rights are implied.

The @vue/devtools-api 6.6.4 npm archive omits a root license text; its original MIT notice was retrieved from the [tagged upstream source](https://github.com/vuejs/vue-devtools/blob/v6.6.4/LICENSE) and preserved with the other runtime notices.

### ESP32 bilingual UI font

`firmware/esp32/main/pixora_cjk_18.c` is a bitmap subset derived from Noto Sans CJK SC Regular Sans2.004, © 2014–2021 Adobe, licensed under SIL OFL 1.1 rather than the application MIT license. See `firmware/esp32/fonts/README.md` and `OFL.txt`.
