# Christmas Buddy V1 板级接口定义表

查看日期：2026-11-28。信号名是原理图/PCB/机械/检查脚本共用的唯一键。

## J1 — USB-C 电源输入（板载母座，朝后下方）

- 候选型号：16pin 板载 USB-C 母座，额定 5V/5A（选型轮锁定）
- 备注：输入链：PTC(3A hold) → SMAJ5.0A TVS → 5V_MAIN 分配

| 脚 | 信号 | 电压域 | 额定 | 方向 | 说明 |
|---|---|---|---|---|---|
| A4/B4/A9/B9 | `VBUS_IN` | 5V | 3A | PWR | 外置认证 5V/3A 适配器 |
| A1/B1/A12/B12 | `GND` | GND | 3A | PWR |  |
| CC1 | `CC1_RD` | - | - | - | 5.1kΩ 下拉至 GND（UFP） |
| CC2 | `CC2_RD` | - | - | - | 5.1kΩ 下拉至 GND |
| DP/DN | `USB_DP/DN` | - | - | - | V1 不接 USB 数据（保持 DNP 焊盘备用） |
| SBU1/2 | `-` | - | - | - | NC |
| D+/D- | `壳地` | - | - | - | 外壳屏蔽接 GND |

## J2 — Raspberry Pi Zero 2 W 排母（2×20，2.54mm，Pi 反扣或立插——机械轮冻结）

- 候选型号：2×20P 2.54mm 排母 H=6.5mm（立插方案）/或 2×20 排针（反扣方案）
- 备注：Pi Zero 2 W 官方 40-pin 定义对齐；机械轮决定立插/反扣，影响 J2 封装方向

| 脚 | 信号 | 电压域 | 额定 | 方向 | 说明 |
|---|---|---|---|---|---|
| P2 | `P5V_PI1` | 5V | 2A | PWR | Pi 供电 |
| P4 | `P5V_PI2` | 5V | 2A | PWR | Pi 供电 |
| P1 | `P3V3_PI` | 3.3V | - | PWR | 仅方案 B 给 mic 供电；方案 A NC |
| P6 | `GND` | GND | - | PWR |  |
| P9 | `GND` | GND | - | PWR |  |
| P14 | `GND` | GND | - | PWR |  |
| P20 | `GND` | GND | - | PWR |  |
| P25 | `GND` | GND | - | PWR |  |
| P30 | `GND` | GND | - | PWR |  |
| P34 | `GND` | GND | - | PWR |  |
| P39 | `GND` | GND | - | PWR |  |
| P12 | `I2S_PCM_CLK` | 3.3V | - | OUT | BCM18 → 麦 BCLK |
| P35 | `I2S_PCM_FS` | 3.3V | - | OUT | BCM19 → 麦 LRCLK |
| P38 | `I2S_PCM_DIN` | 3.3V | - | IN | BCM20 ← 麦 SD |
| P40 | `I2S_PCM_DOUT` | 3.3V | - | OUT | BCM21 → 功放 DIN |
| P19 | `LED_EYE_DIN` | 3.3V | - | OUT | BCM10（方案A：由 ESP32 经缓冲驱动同名网；见 J3） |
| P22 | `AMP_SD` | 3.3V | - | OUT | BCM25，上拉默认静音（安全态） |
| P16 | `BTN_K1` | 3.3V | - | IN | BCM23，内部上拉，按下到 GND |
| P18 | `BTN_K2` | 3.3V | - | IN | BCM24 |
| P24 | `BTN_K3` | 3.3V | - | IN | BCM8 |
| P26 | `BTN_K4` | 3.3V | - | IN | BCM7，晚安键 |
| P3 | `I2C_SDA` | 3.3V | - | BIDIR | BCM2，扩展预留（I2C 温湿度/姿态） |
| P5 | `I2C_SCL` | 3.3V | - | OUT | BCM3 |
| P8 | `UART_PI_TX` | 3.3V | - | OUT | BCM14 → ESP32 RXD0（单向：每网只有一个驱动源） |
| P10 | `UART_ESP_TX` | 3.3V | - | IN | BCM15 ← ESP32 TXD0 |
| P29 | `P_LED_BUF_EN` | 3.3V | - | OUT | BCM5：预留（V1 网表不使用，DNP） |
| P31 | `PI_RUNNING_N` | 3.3V | - | OUT | BCM6：Pi 心跳（ESP32 监控，超时进入安全态） |
| P37 | `SPARE_GPIO` | 3.3V | - | BIDIR | BCM26 预留 |
| P29/31/37 | `TP_*` | - | - | - | 另设测试点，见 TP 清单 |

## U3 — ESP32-S3-WROOM-1-N8R2（方案 A，板载贴片模块）

- 候选型号：ESP32-S3-WROOM-1-N8R2（嘉立创 SMT 扩展库，选型轮锁定 C 编号）
- 备注：方案 B 时 U3 不贴（DNP），LED_EYE_DIN 由 Pi BCM10 直驱（经缓冲），安全静音由 Pi GPIO 承担

| 脚 | 信号 | 电压域 | 额定 | 方向 | 说明 |
|---|---|---|---|---|---|
| 3V3 | `P3V3_MCU` | 3.3V | 500mA | PWR | 专用 buck 供电 |
| EN | `MCU_EN` | 3.3V | - | IN | RC 复位 + 测试点 |
| IO19 | `USB_DN_MCU` | - | - | - | NC（V1 不用 ESP32 USB） |
| IO20 | `USB_DP_MCU` | - | - | - | NC |
| RXD0 | `UART_PI_TX` | 3.3V | - | IN | ← Pi BCM14（方案A） |
| TXD0 | `UART_ESP_TX` | 3.3V | - | OUT | → Pi BCM15（单向驱动，避免双 TX 冲突） |
| IO4 | `LED_DIN_RAW` | 3.3V | - | OUT | RMT 驱动，经 74LVC1T45 缓冲为 5V |
| IO5 | `STAR_ALT` | 3.3V | - | OUT | 备用独立通道（V1 不用，DNP） |
| IO6 | `BTN_K1` | 3.3V | - | IN | 与 Pi 并联读取（去抖主责在 ESP32） |
| IO7 | `BTN_K2` | 3.3V | - | IN |  |
| IO15 | `BTN_K3` | 3.3V | - | IN |  |
| IO16 | `BTN_K4` | 3.3V | - | IN | 晚安键：ESP32 本地强制安全态 |
| IO17 | `AMP_FORCE_GATE` | 3.3V | - | OUT | 安全路径：IO17 经 2N7002 把 AMP_SD 拉地强制静音（Pi 死机仍有效） |
| IO18 | `PI_RUNNING_N` | 3.3V | - | IN | 监控 Pi BCM6 心跳，超时进入安全态 |
| IO3 | `LED_PI` | 3.3V | - | IN | Pi BCM10 经缓冲来的备用数据源 |
| IO0 | `BOOT_BTN` | 3.3V | - | IN | 固件烧录按钮 + 测试点 |
| IO9 | `JTAG_TP1` | 3.3V | - | IN | 测试点（固件调试） |
| IO10 | `JTAG_TP2` | 3.3V | - | IN |  |
| IO11 | `JTAG_TP3` | 3.3V | - | IN |  |
| IO12 | `JTAG_TP4` | 3.3V | - | IN |  |
| IO13 | `JTAG_TP5` | 3.3V | - | IN |  |
| IO14 | `JTAG_TP6` | 3.3V | - | IN |  |

## J4 — 扬声器输出

- 候选型号：PH2.0-2P 卧贴（额定 2A）
- 备注：外置 28mm 8Ω/2W 或 4Ω/3W 腔体喇叭（采购轮定，接口按 4Ω/3W 设计）

| 脚 | 信号 | 电压域 | 额定 | 方向 | 说明 |
|---|---|---|---|---|---|
| 1 | `SPK_P` | 5V(音频) | 400mA峰值 | OUT | MAX98357A 输出+，4Ω 3W 额定 |
| 2 | `SPK_N` | 5V(音频) | 400mA峰值 | OUT | Class-D 差分对，等长就近回流 |

## J5 — 眼睛左（3×3 SK6812 模组）

- 候选型号：PH2.0-3P 卧贴
- 备注：模组端自带下一级 DOUT；左眼 DOUT → 右眼 DIN（模组内飞线，不在板上）

| 脚 | 信号 | 电压域 | 额定 | 方向 | 说明 |
|---|---|---|---|---|---|
| 1 | `P5V_LED` | 5V | 540mA | PWR | LED 轨（PTC 后） |
| 2 | `LED_EYE_DIN` | 5V | - | IN | 5V 电平数据（74LVC1T45 缓冲后） |
| 3 | `GND` | GND | 540mA | PWR |  |

## J6 — 眼睛右（3×3 SK6812 模组）

- 候选型号：PH2.0-3P 卧贴

| 脚 | 信号 | 电压域 | 额定 | 方向 | 说明 |
|---|---|---|---|---|---|
| 1 | `P5V_LED` | 5V | 540mA | PWR |  |
| 2 | `LED_EYE_DIN` | 5V | - | IN | 菊花链第二级 |
| 3 | `GND` | GND | 540mA | PWR |  |

## J7 — 胸前星星灯（4 颗 SK6812）

- 候选型号：PH2.0-3P 卧贴

| 脚 | 信号 | 电压域 | 额定 | 方向 | 说明 |
|---|---|---|---|---|---|
| 1 | `P5V_LED` | 5V | 240mA | PWR |  |
| 2 | `LED_EYE_DIN` | 5V | - | IN | 菊花链第三级 |
| 3 | `GND` | GND | 240mA | PWR |  |

## J8 — 圣诞树灯光扩展（预留，V1 不装配）

- 候选型号：PH2.0-3P 卧贴
- 备注：外接上限 10 颗 SK6812；不使用时盲盖

| 脚 | 信号 | 电压域 | 额定 | 方向 | 说明 |
|---|---|---|---|---|---|
| 1 | `P5V_LED_EXT` | 5V | 600mA | PWR | LED 轨延伸，独立 PTC 0.75A |
| 2 | `LED_EYE_DIN` | 5V | - | IN | 菊花链第 4 级 DIN（树灯模块级联在星星灯之后） |
| 3 | `GND` | GND | 600mA | PWR |  |

## J9 — 调试 UART

- 候选型号：SH1.0-4P 卧贴
- 备注：每网单驱动；SH1.0 间距避免与 2.54 误插

| 脚 | 信号 | 电压域 | 额定 | 方向 | 说明 |
|---|---|---|---|---|---|
| 1 | `P3V3_MCU` | 3.3V | 100mA | PWR | 调试时给逻辑笔/串口桥供电上限 |
| 2 | `UART_PI_TX` | 3.3V | - | IN | Pi BCM14 输出（观察 Pi 控制流） |
| 3 | `UART_ESP_TX` | 3.3V | - | OUT | ESP32 输出（观察 ESP 日志） |
| 4 | `GND` | GND | - | PWR |  |

## 测试点

| 位号 | 信号 | 说明 |
|---|---|---|
| TP1 | `5V_MAIN` | 电源主轨 |
| TP2 | `5V_LED` | LED 轨（PTC 后） |
| TP3 | `P3V3_MCU` | ESP32 供电轨 |
| TP4 | `GND` | 参考地 |
| TP5 | `GND` | 参考地（示波器夹） |
| TP6 | `I2S_PCM_CLK` | I2S 时钟 |
| TP7 | `I2S_PCM_FS` | I2S 帧时钟 |
| TP8 | `I2S_PCM_DIN` | 麦克风数据 |
| TP9 | `AMP_SD` | 功放静音（安全路径验证） |
| TP10 | `LED_EYE_DIN_RAW` | ESP32 RMT 波形 |
| TP11 | `PI_RUNNING_N` | Pi 心跳 |
| TP12 | `MCU_EN` | ESP32 复位 |

## 安全设计注记

- K4（晚安）在两条路径上生效：Pi 软件（最高优先级状态）+ ESP32 硬件级 AMP_SD_FORCED 强制静音——Pi 死机时仍可静音。
- AMP_SD 上拉到静音态：上电/复位/固件崩溃默认无声。
- LED 数据缓冲 74LVC1T45 由 P_LED_BUF_EN 门控：上电默认关闭，防止 GPIO 初始化抖动点亮。
- USB-C 只做 5V 供电不做数据：杜绝陌生 USB 设备枚举进 Pi（隐私）；Pi 自身 USB 口用盲塞。
- 所有外接线缆（喇叭/灯）均走 2A 额定连接器，短路与 PTC 保护兜底；不引入任何市电直连。

