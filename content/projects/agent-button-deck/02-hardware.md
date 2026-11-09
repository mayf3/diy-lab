# G1｜四个按钮 + ESP32-S3 + USB

## 目标

在面包板上让 4 个常开瞬时按钮分别输出 `K1`～`K4` 的 JSON `press`，每次按下只发一次；先不做 PCB、不接锂电池。

## 准备

[预算 BOM](https://github.com/mayf3/diy-lab/blob/main/source-data/agent-button-deck/bom.csv)；推荐按官方 **ESP32-S3-DevKitC-1 v1.1** 对照实物购买。官方板 USB-to-UART 是 **Micro-USB** 口，另一口是 S3 原生 USB，二者用途不同；克隆板 USB-C/引脚布局要重新核对，当前 **HOLD**。需要 4 个常开按钮、面包板、杜邦线、可传数据 USB 线和 Arduino ESP32 环境。无焊接需求。

## 操作

1. **完全断电接线**，4 个按钮一端分别接 `GPIO4 / GPIO5 / GPIO6 / GPIO7`，另一端各接 `GND`；固件使用 `INPUT_PULLUP`，按下为 LOW。四脚轻触开关必须先用万用表核对触点，避免把同侧公共脚接错。
2. 核对 USB-to-UART 端口和主板丝印；不向 GPIO 加 5V。USB 从 Mac 供电，无外接电池/电源。
3. 在 Arduino IDE 选择与你实物匹配的 ESP32-S3 Board，打开 `source-data/agent-button-deck/firmware/AgentButtonDeck.ino`，核查 Arduino Core 版本。通过 **USB-to-UART** 烧录；若按 Espressif 官方 USB-UART 配置，`USB CDC On Boot` 设为 **Disabled**，`Serial` 应走 UART0。不同 Core/主板的菜单可能变化。
4. 串口监视器选择 **115200**：按 K1 应看到 `{"v":1,"event":"press","key":"K1"}`，其余同理。按住 2 秒不能不断重复输出；松开再按才有下一次。
5. 关闭串口监视器后才能启动 G2 Python 端；同一 USB 串口不应被两个进程同时占用。保存真实测试日志和板卡照片（脱敏）。

## 验收

- [ ] 按具体实物确认 USB 端口、GPIO、按钮 NO 触点及供电安全。
- [ ] 四个按键各输出自己的一条 JSON；松开再按能再次输出，长按无连发。
- [ ] 重插 USB 可恢复；记录真实固件、Arduino ESP32 Core 和串口版本。
- [ ] 无实物之前这几项都保持“计划”，不能以编写源码冒充测试通过。

## 出问题怎么办

串口找不到时先换**数据线**、核对 USB-to-UART 口和实际 `/dev/cu.*`，不要固定写死某个设备名。乱码检查波特率 115200。无按键则断电检查 GPIO、GND、NO 开关触点；过热、短路、反复复位立即拔线，不靠更改软件隐藏异常。

**下一关**：[G2 Mac 侧路由](/projects/agent-button-deck/03-host-routing/)。
