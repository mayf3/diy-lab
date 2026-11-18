#!/usr/bin/env python3
"""亲子教学随身记录器｜取景模拟 v2（模拟预测，非实拍）。

## 模型口径（显式声明，全部为实验假设参数，不是项目发起人的已确认需求）

坐标与单位：
- 世界坐标系：X 右、Y 上、Z 前（家长面向 -Z 看向桌子）；长度单位米。
- 相机坐标：给定 yaw（绕 Y）与下倾 pitch（绕相机右轴）构造右/上/光轴基；
  点 d 的相机坐标 Xc=d·right, Yc=d·up, Zc=d·axis。
- 离轴角 θ = atan2(hypot(Xc, Yc), Zc)（度），避免 acos 的域问题；
  距离 = |d|；距离 < EPS_M(1e-4 m) 记 degenerate，不参与判读。

投影模型（等距/equidistant，OpenCV fisheye 同族）：
- 像圆内 r_px = R_px · θ/θ_max，θ_max = 镜头视场角的一半（本轮 180°→90°、150°→75°）。
- 模型有效角域：Zc ≤ ε 判 behind_camera（半球模型看不到光轴后半球）；
  θ > θ_max 判 outside_circle（超出像圆）。本轮所有结论不依赖 >180° 覆盖；
  若未来路线声称 >180°，本模型不适用，须换模型并重新检查。

视场语义与画幅裁切（关键：标称视场角≠各方向有效视场）：
- 画幅 16:9（1920×1080）。两种镜头安装口径分别计算：
  - fit_height：像圆直径=画幅高 1080px（R=540）→ 水平/垂直有效视场由像圆给出，
    左右两侧画幅为无效区；
  - fit_diagonal：像圆直径=画幅对角 2203px（R≈1101）→ 像圆上下溢出画幅被裁切，
    有效水平/垂直视场按画幅边缘的 θ 数值计算（如 180° 镜头水平 ≈157°、垂直 ≈88°）。
- 有效成像判据：像素在像圆内 AND 在画幅内 AND θ≤θ_max AND 未被遮挡；
  「像素坐标落在图内」不是唯一可见条件。

遮挡模型（佩戴者自遮挡简化，几何遮挡不代表真实衣物遮挡）：
- 躯干盒（相机下方及身后）、头/下巴球（相机上方）、手臂胶囊（肩→手，r=45mm，
  不遮挡手部目标自身）。衣物遮挡未建模，列为试录检查项。

姿态敏感性：
- chest（贴身固定）：前倾 φ∈{0,15,30}° 直接叠加到镜头下倾（相机随躯干转动）。
- lanyard（挂绳自由下垂）：相机保持悬垂，下倾受摆动 sway∈{-10,0,+10}° 影响，
  与前倾角近似解耦；位置随颈部前移少量前移。

判读阈值（实验假设）：教学物≥100px、手部≥80px、面部≥60px 记「可读」。
像素宽度按 px_per_deg = R_px/θ_max × 角直径 计算（等距模型像素/度恒定）。

几何视野覆盖 ≠ 真实光学表现：近距离对焦、室内噪点、运动模糊、边缘清晰度
不在本模型内，需资料核实或实拍检查（见项目页「验证边界」）。

用法：
  python3 framing_sim.py                # 全网格 + 代表性图像
  python3 framing_sim.py --selftest     # 关键错误自检（正前方/后方/超域/遮挡/退化）

输出：results.json + 代表性 PNG（均标注「模拟」）；网格运行为纯指标计算。
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

EPS_M = 1e-4
FRAME_W, FRAME_H = 1920, 1080
CROP = {
    "fit_height": FRAME_H / 2,                    # 像圆直径=画幅高，R=540
    "fit_diagonal": math.hypot(FRAME_W, FRAME_H) / 2,  # 像圆直径=对角，R≈1101
}
FOVS = {"180": 180.0, "150": 150.0}
THRESHOLDS = {"教学": 100, "面部": 60, "手部": 80}

_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


# ---------- 相机基与投影 ----------
def basis(yaw_deg: float, pitch_down_deg: float):
    """相机基（右, 上, 光轴）。yaw=180° 表示面向 -Z；pitch 为向下倾斜角。"""
    y, p = math.radians(yaw_deg), math.radians(pitch_down_deg)
    axis = (math.cos(p) * math.sin(y), -math.sin(p), math.cos(p) * math.cos(y))
    right = (math.cos(y), 0.0, -math.sin(y))
    up = (axis[1] * right[2] - axis[2] * right[1],
          axis[2] * right[0] - axis[0] * right[2],
          axis[0] * right[1] - axis[1] * right[0])
    return right, up, axis


def cam_coords(point, cam, yaw, pitch):
    """世界点到相机坐标 (Xc, Yc, Zc) 与距离。"""
    dx, dy, dz = (point[0] - cam[0], point[1] - cam[1], point[2] - cam[2])
    r, u, a = basis(yaw, pitch)
    xc, yc, zc = (dx * r[0] + dy * r[1] + dz * r[2],
                  dx * u[0] + dy * u[1] + dz * u[2],
                  dx * a[0] + dy * a[1] + dz * a[2])
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    return xc, yc, zc, dist


def project(point, cam, pitch, yaw, fov_deg, radius_px):
    """返回 (u, v, theta_deg, status)。status ∈ degenerate/behind_camera/
    outside_circle/outside_frame/ok。ok = 像圆内 AND 角域内 AND 画幅内；
    fit_diagonal 下像圆溢出画幅的裁切会主动判 outside_frame，而非默认可见。"""
    xc, yc, zc, dist = cam_coords(point, cam, yaw, pitch)
    if dist < EPS_M:
        return None, None, None, "degenerate"
    theta = math.degrees(math.atan2(math.hypot(xc, yc), zc))
    if zc <= 1e-9:
        return None, None, theta, "behind_camera"
    theta_max = fov_deg / 2.0
    if theta > theta_max:
        return None, None, theta, "outside_circle"
    phi = math.atan2(yc, xc)
    rr = radius_px * theta / theta_max
    cx, cy = FRAME_W / 2, FRAME_H / 2
    u, v = cx + rr * math.cos(phi), cy - rr * math.sin(phi)
    if u < 0 or u > FRAME_W or v < 0 or v > FRAME_H:
        return u, v, theta, "outside_frame"
    return u, v, theta, "ok"


def effective_fov(fov_deg: float, radius_px: float) -> dict:
    """数值求画幅四边的有效视场（等距模型下按边缘像素的 θ）。"""
    theta_max = fov_deg / 2.0

    def theta_at(u_off, v_off):
        r_px = math.hypot(u_off, v_off)
        return min(theta_max, theta_max * r_px / radius_px)

    h_half = theta_at(FRAME_W / 2, 0)
    v_half = theta_at(0, FRAME_H / 2)
    d_half = theta_at(FRAME_W / 2, FRAME_H / 2)
    return {"horizontal": round(2 * h_half, 1), "vertical": round(2 * v_half, 1),
            "diagonal": round(2 * d_half, 1), "nominal": fov_deg,
            "note": "fit_diagonal 下像圆上下溢出画幅被裁切；fit_height 下像圆"
                    "直径=画幅高，左右为无效区"}


# ---------- 遮挡模型 ----------
def ray_hits_aabb(cam, target, lo, hi):
    """slab 法：相机→目标线段是否与轴对齐盒相交。"""
    tmin, tmax = 0.0, 1.0
    for i in range(3):
        d = target[i] - cam[i]
        if abs(d) < 1e-12:
            if cam[i] < lo[i] or cam[i] > hi[i]:
                return False
            continue
        t0, t1 = (lo[i] - cam[i]) / d, (hi[i] - cam[i]) / d
        if t0 > t1:
            t0, t1 = t1, t0
        tmin, tmax = max(tmin, t0), min(tmax, t1)
        if tmin > tmax:
            return False
    return tmax > 0 and tmin < 1


def ray_hits_sphere(cam, target, center, radius):
    d = tuple(target[i] - cam[i] for i in range(3))
    oc = tuple(cam[i] - center[i] for i in range(3))
    a = sum(x * x for x in d)
    b = 2 * sum(oc[i] * d[i] for i in range(3))
    c = sum(x * x for x in oc) - radius * radius
    disc = b * b - 4 * a * c
    if disc < 0:
        return False
    sq = math.sqrt(disc)
    for t in ((-b - sq) / (2 * a), (-b + sq) / (2 * a)):
        if 0 < t < 1:
            return True
    return False


def seg_seg_distance(p1, p2, q1, q2):
    """两线段 p1-p2 与 q1-q2 的最短距离（Ericson《Real-Time Collision
    Detection》5.1.9，含一点/两点退化为端点情形）。
    历史：v2 首版用 100 点采样近似，曾与另一份临写的精确公式冲突
    （0.0479 vs 0.1668）——对账后确认临写公式的端点钳制有错、采样与
    暴力对拍一致；本版改为正确精确实现，并用密集采样对账兜底。"""
    def sub(a, b):
        return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

    def dot(a, b):
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    d1, d2, r = sub(p2, p1), sub(q2, q1), sub(p1, q1)
    a, e = dot(d1, d1), dot(d2, d2)
    f = dot(d2, r)
    eps = 1e-12
    if a <= eps and e <= eps:
        return math.sqrt(dot(r, r))
    if a <= eps:
        s, t = 0.0, min(1.0, max(0.0, f / e))
    else:
        c = dot(d1, r)
        if e <= eps:
            t, s = 0.0, min(1.0, max(0.0, -c / a))
        else:
            b = dot(d1, d2)
            denom = a * e - b * b
            s = min(1.0, max(0.0, (b * f - c * e) / denom)) if denom > eps else 0.0
            t = (b * s + f) / e
            if t < 0:
                t, s = 0.0, min(1.0, max(0.0, -c / a))
            elif t > 1:
                t, s = 1.0, min(1.0, max(0.0, (b - c) / a))
    cp = tuple(p1[i] + d1[i] * s for i in range(3))
    cq = tuple(q1[i] + d2[i] * t for i in range(3))
    return math.dist(cp, cq)


def ray_hits_capsule(cam, target, seg_a, seg_b, radius):
    """相机→目标线段与肩→手线段（半径 radius 胶囊）的精确相交判定：
    线段最短距离 < radius 判遮挡（边界恰好等于半径不判遮挡）。"""
    return seg_seg_distance(cam, target, seg_a, seg_b) < radius


def build_occluders(cam, hand_target):
    """佩戴者自遮挡（实验假设尺寸）。相机挂在/贴在胸前表面，因此躯干盒
    严格位于相机平面之后（z 更大方向）；头/下巴球在相机上方偏后。
    手臂两种姿态分别评估：抬起至手部目标位（教学进行中）与垂放身侧
    （rest）。衣物遮挡未建模，列为试录检查项。"""
    px, py, pz = cam
    torso = ((px - 0.20, py - 0.50, pz + 0.005), (px + 0.20, py + 0.03, pz + 0.24))
    head = ((px, py + 0.14, pz + 0.06), 0.11)
    shoulder_r = (px + 0.18, py + 0.03, pz - 0.02)
    arm = (shoulder_r, hand_target, 0.045) if hand_target else None
    arm_rest = (shoulder_r, (px + 0.14, py - 0.30, pz - 0.02), 0.045)
    return {"torso": torso, "head": head, "arm_r": arm, "arm_rest": arm_rest}


def check_occlusion(point, cam, occluders, target_is_hand):
    """返回 None / 躯干 / 头部 / 手臂（双姿态都挡）/ 手臂(抬起时) / 手臂垂放时。"""
    lo, hi = occluders["torso"]
    if ray_hits_aabb(cam, point, lo, hi):
        return "躯干"
    hc, hr = occluders["head"]
    if ray_hits_sphere(cam, point, hc, hr):
        return "头部"
    if target_is_hand:
        return None
    raised = occluders.get("arm_r") and ray_hits_capsule(
        cam, point, occluders["arm_r"][0], occluders["arm_r"][1],
        occluders["arm_r"][2])
    rest = occluders.get("arm_rest") and ray_hits_capsule(
        cam, point, occluders["arm_rest"][0], occluders["arm_rest"][1],
        occluders["arm_rest"][2])
    if raised and rest:
        return "手臂"
    if raised:
        return "手臂(抬起时)"
    if rest:
        return "手臂垂放时"
    return None


def px_width(width_m, dist, fov_deg, radius_px):
    px_per_deg = radius_px / (fov_deg / 2.0)
    subtended = math.degrees(2 * math.atan(width_m / 2 / max(dist, 1e-4)))
    return int(px_per_deg * subtended)


def threshold_for(name):
    if "面部" in name:
        return THRESHOLDS["面部"]
    if "手" in name:
        return THRESHOLDS["手部"]
    return THRESHOLDS["教学"]


# ---------- 场景（实验假设几何，家具尺寸为典型值） ----------
TABLE = {"xmin": -0.6, "xmax": 0.6, "zmin": -0.35, "zmax": 0.35, "y": 0.75}
SCENARIOS = {
    "S1-side-reading": {
        "title": "S1 并排读书（并排坐桌旁）",
        "parent_pos": (-0.25, None, 0.62), "camera_yaw": 180.0,
        "targets": [
            {"name": "课本/桌面", "point": (0.10, 0.77, 0.10), "w": 0.20},
            {"name": "家长双手", "point": (0.05, 0.90, 0.22), "w": 0.16, "hand": True},
            {"name": "孩子面部", "point": (0.32, 0.98, 0.52), "w": 0.09},
            {"name": "家长面部", "point": "parent_face", "w": 0.15},
        ],
    },
    "S1-turn45": {
        "title": "S1 转身45°看孩子（对比转身取舍）",
        "parent_pos": (-0.25, None, 0.62), "camera_yaw": 135.0,
        "targets": [
            {"name": "课本/桌面", "point": (0.10, 0.77, 0.10), "w": 0.20},
            {"name": "家长双手", "point": (0.05, 0.90, 0.22), "w": 0.16, "hand": True},
            {"name": "孩子面部", "point": (0.32, 0.98, 0.52), "w": 0.09},
            {"name": "家长面部", "point": "parent_face", "w": 0.15},
        ],
    },
    "S2-face-to-face": {
        "title": "S2 面对面小游戏",
        "parent_pos": (0.0, None, 0.55), "camera_yaw": 180.0,
        "targets": [
            {"name": "桌面玩具", "point": (0.0, 0.78, 0.0), "w": 0.14},
            {"name": "家长双手", "point": (0.0, 0.90, 0.15), "w": 0.16, "hand": True},
            {"name": "孩子面部", "point": (0.0, 0.98, -0.55), "w": 0.09},
            {"name": "家长面部", "point": "parent_face", "w": 0.15},
        ],
    },
    "S3-desk-work": {
        "title": "S3 桌面操作（孩子在旁）",
        "parent_pos": (0.0, None, 0.45), "camera_yaw": 180.0,
        "targets": [
            {"name": "操作工件", "point": (0.0, 0.77, 0.0), "w": 0.18},
            {"name": "家长双手", "point": (0.0, 0.83, 0.05), "w": 0.16, "hand": True},
            {"name": "孩子面部", "point": (0.45, 0.98, 0.10), "w": 0.09},
            {"name": "家长面部", "point": "parent_face", "w": 0.15},
        ],
    },
}
HEIGHTS = {"stand-1.35": 1.35, "seated-1.10": 1.10}
MOUNTS = ("chest", "lanyard")
LEANS = (0, 15, 30)
SWAYS = (0, -10, 10)  # 仅 lanyard 使用；chest 的 pitch 直接随前倾


def camera_for(scen, height, mount, lean, sway):
    """按佩戴方式与前倾/摆动求相机位置与等效下倾（实验假设，见模型口径）。"""
    px, _, pz = scen["parent_pos"]
    if mount == "chest":
        cam = (px, height - 0.10, pz - 0.06 - 0.08 * math.sin(math.radians(lean)))
        return cam, 20 + lean  # 贴身固定：相机随躯干转动
    cam = (px, height - 0.12, pz - 0.03 - 0.05 * math.sin(math.radians(lean)))
    return cam, 20 + (sway or 0)  # 挂绳悬垂：下倾主要受摆动影响，与前倾解耦


def evaluate(scen_key, height_key, mount, lean, sway, fov_key, crop_key,
             render=False, out=None):
    scen = SCENARIOS[scen_key]
    height = HEIGHTS[height_key]
    cam, pitch = camera_for(scen, height, mount, lean, sway)
    radius_px = CROP[crop_key]
    fov = FOVS[fov_key]
    yaw = scen["camera_yaw"]
    # 家长面部坐标按本配置局部计算（不修改全局 SCENARIOS——保证任意执行顺序
    # 与调用组合下结果可重复，历史版本曾就地改写全局导致顺序依赖）
    targets = []
    for t in scen["targets"]:
        if t["point"] == "parent_face":
            targets.append({**t, "point": (cam[0], height + 0.12, cam[2] + 0.06)})
        else:
            targets.append(t)
    hand = next((t["point"] for t in targets if t.get("hand")), None)
    occ = build_occluders(cam, hand)

    metrics = {}
    for tgt in targets:
        p = tgt["point"]
        u, v, theta, status = project(p, cam, pitch, yaw, fov, radius_px)
        m = {"status": status, "theta_deg": None if theta is None else round(theta, 1),
             "distance_m": round(math.dist(cam, p), 2)}
        if status == "ok":
            blocked = check_occlusion(p, cam, occ, bool(tgt.get("hand")))
            m["occluded_by"] = blocked
            pose_risk = blocked in ("手臂(抬起时)", "手臂垂放时")
            if blocked and not pose_risk:
                m["status"] = "occluded"
            elif blocked:
                m["status"] = "arm_risk"  # 随手臂姿态变化：可见但存在遮挡风险
            else:
                m["status"] = "in_frame"
            m["u"], m["v"] = round(u, 1), round(v, 1)
            if m["status"] != "occluded":
                m["px_width"] = px_width(tgt["w"], m["distance_m"], fov, radius_px)
                m["threshold_px"] = threshold_for(tgt["name"])
                m["readable"] = m["px_width"] >= m["threshold_px"]
        elif status == "degenerate":
            m["note"] = "距离过近（<1e-4m），退化输入"
        metrics[tgt["name"]] = m

    if render and out:
        draw_frame(scen_key, height_key, mount, lean, sway, fov_key, crop_key,
                   cam, pitch, occ, metrics, out)
    visible = [k for k, m in metrics.items()
               if m.get("status") in ("in_frame", "arm_risk")]
    readable = [k for k in visible
                if metrics[k].get("readable")
                and metrics[k].get("status") == "in_frame"]
    return {
        "scenario": scen_key, "height": height_key, "mount": mount,
        "lean_deg": lean, "sway_deg": sway if mount == "lanyard" else None,
        "fov": fov_key, "crop": crop_key,
        "camera_pitch_eff_deg": round(pitch, 1),
        "targets": metrics,
        "visible_targets": visible, "readable_targets": readable,
        "all_key_targets_visible": all(
            k in visible for k in metrics if "家长面部" not in k),
    }


# ---------- 绘图（16:9 画幅 + 图例，全部标注「模拟」） ----------
INK, BG = (30, 34, 44), (250, 250, 248)
GOOD, AMBER, BAD, OCC = (36, 130, 89), (196, 140, 40), (170, 60, 54), (120, 108, 160)
PANEL_W = 560


def draw_frame(scen_key, height_key, mount, lean, sway, fov_key, crop_key,
               cam, pitch, occ, metrics, out):
    scen = SCENARIOS[scen_key]
    radius_px = CROP[crop_key]
    fov = FOVS[fov_key]
    yaw = scen["camera_yaw"]
    W = FRAME_W + PANEL_W
    img = Image.new("RGB", (W, FRAME_H), BG)
    draw = ImageDraw.Draw(img)
    f_lab, f_small, f_idx = _font(34), _font(24), _font(26)
    cx, cy = FRAME_W / 2, FRAME_H / 2

    draw.rectangle([0, 0, FRAME_W - 1, FRAME_H - 1], fill=(255, 255, 255),
                   outline=(180, 186, 194), width=3)
    rc = radius_px
    if rc < FRAME_H / 2 - 2:  # fit_height：像圆在画幅内，左右为无效区
        draw.ellipse([cx - rc, cy - rc, cx + rc, cy + rc], outline=(200, 206, 214),
                     width=3)
    draw.line([cx - 16, cy, cx + 16, cy], fill=(150, 156, 164), width=2)
    draw.line([cx, cy - 16, cx, cy + 16], fill=(150, 156, 164), width=2)

    # 桌面网格（鱼眼畸变可见）
    t = TABLE
    xlines = [t["xmin"], t["xmin"] + 0.3, t["xmin"] + 0.6, t["xmin"] + 0.9, t["xmax"]]
    for zi in (t["zmin"], 0, t["zmax"]):
        pts = []
        for xi in xlines:
            u, v, th, st = project((xi, t["y"], zi), cam, pitch, yaw, fov, radius_px)
            if st == "ok":
                pts.append((u, v))
        if len(pts) >= 2:
            draw.line(pts, fill=(205, 210, 216), width=2)
    for xi in xlines:
        pts = []
        for zi in (t["zmin"], 0, t["zmax"]):
            u, v, th, st = project((xi, t["y"], zi), cam, pitch, yaw, fov, radius_px)
            if st == "ok":
                pts.append((u, v))
        if len(pts) >= 2:
            draw.line(pts, fill=(205, 210, 216), width=2)

    # 遮挡体（躯干盒角点投影连线 + 头球投影圈）
    lo, hi = occ["torso"]
    corners = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
               for z in (lo[2], hi[2])]
    proj = []
    for c in corners:
        u, v, th, st = project(c, cam, pitch, yaw, fov, radius_px)
        if st == "ok":
            proj.append((u, v))
    if len(proj) >= 3:
        draw.polygon(proj, outline=OCC, width=2)
    hc, hr = occ["head"]
    u, v, th, st = project(hc, cam, pitch, yaw, fov, radius_px)
    if st == "ok":
        rr = radius_px * math.degrees(math.atan(hr / math.dist(cam, hc))) / (fov / 2)
        draw.ellipse([u - rr, v - rr, u + rr, v + rr], outline=OCC, width=2)

    idx_marks = "①②③④"
    legend = []
    for i, (name, m) in enumerate(metrics.items()):
        mark = idx_marks[i]
        st = m["status"]
        if st in ("in_frame", "arm_risk"):
            color = GOOD if m.get("readable") and st == "in_frame" else AMBER
        elif st == "occluded":
            color = OCC
        else:
            color = BAD
        if m.get("u") is not None:
            r_px = max(7, m.get("px_width", 14) // 2)
            draw.ellipse([m["u"] - r_px, m["v"] - r_px, m["u"] + r_px, m["v"] + r_px],
                         outline=color, width=4)
            draw.text((min(m["u"] + r_px + 4, FRAME_W - 40), m["v"] - 14), mark,
                      fill=color, font=f_idx)
        else:
            draw.text((30, FRAME_H - 44 - i * 32), f"{mark}{name}={m['status']}",
                      fill=BAD, font=f_small)
        verdict = {"in_frame": "可读" if m.get("readable") else "偏小",
                   "arm_risk": f"{m.get('occluded_by')}遮挡风险",
                   "occluded": f"被{m.get('occluded_by')}遮挡",
                   "outside_circle": "超出像圆",
                   "outside_frame": "画幅裁切",
                   "behind_camera": "相机后半球",
                   "degenerate": "退化"}.get(st, st)
        pxs = f"{m['px_width']}px " if "px_width" in m else ""
        legend.append((mark, name, pxs, m.get("theta_deg"), verdict, color))

    px0 = FRAME_W + 24
    draw.text((px0, 20), "模拟预测（非实拍）·v2", fill=BAD, font=f_lab)
    draw.text((px0, 64), scen["title"], fill=INK, font=f_lab)
    draw.text((px0, 108),
              f"{height_key}｜{mount}｜前倾{lean}°"
              + (f"｜摆动{sway}°" if sway is not None else ""),
              fill=(70, 78, 88), font=f_small)
    eff = effective_fov(fov, radius_px)
    draw.text((px0, 140),
              f"FOV{fov_key}({crop_key})｜有效水平{eff['horizontal']}°"
              f"/垂直{eff['vertical']}°", fill=(70, 78, 88), font=f_small)
    y = 190
    for mark, name, pxs, th, verdict, color in legend:
        draw.text((px0, y), f"{mark} {name}", fill=color, font=f_small)
        draw.text((px0 + 220, y),
                  f"{pxs}θ={th if th is not None else '—'} {verdict}",
                  fill=color, font=f_small)
        y += 34
    y += 10
    for line in ("阈值：教学≥100px 手≥80px 面≥60px",
                 "灰紫：遮挡体（躯干/头/手臂简化）",
                 "衣物遮挡未建模→试录检查项",
                 "几何覆盖≠光学画质（对焦/噪点另核）"):
        draw.text((px0, y), line, fill=(90, 98, 108), font=f_small)
        y += 30
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)


# ---------- 自检（关键错误验证例 + 胶囊对账/边界 + 可重复性回归） ----------
def _brute_seg_distance(p1, p2, q1, q2, n=400):
    """密集双向采样距离（自检对账基准，非生产路径）。"""
    d1 = tuple(p2[i] - p1[i] for i in range(3))
    d2 = tuple(q2[i] - q1[i] for i in range(3))
    best = float("inf")
    for i in range(n + 1):
        s = i / n
        p = tuple(p1[j] + d1[j] * s for j in range(3))
        for k in range(n + 1):
            t = k / n
            q = tuple(q1[j] + d2[j] * t for j in range(3))
            dist = math.dist(p, q)
            if dist < best:
                best = dist
    return best


def selftest() -> dict:
    cam, pitch = camera_for(SCENARIOS["S2-face-to-face"], 1.10, "chest", 0, None)
    yaw = 180.0
    r, _, a = basis(yaw, pitch)
    results = {}

    p_axis = tuple(cam[i] + a[i] * 1.0 for i in range(3))          # 1 正前方点
    uu, vv, th, st = project(p_axis, cam, pitch, yaw, 180, 540)
    results["on_axis_center"] = st == "ok" and th is not None and th < 0.01 \
        and abs(uu - FRAME_W / 2) < 2 and abs(vv - FRAME_H / 2) < 2

    p_behind = tuple(cam[i] - a[i] * 0.5 for i in range(3))        # 2 后方点
    _, _, _, st = project(p_behind, cam, pitch, yaw, 180, 540)
    results["behind_rejected"] = st == "behind_camera"

    d80 = tuple(a[i] * math.cos(math.radians(80)) + r[i] * math.sin(math.radians(80))
                for i in range(3))                                 # 3a 超出 150° 域
    p80 = tuple(cam[i] + d80[i] * 1.0 for i in range(3))
    _, _, _, st = project(p80, cam, pitch, yaw, 150, 540)
    results["beyond_150_domain"] = st == "outside_circle"
    d95 = tuple(a[i] * math.cos(math.radians(95)) + r[i] * math.sin(math.radians(95))
                for i in range(3))                                 # 3b 超出半球域
    p95 = tuple(cam[i] + d95[i] * 1.0 for i in range(3))
    _, _, _, st = project(p95, cam, pitch, yaw, 180, 540)
    results["beyond_hemisphere"] = st == "behind_camera"

    hand = next(t["point"] for t in SCENARIOS["S1-side-reading"]["targets"]
                if t.get("hand"))
    occ = build_occluders(cam, hand)
    arm_mid = tuple((occ["arm_r"][0][i] + occ["arm_r"][1][i]) / 2 for i in range(3))
    tgt_below_arm = tuple(arm_mid[i] - (0.0, 0.03, 0.0)[i] for i in range(3))
    uu, vv, th, st = project(tgt_below_arm, cam, pitch, yaw, 180, 540)
    blocked = check_occlusion(tgt_below_arm, cam, occ, False)
    results["inframe_but_occluded"] = (st == "ok" and blocked is not None
                                       and uu is not None
                                       and 0 <= uu <= FRAME_W and 0 <= vv <= FRAME_H)
    results["diag_occluder_name"] = blocked or "none"

    _, _, _, st = project(cam, cam, pitch, yaw, 180, 540)          # 5 退化输入
    results["degenerate_handled"] = st == "degenerate"

    # 6 胶囊精确距离 vs 密集采样对账（相同输入逐例比较）
    cases = [
        (cam, tgt_below_arm, occ["arm_r"][0], occ["arm_r"][1]),   # 曾冲突的真实输入
        (cam, hand, occ["arm_rest"][0], occ["arm_rest"][1]),
        ((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.05, 0.0, 0.3), (0.05, 0.0, 0.5)),
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.5, 0.1, 0.0), (0.5, 0.1, 1.0)),
    ]
    results["capsule_exact_matches_bruteforce"] = all(
        abs(seg_seg_distance(*c) - _brute_seg_distance(*c, n=200)) < 2e-3
        for c in cases)

    # 7 半径边界：射线沿 +Z，手臂段在 X=d 处平行 → 距离恰为 d
    radius = 0.045
    for key, d in (("capsule_below_radius_hits", 0.044),
                   ("capsule_at_radius_strict_clear", 0.045),
                   ("capsule_above_radius_clear", 0.046)):
        results[key] = ray_hits_capsule(
            (0.0, 0.0, 0.0), (0.0, 0.0, 1.0),
            (d, 0.0, 0.3), (d, 0.0, 0.5), radius) == (d < radius)

    # 8 可重复性回归：执行顺序无关 + 身高敏感 + 全局场景不可变
    snap = json.dumps(SCENARIOS, sort_keys=True)
    rA = evaluate("S2-face-to-face", "seated-1.10", "chest", 0, None,
                  "180", "fit_diagonal")
    _ = evaluate("S1-side-reading", "stand-1.35", "chest", 30, None,
                 "180", "fit_height")
    _ = evaluate("S2-face-to-face", "seated-1.10", "lanyard", 15, -10,
                 "150", "fit_height")
    rB = evaluate("S2-face-to-face", "seated-1.10", "chest", 0, None,
                  "180", "fit_diagonal")
    results["order_independent"] = rA == rB
    h135 = evaluate("S2-face-to-face", "stand-1.35", "chest", 0, None,
                    "180", "fit_diagonal")
    results["height_sensitive"] = h135 != rA and (
        h135["targets"]["孩子面部"]["theta_deg"]
        != rA["targets"]["孩子面部"]["theta_deg"])
    results["scenarios_untouched"] = json.dumps(SCENARIOS, sort_keys=True) == snap

    bool_keys = [k for k, v in results.items() if isinstance(v, bool)]
    results["selftest_bool_count"] = len(bool_keys)
    results["all_pass"] = all(results[k] for k in bool_keys)
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="generated/framing_sim")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    out_root = Path(args.out)
    if args.selftest:
        res = selftest()
        print(json.dumps(res, ensure_ascii=False, indent=1))
        raise SystemExit(0 if res["all_pass"] else 1)

    results = {
        "model": {
            "version": "v2",
            "projection": "equidistant (OpenCV fisheye 同族): r_px=R·θ/θ_max",
            "off_axis_angle": "atan2(hypot(Xc,Yc), Zc)；Zc≤ε 判 behind_camera",
            "frame": "16:9 1920×1080",
            "crop_configs": {k: round(v, 1) for k, v in CROP.items()},
            "effective_fov": {f"{fk}/{ck}": effective_fov(FOVS[fk], CROP[ck])
                              for fk in FOVS for ck in CROP},
            "domain_note": "模型有效域 θ∈[0, θ_max]；本轮结论不依赖 >180° 覆盖",
            "occluders": "躯干盒+头球+手臂胶囊（精确线段距离判定，双姿态；衣物未建模）",
            "posture": {"chest": "pitch 随前倾 0/15/30° 转动",
                        "lanyard": "pitch 受摆动 {-10,0,+10}° 影响，位置随前倾少量前移"},
            "reproducibility": "evaluate() 不修改全局 SCENARIOS；结果与执行顺序无关"
                               "（自检回归覆盖）",
        },
        "label": "模拟预测：几何投影+简化遮挡，非实拍；场景/阈值/姿态均为实验假设",
        "thresholds": THRESHOLDS,
        "runs": [], "selftest": selftest(),
    }
    for scen_key in SCENARIOS:
        for h_key in HEIGHTS:
            for mount in MOUNTS:
                for lean in LEANS:
                    sways = SWAYS if mount == "lanyard" else (None,)
                    for sway in sways:
                        for fov_key in FOVS:
                            for crop_key in CROP:
                                results["runs"].append(evaluate(
                                    scen_key, h_key, mount, lean, sway,
                                    fov_key, crop_key))

    # 代表性渲染：基线 / FOV150 失败例 / 前倾 30° 对比（贴身 vs 挂绳）
    media = Path("../../public/media/parent-child-recorder")
    renders = [
        ("S1-side-reading", "seated-1.10", "chest", 0, None, "180", "fit_diagonal",
         media / "sim_s1_tilt20_fov180.png"),
        ("S1-side-reading", "seated-1.10", "chest", 0, None, "150", "fit_diagonal",
         media / "sim_s1_tilt20_fov150.png"),
        ("S2-face-to-face", "seated-1.10", "chest", 0, None, "180", "fit_diagonal",
         media / "sim_s2_tilt20_fov180.png"),
        ("S3-desk-work", "seated-1.10", "chest", 0, None, "180", "fit_diagonal",
         media / "sim_s3_tilt20_fov180.png"),
        ("S1-turn45", "seated-1.10", "chest", 0, None, "180", "fit_diagonal",
         media / "sim_s1_turn45_fov180.png"),
        ("S1-side-reading", "seated-1.10", "chest", 30, None, "180", "fit_diagonal",
         media / "sim_s1_lean30_chest.png"),
        ("S1-side-reading", "seated-1.10", "lanyard", 30, 0, "180", "fit_diagonal",
         media / "sim_s1_lean30_lanyard.png"),
    ]
    for scen, h, mount, lean, sway, fov, crop, path in renders:
        evaluate(scen, h, mount, lean, sway, fov, crop, render=True, out=path)

    # 汇总：按场景×mount×lean 最劣情况统计关键目标可见性（不含家长面部）
    summary = {}
    for scen_key in SCENARIOS:
        for mount in MOUNTS:
            for lean in LEANS:
                rows = [r for r in results["runs"]
                        if r["scenario"] == scen_key and r["mount"] == mount
                        and r["lean_deg"] == lean]
                worst = {}
                for key in ("孩子面部", "课本/桌面", "桌面玩具", "操作工件", "家长双手"):
                    sts = sorted({r["targets"][key]["status"] for r in rows
                                  if key in r["targets"]})
                    worst[key] = "/".join(sts)
                summary.setdefault(scen_key, {})[f"{mount}-lean{lean}"] = worst
    results["posture_worst_case_summary"] = summary

    (out_root / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({
        "runs": len(results["runs"]), "selftest": results["selftest"],
        "effective_fov": results["model"]["effective_fov"],
        "posture_worst_case_summary": summary,
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
