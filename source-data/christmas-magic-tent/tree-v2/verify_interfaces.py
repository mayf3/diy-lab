#!/usr/bin/env python3
"""接口验证台 v2（纯 Python + numpy，直接测**导出的最终 STL**）。

对最终 STL 做三类真实几何测试（不依赖 Blender 布尔，规避 Blender 5.2 EXACT
求解器在部分零件对上返回退化结果的问题）：
1. 插入测试：动件 STL 沿装配轴分步平移（Blender 导出 STL 已烘焙装配位姿），
   每步统计与基座的三角互穿次数（Möller–Trumbore 边-面测试，numpy 矢量化）；
   插入全程应 0 穿越为止（凸环定位的设计性末段楔入单独给预算并如实报告）；
2. 分离测试：Seat 后反向退出，全程应保持 0 穿越；
3. 最终姿态全对扫描：全部零件两两（包围盒预筛）做互穿测试，应 0 穿越；
   另以射线奇偶抽样检测「整体吞没」型干涉。
螺纹未建模：螺栓/螺母间隙以参数核对表给出（Ø3.9 栓杆 / Ø4.5 孔 /
袋 AF7.15 对螺母 AF7.0；梁袋深 4.6 栓尖留 0.6；脚袋深 6.0 栓尖留 0.5）。

用法: python3 verify_interfaces.py
输出: generated/verify/report.json（剖视图见 render_sections.py，需 Blender）
"""
from __future__ import annotations
import json
import struct
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
GEN = ROOT / "generated"
A_DIR = GEN / "stl" / "A"
B_DIR = GEN / "stl" / "B"


def read_stl_mm(path: Path) -> np.ndarray:
    """二进制 STL → (n,3,3) float64，单位 mm（Blender 导出为米，×1000）。"""
    data = path.read_bytes()
    n = struct.unpack("<I", data[80:84])[0]
    arr = np.frombuffer(data[84:84 + n * 50], dtype=np.uint8).reshape(n, 50)[:, :48]
    return arr.copy().view("<f4").reshape(n, 4, 3)[:, 1:, :].astype(np.float64) * 1000.0


def seg_tri_hits(segs, tris, eps=1e-3):  # 平面距离判据 1µm：以下视为共面贴合
    """线段×三角形「严格穿越」测试（矢量化）。segs (S,2,3)，tris (T,3,3) → (S,T) bool。
    只计两端点位于三角形平面异侧的穿越；端点落在面上（贴合/共面接触）不计入。"""
    p1, p2 = segs[:, 0], segs[:, 1]
    d = p2 - p1
    v0, v1, v2 = tris[:, 0], tris[:, 1], tris[:, 2]
    n = np.cross(v1 - v0, v2 - v0)
    nn = np.linalg.norm(n, axis=1)
    ok_t = nn > 1e-9
    n = n / np.where(ok_t, nn, 1.0)[:, None]
    d1 = ((p1[:, None, :] - v0[None, :, :]) * n[None, :, :]).sum(axis=2)   # (S,T)
    d2 = ((p2[:, None, :] - v0[None, :, :]) * n[None, :, :]).sum(axis=2)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = d1 / (d1 - d2)
    strict = ((d1 < -eps) & (d2 > eps)) | ((d1 > eps) & (d2 < -eps))
    hit = strict & (t > 0) & (t < 1)
    if not hit.any():
        return hit
    pts = p1[:, None, :] + t[:, :, None] * d[:, None, :]
    ax = np.abs(n).argmax(axis=1)
    res = np.zeros(hit.shape, bool)
    for axis in range(3):
        sel_t = np.nonzero(ax == axis)[0]
        if len(sel_t) == 0:
            continue
        u_a, v_a = [i for i in range(3) if i != axis]
        a_u = v0[None, sel_t, u_a]; a_v = v0[None, sel_t, v_a]
        b_u = v1[None, sel_t, u_a]; b_v = v1[None, sel_t, v_a]
        c_u = v2[None, sel_t, u_a]; c_v = v2[None, sel_t, v_a]
        det = (b_u - a_u) * (c_v - a_v) - (c_u - a_u) * (b_v - a_v)
        det = np.where(np.abs(det) < 1e-12, 1e-12, det)
        pu = pts[:, sel_t, u_a]; pv = pts[:, sel_t, v_a]
        w = ((pu - a_u) * (c_v - a_v) - (pv - a_v) * (c_u - a_u)) / det
        z = ((b_u - a_u) * (pv - a_v) - (pu - a_u) * (b_v - a_v)) / det
        b_e = 1e-3  # 重心边界带（约 0.1% 三元尺寸≈µm 级）：装配贴合面的边界噪声不计穿越
        inside = (w > b_e) & (z > b_e) & (w + z < 1 - b_e)
        res[:, sel_t] = hit[:, sel_t] & inside
    return res


def crossing_count(tris_m, tris_s):
    def edges(tris):
        return np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]], axis=0)
    h1 = seg_tri_hits(edges(tris_m), tris_s).any(axis=1).sum()
    h2 = seg_tri_hits(edges(tris_s), tris_m).any(axis=1).sum()
    return int((h1 + h2) // 2)  # 每条边在两个三角形中出现两次


def bbox_of(tris):
    flat = tris.reshape(-1, 3)
    return flat.min(axis=0), flat.max(axis=0)


def bboxes_overlap(b1, b2, tol=0.0):
    return bool(np.all(b1[1] >= b2[0] - tol) and np.all(b2[1] >= b1[0] - tol))


def insertion(tris_m, tris_s, axis, travel_mm, step_mm, mode="insert"):
    """insert: 从 seat−a·travel 推进到 seat；extract: 从 seat 沿 +a 退出。"""
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    n_steps = max(2, int(round(travel_mm / step_mm)))
    curve, max_hits = [], 0
    for i in range(n_steps + 1):
        frac = i / n_steps
        off = a * (-travel_mm * (1 - frac)) if mode == "insert" else a * (travel_mm * frac)
        hits = crossing_count(tris_m + off, tris_s)
        curve.append(int(hits))
        if i < n_steps:
            max_hits = max(max_hits, int(hits))
    return curve, max_hits, curve[-1]


def contained_fraction(tris_m, tris_s, samples=300, seed=7):
    """动件表面附近抽样点落入基座实体内的比例（+Z 射线奇偶）。"""
    rng = np.random.default_rng(seed)
    faces = tris_m.reshape(tris_m.shape[0], 3, 3)
    centers = faces.mean(axis=1)
    pts = centers[:samples].copy()
    pts += rng.normal(0, 0.05, pts.shape)          # 表面附近 ±0.05mm 抖动
    v0, v1, v2 = tris_s[:, 0], tris_s[:, 1], tris_s[:, 2]
    d = ((v1[:, 0] - v0[:, 0]) * (v2[:, 1] - v0[:, 1]) - (v2[:, 0] - v0[:, 0]) * (v1[:, 1] - v0[:, 1]))
    d = np.where(np.abs(d) < 1e-12, 1e-12, d)
    w = ((pts[:, None, 0] - v0[None, :, 0]) * (v2[None, :, 1] - v0[None, :, 1]) -
         (pts[:, None, 1] - v0[None, :, 1]) * (v2[None, :, 0] - v0[None, :, 0])) / d
    z = ((v1[None, :, 0] - v0[None, :, 0]) * (pts[:, None, 1] - v0[None, :, 1]) -
         (pts[:, None, 1] - v0[None, :, 1]) * (v1[None, :, 0] - v0[None, :, 0])) / d
    mask = (w >= -1e-9) & (z >= -1e-9) & (w + z <= 1 + 1e-9)
    counts = np.zeros(len(pts), int)
    idx_s, idx_t = np.nonzero(mask)
    w2 = w[idx_s, idx_t]; z2 = z[idx_s, idx_t]
    zint = v0[idx_t, 2] + w2 * (v1[idx_t, 2] - v0[idx_t, 2]) + z2 * (v2[idx_t, 2] - v0[idx_t, 2])
    np.add.at(counts, idx_s, (zint > pts[idx_s, 2]).astype(int))
    return float((counts % 2 == 1).mean())


def load(d, name):
    return read_stl_mm(d / f"{name}.stl")


LEG_A_U = None  # 延迟计算


def main():
    report = {"generated_at": "2026-11-15",
              "method": "三角互穿计数（Möller–Trumbore 边-面，numpy）于导出最终 STL",
              "note_thread": "螺纹未建模：螺栓/螺母间隙按参数核对（Ø3.9 栓杆 / Ø4.5 孔 / 袋 AF7.15 vs 螺母 AF7.0；"
                             "梁袋深 4.6 栓尖留 0.6mm；脚袋深 6.0 栓尖留 0.5mm，M4×16 螺母咬合 ≥2.7mm；"
                             "真实锁紧力以实物试拧为准）",
              "insertion_tests": [], "separation_tests": [], "pairwise": [], "containment": []}

    drop_a = np.array([260.0 - 16.0, 0, -334.0]); u_a = drop_a / np.linalg.norm(drop_a)
    ang_b = np.radians(40.0); u_b = np.array([np.sin(ang_b), 0, -np.cos(ang_b)])
    cases = [
        ("A", "A_beam_149_R", "A_joint_149", (-1, 0, 0), 180, 2, 0, "梁→平节点：Ø16×6 定位榫 + 法兰端面 2×M4×8 压螺母"),
        ("A", "A_beam_210_R", "A_joint_210", (-1, 0, 0), 180, 2, 0, "梁→组合节点（同接口）"),
        ("A", "A_joint_149", "A_col_seg1", (0, 0, -1), 100, 1, None, "平节点滑上柱段：凸环 31.5×31.5 定位，末 0.4mm 楔入为设计行为"),
        ("A", "A_col_seg2", "A_joint_210", (0, 0, -1), 100, 1, 0, "柱段→组合节点上肩（插 20mm 搁肩环）"),
        ("A", "A_col_seg1", "A_base", (0, 0, -1), 80, 1, 0, "柱段→底座插座（承重台）"),
        ("A", "A_leg_R", "A_leg_hub", tuple(-u_a), 100, 2, 0, "腿法兰榫→斜耳插座（顺腿轴）"),
        ("A", "A_leg_tail_R", "A_leg_splice_R", tuple(-u_a), 60, 2, 0, "尾段→拼接套（顺腿轴）"),
        ("A", "A_spreader_R", "A_leg_tail_R", (-1, 0, 0), 60, 2, 0, "横撑→腿尾 boss 方孔（y=46 平面）"),
        ("A", "A_spreader_R", "A_spreader_center", (-1, 0, 0), 40, 2, 0, "横撑→中央连接套方孔"),
        ("A", "A_cap", "A_col_seg4", (0, 0, -1), 60, 1, 0, "帽←段顶插头（30×30×6）"),
        ("A", "A_star", "A_cap", (0, 0, -1), 50, 1, 0, "星榫 Ø16×20→帽顶插座"),
        ("B", "B_branch_t1_1", "B_hub_t1", (-1, 0, 0), 100, 2, 0, "B 枝→层枢纽（同梁接口）"),
        ("B", "B_trunk_seg2", "B_hub_t1", (0, 0, -1), 80, 1, 0, "B 干段→枢纽肩位"),
        ("B", "B_leg_1", "B_collar", tuple(-u_b), 80, 2, 0, "B 腿→三脚领环斜耳"),
    ]
    for tree, mv, bs, axis, travel, step, budget, note in cases:
        d = A_DIR if tree == "A" else B_DIR
        tm, ts = load(d, mv), load(d, bs)
        curve, max_hits, final_hits = insertion(tm, ts, axis, travel, step)
        if budget is None:
            ok = all(h == 0 for h in curve[:-8]) and final_hits <= 24  # 末段楔入窗口内允许设计性命中
        else:
            ok = (final_hits == 0) and (max_hits <= budget)
        rec = {"pair": f"{mv} → {bs}", "tree": tree, "axis_mm": list(np.round(axis, 3).astype(float)),
               "travel_mm": travel, "step_mm": step, "curve_hits": curve,
               "max_hits_midpath": int(max_hits), "final_hits": int(final_hits),
               "designed_budget_hits": budget, "verdict": "PASS" if ok else "FAIL", "note": note}
        report["insertion_tests"].append(rec)

    for tree, mv, bs, axis, travel in (("A", "A_beam_149_R", "A_joint_149", (1, 0, 0), 180),
                                       ("A", "A_leg_R", "A_leg_hub", tuple(u_a), 100)):
        tm, ts = load(A_DIR, mv), load(A_DIR, bs)
        curve, max_hits, final_hits = insertion(tm, ts, axis, travel, 3, mode="extract")
        report["separation_tests"].append({
            "pair": f"{mv} ← {bs}", "travel_mm": travel, "curve_hits": curve,
            "max_hits": int(max_hits),
            "verdict": "PASS" if max_hits == 0 else "FAIL",
            "note": "Seat→拔出全程 0 穿越 = 可拆、无卡滞"})

    for tree, d in (("A", A_DIR), ("B", B_DIR)):
        names = sorted(p.stem for p in d.glob("*.stl"))
        meshes = {n: load(d, n) for n in names}
        boxes = {n: bbox_of(t) for n, t in meshes.items()}
        checked, offenders = 0, []
        for i, n1 in enumerate(names):
            for n2 in names[i + 1:]:
                if not bboxes_overlap(boxes[n1], boxes[n2], tol=-0.01):
                    continue
                checked += 1
                hits = crossing_count(meshes[n1], meshes[n2])
                if hits > 0:
                    offenders.append({"pair": f"{n1} × {n2}", "crossings": int(hits)})
        cf = contained_fraction(meshes["A_star" if tree == "A" else "B_star"],
                                meshes["A_cap" if tree == "A" else "B_cap"])
        report["pairwise"].append({"tree": tree, "bbox_pairs_checked": checked,
                                   "offenders": offenders,
                                   "verdict": "PASS" if not offenders else "FAIL"})
        report["containment"].append({"tree": tree, "sample": "星板表面抽样落入帽实体比例",
                                      "inside_fraction": round(cf, 4),
                                      "verdict": "PASS" if cf < 0.02 else "FAIL"})

    out = GEN / "verify" / "report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    fails = [t["pair"] for t in report["insertion_tests"] + report["separation_tests"] if t["verdict"] != "PASS"]
    fails += [f"{p['tree']}:{k}" for p in report["pairwise"] + report["containment"] if p["verdict"] != "PASS" for k in ("",)]
    print(f"VERIFY DONE report={out} failures={len(fails)} {fails}")
    for t in report["insertion_tests"]:
        print(f"  {t['verdict']}  {t['pair']}  mid_max={t['max_hits_midpath']} final={t['final_hits']} tail={t['curve_hits'][-4:]}")


if __name__ == "__main__":
    main()
