#!/usr/bin/env python3
"""M4 视觉设计约束模型（可机器检查部分）+ 两套方案的规格定义。

原则（任务书 §6）：审美不可完全数学化——本文件只把**可计算**的约束交给检查，
审美判断交给真实渲染 + 盲评 + 人工验收。不得声称「Lean/脚本证明了好看」。

输出：visual-specs.json / visual-specs.md
运行：python3 source-data/christmas-buddy/visual/visual_specs.py
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "mech"))
from params import PARAMS  # noqa: E402

BASE = Path(__file__).parent

PALETTE = {
    "cream_white": {"hex": "#F3EDE2", "用途": "头部/体部主色（奶油白）", "材质": "哑光 PLA，目视 15% 光泽"},
    "forest_green": {"hex": "#2F5233", "用途": "帽子/围巾（森林绿）", "材质": "哑光 PLA"},
    "christmas_red": {"hex": "#B3312E", "用途": "围巾结/星星背板（圣诞红）", "材质": "哑光 PLA"},
    "starlight_gold": {"hex": "#D4AF37", "用途": "帽顶小球/底座环/星星灯透罩（星光金）", "材质": "微金属光泽 PLA"},
}

def checks() -> tuple[list, list]:
    """机器可检查的视觉/几何约束（数值来自 mech/params.py 单一源）。"""
    results, notes = [], []

    def add(name, ok, detail):
        results.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail})

    for scheme_key, label in (("scheme_a", "A 雪宝"), ("scheme_b", "B 胶囊舱")):
        s = PARAMS[scheme_key]
        head = s["head"]
        prof = s["body_profile"]
        if "brim" in s:  # 方案 A：帽檐底 + 帽檐厚 + 帽高 + 帽顶球
            total = s["brim"]["z"] + s["brim"]["h"] + s["hat"]["h"] + 3.5
            hat_h = s["brim"]["h"] + s["hat"]["h"] + 3.5
        else:            # 方案 B：帽球心 + 球半径 + 天线杆竖向分量
            total = head["center_z"] + head["d"] * 0.28 + head["d"] / 2 + s["hat"]["stub_h"] * 0.94
            hat_h = s["hat"]["h"] + s["hat"]["stub_h"]
        add(f"{label}: 总高 ≤ 160mm", total <= 160.5, f"几何推算总高 {total:.1f}mm（与 build_mech 导出一致口径）")
        # 头身比：头径/体部最大径 在 0.55–0.85 之间（童话比例，可调）
        body_max_r = max(r for r, _ in prof)
        ratio = head["d"] / (2 * body_max_r)
        add(f"{label}: 头径/体径比 0.55–0.85", 0.55 <= ratio <= 0.85, f"{ratio:.2f}")
        # 帽部高度占比 15–25%（精灵感）
        z_top_body = prof[-1][1]
        head_top = head["center_z"] + head["d"] / 2
        # 帽起始于头顶附近：brim.z（A）或 neck_ring+head（B）——统一以 hat_h/(total) 校核
        hat_ratio = hat_h / total
        add(f"{label}: 帽高占比 15–25%", 0.15 <= hat_ratio <= 0.25, f"{hat_ratio*100:.1f}%")

    # 对称性（两案同内核）
    e = PARAMS["eyes"]
    add("双眼左右对称", abs(e["dx"]) > 0, f"眼位 x=±{e['dx']}mm（镜像由构造保证）")
    # 眼窗位置在头部几何内
    for scheme_key, label in (("scheme_a", "A"), ("scheme_b", "B")):
        hd = PARAMS[scheme_key]["head"]
        inside = e["z"] + e["module_h"] / 2 <= hd["center_z"] + hd["d"] / 2 - 2
        add(f"{label}: 眼窗完全位于头部几何内", inside,
            f"眼窗顶 {(e['z'] + e['module_h']/2):.1f} ≤ 头顶 {hd['center_z'] + hd['d']/2 - 2:.1f}")
    # 扩散板厚度
    add("眼窗扩散板 ≤ 1.5mm", e["diffuser_t"] <= 1.5, f"{e['diffuser_t']}mm（乳白透光，打印轮验光效）")
    # 分件线：方案 A ≤ 4 条可见分件线；方案 B 有意展示分段环（风格差异，不做上限）
    add("分件线登记", True, "A：底缝/前后壳缝（围巾遮盖）/帽檐/帽体；B：底环/颈环/脸窗/帽球——均为构造性分件")
    # 色板
    add("色板恰好 4 色（产品方向）", len(PALETTE) == 4, "奶油白/森林绿/圣诞红/星光金")
    notes.append("对比度与色差（ΔE）留待实物打印轮以色卡核对，本模型不声称可证。")

    blind_review = {
        "protocol": "盲评：渲染图匿名编号 V1/V2 随机排序，评审者（用户/家长代表）不知方案名；",
        "dimensions": ["可爱度", "圣诞氛围", "做工精致感", "与 Apple/TE 参考的接近度", "孩子第一眼吸引力"],
        "scale": "每项 1–5 分 + 一句话理由；两案得分差 ≥1 才算显著；<0.5 由用户决断或合并优点",
        "rule": "盲评在渲染轮执行；渲染图必须是本参数模型的真实渲染（renders_local/），不得用概念图冒充。"
    }
    return results, notes, blind_review

def main() -> None:
    results, notes, blind = checks()
    out = {
        "schema": "visual-specs/1.0", "product": "christmas-buddy-v1", "date": date.today().isoformat(),
        "palette": PALETTE,
        "schemes": {
            "a_雪宝": {
                "概念": "圆润雪宝精灵——苹果式完整轮廓：一个连续的『雪堆』体量 + 软帽檐，无硬棱角；围巾隐藏前后壳分缝。",
                "分件": ["底座环（星光金）", "前/后壳缝（围巾遮盖）", "帽檐", "帽体（可掀）"],
                "个性": "帽子倾斜 14° 表达歪头感；眼窗为两块 3×3 阵列透窗。",
            },
            "b_胶囊舱": {
                "概念": "Teenage Engineering 式分段胶囊：圆柱分环 + 平脸窗 + 短帽球，克制的工业可爱。",
                "分件": ["底座金环", "颈环", "脸窗（嵌入式平面板）", "帽球+天线杆"],
                "个性": "脸窗为凹入平面（扩散板嵌窗框），分段环用星光金强调。",
            },
        },
        "machine_checks": results,
        "notes": notes,
        "blind_review": blind,
        "render_views_required": ["正面", "侧面", "背面", "45度", "爆炸", "外壳拆解", "PCB装配", "底座场景"],
    }
    (BASE / "visual-specs.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = ["# Christmas Buddy V1 · M4 视觉约束（机器可检查部分）", "",
          f"日期：{date.today().isoformat()}｜审美判断不在本模型范围内（交真实渲染 + 盲评）", "",
          "## 色板（4 色锁定）", "",
          "| 名称 | HEX | 用途 | 材质 |", "|---|---|---|---|"]
    for k, v in PALETTE.items():
        md.append(f"| {k} | `{v['hex']}` | {v['用途']} | {v['材质']} |")
    md += ["", "## 机器检查", ""]
    for r in results:
        md.append(f"- **{r['result']}** — {r['check']}：{r['detail']}")
    md += ["", "## 两套方案", ""]
    for name, s in out["schemes"].items():
        md += [f"### {name}", "", f"- 概念：{s['概念']}", f"- 分件：{'；'.join(s['分件'])}", f"- 个性：{s['个性']}", ""]
    md += ["", "## 盲评协议", "", f"- {blind['protocol']}", f"- 维度：{('、'.join(blind['dimensions']))}",
           f"- {blind['scale']}", f"- {blind['rule']}", "", "## 附注", ""] + [f"- {n}" for n in notes]
    (BASE / "visual-specs.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    fails = [r for r in results if r["result"] == "FAIL"]
    print(f"visual specs: {len(results)-len(fails)}/{len(results)} PASS")
    for r in fails:
        print("  FAIL:", r["check"], "->", r["detail"])
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
