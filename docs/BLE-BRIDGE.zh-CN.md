# V0.5.1 Mac BLE 桥接：开发中

目标：出门时屏幕由普通USB电源供电，Mac联网后通过BLE发送已授权的额度、天气和可选本机活动；不要求咖啡厅Wi-Fi、不共享Mac登录密码、不把上游账号凭据交给屏幕。当前已交付**安全封包与接收器底座**，尚未交付BLE无线显示闭环，不能拔掉数据线作为验收。

## 当前代码

- `clients/ble_wire.py`：AES-256-GCM封包、有界流重组；支持任意GATT分片边界。
- `firmware/esp32/main/ble_wire.c`：同一协议的C接收器，编入ESP32构建；当前未接入NimBLE/GATT运行路径。
- `clients/mac_ble_probe.py`：只读服务扫描，无配对、无凭据传输、不显示附近设备身份；整体20秒超时。
- 现有USB协议继续负责内层签名、会话绑定、序列与数据校验。BLE外层解密成功不代表数据可展示，集成时必须继续执行这些检查。

## 协议 v1（未冻结）

字节顺序：`PBL1`（4）+ 随机IV（12）+ 明文长度（4，大端）+ 密文（n）+ GCM标签（16）。头部20字节全部作为AAD。`1 <= n <= 20000`，整个接收缓冲区最多20036字节，错误后保持拒绝状态，必须显式重置；不静默扫描下一个魔数。内层为现有`PXUSB1`签名帧，BLE使用每次连接生成的独立会话nonce，不能复用USB会话。

加密密钥：`SHA256(b"Pixora BLE v1 key\x00" + scoped_display_token_ascii)`。令牌必须是32–128位ASCII字母、数字、下划线或连字符；来自服务端随机生成的独立显示授权，不接受用户密码或管理员令牌。每包通过系统安全随机源生成新96位IV；生产接口不允许调用者指定IV。公开测试向量仅使用合成`A*32`令牌与固定测试IV，不含任何真实数据。

安全边界：应用层加密不依赖蓝牙配对是否加密；签名/会话/序列校验仍然必需。GATT集成须保证单连接、10秒未完成传输重置、断连清空缓冲与会话、每连接nonce刷新、禁用时停止广播/断连/清空。DoS和射频干扰无法由此协议消除。撤销使用服务端401/403→签名revoked事件，继承现有清除显示行为，不能把网络失败当撤销。

计划服务UUID：`364b4de0-40f2-4d58-9db6-2ded36b6b601`。当前已验收固件没有广播此服务；扫描没有候选并不说明硬件故障。服务名/UUID只是发现入口，不是认证依据。

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

## 接下来两个里程碑

1. **GATT真实传输**：ESP32连接受控广播开关、独立hello与安全重组，Mac认证匹配设备后分片发送，屏幕区分BLE/USB来源。验收：实际额度、天气、活动通过BLE显示，无敏感明文；拒绝错密钥/重放。未完成。
2. **断连与回退**：禁用、撤销、Mac睡眠/唤醒、供电重启和USB/Wi-Fi仲裁；拔数据线只保留电源连续运行，再进行触控/旋转回归。未完成。

现有USB后台服务和ebddd42实物固件仍是当前可用路径；本轮协议代码构建不等于无线已上线。不发布V0.5.1稳定Release。

## 本轮验证记录（2026-10-23）

- Python安全封包7项测试通过。
- C原生ASan/UBSan通过Python公开合成向量、全部分片位置、篡改、截断、错误密钥和有界接收；原有额度/天气/签名/旋转测试通过。
- ESP-IDF v5.5.5新独立构建目录编译通过，未刷入实物。
- Mac蓝牙控制器为开启状态；实际只读扫描在CoreBluetooth初始化阶段20秒超时，未获得无线发现结果，权限状态未证实。当前已验收固件没有BLE服务，不能用此次超时判断设备GATT行为。
- 原USB后台服务仍running。
