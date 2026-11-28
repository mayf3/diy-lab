#!/usr/bin/env python3
"""Christmas Buddy V1 机械参数模型（单一尺寸事实源）。

坐标系：Z 向上，原点在底面中心；+Y 为正面（脸），PCB 位于 XZ 平面（y=0），
前后壳在此分型。所有尺寸 mm。三个消费者：build_mech.py（CAD）、
assembly_check.py（检查）、visual/specs.py（视觉参数）——改尺寸必须过检查。

两套外观方案共享同一功能内核（PCB/腔体/接口位置），只有外部造型不同。
"""
from __future__ import annotations

import json
from pathlib import Path

VIEW_DATE = "2026-11-28"

PARAMS = {
    # ---- 总体 ----
    "total_height_target": (120.0, 160.0),
    "wall": 2.8,                    # 外壳壁厚（3D 打印，P1S 0.4 喷嘴 4 壁圈）
    "clearance": 1.0,               # PCB 与腔体最小间隙（含打印公差 ±0.2×2）
    "print_tolerance_xy": 0.2,      # P1S 0.2mm 公差档实测经验值（计划，打印轮复核）

    # ---- PCB（载板，站立在 XZ 平面）----
    "pcb": {"w": 58.0, "h": 66.0, "t": 1.6, "z0": 10.0,
            "note": "w=X 向，h=Z 向；底边插底座槽，顶边两个 M2.5 沉头螺钉柱"},
    "pi": {"w": 65.0, "d": 30.0, "t": 4.0, "stack_gap": 5.8,
           "z0": 14.0,
           "note": "Zero 2 W 65×30mm；经 2×20 排针反扣叠在 PCB 背面（y<0）"},
    "esp32": {"w": 18.0, "d": 25.5, "t": 2.4, "x": -20.0, "z0": 46.0,
              "note": "ESP32-S3-WROOM-1-N8R2 贴在 PCB 正面（y>0）"},
    "usb_c": {"recess_max": 15.0, "opening_w": 10.0, "opening_h": 4.6,
              "x": -17.0, "z": 13.5,
              "note": "后壳开口椭圆孔；插头过盈深度必须 ≤15mm（常见 USB-C 线缆注塑头 22–30mm，留弯折空间）"},
    "mic": {"hole_d": 2.2, "x": 24.0, "z": 70.0,
            "note": "前壳声孔 Ø2.2 + 密封圈 + 腔后 PCB 上 INMP441（底端口朝 +Y）"},
    "speaker": {"d": 28.0, "t": 5.2, "x": 0.0, "z": 38.0,
                "grille_ratio_min": 0.6,
                "grille_slots": {"count": 16, "w": 2.5, "l": 10.0},
                "note": "Ø28×5.2 贴前壳内壁朝前；16 条 2.5×10mm 栅格缝（首版 12×2×8 面积不足，已按检查结果修正）"},
    "buttons": {"board_w": 26.0, "board_h": 16.0, "x": 0.0, "z": 52.0,
                "pitch_x": 9.0, "pitch_z": 8.0,
                "note": "2×2 按键卫星板贴前壳内壁（z=52，避开体部缩径区——首版 z=56 超腔，检查抓出后下移）"},
    "star": {"module_w": 16.0, "module_h": 16.0, "x": 0.0, "z": 26.0,
             "note": "胸前星星灯（4 颗 SK6812）贴前壳内壁，透光罩"},
    "eyes": {"module_w": 12.0, "module_h": 12.0, "dx": 11.0, "z": 99.0,
             "diffuser_t": 1.2,
             "note": "3×3 SK6812 模组 ×2 位于头部，透过 1.2mm 乳白扩散板"},

    # ---- 外观方案 A「雪宝」（圆润）----
    "scheme_a": {
        "base": {"d": 92.0, "h": 8.0},
        "body_profile": [(41.0, 8.0), (41.0, 30.0), (40.5, 52.0), (37.0, 72.0), (34.0, 82.0), (32.0, 86.0)],
        "head": {"d": 54.0, "center_z": 93.0},
        "brim": {"d": 58.0, "h": 3.0, "z": 105.0},
        "head_note": "center_z 96（原 103）：头球下坐进围巾/体腔，消除 45° 视角的悬浮感——渲染轮目检发现后修正",
        "hat": {"r_top": 9.0, "h": 28.0, "tilt_deg": 14.0},
        "scarf": {"tube_r": 4.5, "ring_r": 36.5, "z": 82.0},
        "profile_note": "直筒段延长到 z=52（容纳按键卫星板）+ z=74 处保持 Ø70 以上（PCB 顶部弦长 62.9mm≥60 需求）——由 assembly_check 首轮 FAIL 修正得出",
    },
    # ---- 外观方案 B「胶囊舱」（TE 风格分段）----
    "scheme_b": {
        "base": {"d": 94.0, "h": 10.0},
        "body_profile": [(39.0, 10.0), (39.0, 64.0), (37.0, 78.0)],
        "neck_ring": {"d": 70.0, "h": 4.0, "z": 78.0},
        "head": {"d": 52.0, "center_z": 100.0},
        "hat": {"d": 50.0, "h": 14.0, "stub_h": 12.0, "tilt_deg": 0.0},
        "face_plate": {"w": 26.0, "h": 16.0, "z": 98.0},
    },
}

def inner_radius_at(z: float, profile) -> float:
    """体部内半径：外轮廓线性内插 − 壁厚。z 低于/高于 profile 区间时用端值。"""
    (r0, z0), (r1, z1) = profile[0], profile[-1]
    if z <= profile[0][1]:
        r = profile[0][0]
    elif z >= profile[-1][1]:
        r = profile[-1][0]
    else:
        for i in range(len(profile) - 1):
            ra, za = profile[i]
            rb, zb = profile[i + 1]
            if za <= z <= zb:
                t = (z - za) / (zb - za)
                r = ra + (rb - ra) * t
                break
    return r - PARAMS["wall"]

def chord(r: float, offset: float) -> float:
    """半径 r 的圆在距圆心 offset 处的弦长。"""
    r = max(r - PARAMS["clearance"], 0)
    if r <= abs(offset):
        return 0.0
    return 2.0 * (r * r - offset * offset) ** 0.5

def dump_json() -> str:
    return json.dumps({"schema": "mech-params/1.0", "view_date": VIEW_DATE, "params": PARAMS},
                      ensure_ascii=False, indent=2)

if __name__ == "__main__":
    Path(__file__).with_name("mech_params.json").write_text(dump_json(), encoding="utf-8")
    print("mech_params.json written")
