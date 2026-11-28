#!/usr/bin/env python3
"""Christmas Buddy V1 接口定义表（deliverable I 的一部分）。

单一事实源：本脚本定义全部板级接口 → 输出 interfaces.json + interfaces.md。
机械设计（mech/）与原理图（eda/）必须引用此处 signal 名，check 脚本核对一致性。

运行：python3 source-data/christmas-buddy/interfaces/interfaces.py
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

VIEW_DATE = "2026-11-28"

@dataclass
class Pin:
    pin: str            # 连接器针脚号
    signal: str         # 信号名（全局唯一，原理图/PCB/机械共用）
    v: str              # 电压域
    ma: str             # 额定电流（每脚）
    direction: str      # IN/OUT/PWR/BIDIR
    note: str = ""

@dataclass
class Connector:
    ref: str            # 位号
    name: str
    model_plan: str     # 候选型号（计划，选型轮锁定）
    pins: list
    note: str = ""

CONNECTORS = [
    Connector("J1", "USB-C 电源输入（板载母座，朝后下方）", "16pin 板载 USB-C 母座，额定 5V/5A（选型轮锁定）", [
        Pin("A4/B4/A9/B9", "VBUS_IN", "5V", "3A", "PWR", "外置认证 5V/3A 适配器"),
        Pin("A1/B1/A12/B12", "GND", "GND", "3A", "PWR", ""),
        Pin("CC1", "CC1_RD", "-", "-", "-", "5.1kΩ 下拉至 GND（UFP）"),
        Pin("CC2", "CC2_RD", "-", "-", "-", "5.1kΩ 下拉至 GND"),
        Pin("DP/DN", "USB_DP/DN", "-", "-", "-", "V1 不接 USB 数据（保持 DNP 焊盘备用）"),
        Pin("SBU1/2", "-", "-", "-", "-", "NC"),
        Pin("D+/D-", "壳地", "-", "-", "-", "外壳屏蔽接 GND"),
    ], note="输入链：PTC(3A hold) → SMAJ5.0A TVS → 5V_MAIN 分配"),

    Connector("J2", "Raspberry Pi Zero 2 W 排母（2×20，2.54mm，Pi 反扣或立插——机械轮冻结）", "2×20P 2.54mm 排母 H=6.5mm（立插方案）/或 2×20 排针（反扣方案）", [
        Pin("P2", "P5V_PI1", "5V", "2A", "PWR", "Pi 供电"),
        Pin("P4", "P5V_PI2", "5V", "2A", "PWR", "Pi 供电"),
        Pin("P1", "P3V3_PI", "3.3V", "-", "PWR", "仅方案 B 给 mic 供电；方案 A NC"),
        Pin("P6", "GND", "GND", "-", "PWR", ""),
        Pin("P9", "GND", "GND", "-", "PWR", ""),
        Pin("P14", "GND", "GND", "-", "PWR", ""),
        Pin("P20", "GND", "GND", "-", "PWR", ""),
        Pin("P25", "GND", "GND", "-", "PWR", ""),
        Pin("P30", "GND", "GND", "-", "PWR", ""),
        Pin("P34", "GND", "GND", "-", "PWR", ""),
        Pin("P39", "GND", "GND", "-", "PWR", ""),
        Pin("P12", "I2S_PCM_CLK", "3.3V", "-", "OUT", "BCM18 → 麦 BCLK"),
        Pin("P35", "I2S_PCM_FS", "3.3V", "-", "OUT", "BCM19 → 麦 LRCLK"),
        Pin("P38", "I2S_PCM_DIN", "3.3V", "-", "IN", "BCM20 ← 麦 SD"),
        Pin("P40", "I2S_PCM_DOUT", "3.3V", "-", "OUT", "BCM21 → 功放 DIN"),
        Pin("P19", "LED_EYE_DIN", "3.3V", "-", "OUT", "BCM10（方案A：由 ESP32 经缓冲驱动同名网；见 J3）"),
        Pin("P22", "AMP_SD", "3.3V", "-", "OUT", "BCM25，上拉默认静音（安全态）"),
        Pin("P16", "BTN_K1", "3.3V", "-", "IN", "BCM23，内部上拉，按下到 GND"),
        Pin("P18", "BTN_K2", "3.3V", "-", "IN", "BCM24"),
        Pin("P24", "BTN_K3", "3.3V", "-", "IN", "BCM8"),
        Pin("P26", "BTN_K4", "3.3V", "-", "IN", "BCM7，晚安键"),
        Pin("P3", "I2C_SDA", "3.3V", "-", "BIDIR", "BCM2，扩展预留（I2C 温湿度/姿态）"),
        Pin("P5", "I2C_SCL", "3.3V", "-", "OUT", "BCM3"),
        Pin("P8", "UART_PI_TX", "3.3V", "-", "OUT", "BCM14 → ESP32 RXD0（单向：每网只有一个驱动源）"),
        Pin("P10", "UART_ESP_TX", "3.3V", "-", "IN", "BCM15 ← ESP32 TXD0"),
        Pin("P29", "P_LED_BUF_EN", "3.3V", "-", "OUT", "BCM5：预留（V1 网表不使用，DNP）"),
        Pin("P31", "PI_RUNNING_N", "3.3V", "-", "OUT", "BCM6：Pi 心跳（ESP32 监控，超时进入安全态）"),
        Pin("P37", "SPARE_GPIO", "3.3V", "-", "BIDIR", "BCM26 预留"),
        Pin("P29/31/37", "TP_*", "-", "-", "-", "另设测试点，见 TP 清单"),
    ], note="Pi Zero 2 W 官方 40-pin 定义对齐；机械轮决定立插/反扣，影响 J2 封装方向"),

    Connector("U3", "ESP32-S3-WROOM-1-N8R2（方案 A，板载贴片模块）", "ESP32-S3-WROOM-1-N8R2（嘉立创 SMT 扩展库，选型轮锁定 C 编号）", [
        Pin("3V3", "P3V3_MCU", "3.3V", "500mA", "PWR", "专用 buck 供电"),
        Pin("EN", "MCU_EN", "3.3V", "-", "IN", "RC 复位 + 测试点"),
        Pin("IO19", "USB_DN_MCU", "-", "-", "-", "NC（V1 不用 ESP32 USB）"),
        Pin("IO20", "USB_DP_MCU", "-", "-", "-", "NC"),
        Pin("RXD0", "UART_PI_TX", "3.3V", "-", "IN", "← Pi BCM14（方案A）"),
        Pin("TXD0", "UART_ESP_TX", "3.3V", "-", "OUT", "→ Pi BCM15（单向驱动，避免双 TX 冲突）"),
        Pin("IO4", "LED_DIN_RAW", "3.3V", "-", "OUT", "RMT 驱动，经 74LVC1T45 缓冲为 5V"),
        Pin("IO5", "STAR_ALT", "3.3V", "-", "OUT", "备用独立通道（V1 不用，DNP）"),
        Pin("IO6", "BTN_K1", "3.3V", "-", "IN", "与 Pi 并联读取（去抖主责在 ESP32）"),
        Pin("IO7", "BTN_K2", "3.3V", "-", "IN", ""),
        Pin("IO15", "BTN_K3", "3.3V", "-", "IN", ""),
        Pin("IO16", "BTN_K4", "3.3V", "-", "IN", "晚安键：ESP32 本地强制安全态"),
        Pin("IO17", "AMP_FORCE_GATE", "3.3V", "-", "OUT", "安全路径：IO17 经 2N7002 把 AMP_SD 拉地强制静音（Pi 死机仍有效）"),
        Pin("IO18", "PI_RUNNING_N", "3.3V", "-", "IN", "监控 Pi BCM6 心跳，超时进入安全态"),
        Pin("IO3", "LED_PI", "3.3V", "-", "IN", "Pi BCM10 经缓冲来的备用数据源"),
        Pin("IO0", "BOOT_BTN", "3.3V", "-", "IN", "固件烧录按钮 + 测试点"),
        Pin("IO9", "JTAG_TP1", "3.3V", "-", "IN", "测试点（固件调试）"),
        Pin("IO10", "JTAG_TP2", "3.3V", "-", "IN", ""),
        Pin("IO11", "JTAG_TP3", "3.3V", "-", "IN", ""),
        Pin("IO12", "JTAG_TP4", "3.3V", "-", "IN", ""),
        Pin("IO13", "JTAG_TP5", "3.3V", "-", "IN", ""),
        Pin("IO14", "JTAG_TP6", "3.3V", "-", "IN", ""),
    ], note="方案 B 时 U3 不贴（DNP），LED_EYE_DIN 由 Pi BCM10 直驱（经缓冲），安全静音由 Pi GPIO 承担"),

    Connector("J4", "扬声器输出", "PH2.0-2P 卧贴（额定 2A）", [
        Pin("1", "SPK_P", "5V(音频)", "400mA峰值", "OUT", "MAX98357A 输出+，4Ω 3W 额定"),
        Pin("2", "SPK_N", "5V(音频)", "400mA峰值", "OUT", "Class-D 差分对，等长就近回流"),
    ], note="外置 28mm 8Ω/2W 或 4Ω/3W 腔体喇叭（采购轮定，接口按 4Ω/3W 设计）"),

    Connector("J5", "眼睛左（3×3 SK6812 模组）", "PH2.0-3P 卧贴", [
        Pin("1", "P5V_LED", "5V", "540mA", "PWR", "LED 轨（PTC 后）"),
        Pin("2", "LED_EYE_DIN", "5V", "-", "IN", "5V 电平数据（74LVC1T45 缓冲后）"),
        Pin("3", "GND", "GND", "540mA", "PWR", ""),
    ], note="模组端自带下一级 DOUT；左眼 DOUT → 右眼 DIN（模组内飞线，不在板上）"),

    Connector("J6", "眼睛右（3×3 SK6812 模组）", "PH2.0-3P 卧贴", [
        Pin("1", "P5V_LED", "5V", "540mA", "PWR", ""),
        Pin("2", "LED_EYE_DIN", "5V", "-", "IN", "菊花链第二级"),
        Pin("3", "GND", "GND", "540mA", "PWR", ""),
    ], note=""),

    Connector("J7", "胸前星星灯（4 颗 SK6812）", "PH2.0-3P 卧贴", [
        Pin("1", "P5V_LED", "5V", "240mA", "PWR", ""),
        Pin("2", "LED_EYE_DIN", "5V", "-", "IN", "菊花链第三级"),
        Pin("3", "GND", "GND", "240mA", "PWR", ""),
    ], note=""),

    Connector("J8", "圣诞树灯光扩展（预留，V1 不装配）", "PH2.0-3P 卧贴", [
        Pin("1", "P5V_LED_EXT", "5V", "600mA", "PWR", "LED 轨延伸，独立 PTC 0.75A"),
        Pin("2", "LED_EYE_DIN", "5V", "-", "IN", "菊花链第 4 级 DIN（树灯模块级联在星星灯之后）"),
        Pin("3", "GND", "GND", "600mA", "PWR", ""),
    ], note="外接上限 10 颗 SK6812；不使用时盲盖"),

    Connector("J9", "调试 UART", "SH1.0-4P 卧贴", [
        Pin("1", "P3V3_MCU", "3.3V", "100mA", "PWR", "调试时给逻辑笔/串口桥供电上限"),
        Pin("2", "UART_PI_TX", "3.3V", "-", "IN", "Pi BCM14 输出（观察 Pi 控制流）"),
        Pin("3", "UART_ESP_TX", "3.3V", "-", "OUT", "ESP32 输出（观察 ESP 日志）"),
        Pin("4", "GND", "GND", "-", "PWR", ""),
    ], note="每网单驱动；SH1.0 间距避免与 2.54 误插"),
]

TEST_POINTS = [
    {"ref": "TP1", "signal": "5V_MAIN", "note": "电源主轨"},
    {"ref": "TP2", "signal": "5V_LED", "note": "LED 轨（PTC 后）"},
    {"ref": "TP3", "signal": "P3V3_MCU", "note": "ESP32 供电轨"},
    {"ref": "TP4", "signal": "GND", "note": "参考地"},
    {"ref": "TP5", "signal": "GND", "note": "参考地（示波器夹）"},
    {"ref": "TP6", "signal": "I2S_PCM_CLK", "note": "I2S 时钟"},
    {"ref": "TP7", "signal": "I2S_PCM_FS", "note": "I2S 帧时钟"},
    {"ref": "TP8", "signal": "I2S_PCM_DIN", "note": "麦克风数据"},
    {"ref": "TP9", "signal": "AMP_SD", "note": "功放静音（安全路径验证）"},
    {"ref": "TP10", "signal": "LED_EYE_DIN_RAW", "note": "ESP32 RMT 波形"},
    {"ref": "TP11", "signal": "PI_RUNNING_N", "note": "Pi 心跳"},
    {"ref": "TP12", "signal": "MCU_EN", "note": "ESP32 复位"},
]

SAFETY_NOTES = [
    "K4（晚安）在两条路径上生效：Pi 软件（最高优先级状态）+ ESP32 硬件级 AMP_SD_FORCED 强制静音——Pi 死机时仍可静音。",
    "AMP_SD 上拉到静音态：上电/复位/固件崩溃默认无声。",
    "LED 数据缓冲 74LVC1T45 由 P_LED_BUF_EN 门控：上电默认关闭，防止 GPIO 初始化抖动点亮。",
    "USB-C 只做 5V 供电不做数据：杜绝陌生 USB 设备枚举进 Pi（隐私）；Pi 自身 USB 口用盲塞。",
    "所有外接线缆（喇叭/灯）均走 2A 额定连接器，短路与 PTC 保护兜底；不引入任何市电直连。",
]

def main() -> None:
    out = {
        "schema": "interface-table/1.0", "product": "christmas-buddy-v1", "view_date": VIEW_DATE,
        "connectors": [asdict(c) for c in CONNECTORS],
        "test_points": TEST_POINTS,
        "safety_notes": SAFETY_NOTES,
    }
    base = Path(__file__).parent
    (base / "interfaces.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = ["# Christmas Buddy V1 板级接口定义表", "", f"查看日期：{VIEW_DATE}。信号名是原理图/PCB/机械/检查脚本共用的唯一键。", ""]
    for c in CONNECTORS:
        md += [f"## {c.ref} — {c.name}", "",
               f"- 候选型号：{c.model_plan}" + (f"\n- 备注：{c.note}" if c.note else ""), "",
               "| 脚 | 信号 | 电压域 | 额定 | 方向 | 说明 |", "|---|---|---|---|---|---|"]
        for p in c.pins:
            md.append(f"| {p.pin} | `{p.signal}` | {p.v} | {p.ma} | {p.direction} | {p.note} |")
        md.append("")
    md += ["## 测试点", "", "| 位号 | 信号 | 说明 |", "|---|---|---|"]
    for t in TEST_POINTS:
        md.append(f"| {t['ref']} | `{t['signal']}` | {t['note']} |")
    md += ["", "## 安全设计注记", ""]
    for s in SAFETY_NOTES:
        md.append(f"- {s}")
    md.append("")
    (base / "interfaces.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"interfaces: {len(CONNECTORS)} connectors, {len(TEST_POINTS)} test points, {sum(len(c.pins) for c in CONNECTORS)} pins")

if __name__ == "__main__":
    main()
