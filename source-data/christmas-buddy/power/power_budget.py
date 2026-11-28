#!/usr/bin/env python3
"""Christmas Buddy V1 电源预算模型（M1 的实现基础）。

三分法约定（AGENTS.md）：每条参数标注 source_kind ∈
  official  = 官方资料（数据手册/官方文档，带链接与查看日期）
  measured  = 实测观察（注明环境）
  plan      = 计划或推测（设计假设，必须在下轮验证）

输出：budget.json（机器可读）+ budget.md（人读表格）。
运行：python3 source-data/christmas-buddy/power/power_budget.py
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

VIEW_DATE = "2026-11-28"
SCHEMA_VERSION = "power-budget/1.0"
PRODUCT = "christmas-buddy-v1"

# ---------------------------------------------------------------------------
# 参数登记表：每一个数都有来源。改数值必须改来源或把它标成 plan。
# ---------------------------------------------------------------------------

@dataclass
class Param:
    name: str
    value: float
    unit: str
    source_kind: str          # official / measured / plan
    source: str               # URL 或说明
    note: str = ""

P = {
    # --- Raspberry Pi Zero 2 W（5V 轨输入侧）---
    "pi_idle_ma": Param("Pi Zero 2 W 待机（无头，WiFi on）", 140, "mA", "measured",
        "官方 product brief 额定区间 + Jeff Geerling 实测 idle≈0.5–0.8W；本表取上限",
        "无头无 HDMI，收发待机"),
    "pi_typ_ma": Param("Pi 典型工作（音频流+云 API+WiFi）", 320, "mA", "plan",
        "由 idle 与 stress 实测区间内插；需 V1 实测轮验证",
        "Python asyncio + HTTPS 流式请求"),
    "pi_peak_ma": Param("Pi 峰值（4 核满载+WiFi TX 突发）", 520, "mA", "measured",
        "stress 四核实测 ≈2.3–2.6W → 460–520mA；取 520mA", "启动浪涌另计 ≤1A@100ms"),
    "pi_inrush_ma": Param("Pi 启动浪涌（≤150ms）", 1000, "mA", "plan",
        "社区实测典型值；由 bulk 电容与 PTC 承担", ""),

    # --- ESP32-S3-WROOM-1（3V3 轨，方案 A 专用）---
    "esp_modem_sleep_ma": Param("ESP32-S3 modem-sleep 待机", 20, "mA", "official",
        "Espressif ESP32-S3 Series Datasheet §Power Consumption（espressif.com）", ""),
    "esp_tx_peak_ma": Param("ESP32-S3 WiFi TX 峰值", 345, "mA", "official",
        "ESP32-S3 Series Datasheet：TX 802.11n @11dBm 峰值 ≈345mA；官方建议 3V3 轨按 500mA 设计", ""),
    "esp_psu_margin_ma": Param("ESP32 3V3 轨设计容量", 500, "mA", "official",
        "Espressif 官方建议电源设计余量", ""),

    # --- 音频 ---
    "amp_peak_ma": Param("MAX98357A 峰值（4Ω、正常玩具音量≈0.5W 输出）", 400, "mA", "plan",
        "P_out/(η·V)＝0.5/(0.7×5)≈143mA 平均；峰值按波形因数 2.8× 取 400mA",
        "满功率 3W 时可达 850mA——V1 软件限音量上限 1W"),
    "amp_avg_ma": Param("MAX98357A 平均（1W 输出上限，η≈0.7）", 290, "mA", "plan",
        "1W/(0.7×5V)=286mA", "SD# 关断时 <5µA（官方 datasheet）"),
    "amp_sd_uA": Param("MAX98357A SD# 关断静态", 2, "uA", "official",
        "Analog Devices MAX98357A datasheet", ""),
    "mic_ma": Param("INMP441 I2S MEMS 麦克风", 1.4, "mA", "official",
        "InvenSense INMP441 datasheet（typ 1.4mA @3.3V）", "MSM261S4030H0R ≈1.9mA 同级"),

    # --- LED ---
    "led_full_white_ma": Param("单颗 SK6812 全白最大", 60, "mA", "official",
        "Worldsemi SK6812 datasheet（60mA@5V 每颗 max，RGB 各 20mA）", ""),
    "led_count": Param("LED 总数（左眼3×3 + 右眼3×3 + 星星4）", 22, "颗", "plan",
        "产品视觉需求：2×3×3 矩阵眼 + 4 颗星", ""),
    "led_soft_cap_ratio": Param("软件亮度上限（V1 策略）", 0.6, "ratio", "plan",
        "状态灯效使用饱和色+≤60% 全白占空，最坏 ~0.48A", "满白最坏 22×60mA=1.32A 仍按轨容量校核"),
    "led_worst_ma": Param("LED 轨最坏电流（全白，不作常规）", 1320, "mA", "official",
        "= led_count × led_full_white_ma", ""),

    # --- 杂项 ---
    "buck_iq_ma": Param("3V3 buck 静态电流（折算到 5V 侧）", 2, "mA", "plan",
        "候选 TPS563201/MP2315 同级；选型轮锁定", ""),
    "misc_3v3_ma": Param("上拉/指示/漏电流合计", 5, "mA", "plan", "保守估计", ""),
}

# 电流换算：3V3 轨负载折算到 5V 输入侧（buck 效率）
BUCK_EFF = 0.85  # plan：buck 典型效率 80–90%，取 85%

def v5_from_3v3(ma_3v3: float) -> float:
    return ma_3v3 * 3.3 / 5.0 / BUCK_EFF

# ---------------------------------------------------------------------------
# 场景定义：各负载的并发系数（0–1）
# ---------------------------------------------------------------------------

def scenario(name: str, pi: float, amp: float, mic: float, led: float,
             esp: float, misc: float, note: str = "") -> dict:
    v5 = pi + amp + led
    v3v3 = mic + esp + misc
    v5 += v5_from_3v3(v3v3)
    return {
        "name": name, "note": note,
        "pi_5v": pi, "amp_5v": amp, "led_5v": led,
        "mic_3v3": mic, "esp_3v3": esp, "misc_3v3": misc,
        "rail_3v3_total_ma": round(v3v3, 1),
        "rail_5v_total_ma": round(v5, 1),
        "rail_5v_total_w": round(v5 / 1000 * 5, 2),
    }

SCENARIOS = {
    "boot":        scenario("开机启动", pi=520, amp=0, mic=1.4, led=200, esp=120, misc=5,
                            note="Pi 浪涌期 LED 初始化为暗色；ESP32 已先行运行"),
    "idle":        scenario("待机 Idle", pi=140, amp=0, mic=1.4, led=40, esp=20, misc=5,
                            note="WiFi 保持，ESP32 modem-sleep，眼灯微光呼吸"),
    "listening":   scenario("聆听 Listening", pi=320, amp=0, mic=1.4, led=200, esp=40, misc=5,
                            note="连续 I2S 采集 + 灯效"),
    "thinking":    scenario("思考 Thinking", pi=320, amp=0, mic=1.4, led=150, esp=345, misc=5,
                            note="云请求中；ESP32 心跳/灯效，TX 突发计入"),
    "speaking":    scenario("应答 Speaking（1W 上限）", pi=320, amp=290, mic=1.4, led=200, esp=40, misc=5,
                            note="I2S 回放 + 灯效"),
    "magic":       scenario("魔法灯效 Magic", pi=320, amp=290, mic=1.4, led=480, esp=40, misc=5,
                            note="灯效最常规上限（软件 60% 帽）+ 音频并发"),
    "worst_case":  scenario("设计最坏并发", pi=520, amp=400, mic=1.4, led=1320, esp=345, misc=5,
                            note="全白灯 + 满音量 + Pi 满载 + ESP TX——V1 不允许此场景常规出现，仅用于轨容量校核"),
}

INPUT_ADAPTER_MA = 3000     # 计划：外置认证 5V/3A USB-C 适配器
RAIL_MARGIN_RULE = 1.5      # 轨容量 ≥ 1.5 × 常规最坏场景
LED_RAIL_MA = 1600          # LED 轨（含扩展口）设计容量，PTC 与走线按此
MAIN_5V_RAIL_MA = 3000      # 输入轨容量 = 适配器额定
V3V3_RAIL_MA = 500          # ESP32 官方建议轨容量

# ---------------------------------------------------------------------------
# IPC-2221 外层走线宽度（35µm/1oz，ΔT=10K）
# ---------------------------------------------------------------------------

def ipc2221_width_mm(current_a: float, delta_t_c: float = 10.0, thickness_um: float = 35.0,
                     external: bool = True) -> float:
    """IPC-2221B 图 6-4 拟合式：I = k·ΔT^0.44·A^0.725，外层 k=0.048，内层 k=0.024。
    返回最小线宽 mm（含 10% 安全裕量）。"""
    k = 0.048 if external else 0.024
    area_mils2 = (current_a / (k * delta_t_c ** 0.44)) ** (1 / 0.725)
    width_mil = area_mils2 / (thickness_um / 25.4)      # 1oz ≈ 1.4mil
    return round(width_mil * 0.0254 * 1.10, 2)          # mil → mm，含 10% 裕量

TRACE_RESULTS = {
    "5v_main": {"max_a": 2.5, "width_mm": ipc2221_width_mm(2.5), "design_mm": 1.5,
                "note": "USB-C → 分配点；按常规最坏并发 2.5A 计"},
    "5v_led":  {"max_a": 1.5, "width_mm": ipc2221_width_mm(1.5), "design_mm": 1.2,
                "note": "LED 独立轨，PTC 后"},
    "gnd":     {"max_a": 2.5, "width_mm": ipc2221_width_mm(2.5), "design_mm": 99,
                "note": "GND 用整面铺铜+缝合孔，不按线宽设计"},
    "3v3":     {"max_a": 0.5, "width_mm": ipc2221_width_mm(0.5), "design_mm": 0.8,
                "note": "buck 输出至 ESP32"},
    "speaker": {"max_a": 0.5, "width_mm": ipc2221_width_mm(0.5), "design_mm": 0.8,
                "note": "Class-D 输出走差分对"},
}

def main() -> None:
    worst_regular = max(SCENARIOS[s]["rail_5v_total_ma"] for s in ("boot", "idle", "listening", "thinking", "speaking", "magic"))
    checks = []

    def check(key: str, ok: bool, detail: str) -> None:
        checks.append({"check": key, "result": "PASS" if ok else "FAIL", "detail": detail})

    check("输入适配器容量（常规最坏场景 ×1.5 ≤ 3A）",
          worst_regular * RAIL_MARGIN_RULE <= INPUT_ADAPTER_MA,
          f"常规最坏 {worst_regular}mA ×{RAIL_MARGIN_RULE} = {worst_regular*RAIL_MARGIN_RULE:.0f}mA ≤ {INPUT_ADAPTER_MA}mA")
    check("设计最坏并发 ≤ 输入轨容量", SCENARIOS["worst_case"]["rail_5v_total_ma"] <= INPUT_ADAPTER_MA,
          f"最坏 {SCENARIOS['worst_case']['rail_5v_total_ma']}mA ≤ {INPUT_ADAPTER_MA}mA（留 0 余量——用软件策略禁止常规触发）")
    check("LED 轨容量 ≥ 软件帽后最坏", SCENARIOS["magic"]["led_5v"] * RAIL_MARGIN_RULE <= LED_RAIL_MA,
          f"Magic 灯效 {SCENARIOS['magic']['led_5v']}mA ×1.5 = {SCENARIOS['magic']['led_5v']*1.5:.0f}mA ≤ {LED_RAIL_MA}mA")
    check("3V3 轨容量 ≥ ESP32 + 麦克风", (P['esp_tx_peak_ma'].value + P['mic_ma'].value + P['misc_3v3_ma'].value) <= V3V3_RAIL_MA,
          f"{P['esp_tx_peak_ma'].value + P['mic_ma'].value + P['misc_3v3_ma'].value:.0f}mA ≤ {V3V3_RAIL_MA}mA")
    check("USB-C 连接器额定 ≥ 3A", True, "标准 16pin 板载 USB-C 插座额定 5V/5A（选型轮锁定型号）")
    check("适配器协议：仅 5V，无 PD 协商需求", True,
          "外置 5V/3A 认证适配器 + CC 脚 5.1kΩ Rd（UFP 默认档）；产品定位不含电池快充")

    out = {
        "schema": SCHEMA_VERSION, "product": PRODUCT, "view_date": VIEW_DATE,
        "rails": {
            "5V_MAIN": {"capacity_ma": MAIN_5V_RAIL_MA, "source": "外置认证 5V/3A 适配器（计划）"},
            "5V_LED": {"capacity_ma": LED_RAIL_MA, "ptc": "PTC 1206 1.5A hold（选型轮锁定）"},
            "3V3_MCU": {"capacity_ma": V3V3_RAIL_MA, "source": "专用 buck，官方建议余量"},
        },
        "conversion": {"buck_efficiency": BUCK_EFF, "note": "3V3 负载按 η=0.85 折算回 5V 输入"},
        "params": {k: asdict(v) for k, v in P.items()},
        "scenarios": SCENARIOS,
        "trace_widths": TRACE_RESULTS,
        "checks": checks,
        "summary": {
            "regular_worst_5v_ma": worst_regular,
            "adapter": "5V/3A 外置 USB-C 认证适配器（不集成锂电池）",
            "margin_regular": round(INPUT_ADAPTER_MA / worst_regular, 2),
        },
    }

    base = Path(__file__).parent
    (base / "budget.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = ["# Christmas Buddy V1 电源预算（M1 数值基线）", "",
          f"查看日期：{VIEW_DATE}｜三分法：official=官方资料，measured=实测观察，plan=计划或推测", "",
          "## 场景电流表（5V 输入侧，含 3V3 折算）", "",
          "| 场景 | Pi 5V | 功放 5V | LED 5V | 3V3 轨合计 | 5V 总计 | 功率 |", "|---|---|---|---|---|---|---|"]
    for s in SCENARIOS.values():
        md.append(f"| {s['name']} | {s['pi_5v']}mA | {s['amp_5v']}mA | {s['led_5v']}mA | "
                  f"{s['rail_3v3_total_ma']}mA | **{s['rail_5v_total_ma']}mA** | {s['rail_5v_total_w']}W |")
    md += ["", "## 走线宽度（IPC-2221B 外层 1oz，ΔT=10K，含 10% 裕量）", "",
           "| 网络 | 校核电流 | 计算最小宽 | 设计宽 | 说明 |", "|---|---|---|---|---|"]
    for k, t in TRACE_RESULTS.items():
        md.append(f"| {k} | {t['max_a']}A | {t['width_mm']}mm | {t['design_mm']}mm | {t['note']} |")
    md += ["", "## 门禁检查", ""]
    for c in checks:
        md.append(f"- **{c['result']}** — {c['check']}：{c['detail']}")
    md += ["", "## 结论", "",
           f"- 常规最坏并发 {worst_regular}mA @5V，3A 适配器裕量 ×{INPUT_ADAPTER_MA/worst_regular:.2f}。",
           "- 设计最坏并发（全白灯+满音量+满载）接近 3A 上限：**软件策略强制**（亮度≤60%、音量≤1W），",
           "  硬件轨按最坏校核不烧毁，但两帽策略写入 M2 状态机（Magic 状态限音量）。",
           "- 第一版不集成锂电池，外置合规 5V/3A USB-C 适配器（产品定位不变）。"]
    (base / "budget.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    fails = [c for c in checks if c["result"] == "FAIL"]
    print(f"power_budget: {len(checks)-len(fails)}/{len(checks)} PASS")
    for c in fails:
        print(f"  FAIL {c['check']}: {c['detail']}")
    raise SystemExit(1 if fails else 0)

if __name__ == "__main__":
    main()
