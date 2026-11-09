# Agent Button Deck｜AI 实体快捷控制台

> **准备中（2026-11-09）**｜[需求 Issue #15](https://github.com/mayf3/diy-lab/issues/15)。目前只有设计与示例，**未采购、未接线、未烧录、未验证真实 Agent 会话投递**。

做一个可扩展的实体按键控制器：从四键开始，按键发 `K1`～`K4`，电脑根据自己的配置打开应用/网页、运行快捷指令，或调用**自己部署和授权**的本地 Agent 适配器。可以重新分配按键，无需重刷硬件。

## 先做什么

1. [G0｜零硬件验证](/projects/agent-button-deck/01-start/)：用键盘输入模拟四个按键事件；默认 dry-run，¥0。
2. [G1｜硬件接线与烧录](/projects/agent-button-deck/02-hardware/)：ESP32-S3 DevKitC-1、四个常开按钮、面包板，USB-UART 连接 Mac。
3. [G2｜电脑与 Agent 路由](/projects/agent-button-deck/03-host-routing/)：改本机私有 JSON 映射、启用已审阅的 Mac 动作；定义 localhost Agent adapter 接口。
4. [G3–G4｜扩展和验收](/projects/agent-button-deck/04-extensions/)：MCP23017 更多键、旋钮、BLE、语音、3D 打印模块化外壳。

**双版本教程**：[新手人类版](/projects/agent-button-deck/human-track/) · [Agent 执行版](/projects/agent-button-deck/agent-track/)。共同数据源：`source-data/agent-button-deck/workflow.json`；沿用 [DOAVR 原语](/guide/diy-primitives/)。

## 推荐 V1 技术链

```text
K1..K4 常开按钮 ── GPIO4/5/6/7 ── ESP32-S3
                                       │
                          USB-to-UART（有线）
                                       ▼
                     Mac Python 安全事件路由器
                           （默认 dry-run）
                            │     │      │
                         打开 App  Shortcut localhost adapter
                            │     │      │
                          本机动作      已授权 Agent/会话
```

设备只传按钮 ID，不存 token、隐私会话或执行脚本；电脑负责允许哪些动作。V1 按键串口协议与原生 USB HID / BLE HID **不同**，后两者必须另写固件与适配，不是勾选“无线”就能使用。红外需要 Mac 侧额外接收器，不作为首选。

| 按键 | 初始示例 | 条件 |
| --- | --- | --- |
| K1 | `open_app` → `com.apple.Notes` | Mac 有备忘录 |
| K2 | `open_url` → `https://example.com` | 可替换成**私有配置**中的会话网页 |
| K3 | `shortcut` → `AI Lab Capture` | 自行创建同名快捷指令 |
| K4 | `agent_event` → 本地 `127.0.0.1` 的 `research` 路由 | **必须先有授权 adapter；本 PR 不实现目标 API** |

**打开某个 ChatGPT 会话 URL 不等于向该会话自动发送消息。** 实际投递取决于目标平台是否提供稳定且被授权的 API、adapter 和真实回执。

**预算**：G0 不买任何硬件；G1 约 **¥90–200**（方案级估算，不是实时商家报价，详情见 BOM）。G3 扩展单独核价。优先复用已有 Mac、3D 打印机与数据线，不首购 PCB/电池/屏幕。

参考：[Espressif 官方 DevKitC-1 v1.1](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html) · [Arduino 串口排错](https://docs.espressif.com/projects/arduino-esp32/en/latest/troubleshooting.html) · [Apple Shortcuts CLI](https://support.apple.com/guide/shortcuts-mac/apd455c82f02/mac) · [MCP23017](https://www.microchip.com/en-us/product/mcp23017)（资料核查于 2026-11-09）。
