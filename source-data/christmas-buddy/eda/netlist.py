#!/usr/bin/env python3
"""Christmas Buddy V1 初版原理图 · 网表级设计 + ERC-lite（deliverable D）。

这是「网表级原理图」：器件、引脚、网络、方向、电压域的机器可读完整定义。
它不是嘉立创 EDA 工程（那是在客户端内的下一阶段任务 T-E1）。
ERC-lite 规则：单驱动冲突 / 悬空引脚 / 电压域越界 / 电源轨存在性 / 安全默认态 /
接口表信号对齐。

输出：netlist.json / erc_report.json / erc_report.md
运行：python3 source-data/christmas-buddy/eda/netlist.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

BASE = Path(__file__).parent

def D(ref, part, mpn, pins, kind="ic", note=""):
    return {"ref": ref, "part": part, "mpn": mpn, "kind": kind, "note": note,
            "pins": {p["pin"]: p for p in pins}}

def P(pin, net, dr, vd, tol5=False, pull=None, note="", flag=None):
    """dr: OUT/IN/PWR/NC；vd: 电压域；tol5: 是否 5V 容忍；pull: 内部上/下拉"""
    return {"pin": pin, "net": net, "dir": dr, "vdom": vd, "tol5v": tol5,
            "pull": pull, "note": note, "flag": flag}  # flag: dnp/预留

DEVICES = [
    # ---- 主控（模块，经 J2 40P 排母安装）----
    D("U1", "Raspberry Pi Zero 2 W", "RP3A0（SC0542）", [
        P("P5V1", "5V_MAIN", "PWR", "5V", note="2A 额定"),
        P("P5V2", "5V_MAIN", "PWR", "5V", note="2A 额定"),
        P("GND1", "GND", "PWR", "0V"),
        P("BCM18", "I2S_PCM_CLK", "OUT", "3V3"),
        P("BCM19", "I2S_PCM_FS", "OUT", "3V3"),
        P("BCM20", "I2S_PCM_DIN", "IN", "3V3"),
        P("BCM21", "I2S_PCM_DOUT", "OUT", "3V3"),
        P("BCM25", "AMP_SD", "OUT", "3V3", note="高=出声，低=静音；复位默认输入态→外部下拉静音"),
        P("BCM23", "BTN_K1", "IN", "3V3", pull="up"),
        P("BCM24", "BTN_K2", "IN", "3V3", pull="up"),
        P("BCM8", "BTN_K3", "IN", "3V3", pull="up"),
        P("BCM7", "BTN_K4", "IN", "3V3", pull="up", note="晚安，最高优先"),
        P("BCM14", "UART_PI_TX", "OUT", "3V3"),
        P("BCM15", "UART_ESP_TX", "IN", "3V3"),
        P("BCM10", "LED_PI", "OUT", "3V3", flag="仅方案B"),
        P("BCM6", "PI_RUNNING_N", "OUT", "3V3", note="心跳"),
        P("BCM2", "I2C_SDA", "IN", "3V3", pull="up", flag="预留"),
        P("BCM3", "I2C_SCL", "OUT", "3V3", pull="up", flag="预留"),
        P("BCM5", "P_LED_BUF_EN", "OUT", "3V3", flag="预留"),
        P("BCM26", "SPARE_GPIO", "IN", "3V3", flag="预留"),
        P("P3V3", "3V3_PI", "PWR", "3V3", flag="仅方案B"),
    ], kind="module", note="512MB；云 AI/音频主控；USB 数据不接"),
    # ---- 音频 ----
    D("U2", "MAX98357A", "MAX98357AETE+（C 编号待核）", [
        P("VDD", "5V_MAIN", "PWR", "5V"),
        P("GND", "GND", "PWR", "0V"),
        P("SD_MODE", "AMP_SD", "IN", "5V", tol5=False, note="内部模式脚，实际阈值按数据手册核对；下拉=静音默认态"),
        P("GAIN", "GAIN_STRAP", "IN", "5V", note="增益 strapped，待数据手册核对"),
        P("DIN", "I2S_PCM_DOUT", "IN", "3V3", tol5=True),
        P("BCLK", "I2S_PCM_CLK", "IN", "3V3", tol5=True),
        P("LRC", "I2S_PCM_FS", "IN", "3V3", tol5=True),
        P("OUTP", "SPK_P", "OUT", "5V_AUDIO"),
        P("OUTN", "SPK_N", "OUT", "5V_AUDIO"),
    ], note="I2S Class-D，3W@4Ω 上限，V1 软件限 1W"),
    D("U5", "INMP441", "INMP441（C 编号待核）", [
        P("VDD", "3V3_MCU", "PWR", "3V3"),
        P("GND", "GND", "PWR", "0V"),
        P("SCK", "I2S_PCM_CLK", "IN", "3V3"),
        P("WS", "I2S_PCM_FS", "IN", "3V3"),
        P("SD", "I2S_PCM_DIN", "OUT", "3V3"),
        P("LRSL", "GND", "IN", "0V", note="左声道帧输出"),
    ], note="底端口 MEMS 麦，声学密封垫 + 前壳 Ø2.2 孔"),
    # ---- HMI 协处理器（方案 A 贴装；方案 B 不贴）----
    D("U3", "ESP32-S3-WROOM-1-N8R2", "C 编号待核（扩展库）", [
        P("3V3", "3V3_MCU", "PWR", "3V3"),
        P("EN", "MCU_EN", "IN", "3V3", pull="up", note="10k 上拉 + 1µF"),
        P("GND", "GND", "PWR", "0V"),
        P("RXD0", "UART_PI_TX", "IN", "3V3"),
        P("TXD0", "UART_ESP_TX", "OUT", "3V3"),
        P("IO4", "LED_DIN_RAW", "OUT", "3V3", note="RMT 驱动眼/星/树灯链"),
        P("IO5", "STAR_ALT", "OUT", "3V3", flag="dnp", note="备用独立通道，V1 不用"),
        P("IO6", "BTN_K1", "IN", "3V3", pull="up"),
        P("IO7", "BTN_K2", "IN", "3V3", pull="up"),
        P("IO15", "BTN_K3", "IN", "3V3", pull="up"),
        P("IO16", "BTN_K4", "IN", "3V3", pull="up", note="晚安硬件级响应"),
        P("IO17", "AMP_FORCE_GATE", "OUT", "3V3", note="低电平默认；高=经 Q1 强制静音"),
        P("IO18", "PI_RUNNING_N", "IN", "3V3"),
        P("IO0", "BOOT_BTN", "IN", "3V3", pull="up", note="烧录/恢复"),
        P("IO9", "JTAG_TP1", "IN", "3V3", flag="预留"),
        P("IO10", "JTAG_TP2", "IN", "3V3", flag="预留"),
        P("IO11", "JTAG_TP3", "IN", "3V3", flag="预留"),
        P("IO12", "JTAG_TP4", "IN", "3V3", flag="预留"),
        P("IO13", "JTAG_TP5", "IN", "3V3", flag="预留"),
        P("IO14", "JTAG_TP6", "IN", "3V3", flag="预留"),
    ], kind="module", note="方案 B：本器件 DNP"),
    # ---- 电平转换 ----
    D("U6", "SN74LVC1T45", "SN74LVC1T45DBVR（C 编号待核）", [
        P("VCCA", "3V3_MCU", "PWR", "3V3"),
        P("A", "BUF_A", "IN", "3V3"),
        P("GND", "GND", "PWR", "0V"),
        P("DIR", "GND", "IN", "0V", note="固定 A→B"),
        P("VCCB", "5V_LED", "PWR", "5V"),
        P("B", "LED_EYE_DIN", "OUT", "5V"),
    ], note="3.3→5V LED 数据缓冲"),
    # ---- 3V3 电源 ----
    D("U4", "TPS563201（候选主选）", "TPS563201DRLR（C 编号待核）", [
        P("VIN", "5V_MAIN", "PWR", "5V"),
        P("EN", "5V_MAIN", "IN", "5V", note="经 R_EN 上电即启"),
        P("GND", "GND", "PWR", "0V"),
        P("SW", "BUCK_SW", "OUT", "5V"),
        P("FB", "BUCK_FB", "IN", "3V3", note="分压反馈，阻值按数据手册公式核算（CALC）"),
        P("BOOT", "BUCK_BOOT", "IN", "5V", note="自举电容"),
    ], kind="power", note="5V→3.3V buck；备选 AMS1117-3.3（DNP，发热需实测）"),
    D("L1", "功率电感 4.7µH/2A", "（选型轮按 datasheet 公式核定）", [
        P("1", "BUCK_SW", "PWR", "5V"),
        P("2", "3V3_MCU", "PWR", "3V3"),
    ], kind="passive", note="CHECK：数值为候选"),
    # ---- 保护与输入 ----
    D("F1", "PTC 3A hold", "（1206 PTC，C 编号待核）", [
        P("1", "5V_IN", "PWR", "5V"), P("2", "5V_F", "PWR", "5V"),
    ], kind="protect"),
    D("F2", "PTC 1.6A hold", "（1206 PTC，C 编号待核）", [
        P("1", "5V_MAIN", "PWR", "5V"), P("2", "5V_LED", "PWR", "5V"),
    ], kind="protect"),
    D("F3", "PTC 0.75A hold", "（0805 PTC，C 编号待核）", [
        P("1", "5V_LED", "PWR", "5V"), P("2", "5V_LED_EXT", "PWR", "5V"),
    ], kind="protect"),
    D("D1", "TVS SMAJ5.0A", "（C 编号待核）", [
        P("K", "5V_IN", "PWR", "5V"), P("A", "GND", "PWR", "0V"),
    ], kind="protect", note="输入浪涌吸收"),
    D("SW5", "电源侧键", "（SS-12D00 拨动，C 编号待核）", [
        P("1", "5V_F", "PWR", "5V"), P("2", "5V_MAIN", "PWR", "5V"),
    ], kind="mech", note="硬断电开关（后壳）"),
    # ---- 桥选与安全路径 ----
    D("S1", "焊桥（方案A：ESP32 驱动 LED）", "PCB 焊桥", [
        P("1", "LED_DIN_RAW", "PAS", "3V3"), P("2", "BUF_A", "PAS", "3V3"),
    ], kind="bridge", note="方案A 闭合"),
    D("S2", "焊桥（方案B：Pi 驱动 LED）", "PCB 焊桥", [
        P("1", "LED_PI", "PAS", "3V3"), P("2", "BUF_A", "PAS", "3V3"),
    ], kind="bridge", note="方案B 闭合（与 S1 互斥）"),
    D("Q1", "2N7002", "（C 编号待核）", [
        P("G", "AMP_FORCE_GATE", "IN", "3V3"),
        P("D", "AMP_SD", "IN", "5V", note="漏极把 AMP_SD 拉到地=强制静音"),
        P("S", "GND", "PWR", "0V"),
    ], kind="discrete", note="ESP32 硬件静音路径"),
    # ---- 阻容（关键项；去耦按每器件 100nF+10µF 惯例，详见 BOM）----
    D("R_SD", "100kΩ 下拉", "0402（C 编号待核）", [
        P("1", "AMP_SD", "IN", "5V"), P("2", "GND", "PWR", "0V"),
    ], kind="passive", note="静音默认态"),
    D("R_G", "100kΩ 下拉", "0402（C 编号待核）", [
        P("1", "AMP_FORCE_GATE", "IN", "3V3"), P("2", "GND", "PWR", "0V"),
    ], kind="passive"),
    D("R_EN", "100kΩ", "0402（C 编号待核）", [
        P("1", "5V_MAIN", "PWR", "5V"), P("2", "MCU_EN", "IN", "3V3", tol5=True),
    ], kind="passive", note="ESP32 EN 上拉"),
    D("R_CC1", "5.1kΩ Rd", "0402（C 编号待核）", [
        P("1", "CC1_RD", "PWR", "0V"), P("2", "GND", "PWR", "0V"),
    ], kind="passive"),
    D("R_CC2", "5.1kΩ Rd", "0402（C 编号待核）", [
        P("1", "CC2_RD", "PWR", "0V"), P("2", "GND", "PWR", "0V"),
    ], kind="passive"),
    D("R_GN", "100kΩ GAIN 脚带", "0402（C 编号待核）", [
        P("1", "GAIN_STRAP", "IN", "5V"), P("2", "GND", "PWR", "0V"),
    ], kind="passive", note="增益档位待数据手册核对"),
    D("R_FBH", "分压上臂（CALC）", "0402（C 编号待核）", [
        P("1", "3V3_MCU", "PWR", "3V3"), P("2", "BUCK_FB", "IN", "3V3"),
    ], kind="passive"),
    D("R_FBL", "分压下臂（CALC）", "0402（C 编号待核）", [
        P("1", "BUCK_FB", "IN", "3V3"), P("2", "GND", "PWR", "0V"),
    ], kind="passive"),
    # ---- 按键与座子 ----
    D("SW1", "轻触开关 K1 说话", "TS-1187A（C 编号待核）", [
        P("1", "BTN_K1", "OUT", "3V3", note="按下对地导通"), P("2", "GND", "PWR", "0V")], kind="mech"),
    D("SW2", "轻触开关 K2 重复", "TS-1187A", [
        P("1", "BTN_K2", "OUT", "3V3", note="按下对地导通"), P("2", "GND", "PWR", "0V")], kind="mech"),
    D("SW3", "轻触开关 K3 魔法灯效", "TS-1187A", [
        P("1", "BTN_K3", "OUT", "3V3", note="按下对地导通"), P("2", "GND", "PWR", "0V")], kind="mech"),
    D("SW4", "轻触开关 K4 晚安", "TS-1187A", [
        P("1", "BTN_K4", "OUT", "3V3", note="按下对地导通"), P("2", "GND", "PWR", "0V")], kind="mech"),
    D("SW6", "BOOT 轻触", "侧键 2 脚", [
        P("1", "BOOT_BTN", "OUT", "3V3", note="按下对地导通"), P("2", "GND", "PWR", "0V")], kind="mech"),
    D("J1", "USB-C 16pin 母座", "（板载 5A，C 编号待核）", [
        P("VBUS", "5V_IN", "PWR", "5V"),
        P("GND", "GND", "PWR", "0V"),
        P("CC1", "CC1_RD", "IN", "0V"),
        P("CC2", "CC2_RD", "IN", "0V"),
        P("DP", "USB_DP_NC", "IN", "0V", flag="dnp"),
        P("DN", "USB_DN_NC", "IN", "0V", flag="dnp"),
    ], kind="conn", note="仅 5V 供电，不接数据（隐私边界）"),
    D("J4", "PH2.0-2P 扬声器座", "PH2.0 卧贴", [
        P("1", "SPK_P", "PAS", "5V_AUDIO"), P("2", "SPK_N", "PAS", "5V_AUDIO")], kind="conn"),
    D("J5", "PH2.0-3P 左眼模组", "PH2.0 卧贴", [
        P("1", "5V_LED", "PWR", "5V"), P("2", "LED_EYE_DIN", "IN", "5V"), P("3", "GND", "PWR", "0V")], kind="conn"),
    D("J6", "PH2.0-3P 右眼模组", "PH2.0 卧贴", [
        P("1", "5V_LED", "PWR", "5V"), P("2", "LED_EYE_DIN", "IN", "5V"), P("3", "GND", "PWR", "0V")], kind="conn"),
    D("J7", "PH2.0-3P 星星灯", "PH2.0 卧贴", [
        P("1", "5V_LED", "PWR", "5V"), P("2", "LED_EYE_DIN", "IN", "5V"), P("3", "GND", "PWR", "0V")], kind="conn"),
    D("J8", "PH2.0-3P 树灯扩展", "PH2.0 卧贴", [
        P("1", "5V_LED_EXT", "PWR", "5V"), P("2", "LED_EYE_DIN", "IN", "5V"), P("3", "GND", "PWR", "0V")], kind="conn",
        note="V1 不装配"),
    D("J9", "SH1.0-4P 调试座", "SH1.0 卧贴", [
        P("1", "3V3_MCU", "PWR", "3V3"), P("2", "UART_PI_TX", "IN", "3V3"),
        P("3", "UART_ESP_TX", "IN", "3V3"), P("4", "GND", "PWR", "0V")], kind="conn"),
    D("J10", "PH2.0-6P 按键卫星板座", "PH2.0 卧贴", [
        P("1", "BTN_K1", "IN", "3V3"), P("2", "BTN_K2", "IN", "3V3"),
        P("3", "BTN_K3", "IN", "3V3"), P("4", "BTN_K4", "IN", "3V3"),
        P("5", "GND", "PWR", "0V"), P("6", "KEY_NC", "NC", "-", flag="dnp")], kind="conn",
        note="卫星板上的 4 键与此并联（SW1-4 在主板上，二者取其一装配——装配轮决定）"),
]

# 网络属性：驱动豁免与说明
NET_ATTR = {
    "GND": {"kind": "power", "vdom": "0V"},
    "5V_IN": {"kind": "power", "vdom": "5V"}, "5V_F": {"kind": "power", "vdom": "5V"},
    "5V_MAIN": {"kind": "power", "vdom": "5V"}, "5V_LED": {"kind": "power", "vdom": "5V"},
    "5V_LED_EXT": {"kind": "power", "vdom": "5V"},
    "3V3_MCU": {"kind": "power", "vdom": "3V3"}, "3V3_PI": {"kind": "power", "vdom": "3V3"},
    "5V_AUDIO": {"kind": "power", "vdom": "5V_AUDIO", "note": "Class-D 输出，差分对"},
    "LED_EYE_DIN": {"note": "菊花链一级驱动（J5/J6/J7/J8 的 DIN 全部并联由 U6.B 驱动——多模组并联不是电气冲突，是同一信号广播；SK6812 链式布线在模组间飞线完成）"},
    "BUF_A": {"kind": "analog", "note": "S1/S2 焊桥二选一闭合，物理上互斥，ERC 豁免双驱动"},
    "GAIN_STRAP": {"kind": "analog"}, "BUCK_FB": {"kind": "analog"}, "BUCK_BOOT": {"kind": "analog"},
    "BUCK_SW": {"note": "开关节点"}, "MCU_EN": {"note": "RC 复位节点"},
    "STAR_ALT": {"kind": "nc", "note": "备用通道 DNP"},
    "USB_DP_NC": {"kind": "nc"}, "USB_DN_NC": {"kind": "nc"}, "KEY_NC": {"kind": "nc"},
    "SPARE_GPIO": {"kind": "nc"}, "JTAG_TP1": {"kind": "tp"}, "JTAG_TP2": {"kind": "tp"},
    "JTAG_TP3": {"kind": "tp"}, "JTAG_TP4": {"kind": "tp"}, "JTAG_TP5": {"kind": "tp"},
    "JTAG_TP6": {"kind": "tp"}, "P_LED_BUF_EN": {"kind": "nc", "note": "预留，V1 不用"},
    "I2C_SDA": {"kind": "nc"}, "I2C_SCL": {"kind": "nc"},
}

VDOM_OK = {"0V": 0, "3V3": 3, "5V": 5, "5V_AUDIO": 5}

def build_nets():
    nets = defaultdict(list)
    for dev in DEVICES:
        for pname, p in dev["pins"].items():
            nets[p["net"]].append({"ref": dev["ref"], "pin": pname, **{k: p[k] for k in ("dir", "vdom", "tol5v", "pull", "flag")}})
    return nets

def erc():
    nets = build_nets()
    errors, warns = [], []

    for name, pins in nets.items():
        attrs = NET_ATTR.get(name, {})
        drivers = [p for p in pins if p["dir"] == "OUT"]
        pwrs = [p for p in pins if p["dir"] == "PWR"]
        if attrs.get("kind") in ("power", "nc", "tp", "analog"):
            continue
        if not drivers and not pwrs:
            has_pull = any(p.get("pull") for p in pins)
            if not has_pull:
                errors.append(f"{name}: 无驱动且无上/下拉")
        # 双驱动检查（焊桥互斥豁免）
        if len(drivers) > 1 and name not in ("BUF_A", "LED_EYE_DIN"):
            errors.append(f"{name}: 多驱动 {sorted({p['ref'] for p in drivers})}")
        # 电压域检查
        net_v = max((VDOM_OK.get(p["vdom"], 0) for p in pins if p["dir"] in ("OUT", "PWR")), default=0)
        for p in pins:
            pv = VDOM_OK.get(p["vdom"], 0)
            if pv < net_v and not p.get("tol5v") and net_v > 3:
                errors.append(f"{name}.{p['ref']}.{p['pin']}: {p['vdom']} 器件接到 {net_v}V 域且未标 5V 容忍")

    for rail in ("5V_MAIN", "5V_LED", "3V3_MCU", "GND", "5V_IN"):
        if rail not in nets:
            errors.append(f"电源轨缺失: {rail}")

    # 安全默认态
    amp = nets.get("AMP_SD", [])
    if not any(p["ref"] == "R_SD" for p in amp):
        errors.append("AMP_SD 缺下拉（上电默认必须静音）")
    q1 = nets.get("AMP_FORCE_GATE", [])
    if not any(p["ref"] == "R_G" for p in q1):
        errors.append("AMP_FORCE_GATE 缺下拉")

    # 接口表对齐
    try:
        itable = json.loads((BASE.parent / "interfaces" / "interfaces.json").read_text(encoding="utf-8"))
        sigs = set()
        for c in itable["connectors"]:
            for pin in c["pins"]:
                sigs.add(pin["signal"])
        sigs.discard("-")
        # 连接器引脚级信号名 → 网表网络名 别名（同一物理点的两种称呼）
        alias = {"VBUS_IN": "5V_IN", "P5V_PI1": "5V_MAIN", "P5V_PI2": "5V_MAIN",
                 "P3V3_MCU": "3V3_MCU", "P3V3_PI": "3V3_PI", "P5V_LED": "5V_LED",
                 "P5V_LED_EXT": "5V_LED_EXT", "USB_DP/DN": None, "壳地": None,
                 "TP_*": None, "USB_DP_MCU": None, "USB_DN_MCU": None}
        mapped = {alias.get(s, s) for s in sigs}
        mapped.discard(None)
        sigs = mapped
        netnames = set(nets.keys()) | set(NET_ATTR.keys())
        for s in sorted(sigs):
            if s in ("TP_*", "壳地", "USB_DP/DN"):
                continue
            if s not in netnames:
                warns.append(f"接口表信号 {s} 未在网表中出现（应为预留或已改名）")
    except FileNotFoundError:
        warns.append("interfaces.json 未生成，跳过对齐检查")

    return nets, errors, warns

def main() -> None:
    nets, errors, warns = erc()
    netlist = {
        "schema": "cbu-netlist/0.2", "product": "christmas-buddy-v1",
        "date": date.today().isoformat(),
        "architecture": "A（Pi Zero 2 W + ESP32-S3 协处理器；方案 B 变化点以 flag 标注）",
        "devices": [{**d, "pin_list": list(d["pins"].keys())} for d in DEVICES],
        "nets": {k: sorted(v, key=lambda p: (p["ref"], p["pin"])) for k, v in sorted(nets.items())},
        "net_attrs": NET_ATTR,
        "erc": {"errors": errors, "warnings": warns},
    }
    (BASE / "netlist.json").write_text(json.dumps(netlist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = ["# Christmas Buddy V1 · 网表级原理图 ERC-lite 报告", "",
          f"日期：{date.today().isoformat()}｜器件 {len(DEVICES)}，网络 {len(nets)}", "",
          f"- 器件清单：{'、'.join(d['ref'] for d in DEVICES)}", "",
          "## ERC 结果", ""]
    for e in errors:
        md.append(f"- **ERROR** — {e}")
    for w in warns:
        md.append(f"- **WARN** — {w}")
    if not errors and not warns:
        md.append("- 全部通过（0 error, 0 warning）")
    (BASE / "erc_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"netlist: {len(DEVICES)} devices, {len(nets)} nets; ERC errors={len(errors)} warns={len(warns)}")
    for e in errors:
        print("  ERROR:", e)
    for w in warns:
        print("  WARN:", w)
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    main()
