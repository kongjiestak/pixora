# V0.5.1 Mac BLE 桥接：开发中

目标：出门时屏幕由普通USB电源供电，Mac联网后通过BLE发送已授权的额度、天气和可选本机活动；不要求咖啡厅Wi-Fi、不共享Mac登录密码、不把上游账号凭据交给屏幕。当前已加入安全封包、GATT接收端和Mac发送端；无线闭环仍待实物验证，不能仅凭构建就拔掉数据线作为验收。

## 当前代码

- `clients/ble_wire.py`：AES-256-GCM封包、有界流重组；支持任意GATT分片边界。
- `firmware/esp32/main/ble_wire.c`：同一协议的C接收器，编入ESP32构建；由`ble_bridge.c`接入NimBLE/GATT路径。
- `clients/mac_ble_probe.py`：只读服务扫描，无配对、无凭据传输、不显示附近设备身份；整体20秒超时。
- `clients/mac_ble_bridge.py`：通过签名hello认证目标，读取同一HTTPS限权数据，按协商MTU分片加密发送，并验证绑定会话/序号/事件的签名ACK。
- `firmware/esp32/main/ble_bridge.c`：单连接GATT、逐连接随机nonce、10秒传输超时检查、错误断连、重连清空会话与缓冲；默认关闭，在屏幕“连接与数据来源”中单独开启Mac蓝牙。
- 现有USB协议继续负责内层签名、会话绑定、序列与数据校验。BLE外层解密成功不代表数据可展示，集成时必须继续执行这些检查。

## 协议 v1（未冻结）

字节顺序：`PBL1`（4）+ 随机IV（12）+ 明文长度（4，大端）+ 密文（n）+ GCM标签（16）。头部20字节全部作为AAD。`1 <= n <= 20000`，整个接收缓冲区最多20036字节，错误后保持拒绝状态，必须显式重置；不静默扫描下一个魔数。内层为现有`PXUSB1`签名帧，BLE使用每次连接生成的独立会话nonce，不能复用USB会话。

加密密钥：`SHA256(b"Pixora BLE v1 key\x00" + scoped_display_token_ascii)`。令牌必须是32–128位ASCII字母、数字、下划线或连字符；来自服务端随机生成的独立显示授权，不接受用户密码或管理员令牌。每包通过系统安全随机源生成新96位IV；生产接口不允许调用者指定IV。公开测试向量仅使用合成`A*32`令牌与固定测试IV，不含任何真实数据。

安全边界：应用层加密不依赖蓝牙配对是否加密；签名/会话/序列校验仍然必需。GATT集成须保证单连接、10秒未完成传输重置、断连清空缓冲与会话、每连接nonce刷新、禁用时停止广播/断连/清空。DoS和射频干扰无法由此协议消除。撤销使用服务端401/403→签名revoked事件，继承现有清除显示行为，不能把网络失败当撤销。

计划服务UUID：`364b4de0-40f2-4d58-9db6-2ded36b6b601`。只有升级GATT固件并手动打开Mac蓝牙后才广播；扫描没有候选并不说明硬件故障。服务名/UUID只是发现入口，不是认证依据。

## 运行与测试

Python 3.10+，建议独立虚拟环境：

```sh
python3 -m venv .venv-ble
.venv-ble/bin/pip install -r clients/requirements-ble.txt
.venv-ble/bin/python -m unittest discover -s tests -p test_ble_wire.py -v
.venv-ble/bin/python clients/mac_ble_probe.py
IDF_PATH=/path/to/esp-idf CC=clang firmware/esp32/host-tests/run.sh
```

macOS由启动应用持有蓝牙隐私权限；初始化超时/拒绝时仅报告不可用，不修改隐私数据库、不自动配对附近设备。蓝牙已开启不等于启动应用已经获准扫描。参考 [Bleak Scanner](https://bleak.readthedocs.io/en/latest/api/scanner.html) 与 [Client](https://bleak.readthedocs.io/en/latest/api/client.html)。

## 集成与验收关口

1. **GATT真实传输**：ESP32连接受控广播开关、独立hello与安全重组，Mac认证匹配设备后分片发送，屏幕区分BLE/USB来源。验收：实际额度、天气、活动通过BLE显示，无敏感明文；拒绝错密钥/重放。代码已接入，实物未验收。
2. **断连与回退**：禁用、撤销、Mac睡眠/唤醒、供电重启和USB/Wi-Fi仲裁；拔数据线只保留电源连续运行，再进行触控/旋转回归。未完成。

USB仍是回退路径，已保留ebddd42校验通过的应用备份；代码构建不等于无线验收通过。不发布V0.5.1稳定Release。

## 本轮验证记录（2026-10-23）

- Python安全封包7项测试通过。
- C原生ASan/UBSan通过Python公开合成向量、全部分片位置、篡改、截断、错误密钥和有界接收；原有额度/天气/签名/旋转测试通过。
- ESP-IDF v5.5.5新独立构建目录编译通过，未刷入实物。
- Mac蓝牙控制器为开启状态；实际只读扫描在CoreBluetooth初始化阶段20秒超时，未获得无线发现结果，权限状态未证实。当前已验收固件没有BLE服务，不能用此次超时判断设备GATT行为。
- 原USB后台服务仍running。

## GATT原型使用

屏幕默认关闭BLE：点设置→“连接与数据来源”→“Mac蓝牙 / 关”（旧的首页右下角连接状态入口也保留），手动开启。该开关独立保存，不扩大服务端显示权限。传输优先级：65秒内有效USB优先，其次BLE，其次Wi-Fi。USB优先时BLE ACK只表示已认证并进入接收队列，不证明画面当前取自BLE。

```sh
.venv-ble/bin/python clients/mac_ble_bridge.py --config /private/path/display.json --once
# 连续运行：去掉--once；出错重试5秒；额度/天气HTTPS30秒，本机活动可选5秒。
```

配置沿用当前独立显示配置（权限600，server/token/device_id，activity_enabled可选），不使用Mac密码或Codex登录凭据。服务/hello/data/ack UUID分别以b601/b602/b603/b604结尾。ACK是`PXBLE_ACK <sequence> <kind> <HMAC>`，签名消息为`ack <nonce> <sequence> <kind>`。接收端验证后入队，真实显示通过屏幕“MAC蓝牙/已连接”和用户观察验收。

### 蓝牙实物启动追加检查
用户允许蓝牙后，CoreBluetooth授权枚举为3，实际只读扫描完成（已验收旧固件无服务，候选0）。首版GATT固件升级保留NVS，USB认证与回执通过，但私密启动诊断发现SPI DMA分配错误，不能进入无线验收；将NimBLE主机动态分配改为外部PSRAM，保留内部任务栈，并增加无敏感信息的DMA容量计数，需重新构建/升级/检查。未把USB ACK当作屏幕正常。

### 当前实物状态（PSRAM修复版）
GATT原型与NimBLE外部PSRAM分配版已仅升级应用，分区表不变，升级前后NVS验证保留；旧ebddd42应用单独备份并校验。约45秒实物私密诊断有7次USB真实签名回执，DMA错误/断言/panic均0；USB后台已恢复。尚待用户打开Mac蓝牙开关，未观察到蓝牙无线认证/数据ACK，不能把本次USB检查写成BLE通过。11项Python安全/发送端测试通过；LVGL实际指针测试覆盖新开关保存、独立回调与返回不重叠，固件/主题检查通过。

### 2026-10-23 待机花屏回归（无线验收暂停）

用户报告入口难找、长时间待机整屏彩条/乱码且只有重启恢复。40764f7不能算稳定版本；已先回退到校验通过的ebddd42应用，刷写后验证应用与NVS，USB恢复。原始问题仍未定位到唯一根因。

代码审查确认BSP默认50行PSRAM绘图缓冲会依赖SPI临时内部DMA中转分配；此前已出现过该错误，45秒无错误不能证明长待机稳定。候选修复改为应用端通过公开BSP/适配器API预分配单个8行内部绘图缓冲（7680字节），启动断言DMA可用，先预留后初始化BLE；图形对象仍在PSRAM。保持原像素格式、QSPI时钟、两像素对齐、绝对面板旋转与触摸映射，不修改托管源。原生LVGL测试也使用相同8行缓冲和实际对齐回调，增加可发现的“设置→连接与数据来源”入口验证。是否解决物理整屏花屏仍需长待机和用户观察，不能仅用短日志下结论。

### 入口验收与切屏性能（dev2→dev3）
用户已确认新入口可见、进入和返回正常，仅确认入口，不代表待机花屏通过；另报告切屏卡顿。dev2约180秒观察有33次USB ACK，DMA/bitmap/panic为0；60秒与121秒DMA free=85667/largest=45056/min=46072。缓存布局准备常为1ms，但完整绘制统计出现mean240/max458ms，单8行缓冲有明显重画开销。dev3保持单个启动预分配内部DMA缓冲，将行数提高到24（23040字节），减少分块次数；不改SPI时钟、旋转或触摸规则，不恢复PSRAM大块临时中转。生产/原生UI测试共享PIXORA_DRAW_ROWS与面板对齐回调，增加导航绘制耗时日志。性能与长待机分别验收，不能相互替代。

### dev3短时观察（非长待机验收）
候选0.5.1-dev3已升级同一实物，NVS验证保留；启动确认24行/23040字节/单内部缓冲。最终约3分钟观察33次USB回执、DMA/bitmap/panic/assert均0；60/120秒dma_free=71187、largest=31744、min=30620一致。初始绘制样本mean139/max214ms，dev2曾mean240/max458ms；样本非严格同帧对照，不计算性能提升比例，也不能替代用户切屏体验。入口进入/返回已由用户通过；切屏速度及长待机花屏仍待实物反馈。蓝牙无线验收继续暂停。
