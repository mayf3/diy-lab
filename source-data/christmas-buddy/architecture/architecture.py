#!/usr/bin/env python3
"""方案 A（Pi + ESP32-S3 协处理器）vs 方案 B（Pi 单主控）结构化比较。

评分 1–5（5 最好），权重合计 100。数据来源：power/budget.json、官方 datasheet、
价格标注为计划值（采购轮以嘉立创/LCSC 实价复核）。
运行：python3 source-data/christmas-buddy/architecture/architecture.py
"""
from __future__ import annotations

import json
from pathlib import Path

VIEW_DATE = "2026-11-28"

CRITERIA = [
    # (准则, 权重, A得分, B得分, 依据)
    ("BOM 成本（板+贴片）", 10, 3, 5,
     "A 多 ESP32-S3 模块≈¥15–22 + buck/LDO/缓冲≈¥6 → +¥25±5（plan，SMT 贴片 5 件摊销）"),
    ("PCB 面积", 8, 3, 5,
     "A 需多 ~25×25mm（ESP32 模块 18×25.5 + 外围）；两案初版外形均为 ~58×78mm 内可容纳"),
    ("整机功耗", 5, 4, 5,
     "A 常态 +30–60mA@3.3V（modem-sleep 待机，power/budget.json 已计入）；差 ~0.2W，可忽略"),
    ("接口/时序余量", 18, 5, 2,
     "B：SK6812 需 SPI-DMA 或 PWM 编码，与 PCM I2S 音频共用 DMA/时钟域，冲突需小心调度；"
     "A：ESP32 RMT 独立外设专责 LED，Pi 专职音频。B 可行但把风险压在软件细节上"),
    ("软件复杂度", 15, 3, 4,
     "A：+1 套 MCU 固件（LED 动画+按键+UART 协议，约 300–600 行，Agent 可维护）；"
     "B：全部在 Linux 侧，但需要 watchdog+灯效实时性补丁"),
    ("可靠性/失效安全", 20, 5, 2,
     "关键差异：K4 晚安强制静音走 ESP32 硬件路径（AMP_SD_FORCED），Pi 死机/重启时眼睛仍受控、"
     "耳朵仍有声学静音；B 案静音/灯效全部依赖 Linux 存活，child-facing 产品该项权重最高"),
    ("升级能力", 10, 5, 3,
     "A：未来换 SBC/CM5 或加电池管理时，HMI 固件不动；B：换核心板=全部重写"),
    ("制造难度", 6, 4, 5,
     "A 多一颗模块贴装（扩展库 C 编号，嘉立创 SMT 可贴）；B 元件更少"),
    ("调试/测试难度", 8, 4, 4,
     "A 多一个调试对象但隔离性好（音频与灯效各自独立可测）；B 系统耦合高，出问题定位靠 Linux 内部"),
]

VERDICT = {
    "recommended": "A",
    "rationale": [
        "面向儿童的失效安全（晚安强制静音、Pi 死机时眼睛受控）权重最高，A 有硬件安全路径，B 没有。",
        "SK6812 与 I2S 音频的资源冲突在 B 案是持续性工程债；A 案把实时性外设交给 ESP32 专用外设（RMT），Linux 只做云交互。",
        "A 增量成本 ≈¥25–30、功耗 ≈0.2W、面积 ≈6cm²，相对收益（失效安全+时序隔离+升级能力）不成立为否决项。",
    ],
    "fallback_trigger": [
        "若 ESP32-S3 固件与 Pi 的 UART 集成超过 2 个迭代周仍不稳定 → 降级 B（U3 不贴，跳线改配置），降级决定须用户确认。",
        "若嘉立创 SMT 对 U3 模块贴装报价或良率异常 → 改手焊模块（模块为 0.5mm 间距半孔工艺，需钢网+热风，人完成）。",
    ],
    "not_decided_by_agent": ["最终架构冻结须用户签字（门禁 11）。"],
}

PI_ASSESSMENT = {
    "memory": {
        "spec": "512MB LPDDR2（官方 product brief）",
        "verdict_对产品": "够用但紧",
        "detail": "OS+Python 运行时 ≈200–260MB；流式 ASR/TTS/GPT 全部走云 API，无本地大模型；"
                  "启用 zram + 精简 OS 后余量可控。禁止在本机跑本地推理（产品定位=云交互）。",
        "fallback": "若实测轮余量 <80MB 常态 → 换 1–2GB SBC（Orange Pi Zero 3 1GB/Radxa Zero 3W，同为 Allwinner/Rockchip ARM64，"
                    "软件成熟度低于 Raspberry Pi OS，仅作备选不改定位）",
    },
    "audio_concurrency": {
        "spec": "BCM2710A1 PCM 控制器支持 I2S 输入+输出同时（全双工）",
        "verdict_对产品": "满足",
        "detail": "16kHz 单声道采集（mic）与 44.1kHz 立体声回放（DAC）可同时运行于 ALSA；"
                  "CPU 占用 <10%。麦克风 INMP441 时钟由 Pi 供（master 模式）。",
    },
    "response_latency": {
        "spec": "云链路：采集→ASR→GPT→TTS→回放",
        "verdict_对产品": "V1 目标 p50≤3s、p95≤5s（首个音频）",
        "detail": "流式 ASR + GPT 流式 + 流式 TTS 并行化可到 1.5–2.5s；非流式退化到 4–8s 不可接受，"
                  "故任务书把「流式管线」列为软件任务的验收项。该指标属实测轮验证，本预研不声称达成。",
    },
}

def main() -> None:
    wsum = sum(c[1] for c in CRITERIA)
    score_a = sum(c[1] * c[2] for c in CRITERIA) / wsum
    score_b = sum(c[1] * c[3] for c in CRITERIA) / wsum
    out = {
        "schema": "architecture-compare/1.0", "product": "christmas-buddy-v1", "view_date": VIEW_DATE,
        "plan_a": {
            "name": "模块化：Pi Zero 2 W（云 AI/音频）+ ESP32-S3（HMI 协处理器）+ 载板",
            "pi_role": "WiFi、云 API（ASR/GPT/TTS）、I2S 音频采集回放",
            "esp_role": "LED 眼睛/星星 RMT 驱动、按键去抖、K4 安全静音、Pi 心跳看护、未来电池管理",
        },
        "plan_b": {
            "name": "简化：Pi Zero 2 W 单主控 + 载板（无第二 MCU）",
            "pi_role": "全部：云 API、音频、LED（SPI/PWM 编码）、按键",
            "esp_role": "无（U3 不贴）",
        },
        "criteria": [{"name": c[0], "weight": c[1], "score_a": c[2], "score_b": c[3], "basis": c[4]} for c in CRITERIA],
        "weighted_scores": {"plan_a": round(score_a, 2), "plan_b": round(score_b, 2)},
        "verdict": VERDICT,
        "pi_assessment": PI_ASSESSMENT,
        "price_basis": "全部价格为 计划或推测（plan）；采购执行轮以嘉立创/LCSC 实价复核后才可进入下单清单",
    }
    base = Path(__file__).parent
    (base / "architecture.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = ["# Christmas Buddy V1 电子架构比较（方案 A vs 方案 B）", "",
          f"查看日期：{VIEW_DATE}｜评分 1–5（5 最好），权重合计 {wsum}", "",
          "| 准则 | 权重 | A | B | 依据 |", "|---|---|---|---|---|"]
    for c in CRITERIA:
        md.append(f"| {c[0]} | {c[1]} | {c[2]} | {c[3]} | {c[4]} |")
    md += ["", f"**加权总分：A = {score_a:.2f}，B = {score_b:.2f}**", "",
           "## 推荐", ""]
    md += [f"- {r}" for r in VERDICT["rationale"]]
    md += ["", "## 降级触发条件（B 案回退）", ""]
    md += [f"- {t}" for t in VERDICT["fallback_trigger"]]
    md += ["", "## Pi Zero 2 W 适用性评估", ""]
    for k, v in PI_ASSESSMENT.items():
        md.append(f"### {k}\n\n- 规格：{v['spec']}\n- 判定：**{v['verdict_对产品']}**\n- {v['detail']}\n- 兜底：{v.get('fallback', '—（按任务书验收项验证）')}\n")
    md += ["", "## 结论边界", "",
           "- 本比较是工程预研结论；架构冻结须用户签字确认。",
           "- 「不要预设 ESP32 一定存在」：B 案得分主要输在失效安全与时序隔离，而非成本——若把可靠性权重从 20 降到 10，两案接近。"
           "这正是把它交给用户决策的原因。"]
    (base / "architecture.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"architecture: A={score_a:.2f} B={score_b:.2f}, recommended={VERDICT['recommended']}")

if __name__ == "__main__":
    main()
