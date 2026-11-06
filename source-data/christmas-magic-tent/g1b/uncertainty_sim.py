#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G1b 参数不确定性模拟（纯 Python，无需 Blender）。

对真实近候选的未知尺寸（檐口高 E、门净宽、门净高、"总高≠屋脊高"的解释差）
不做单点猜测，而是在假设网格上重跑 G0 几何检查，输出三类判定：
  DETERMINISTIC_PASS —— 网格内全部组合通过
  CONDITIONAL        —— 部分组合通过（给出失效边界）
  CANNOT_JUDGE       —— 数据不足（本模拟中不出现；缺数据的字段靠本模拟兜底）

检查项（G0 同一几何引擎，阈值同一套）：
  door_clear        门洞顶角净空 ≥ 5cm（门顶进入山墙区域的真实屋面线检查）
  door_margin       门洞侧边净宽 ≥ 10cm
  ridge_headroom    屋脊净高 - 115cm 儿童占位 ≥ 10cm
  floor_area        帐内可用面积 ≥ 1.0㎡（搜寻需求书硬条件）

运行：python3 uncertainty_sim.py
输出：uncertainty_matrix.csv / uncertainty_summary.json / uncertainty_summary.md
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "g0"))
import tent_generator as tg  # noqa: E402

# --- 真实近候选（尺寸来自公开页规格表；杆径等不在本模拟范围）---
CANDIDATES = [
    {"id": "HK_160x100x130", "name": "HelloKitty 游戏屋·加长版", "shape": "B 宽门面",
     "F": 1.60, "D": 1.00, "H_total": 1.30,
     "status": "G1a 待锁定 SKU（加长版杆径待核实）"},
    {"id": "HK_narrow_door", "name": "HelloKitty 同尺寸·门在100cm窄面（敏感性变体）",
     "shape": "窄门面（F/D 交换）",
     "F": 1.00, "D": 1.60, "H_total": 1.30,
     "status": "敏感性测试：门位改在 100cm 窄面，其余同 HK_160x100x130"},
    {"id": "HJG_135x105x135", "name": "何佳功 曲奇熊小屋", "shape": "A 窄门面",
     "F": 1.35, "D": 1.05, "H_total": 1.35,
     "status": "G1a 待锁定 SKU"},
    {"id": "HOVLIG_120x120x164", "name": "宜家 HÖVLIG（仅参考）", "shape": "近似方",
     "F": 1.20, "D": 1.20, "H_total": 1.64,
     "status": "官方禁止悬挂灯串/装饰 → 非采购目标，仅结构参考"},
]

# --- 假设网格 ---
E_CORE = [0.70, 0.75, 0.80, 0.85]      # 檐口高假设带（0.70 低于需求书 0.75，用于灵敏度）
DW_GRID = [0.60, 0.65, 0.70]           # 门净宽（需求书 ≥0.60）
DH_GRID = [0.80, 0.85, 0.90]           # 门净高（需求书 ≥0.80）
DELTA_GRID = [0.0, 0.05]               # 屋脊高 = 总高 - delta（总高口径不确定）
BRIEF_E_MIN = 0.75                     # 需求书硬条件：檐口 ≥75cm

CHECKS = [
    ("door_clear", "门洞顶角净空≥5cm", lambda d: d["door_clear"] - 0.05),
    ("door_margin", "门侧净宽≥10cm", lambda d: d["door_margin"] - 0.10),
    ("ridge_headroom", "屋脊-115cm儿童≥10cm", lambda d: d["ridge_headroom_115"] - 0.10),
    ("floor_area", "帐内面积≥1.0㎡", lambda d: d["floor_inner_area"] - 1.0),
]


def run_combo(cand, E, dw, dh, delta):
    tg.CFG["variants"]["A"]["F"] = cand["F"]
    tg.CFG["variants"]["A"]["D"] = cand["D"]
    tg.CFG["E"] = E
    tg.CFG["H"] = round(cand["H_total"] - delta, 4)
    tg.CFG["door_w"] = dw
    tg.CFG["door_h"] = dh
    return tg.derive("A")


def frontier_door_clear(cand, dh, dw=0.70, delta=0.05):
    """最不利门宽/屋脊解释下，门洞净空达标的最低檐高（cm）。"""
    e = 0.50
    while e <= 0.90:
        d = run_combo(cand, e, dw, dh, delta)
        if d["door_clear"] >= 0.05:
            return round(e * 100, 1)
        e += 0.005
    return None


def main():
    rows = []
    summary = {"meta": {
        "generated_by": "uncertainty_sim.py (G1b)",
        "engine": "tent_generator.derive() — 与 G0 同一几何公式",
        "date": "2026-11-06",
        "grid": {"E_core_cm": [x * 100 for x in E_CORE],
                 "door_w_cm": [x * 100 for x in DW_GRID],
                 "door_h_cm": [x * 100 for x in DH_GRID],
                 "ridge_delta_cm": [x * 100 for x in DELTA_GRID]},
        "note": "理想几何模型上的不确定性分析；不是实物验证，不是安全认证。",
    }, "candidates": []}

    for cand in CANDIDATES:
        combos = [(E, dw, dh, dl)
                  for E in E_CORE for dw in DW_GRID
                  for dh in DH_GRID for dl in DELTA_GRID]
        results = {cid: [] for cid, _, _ in CHECKS}
        strips = []
        brief_ok = []   # 需求书合规子集(E≥75cm)内逐组合是否全过
        for E, dw, dh, dl in combos:
            d = run_combo(cand, E, dw, dh, dl)
            ok_all = all(fn(d) >= 0 for _, _, fn in CHECKS)
            for cid, _, fn in CHECKS:
                results[cid].append(fn(d) >= 0)
            strips.append(d["standing_strip_110"] * 100)
            if E >= BRIEF_E_MIN:
                brief_ok.append(ok_all)
            rows.append([cand["id"], round(E * 100), round(dw * 100),
                         round(dh * 100), round(dl * 100),
                         round(d["door_clear"] * 100, 1),
                         round(d["door_margin"] * 100, 1),
                         round(d["ridge_headroom_115"] * 100, 1),
                         round(d["floor_inner_area"], 3),
                         round(d["standing_strip_110"] * 100, 1),
                         round(d["standing_strip_115"] * 100, 1),
                         "PASS" if E >= BRIEF_E_MIN else "below-brief"])

        cand_out = {"id": cand["id"], "name": cand["name"], "shape": cand["shape"],
                    "status": cand["status"],
                    "core_grid_combos": len(combos),
                    "checks": {}, "standing_strip_110_cm_range":
                        [round(min(strips)), round(max(strips))]}

        for cid, label, _ in CHECKS:
            n_pass = sum(results[cid])
            if n_pass == len(combos):
                verdict = "DETERMINISTIC_PASS"
            elif n_pass == 0:
                verdict = "DETERMINISTIC_FAIL"
            else:
                verdict = "CONDITIONAL"
            cand_out["checks"][cid] = {
                "label": label, "verdict": verdict,
                "pass_rate": f"{n_pass}/{len(combos)}"}

        # 门洞净空的失效边界（最不利：门宽70、屋脊=总高-5cm）
        cand_out["frontier_door_clear_cm"] = {
            "premise": "门净宽70cm、屋脊高=总高-5cm（最不利解释）",
            **{f"door_h_{int(dh*100)}cm": frontier_door_clear(cand, dh)
               for dh in (0.80, 0.85, 0.90, 0.95)}}

        # 需求书合规子集（E≥75cm）内的判定
        cand_out["brief_compliant_subset"] = {
            "combos": len(brief_ok), "all_pass": all(brief_ok)}

        summary["candidates"].append(cand_out)

    # --- 写文件 ---
    with open(os.path.join(HERE, "uncertainty_matrix.csv"), "w",
              encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["candidate", "E_cm", "door_w_cm", "door_h_cm",
                    "ridge_delta_cm", "door_clear_cm", "door_margin_cm",
                    "ridge_headroom_115_cm", "floor_area_m2",
                    "strip110_cm", "strip115_cm", "brief_compliant(E>=75)"])
        w.writerows(rows)

    with open(os.path.join(HERE, "uncertainty_summary.json"), "w",
              encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # --- 控制台摘要 ---
    print("=" * 72)
    for c in summary["candidates"]:
        print(f"\n[{c['id']}] {c['name']}（{c['shape']}，{c['core_grid_combos']} 组合）")
        for cid, chk in c["checks"].items():
            print(f"  {chk['verdict']:20s} {chk['label']:22s} pass {chk['pass_rate']}")
        fr = c["frontier_door_clear_cm"]
        print(f"  门洞净空失效边界（{fr['premise']}）:")
        for k, v in fr.items():
            if k != "premise":
                print(f"    {k}: 最低檐高 {v} cm")
        print(f"  站立条带(110cm儿童)范围: {c['standing_strip_110_cm_range']} cm")
        print(f"  需求书合规子集(E≥75cm) 全部通过: {c['brief_compliant_subset']['all_pass']}")
    print("\n[OUT] uncertainty_matrix.csv / uncertainty_summary.json")
    print("[OUT] 见 uncertainty_summary.md（人工可读版由下一次提交写入）")


if __name__ == "__main__":
    main()
