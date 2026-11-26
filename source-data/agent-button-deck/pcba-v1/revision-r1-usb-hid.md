# Button Deck 设计修订 R1：原生 USB HID 键盘路线

**状态：发起人已确认方向（2026-11-26）；固件为草稿未编译；载板尚未设计。**
本文是 [product-brief.md](product-brief.md) 与 [interface-contract.md](interface-contract.md) 的设计修订记录：
发起人确认采用**真键盘模式**——按键直接作为 USB 键盘快捷键触发电脑功能，不依赖 Mac 常驻 bridge 程序。

## R1 变更内容

| 项 | 原方案（路线 A） | R1 确认方案（路线 B） |
| --- | --- | --- |
| 通信口 | USB-to-UART（Micro-USB）+ Mac 常驻 `agent_button_bridge.py` | **ESP32-S3 原生 USB OTG 口**（HID 键盘）+ 保留 UART 口做烧录维护 |
| 按键效果 | 串口 JSON 事件 → bridge 执行动作（bridge 未运行则失灵） | **真实键盘快捷键 F13–F16**，任何绑定了这些键的 App/系统功能直接触发，即插即用 |
| 固件 | `AgentButtonDeck.ino`（串口事件，`5654c5d`，未编译烧录） | 新写 `AgentButtonDeckHID.ino`（USBHIDKeyboard，草稿见同目录） |
| Mac 端 | 需要 bridge + 映射配置 | 无需常驻程序；用户在系统/应用里自行绑定 F13–F16 |
| 硬件载板 | 四键 + 插座 | **不变**：仍是四键 + 两排插座；外壳需同时露出两个 USB 口 |

不改变的部分：ESP32-S3-DevKitC-1 预焊板插载板的路线、GPIO4–7 常开按键接地、
内部上拉、35 ms 去抖、四键独立无组合键语义、P1S 打印外壳、与口喷神器及亲子记录器相互独立。

## R1 官方事实核对（2026-11-26，Espressif v1.1 用户指南）

- **J1 / J3 各为 22 针排针**；GPIO4–7 分别对应 J1 第 4–7 脚；GND 位于 J1.22 与 J3.1/21/22。
  → 载板插座方案：**每侧 2 个 1×11P 2.54mm 排母拼接成 22 位**（1×22P 单件在当前元件库未见，
  11P 型号已核实存在），两侧共 4 个排母；两排排距待官方尺寸图/实物核对后冻结。
- **供电**：官方口径「USB-to-UART Port and ESP32-S3 USB Port (either one or both), default power
  supply (recommended)」——即 **OTG 口单口供电为官方推荐方式之一**，HID 模式只插 OTG 口即可工作。
- **USB 口类型**：USB-to-UART 口官方明确为 Micro-USB；OTG 口连接器类型官方文档未标注
  （实物/商品图为准，载板外壳开孔按实物核对后再冻结）。
- 两口均可烧录；日常 HID 走 OTG 口，UART 口保留为烧录/维护口，装壳后需可接近。

## R1 固件（草稿，未编译）

`AgentButtonDeckHID.ino`：GPIO4–7 上拉输入、35 ms 去抖、按下沿发送 F13/F14/F15/F16、
开机初态不补发、多键独立——事件语义与 `5654c5d` 串口版一致，仅把“串口 JSON 输出”替换为
“USB HID 键盘按键”。编译/烧录配置（Arduino-ESP32 Core 版本、FQBN、USB 模式菜单）待首次
编译时锁定并记录，当前不虚构任何编译结果。

## R1 待核实清单（进元件采购门禁）

1. ESP32-S3-DevKitC-1 预焊排针版：准确 SKU、Flash/PSRAM、现价与库存（购买入口：乐鑫官方渠道
   或立创商城；搜索当日受限，SKU 核实顺延）。
2. 四键开关最终选型（两个已核实候选：Omron B3F-4055 插件 6×6（立创 C9900023790）、
   无声贴片 6×6×5（C9900014294）——以按键手感和工厂装配能力定档）。
3. 1×11P 2.54mm 排母（已核实存在：C9900027094 等，×4）。
4. OTG 口连接器实物类型与两 USB 口开孔尺寸（到货实物核对）。
5. F13–F16 组合键在发起人 Mac 上的绑定清单（用户操作，提供绑定指引）。
