#!/usr/bin/env python3
"""Christmas Buddy V1 初版原理图 · 网表级设计 v0.3 + ERC v2（P0-1/2/3 修复 + 系统性规则）。

v0.3 变更（PR #32 Batch2，修复 4 条 Codex 审查线程 + LED 拓扑重构）：
  P0-1  R_EN 上拉 5V_MAIN → 3V3_MCU。依据：ESP32-S3 数据手册 VIH=0.75×VDD1，绝对上限
        VDD1+0.3V（=3.6V），5V 上拉违规。EN 不得悬空（官方 Pin Definitions 注记）。
        RC 复位：R_EN 10kΩ + C_EN 1µF → τ=10ms > strapping tH=3ms（官方 Table 4-2）。
  P0-2  AMP_SD 仲裁重构。依据 MAX98357A 数据手册：SD_MODE 内部下拉 RPD 92–108kΩ，
        模式选择=阻值编码：direct-high=LEFT；RSMALL=94×VDDIO−100=RIGHT；
        RLARGE=222.2×VDDIO−100=(L+R)/2（VDDIO=3.3V → RLARGE=633.3kΩ）。
        设计：BCM25 → R_MODE 620kΩ → SD 节点。BCM25 高=V_SD 0.458V∈(0.16,0.77) →
        (L+R)/2 单声道模式+输出开；BCM25 低/悬空/Pi 死机=内部下拉→shutdown。
        ESP32 IO17→Q1 强制拉低为最高优先覆盖：与 Pi 高电平只争用 5.3µA（3.3V/620k），
        无电气应力。外置 R_SD 删除（避免改变内部 100k 分压，破坏模式编码）。
  P0-3  U6 DIR 接 GND → 接 VCCA。依据 TI SCES515N 功能表：DIR=L: B→A；DIR=H: A→B。
        A→B 需要 DIR=H；DIR 以 VCCA 为参考，VIH(DIR)=2V@VCCA 3–3.6V → 接 VCCA。
        断电安全：VCC isolation——任一 VCC=GND 时两端口高阻（官方 Feature）。
  LED   菊花链重构：J5–J8 改 PH2.0-4P（5V/GND/DIN/DOUT），逐级 DOUT→下级 DIN，
        不再并联 DIN。LED 编号映射与刷新时间计算见 interfaces.md。

ERC v2 规则：单驱动/多驱动隔离、悬空、电压域、上拉域越界（P0-1 类）、驱动隔离
（推挽 OUT 与晶体管下拉必须电阻隔离，P0-2 类）、翻译器方向（P0-3 类）、I2S 方向、
LED 链拓扑、PTC/TVS/CC 属性核验、DNP 连接、焊桥互斥、调试接口存在性。

负向测试：netlist_tests.py（构造变异网表，断言每条规则能拒绝对应错误）。
运行：python3 source-data/christmas-buddy/eda/netlist.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

BASE = Path(__file__).parent

def D(ref, part, mpn, pins, kind="ic", note="", attrs=None):
    return {"ref": ref, "part": part, "mpn": mpn, "kind": kind, "note": note,
            "attrs": attrs or {}, "pins": {p["pin"]: p for p in pins}}

def P(pin, net, dr, vd, tol5=False, pull=None, note="", flag=None):
    return {"pin": pin, "net": net, "dir": dr, "vdom": vd, "tol5v": tol5,
            "pull": pull, "note": note, "flag": flag}

# 数据手册事实（官方 PDF 已本地提取，2026-11-28，见 erc_report 引用）
FACTS = {
    "esp32_en": "ESP32-S3 WROOM-1 Datasheet §Pin Definitions: EN High=on/Low=off，不得悬空；"
                "§DC Characteristics: VIH=0.75×VDD1，绝对上限 VDD1+0.3V；§Strapping: tSU=0ms/tH=3ms",
    "max98357_sd": "MAX98357A Datasheet §SD_MODE and shutdown operation: 内部 RPD 92–108kΩ；"
                   "RLARGE(kΩ)=222.2×VDDIO−100 → (L+R)/2 模式，VDDIO=3.3V → 633.3kΩ；"
                   "比较点 B0=0.16V/B1=0.77V/B2=1.4V (typ)；GAIN_SLOT=GND→+12dB（官方正文）",
    "lvc1t45": "TI SCES515N: DIR=L: B→A / DIR=H: A→B；DIR 参考 VCCA，VIH(DIR)=2V@3–3.6V；"
               "VCC isolation：任一 VCC=GND 两端口高阻",
}

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
        P("BCM25", "AMP_EN_PI", "OUT", "3V3", note="高=允许发声((L+R)/2 模式)；低/悬空=静音；经 R_MODE 隔离"),
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
        P("SD_MODE", "AMP_SD", "IN", "5V", tol5=False,
          note="内部 100kΩ 下拉（官方 92–108kΩ）；<0.16V=shutdown；0.16–0.77V=(L+R)/2 模式；"
               "本设计经 R_MODE 620k 上拉到 3.3V 逻辑 → 0.458V=(L+R)/2 单声道"),
        P("GAIN", "GAIN_STRAP", "IN", "5V", note="经 U7 接 GND=+12dB（官方正文）"),
        P("DIN", "I2S_PCM_DOUT", "IN", "3V3", tol5=True),
        P("BCLK", "I2S_PCM_CLK", "IN", "3V3", tol5=True),
        P("LRC", "I2S_PCM_FS", "IN", "3V3", tol5=True),
        P("OUTP", "SPK_P", "OUT", "5V_AUDIO"),
        P("OUTN", "SPK_N", "OUT", "5V_AUDIO"),
    ], note="I2S Class-D，3W@4Ω 上限，V1 软件限 1W"),
    D("U7", "GAIN 脚接地带", "0Ω 跨接（或直接铺铜）", [
        P("1", "GAIN_STRAP", "PAS", "5V"), P("2", "GND", "PWR", "0V"),
    ], kind="passive", note="12dB 固定增益（官方接法），音量由软件控制"),
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
        P("EN", "MCU_EN", "IN", "3V3", pull="up",
          note="官方：不得悬空；R_EN 上拉到 3V3_MCU（VIH=0.75×VDD1，5V 域违规）+ C_EN 1µF，RC=10ms>tH 3ms"),
        P("GND", "GND", "PWR", "0V"),
        P("RXD0", "UART_PI_TX", "IN", "3V3"),
        P("TXD0", "UART_ESP_TX", "OUT", "3V3"),
        P("IO4", "LED_DIN_RAW", "OUT", "3V3", note="RMT 驱动眼/星/树灯链"),
        P("IO6", "BTN_K1", "IN", "3V3", pull="up"),
        P("IO7", "BTN_K2", "IN", "3V3", pull="up"),
        P("IO15", "BTN_K3", "IN", "3V3", pull="up"),
        P("IO16", "BTN_K4", "IN", "3V3", pull="up", note="晚安硬件级响应"),
        P("IO17", "AMP_FORCE_GATE", "OUT", "3V3", note="低=默认（R_G 下拉）；高=Q1 导通强制静音，可覆盖 Pi"),
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
        P("DIR", "3V3_MCU", "IN", "3V3", note="官方功能表 DIR=H: A→B；DIR 参考 VCCA，接 VCCA 即高"),
        P("VCCB", "5V_LED", "PWR", "5V"),
        P("B", "LED_DIN", "OUT", "5V"),
    ], note="3.3→5V LED 数据缓冲（A→B 方向）", attrs={"translator": {"a_to_b_when_dir": "HIGH"}}),
    # ---- 3V3 电源 ----
    D("U4", "TPS563201（候选主选）", "TPS563201DRLR（C 编号待核）", [
        P("VIN", "5V_MAIN", "PWR", "5V"),
        P("EN", "BUCK_EN", "IN", "5V", note="经 R_EN2 上电即启"),
        P("GND", "GND", "PWR", "0V"),
        P("SW", "BUCK_SW", "OUT", "5V"),
        P("FB", "BUCK_FB", "IN", "3V3", note="分压反馈，阻值按数据手册公式核算（CALC）"),
        P("BOOT", "BUCK_BOOT", "IN", "5V", note="自举电容"),
    ], kind="power", note="5V→3.3V buck；备选 AMS1117-3.3（DNP，发热需实测）"),
    D("L1", "功率电感 4.7µH/2A", "（选型轮按 datasheet 公式核定）", [
        P("1", "BUCK_SW", "PAS", "5V"),
        P("2", "3V3_MCU", "PWR", "3V3"),
    ], kind="passive", note="CHECK：数值为候选"),
    # ---- 保护与输入 ----
    D("F1", "PTC 3A hold", "（1206 PTC，C 编号待核）", [
        P("1", "5V_IN", "PWR", "5V"), P("2", "5V_F", "PWR", "5V"),
    ], kind="protect", attrs={"ptc_hold_a": 3.0}),
    D("F2", "PTC 1.6A hold", "（1206 PTC，C 编号待核）", [
        P("1", "5V_MAIN", "PWR", "5V"), P("2", "5V_LED", "PWR", "5V"),
    ], kind="protect", attrs={"ptc_hold_a": 1.6}),
    D("F3", "PTC 0.75A hold", "（0805 PTC，C 编号待核）", [
        P("1", "5V_LED", "PWR", "5V"), P("2", "5V_LED_EXT", "PWR", "5V"),
    ], kind="protect", attrs={"ptc_hold_a": 0.75}),
    D("D1", "TVS SMAJ5.0A", "（C 编号待核）", [
        P("K", "5V_IN", "PWR", "5V"), P("A", "GND", "PWR", "0V"),
    ], kind="protect", attrs={"tvs_standoff_v": 5.0, "tvs_vbr_min": 6.4, "tvs_vc_5a": 9.2}),
    D("SW5", "电源侧键", "（SS-12D00 拨动，C 编号待核）", [
        P("1", "5V_F", "PWR", "5V"), P("2", "5V_MAIN", "PWR", "5V"),
    ], kind="mech", note="硬断电开关（后壳）"),
    # ---- AMP_SD 仲裁网络（P0-2）----
    D("R_MODE", "620kΩ ±1% ((L+R)/2 模式电阻)", "0402（C 编号待核）", [
        P("1", "AMP_EN_PI", "PAS", "3V3"), P("2", "AMP_SD", "PAS", "5V", tol5=True),
    ], kind="passive",
        note="官方公式 RLARGE=222.2×VDDIO−100=633.3kΩ@3.3V → 620k 实值；"
             "BCM25 高时 V_SD=3.3×100/(620+100)=0.458V∈(0.16,0.77)→(L+R)/2 单声道；"
             "BCM25 低/悬空→内部 100k 下拉→shutdown；Q1 强制拉低时 Pi 高仅灌 5.3µA"),
    D("R_G", "100kΩ 下拉", "0402（C 编号待核）", [
        P("1", "AMP_FORCE_GATE", "IN", "3V3"), P("2", "GND", "PWR", "0V"),
    ], kind="passive"),
    D("Q1", "2N7002", "（C 编号待核）", [
        P("G", "AMP_FORCE_GATE", "IN", "3V3"),
        P("D", "AMP_SD", "IN", "5V", note="漏极把 AMP_SD 拉到地=强制静音（与 Pi 隔离经 R_MODE）"),
        P("S", "GND", "PWR", "0V"),
    ], kind="discrete", note="ESP32 硬件静音路径；官方 SD_MODE 内部下拉提供默认 shutdown"),
    # ---- ESP32 EN 复位（P0-1）----
    D("R_EN", "10kΩ 上拉", "0402（C 编号待核）", [
        P("1", "3V3_MCU", "PWR", "3V3"), P("2", "MCU_EN", "IN", "3V3"),
    ], kind="passive", note="官方：EN 不得悬空；上拉必须在 3.3V 域（VIH=0.75×VDD1，5V 违规）"),
    D("C_EN", "1µF", "0402（C 编号待核）", [
        P("1", "MCU_EN", "IN", "3V3"), P("2", "GND", "PWR", "0V"),
    ], kind="passive", note="RC 复位：τ=10ms > 官方 strapping tH=3ms"),
    D("R_EN2", "100kΩ", "0402（C 编号待核）", [
        P("1", "5V_MAIN", "PWR", "5V"), P("2", "BUCK_EN", "IN", "5V"),
    ], kind="passive", note="buck EN（宽输入器件，5V 域合法）"),
    # ---- USB-C CC ----
    D("R_CC1", "5.1kΩ Rd", "0402（C 编号待核）", [
        P("1", "CC1_RD", "PWR", "0V"), P("2", "GND", "PWR", "0V"),
    ], kind="passive"),
    D("R_CC2", "5.1kΩ Rd", "0402（C 编号待核）", [
        P("1", "CC2_RD", "PWR", "0V"), P("2", "GND", "PWR", "0V"),
    ], kind="passive"),
    D("J1", "USB-C 16pin 母座", "（板载 5A，C 编号待核）", [
        P("VBUS", "5V_IN", "PWR", "5V"),
        P("GND", "GND", "PWR", "0V"),
        P("CC1", "CC1_RD", "IN", "0V"),
        P("CC2", "CC2_RD", "IN", "0V"),
        P("DP", "USB_DP_NC", "IN", "0V", flag="dnp"),
        P("DN", "USB_DN_NC", "IN", "0V", flag="dnp"),
    ], kind="conn", note="仅 5V 供电，不接数据（隐私边界）"),
    # ---- 阻容（关键项）----
    D("R_FBH", "分压上臂（CALC）", "0402（C 编号待核）", [
        P("1", "3V3_MCU", "PWR", "3V3"), P("2", "BUCK_FB", "IN", "3V3"),
    ], kind="passive"),
    D("R_FBL", "分压下臂（CALC）", "0402（C 编号待核）", [
        P("1", "BUCK_FB", "IN", "3V3"), P("2", "GND", "PWR", "0V"),
    ], kind="passive"),
    # ---- 焊桥 ----
    D("S1", "焊桥（方案A：ESP32 驱动 LED）", "PCB 焊桥", [
        P("1", "LED_DIN_RAW", "PAS", "3V3"), P("2", "BUF_A", "PAS", "3V3"),
    ], kind="bridge", note="方案A 闭合", attrs={"bridge_group": "LED_SRC", "closed_in": "A"}),
    D("S2", "焊桥（方案B：Pi 驱动 LED）", "PCB 焊桥", [
        P("1", "LED_PI", "PAS", "3V3"), P("2", "BUF_A", "PAS", "3V3"),
    ], kind="bridge", note="方案B 闭合（与 S1 互斥）", attrs={"bridge_group": "LED_SRC", "closed_in": "B"}),
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
    D("J4", "PH2.0-2P 扬声器座", "PH2.0 卧贴", [
        P("1", "SPK_P", "PAS", "5V_AUDIO"), P("2", "SPK_N", "PAS", "5V_AUDIO")], kind="conn"),
    # ---- LED 菊花链（4P，逐级 DOUT→下级 DIN）----
    D("J5", "PH2.0-4P 左眼模组（链级1）", "PH2.0 卧贴", [
        P("1", "5V_LED", "PWR", "5V"), P("2", "GND", "PWR", "0V"),
        P("3", "LED_DIN", "IN", "5V"), P("4", "LED_CHAIN1", "OUT", "5V"),
    ], kind="conn", note="模组 LED0–8；DOUT 返回板内进链级2"),
    D("J6", "PH2.0-4P 右眼模组（链级2）", "PH2.0 卧贴", [
        P("1", "5V_LED", "PWR", "5V"), P("2", "GND", "PWR", "0V"),
        P("3", "LED_CHAIN1", "IN", "5V"), P("4", "LED_CHAIN2", "OUT", "5V"),
    ], kind="conn", note="模组 LED9–17"),
    D("J7", "PH2.0-4P 星星灯（链级3）", "PH2.0 卧贴", [
        P("1", "5V_LED", "PWR", "5V"), P("2", "GND", "PWR", "0V"),
        P("3", "LED_CHAIN2", "IN", "5V"), P("4", "LED_CHAIN3", "OUT", "5V"),
    ], kind="conn", note="模组 LED18–21"),
    D("J8", "PH2.0-4P 树灯扩展（链级4，V1 不装配）", "PH2.0 卧贴", [
        P("1", "5V_LED_EXT", "PWR", "5V"), P("2", "GND", "PWR", "0V"),
        P("3", "LED_CHAIN3", "IN", "5V"), P("4", "LED_CHAIN_END", "OUT", "5V"),
    ], kind="conn", note="LED22–31（上限 10 颗）；末级 DOUT 悬空盲盖"),
    D("J9", "SH1.0-4P 调试座", "SH1.0 卧贴", [
        P("1", "3V3_MCU", "PWR", "3V3"), P("2", "UART_PI_TX", "IN", "3V3"),
        P("3", "UART_ESP_TX", "IN", "3V3"), P("4", "GND", "PWR", "0V")], kind="conn"),
    D("J10", "PH2.0-6P 按键卫星板座", "PH2.0 卧贴", [
        P("1", "BTN_K1", "IN", "3V3"), P("2", "BTN_K2", "IN", "3V3"),
        P("3", "BTN_K3", "IN", "3V3"), P("4", "BTN_K4", "IN", "3V3"),
        P("5", "GND", "PWR", "0V"), P("6", "KEY_NC", "NC", "-", flag="dnp")], kind="conn",
        note="卫星板上的 4 键与此并联（SW1-4 在主板上，二者取其一装配——装配轮决定）"),
]

NET_ATTR = {
    "GND": {"kind": "power", "vdom": "0V"},
    "5V_IN": {"kind": "power", "vdom": "5V"}, "5V_F": {"kind": "power", "vdom": "5V"},
    "5V_MAIN": {"kind": "power", "vdom": "5V"}, "5V_LED": {"kind": "power", "vdom": "5V"},
    "5V_LED_EXT": {"kind": "power", "vdom": "5V"},
    "3V3_MCU": {"kind": "power", "vdom": "3V3"}, "3V3_PI": {"kind": "power", "vdom": "3V3"},
    "5V_AUDIO": {"kind": "power", "vdom": "5V_AUDIO", "note": "Class-D 输出，差分对"},
    "AMP_EN_PI": {"kind": "logic", "note": "BCM25 经 R_MODE 隔离进 AMP_SD（驱动隔离规则的被隔离侧）"},
    "AMP_SD": {"kind": "analog", "note": "MAX98357A SD_MODE：内部 100k 下拉；Q1 拉低=强制静音；"
              "R_MODE 隔离 Pi 驱动——任何推挽 OUT 不得直连本网（P0-2 规则）"},
    "GAIN_STRAP": {"kind": "analog", "note": "经 U7 接地=+12dB（官方）"},
    "BUF_A": {"kind": "analog", "note": "S1/S2 焊桥互斥"},
    "BUCK_FB": {"kind": "analog"}, "BUCK_BOOT": {"kind": "analog"}, "BUCK_SW": {"note": "开关节点"},
    "MCU_EN": {"kind": "analog", "note": "RC 复位节点 10ms"},
    "BUCK_EN": {"kind": "logic", "note": "buck EN 5V 域合法（宽输入）"},
    "USB_DP_NC": {"kind": "nc"}, "USB_DN_NC": {"kind": "nc"}, "KEY_NC": {"kind": "nc"},
    "SPARE_GPIO": {"kind": "nc"}, "P_LED_BUF_EN": {"kind": "nc", "note": "预留，V1 不用"},
    "I2C_SDA": {"kind": "nc"}, "I2C_SCL": {"kind": "nc"}, "STAR_ALT": {"kind": "nc"},
    "LED_CHAIN_END": {"kind": "nc", "note": "末级 DOUT 悬空（树灯未装时盲盖）"},
    "JTAG_TP1": {"kind": "tp"}, "JTAG_TP2": {"kind": "tp"}, "JTAG_TP3": {"kind": "tp"},
    "JTAG_TP4": {"kind": "tp"}, "JTAG_TP5": {"kind": "tp"}, "JTAG_TP6": {"kind": "tp"},
    "LED_DIN": {"kind": "led_chain", "stage": 0, "note": "U6.B → 左眼 DIN"},
    "LED_CHAIN1": {"kind": "led_chain", "stage": 1, "note": "左眼 DOUT → 右眼 DIN"},
    "LED_CHAIN2": {"kind": "led_chain", "stage": 2, "note": "右眼 DOUT → 星灯 DIN"},
    "LED_CHAIN3": {"kind": "led_chain", "stage": 3, "note": "星灯 DOUT → 树灯 DIN"},
}

VDOM_OK = {"0V": 0, "3V3": 3, "5V": 5, "5V_AUDIO": 5}
LED_STAGES = [  # (stage net, module ref, led range)
    ("LED_DIN", "J5", (0, 8)), ("LED_CHAIN1", "J6", (9, 17)),
    ("LED_CHAIN2", "J7", (18, 21)), ("LED_CHAIN3", "J8", (22, 31)),
]
LED_COUNT_MAX = 32  # 22 常配 + 10 扩展；刷新 = 32×30µs + 50µs ≈ 1.01ms @800kHz

def build_nets(devices=None):
    nets = defaultdict(list)
    for dev in (devices if devices is not None else DEVICES):
        for pname, p in dev["pins"].items():
            nets[p["net"]].append({"ref": dev["ref"], "pin": pname,
                                   **{k: p[k] for k in ("dir", "vdom", "tol5v", "pull", "flag")}})
    return nets

def run_erc(nets=None, attrs=None, devices=None):
    nets = nets if nets is not None else build_nets()
    attrs = attrs if attrs is not None else NET_ATTR
    devices = devices if devices is not None else DEVICES
    errors, warns = [], []

    for name, pins in nets.items():
        a = attrs.get(name, {})
        kind = a.get("kind", "logic")
        drivers = [p for p in pins if p["dir"] == "OUT"]
        pwrs = [p for p in pins if p["dir"] == "PWR"]

        if kind in ("power", "nc", "tp", "analog"):
            continue

        if not drivers and not pwrs and not any(p.get("pull") for p in pins):
            # 电阻桥到电源网 = 上拉/下拉（结构性识别，不靠手填 flag）
            pulled = False
            for dev in devices:
                if dev["kind"] in ("passive", "bridge") and len(dev["pins"]) == 2:
                    dpins = list(dev["pins"].values())
                    on_net = [q for q in dpins if q["net"] == name]
                    if on_net:
                        other = dpins[0] if dpins[1] is on_net[0] else dpins[1]
                        if other["dir"] == "PWR" or VDOM_OK.get(other["vdom"], 0) > 0:
                            pulled = True
            if not pulled:
                errors.append(f"{name}: 无驱动且无上/下拉")

        if len(drivers) > 1 and name != "BUF_A":
            errors.append(f"{name}: 多驱动 {sorted({p['ref'] for p in drivers})}")

        net_v = max((VDOM_OK.get(p["vdom"], 0) for p in pins if p["dir"] in ("OUT", "PWR")), default=0)
        for p in pins:
            pv = VDOM_OK.get(p["vdom"], 0)
            if pv < net_v and not p.get("tol5v") and net_v > 3:
                errors.append(f"{name}.{p['ref']}.{p['pin']}: {p['vdom']} 器件接到 {net_v}V 域且未标 5V 容忍")

        if name in ("I2S_PCM_CLK", "I2S_PCM_FS") and len(drivers) != 1:
            errors.append(f"{name}: I2S 主时钟必须单驱动（Pi）")
        if name == "I2S_PCM_DIN" and len(drivers) != 1:
            errors.append(f"{name}: 麦克风数据必须单驱动（mic→Pi）")

    # P0-1 类：上拉域检查——passive 一侧 PWR>3V，另一侧 3V3 逻辑 IN → 违规
    for dev in devices:
        if dev["kind"] != "passive" or len(dev["pins"]) < 2:
            continue
        s1, s2 = list(dev["pins"].values())[:2]
        for a, b in ((s1, s2), (s2, s1)):
            va, vb = VDOM_OK.get(a["vdom"], 0), VDOM_OK.get(b["vdom"], 0)
            if a["dir"] == "PWR" and va > 3 and b["vdom"] == "3V3" and b["dir"] == "IN":
                errors.append(f"{dev['ref']}({dev['part'][:12]}): {va}V 域上拉到 3V3 逻辑引脚 {b['net']}（P0-1 类）")

    # P0-2 类：含晶体管下拉的网禁止任何推挽 OUT 直连
    for name, pins in nets.items():
        if any(p["ref"] == "Q1" for p in pins) and name != "AMP_FORCE_GATE":
            outs = [p for p in pins if p["dir"] == "OUT"]
            if outs:
                errors.append(f"{name}: 晶体管强制拉低网络存在直连推挽驱动 {sorted({p['ref'] for p in outs})}（P0-2 类）")

    # P0-3 类：翻译器方向
    for dev in devices:
        tr = dev.get("attrs", {}).get("translator")
        if not tr:
            continue
        dir_pin, vcca_pin = dev["pins"].get("DIR"), dev["pins"].get("VCCA")
        if dir_pin is None or vcca_pin is None:
            continue
        if tr.get("a_to_b_when_dir") == "HIGH" and dir_pin["net"] != vcca_pin["net"]:
            errors.append(f"{dev['ref']}: 声明 A→B 但 DIR 未接 VCCA（现接 {dir_pin['net']}，P0-3 类）")

    # LED 菊花链拓扑
    for stage_net, module_ref, _range in LED_STAGES:
        pins = nets.get(stage_net, [])
        dins = [p for p in pins if p["pin"] == "3" and p["dir"] == "IN" and p["ref"] == module_ref]
        srcs = [p for p in pins if p["dir"] == "OUT" and p["ref"] != module_ref]
        if len(dins) != 1:
            errors.append(f"{stage_net}: 模组 {module_ref} DIN 引脚异常（{len(dins)}）")
        if stage_net == "LED_DIN" and not any(p["ref"] == "U6" for p in srcs):
            errors.append(f"{stage_net}: 链级0 缺驱动源（U6.B）")
        if stage_net != "LED_DIN" and len(srcs) != 1:
            errors.append(f"{stage_net}: 链级输入应有且仅有一个上级 DOUT 源（{len(srcs)}）")

    # 电源/保护属性核验
    for dev in devices:
        at = dev.get("attrs", {})
        if "ptc_hold_a" in at and at["ptc_hold_a"] < 0.3:
            errors.append(f"{dev['ref']}: PTC hold 低于最小负载")
        if "tvs_standoff_v" in at and at["tvs_standoff_v"] < 5.0:
            errors.append(f"{dev['ref']}: TVS 反向截止电压 < 5V 工作电压")

    for rail in ("5V_MAIN", "5V_LED", "3V3_MCU", "GND", "5V_IN"):
        if rail not in nets:
            errors.append(f"电源轨缺失: {rail}")

    for cc in ("CC1_RD", "CC2_RD"):
        pins = nets.get(cc, [])
        if not any(p["ref"].startswith("R_CC") for p in pins):
            errors.append(f"{cc}: 缺 5.1kΩ Rd 下拉")

    groups = defaultdict(list)
    for dev in devices:
        g = dev.get("attrs", {}).get("bridge_group")
        if g:
            groups[g].append(dev)
    for g, devs in groups.items():
        schemes = [d.get("attrs", {}).get("closed_in") for d in devs]
        if len(schemes) != len(set(schemes)):
            errors.append(f"焊桥组 {g}: 归属冲突")

    if "UART_PI_TX" not in nets or "UART_ESP_TX" not in nets:
        errors.append("调试 UART 网络缺失")

    for dev in devices:
        for pname, p in dev["pins"].items():
            if p.get("flag") == "dnp":
                kind = attrs.get(p["net"], {}).get("kind", "logic")
                if kind not in ("nc",):
                    warns.append(f"{dev['ref']}.{pname}: dnp 引脚落在非 nc 网 {p['net']}")

    # 接口表对齐
    try:
        itable = json.loads((BASE.parent / "interfaces" / "interfaces.json").read_text(encoding="utf-8"))
        alias = {"VBUS_IN": "5V_IN", "P5V_PI1": "5V_MAIN", "P5V_PI2": "5V_MAIN",
                 "P3V3_MCU": "3V3_MCU", "P3V3_PI": "3V3_PI", "P5V_LED": "5V_LED",
                 "P5V_LED_EXT": "5V_LED_EXT", "USB_DP/DN": None, "壳地": None,
                 "TP_*": None, "USB_DP_MCU": None, "USB_DN_MCU": None}
        sigs = set()
        for c in itable["connectors"]:
            for pin in c["pins"]:
                sigs.add(pin["signal"])
        sigs.discard("-")
        mapped = {alias.get(s, s) for s in sigs}
        mapped.discard(None)
        netnames = set(nets.keys()) | set(attrs.keys())
        for s in sorted(mapped):
            if s not in netnames:
                warns.append(f"接口表信号 {s} 未在网表中出现（应为预留或已改名）")
    except FileNotFoundError:
        warns.append("interfaces.json 未生成，跳过对齐检查")

    return nets, errors, warns

def main() -> None:
    nets, errors, warns = run_erc()
    netlist = {
        "schema": "cbu-netlist/0.3", "product": "christmas-buddy-v1",
        "date": date.today().isoformat(),
        "architecture": "A（Pi Zero 2 W + ESP32-S3 协处理器；方案 B 变化点以 flag 标注）",
        "datasheet_facts": FACTS,
        "led_chain": {"stages": [{"net": n, "module": m, "leds": list(r)} for n, m, r in LED_STAGES],
                      "max_leds": LED_COUNT_MAX,
                      "refresh_ms": round((LED_COUNT_MAX * 24 * 1.25 + 50) / 1000, 2),
                      "note": "WS2812/SK6812 位时长 1.25µs×24bit=30µs/颗 @800kHz"},
        "amp_sd_arbitration": {
            "design": "BCM25 → R_MODE 620k → SD 节点；Q1（ESP32 IO17 门控）拉低强制静音；"
                      "SD 内部 100k 下拉提供默认 shutdown（官方）",
            "cases": {
                "Pi 高": "V_SD=3.3×100/720=0.458V ∈ (0.16,0.77) → (L+R)/2 模式，输出开",
                "Pi 低": "节点 0V → shutdown",
                "Pi 悬空/死机": "内部 100k 下拉 → 0V → shutdown（安全默认）",
                "ESP32 强制（K4）": "Q1 导通 → 0V；Pi 高仅灌 3.3/620k=5.3µA，无争用应力",
                "ESP32 死机": "R_G 下拉 → Q1 截止 → Pi 正常控制",
            },
        },
        "devices": [{**d, "pin_list": list(d["pins"].keys())} for d in DEVICES],
        "nets": {k: sorted(v, key=lambda p: (p["ref"], p["pin"])) for k, v in sorted(nets.items())},
        "net_attrs": NET_ATTR,
        "erc": {"errors": errors, "warnings": warns},
    }
    (BASE / "netlist.json").write_text(json.dumps(netlist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = ["# Christmas Buddy V1 · 网表级原理图 ERC v2 报告", "",
          f"日期：{date.today().isoformat()}｜器件 {len(DEVICES)}，网络 {len(nets)}", "",
          "## 数据手册事实（官方 PDF 本地提取，2026-11-28）", ""]
    for k, v in FACTS.items():
        md.append(f"- **{k}**：{v}")
    md += ["", "## P0 修复摘要", "",
           "- P0-1：R_EN 上拉 5V_MAIN→3V3_MCU，新增 C_EN 1µF（RC=10ms>tH 3ms）",
           "- P0-2：AMP_SD 仲裁重构——删除外置下拉（保留官方内部 100k），BCM25 经 R_MODE 620k 隔离，"
           "Q1 强制静音与 Pi 高电平争用电流仅 5.3µA；(L+R)/2 单声道模式由阻值编码实现",
           "- P0-3：U6 DIR GND→VCCA（官方功能表 DIR=H: A→B）", "",
           "## ERC 结果", ""]
    for e in errors:
        md.append(f"- **ERROR** — {e}")
    for w in warns:
        md.append(f"- **WARN** — {w}")
    if not errors and not warns:
        md.append("- 全部通过（0 error, 0 warning）")
    (BASE / "erc_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"netlist v0.3: {len(DEVICES)} devices, {len(nets)} nets; ERC errors={len(errors)} warns={len(warns)}")
    for e in errors:
        print("  ERROR:", e)
    for w in warns:
        print("  WARN:", w)
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    main()
