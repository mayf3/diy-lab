# Agent Button Deck｜AI 实体快捷控制台｜Agent 执行规范（机器工作流视图）

> **自动生成·规范草案，未代表真实执行。** 唯一规范源：source-data/agent-button-deck/workflow.json。源资料需在执行当天重新检索；不要将下列 planned 标记为 verified。

**D（目标）**：制作以四个实体按键起步的电脑控制器：硬件只发匿名按钮 ID，Mac 侧用户自定安全映射，后续可通过另行授权的 adapter 路由到指定 Agent。

**受众约束**：初学者或有编程经验的创客；不预设 ESP32、Mac、3D 打印机或焊台。

**禁止误解为目标**：

- V1 不做蓝牙 HID、永久开麦、PC 端任意命令执行或不可逆自动化
- 不把打开 ChatGPT/其他 Agent 会话网页等同于自动向会话发送消息
- 设备端不存私人会话地址、token 或 API Key
- 不把离线 dry-run 或文字教程冒充实物通电与 Agent API 成功

## 启动协议

1. 读取当前用户的设备/预算/技能约束；**只问缺少且会改变实际方案的信息**。不要假设用户有 P1S 或 Mac。
2. 自行获取官方上游、工程文件、BOM 和适用的软件版本；对上游每一个关键型号/版本记录来源、时间、可验证范围。
3. 可用工具能读到的页面、CAD/模型、硬件规格和报价，**自己调用工具检查**，不要把“去看源码”转交给用户。工具受限时请求最低限度文件，不编造已检查。
4. 报告每一关的状态：planned / observed / failed / blocked，输出证据位置、影响以及下一步。**模拟 ≠ 实物、读取 ≠ 验收、建议 ≠ 批准付款。**
5. 对付款、首次通电、不可逆烧录/焊接、儿童使用和安全相关动作，要求真实用户决定或现场证据；不绕过安全检查。

## O（资源选择和替代路线）

| 先看条件 | 你可以选什么 | AI 应如何分流 |
| --- | --- | --- |
| 你现在有哪些材料？ | 有核对过的 ESP32-S3 和 4 键 / 购入最小开发板和面包板材料 / 先做 G0 离线模拟不买东西 | 优先无成本 G0；G1 不必焊 PCB，不必有 3D 打印机 |
| 你的电脑系统？ | macOS 可用本 PR 动作路由器 / Windows 只运行无动作 dry-run / Linux 只运行无动作 dry-run | 本 PR 实际主机动作仅适配 macOS；跨平台需另做执行器 |
| 通信方式怎么选择？ | 首选 USB-UART 可靠基线 / 后续 BLE HID（发热键） / 后续 BLE GATT（需要电脑端接收器） / 红外（电脑需额外接收器） | V1 选 USB；无线/红外需独立固件、供电和重连验收，不承诺直接兼容 |
| 你想让按键怎样指向 Agent？ | 打开用户自己配置的 HTTPS 会话网页 / 运行已审阅的 macOS Shortcut / 通过经授权的 localhost adapter 发送 route_id / 暂不启用 Agent 动作 | 会话选择、审批、私密令牌和 API 回执全部由电脑端负责；设备只发送 K 编号 |

## 官方上游参考（执行时复核）

- Espressif DevKitC-1 v1.1 引脚、端口和供电：[来源](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html)
- Arduino-ESP32 Serial/USB CDC 配置与问题排查：[来源](https://docs.espressif.com/projects/arduino-esp32/en/latest/troubleshooting.html)
- macOS shortcuts 命令行官方文档：[来源](https://support.apple.com/guide/shortcuts-mac/apd455c82f02/mac)
- pySerial 官方串口连接教程：[来源](https://pyserial.readthedocs.io/en/latest/shortintro.html)
- 16 位 I²C GPIO 扩展器官方资料：[来源](https://www.microchip.com/en-us/product/mcp23017)

## A/V/R（动作、证据、依赖与阻断）

### A01 · 确定四个按钮的真实目标

- **执行者**：shared；**依赖**：无；**状态**：planned
- **目的**：把你想要的动作、设备条件与不允许的自动化写成目标表
- **Agent 必做**：

- 说明 USB、BLE、红外及在 Mac 上转发到 Agent 的差别
- 优先推荐不花钱的 G0

- **必须由人完成/提供**：

- 选择 4 个可逆行为，确认要不要先只做软件模拟

- **应交付**：四个按键的目标表与边界
- **V 证据**：human-confirmation，四个目标经本人确认，但不代表已经完成，当前 planned
- **R 遇阻条件**：若包含生产写入/付款等高风险行为，改为仅打开页面或额外审批
- **深入说明**：[详细教程](/projects/agent-button-deck/01-start/)

### A02 · 查证主控与 BOM

- **执行者**：agent；**依赖**：A01；**状态**：planned
- **目的**：整理板卡官方规格、连接方法和当前缺口
- **Agent 必做**：

- 查 Espressif 官方板级文档，锁定 GPIO4–7、USB-UART 和供电边界
- 列出资料出处和商家版次差异，保持未核实型号 HOLD

- **必须由人完成/提供**：

本关不要求你操作。

- **应交付**：BOM 与价格估算；阻断问题及官方来源
- **V 证据**：public-source，关键硬件结论有官方资料；预算估算不当作真实报价，当前 planned
- **R 遇阻条件**：板卡版次/USB 口不明确则不能执行 G1 采购/接线
- **深入说明**：[详细教程](/projects/agent-button-deck/02-hardware/)

### A03 · 跑无硬件软件 dry-run

- **执行者**：agent；**依赖**：A01；**状态**：planned
- **目的**：验证 JSON 按钮事件和电脑安全白名单
- **Agent 必做**：

- 执行 Python 单元测试与 K1–K4 标准输入模拟
- 验证未知按键及任意 shell、file URL、非本机 Agent 端点配置被拒绝

- **必须由人完成/提供**：

本关不要求你操作。

- **应交付**：G0 软件输出和测试结果
- **V 证据**：simulation，四个动作仅打印 dry-run 且恶意输入拒绝；不假装有硬件，当前 planned
- **R 遇阻条件**：测试失败就修解析器/白名单，不提前启用真实动作
- **深入说明**：[详细教程](/projects/agent-button-deck/01-start/)

### A04 · 审批最小采购

- **执行者**：human；**依赖**：A02, A03；**状态**：planned
- **目的**：在清楚型号接口、预算和缺口后决定是否购买
- **Agent 必做**：

- 提供必要 SKU、现有物品可复用表和未知报价

- **必须由人完成/提供**：

- 确认是否购买开发板、常开按键、面包板和数据线；付款由本人完成

- **应交付**：人工采购决定与准确 SKU
- **V 证据**：human-approval，得到人的明确决定；存在 HOLD 时可以先不购买，当前 planned
- **R 遇阻条件**：未确认型号或报价就保持离线阶段，不强迫采购
- **深入说明**：[详细教程](/projects/agent-button-deck/02-hardware/)

### A05 · 断电接线和首次烧录

- **执行者**：shared；**依赖**：A04；**状态**：planned
- **目的**：用 GPIO4–GPIO7 读取四个常开按钮并发送串口 JSON
- **Agent 必做**：

- 依据实际主板与 Core 版本提供接线、烧录和故障定位建议
- 核对 USB CDC On Boot 与物理 USB-UART 端口

- **必须由人完成/提供**：

- 断电完成按键和 GND 接线、检查有无短路
- 批准首次插 USB 和烧录，按键提供脱敏串口日志

- **应交付**：接线照片和板卡型号；Arduino Core 版本及四键日志
- **V 证据**：device-log，四键输出无串台且按住两秒不连发；必须是实机记录，当前 planned
- **R 遇阻条件**：过热/反复复位/触点未明立即拔线，禁止用 G0 当作通电验收
- **深入说明**：[详细教程](/projects/agent-button-deck/02-hardware/)

### A06 · Mac 根据私有配置执行动作

- **执行者**：shared；**依赖**：A03, A05；**状态**：planned
- **目的**：真实 USB 事件通过 Mac 侧白名单执行已批准的行为
- **Agent 必做**：

- 根据实际串口定位问题，先跑默认 dry-run
- 检查 URL/Shortcut/App/adapter 配置均在白名单内

- **必须由人完成/提供**：

- 将示例配置复制到仓库外并修改
- 审阅可逆动作后明确加 --enable-actions 并真实测试

- **应交付**：Mac 动作记录及失败日志
- **V 证据**：device-log，至少两种已批准的 Mac 行为由实物按钮正确触发，当前 planned
- **R 遇阻条件**：权限/串口占用/不希望的动作出现时停止并退回 dry-run
- **深入说明**：[详细教程](/projects/agent-button-deck/03-host-routing/)

### A07 · 隔离指定 Agent 会话路由

- **执行者**：shared；**依赖**：A06；**状态**：planned
- **目的**：区分打开网页和经 adapter 真正投递 Agent 事件
- **Agent 必做**：

- 定义 localhost route_id POST 契约及日志，不在设备中存机密
- 查询特定平台合法 API 是否支持指定目标，缺少凭证时明确未实现

- **必须由人完成/提供**：

- 自行决定是否部署/启用有权限的 Agent adapter
- 仅在明确授权时进行一次端到端目标与回执测试

- **应交付**：adapter 契约或真实测试回执
- **V 证据**：device-log，确实有获授权 adapter 将事件送达正确会话并返回可核对回执，才能称完成，当前 planned
- **R 遇阻条件**：无 adapter/合法 API 时仅打开会话网址或继续 dry-run
- **深入说明**：[详细教程](/projects/agent-button-deck/03-host-routing/)

### A08 · 模块化扩展与真实复测

- **执行者**：shared；**依赖**：A05, A06；**状态**：planned
- **目的**：在四键基线上逐项扩充按键、旋钮、BLE 与语音并建立测试记录
- **Agent 必做**：

- 调查 3.3V MCP23017、BLE HID/GATT 与 Mac 录音的接口边界
- 设计扩展固件的独立验收、外壳量规和回退路线

- **必须由人完成/提供**：

- 选择一个扩展并决定是否买料，负责真实组装和安全测试
- 逐键各按 10 次，USB 重插 3 次，保留所有失败日志

- **应交付**：选定扩展的测试证据或 HOLD；实际成本与完整验收记录
- **V 证据**：physical-observation，有实物原始证据才标已验证；蓝牙/I2C/语音不因设计文档而自动通过，当前 planned
- **R 遇阻条件**：扩展失败立即退回 USB 四键基线并记录真实问题
- **深入说明**：[详细教程](/projects/agent-button-deck/04-extensions/)

## 完工报告格式

```text
项目目标 / 当前读者资源：
上游版本与来源（检查日期、实际看到的证据）：
本次已执行动作及输出（Agent 完成 / 人完成 / 供应商完成）：
计划和实测：分别列明，不允许互相替代
阻塞项与实际风险：
需要人做的下一件事：
是否具备付款 / 实物通电 / 公开发布的前提：
```

未经真实观察，不能填写“实测通过”。每次只汇报当前关键关卡，不需把整份原语表重复贴给读者。
