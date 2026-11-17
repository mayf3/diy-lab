#!/usr/bin/env python3
"""亲子教学随身记录器｜取景模拟（模拟预测，非实拍）。

用显式等距鱼眼投影模型（与 OpenCV fisheye / equidistant 模型同口径）：
  3D 点 → 相机坐标 (xc,yc,zc)；θ = arccos(zc/|d|)（偏离光轴角）；
  像素半径 r_px = R_px · θ/θ_max（等距：像素/角度在全幅恒定）。
这是几何投影示意图，不是真实渲染画质；所有场景参数均为本轮实验性假设，
不是项目发起人已确认的需求。

比较轴（实验参数）：
  佩戴高度：1.35 m（成人站立挂脖） / 1.10 m（成人就座挂脖）
  镜头下倾：0° / 20° / 35°
  视场角：180°（典型鱼眼模组规格，等距模型） / 150°（广角对照）
场景（三个候选教学场景，几何为典型家具尺寸假设）：
  S1 并排读书 / S2 面对面小游戏 / S3 桌面操作

用法：python3 framing_sim.py [--out generated/framing_sim]
输出：results.json（每个配置×场景的量化指标）+ 若干 PNG（鱼眼示意 + 俯视几何图）。
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------- 可复用的中文绘图字体（与仓内其他脚本同策略） ----------
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


# ---------- 投影模型 ----------
def basis(yaw_deg: float, pitch_down_deg: float):
    """相机基：(右, 上, 光轴)。yaw=180° 表示佩戴者面向 -Z（桌子方向）。"""
    y, p = math.radians(yaw_deg), math.radians(pitch_down_deg)
    ax = math.cos(p) * math.sin(y)
    ay = -math.sin(p)
    az = math.cos(p) * math.cos(y)
    axis = (ax, ay, az)
    right = (math.cos(y), 0.0, -math.sin(y))
    up = (axis[1] * right[2] - axis[2] * right[1],
          axis[2] * right[0] - axis[0] * right[2],
          axis[0] * right[1] - axis[1] * right[0])
    return right, up, axis


def project(point, cam, pitch, yaw, fov_deg, img_px):
    """返回 (u, v, theta_deg, in_circle)。世界坐标：X 右，Y 上，Z 前。"""
    dx, dy, dz = (point[0] - cam[0], point[1] - cam[1], point[2] - cam[2])
    r, u, a = basis(yaw, pitch)
    xc, yc, zc = (dx * r[0] + dy * r[1] + dz * r[2],
                  dx * u[0] + dy * u[1] + dz * u[2],
                  dx * a[0] + dy * a[1] + dz * a[2])
    norm = math.sqrt(dx * dx + dy * dy + dz * dz) or 1e-9
    cos_t = max(-1.0, min(1.0, zc / norm))
    theta = math.degrees(math.acos(cos_t))
    phi = math.atan2(yc, xc)
    theta_max = fov_deg / 2.0
    radius_px = (img_px / 2.0) * 0.94  # 像圆略小于画幅，留标注边
    rr = radius_px * theta / theta_max
    cx = cy = img_px / 2.0
    return (cx + rr * math.cos(phi), cy - rr * math.sin(phi), theta, theta <= theta_max)


def px_width(width_m: float, dist_m: float, fov_deg: float, img_px: int) -> int:
    """等距模型：像素/度恒定 → 目标宽度像素 = px_per_deg × 角直径。"""
    px_per_deg = (img_px / 2.0) * 0.94 / (fov_deg / 2.0)
    subtended = math.degrees(2 * math.atan(width_m / 2 / max(dist_m, 0.05)))
    return int(px_per_deg * subtended)


# ---------- 场景定义（实验性假设参数） ----------
TABLE = {"xmin": -0.6, "xmax": 0.6, "zmin": -0.35, "zmax": 0.35, "y": 0.75}

SCENARIOS = {
    "S1-side-reading": {
        "title": "S1 并排读书（并排坐桌旁）",
        "camera_yaw": 180.0,  # 家长面向 -Z（桌子）
        "parent_pos": (-0.25, None, 0.62),  # y 由佩戴高度填充
        "targets": [
            {"name": "课本/桌面", "point": (0.10, 0.77, 0.10), "w": 0.20},
            {"name": "家长双手", "point": (0.05, 0.90, 0.22), "w": 0.16},
            {"name": "孩子面部", "point": (0.32, 0.98, 0.52), "w": 0.09},
        ],
    },
    "S2-face-to-face": {
        "title": "S2 面对面小游戏",
        "camera_yaw": 180.0,
        "parent_pos": (0.0, None, 0.55),
        "targets": [
            {"name": "桌面玩具", "point": (0.0, 0.78, 0.0), "w": 0.14},
            {"name": "孩子面部", "point": (0.0, 0.98, -0.55), "w": 0.09},
            {"name": "家长双手", "point": (0.0, 0.90, 0.15), "w": 0.16},
        ],
    },
    "S3-desk-work": {
        "title": "S3 桌面操作（孩子在旁）",
        "camera_yaw": 180.0,
        "parent_pos": (0.0, None, 0.45),
        "targets": [
            {"name": "操作工件", "point": (0.0, 0.77, 0.0), "w": 0.18},
            {"name": "家长双手", "point": (0.0, 0.83, 0.05), "w": 0.16},
            {"name": "孩子面部", "point": (0.45, 0.98, 0.10), "w": 0.09},
        ],
    },
}

HEIGHTS = {"stand-1.35": 1.35, "seated-1.10": 1.10}
TILTS = [0, 20, 35]
FOVS = [180, 150]
# 实验阈值（模拟判读用，非最终验收标准）：教学物 ≥100px、面部 ≥60px 才记“可读”
PX_THRESH = {"教学": 100, "面部": 60, "手部": 80}


def threshold_for(name: str) -> int:
    if "面部" in name:
        return PX_THRESH["面部"]
    if "手" in name:
        return PX_THRESH["手部"]
    return PX_THRESH["教学"]


# ---------- 绘图 ----------
INK, EDGE, BG = (30, 34, 44), (17, 24, 39), (250, 250, 248)
ACCENT = (196, 74, 56)
GOOD, BAD = (36, 130, 89), (170, 60, 54)


def draw_scene(cfg_label: str, scen_key: str, height: float, tilt: int, fov: int,
               out: Path, img_px: int = 1080) -> dict:
    """左侧鱼眼画幅 + 右侧图例/局部放大，避免标注互相重叠。"""
    scen = SCENARIOS[scen_key]
    cam = (scen["parent_pos"][0], height, scen["parent_pos"][2])
    yaw = scen["camera_yaw"]
    panel_w = 520
    img = Image.new("RGB", (img_px + panel_w, img_px), BG)
    draw = ImageDraw.Draw(img)
    f_lab, f_small, f_idx = _font(30), _font(22), _font(26)

    theta_max = fov / 2.0
    radius = img_px / 2.0 * 0.94
    c = img_px / 2.0
    draw.ellipse([c - radius, c - radius, c + radius, c + radius], fill=(255, 255, 255),
                 outline=(180, 186, 194), width=3)
    draw.line([c - 14, c, c + 14, c], fill=(150, 156, 164), width=2)
    draw.line([c, c - 14, c, c + 14], fill=(150, 156, 164), width=2)

    # 桌面网格（等距投影下可见弯曲，直观展示鱼眼畸变）
    t = TABLE
    verts = []
    for zi in [t["zmin"], 0, t["zmax"]]:
        row = []
        for xi in [t["xmin"], t["xmin"] + 0.3, t["xmin"] + 0.6, t["xmin"] + 0.9, t["xmax"]]:
            row.append((xi, t["y"], zi))
        verts.append(row)
    for row in verts:
        pts = []
        for p in row:
            u, v, th, ok = project(p, cam, tilt, yaw, fov, img_px)
            if ok:
                pts.append((u, v))
        if len(pts) >= 2:
            draw.line(pts, fill=(205, 210, 216), width=2)
    for col in range(5):
        pts = []
        for row in verts:
            p = row[col]
            u, v, th, ok = project(p, cam, tilt, yaw, fov, img_px)
            if ok:
                pts.append((u, v))
        if len(pts) >= 2:
            draw.line(pts, fill=(205, 210, 216), width=2)

    idx_marks = "①②③④⑤"
    legend = []
    boxes = []
    for i, tgt in enumerate(scen["targets"]):
        p = tgt["point"]
        dist = math.dist(cam, p)
        u, v, th, ok = project(p, cam, tilt, yaw, fov, img_px)
        pw = px_width(tgt["w"], dist, fov, img_px)
        thr = threshold_for(tgt["name"])
        quality = "readable" if ok and pw >= thr else "small"
        color = GOOD if quality == "readable" else (ACCENT if ok else BAD)
        mark = idx_marks[i]
        if ok:
            r_px = max(7, pw // 2)
            draw.ellipse([u - r_px, v - r_px, u + r_px, v + r_px], outline=color, width=4)
            boxes.append((u - r_px, v - r_px, u + r_px, v + r_px))
            lx, ly = min(max(u + r_px + 4, 8), img_px - 40), v - 14
            while any(bx0 - 4 <= lx <= bx1 + 4 and by0 - 4 <= ly + 13 <= by1 + 4
                      for bx0, by0, bx1, by1 in boxes[:-1]):
                lx += 20  # 标号落在其他目标圈上时外移
            draw.text((lx, ly), mark, fill=color, font=f_idx)
        else:
            ang = math.atan2(c - v, u - c)
            ex, ey = c + (radius - 18) * math.cos(ang), c - (radius - 18) * math.sin(ang)
            draw.ellipse([ex - 16, ey - 16, ex + 16, ey + 16], outline=BAD, width=3)
            draw.text((ex - 10, ey - 15), mark, fill=BAD, font=f_idx)
        legend.append((mark, tgt["name"], pw, th, dist, ok,
                       "可读" if quality == "readable" else ("偏小" if ok else "视场外"), color))

    # 家长头部示意（相机=挂脖位置，位于头部下方约 0.25m）
    head_p = (cam[0], height + 0.25, cam[2])
    u, v, th, ok = project(head_p, cam, tilt, yaw, fov, img_px)
    if ok:
        draw.ellipse([u - 6, v - 30, u + 6, v + 6], outline=(120, 128, 138), width=2)

    # ---- 右侧图例面板 ----
    px0 = img_px + 24
    draw.text((px0, 20), "模拟预测（非实拍）", fill=ACCENT, font=f_lab)
    draw.text((px0, 62), scen["title"], fill=INK, font=f_lab)
    draw.text((px0, 104), f"配置：{cfg_label}", fill=(70, 78, 88), font=f_small)
    draw.text((px0, 134), f"镜头下倾 {tilt}°｜FOV {fov}°｜等距鱼眼模型", fill=(70, 78, 88),
              font=f_small)
    y = 190
    draw.text((px0, y), "目标判读（阈值见下）", fill=INK, font=f_small)
    y += 40
    for mark, name, pw, th, dist, ok, verdict, color in legend:
        draw.text((px0, y), f"{mark} {name}", fill=color, font=f_small)
        draw.text((px0 + 200, y), f"{pw}px θ={th:.0f}° {verdict}", fill=color, font=f_small)
        y += 34
    y += 12
    draw.text((px0, y), "阈值（实验假设）：教学物≥100px，", fill=(90, 98, 108), font=f_small)
    y += 28
    draw.text((px0, y), "手部≥80px，面部≥60px 记“可读”", fill=(90, 98, 108), font=f_small)
    y += 44
    draw.text((px0, y), "灰色：家长头部示意（相机=挂脖位置）", fill=(120, 128, 138),
              font=f_small)
    y += 28
    draw.text((px0, y), "网格：桌面 1.2×0.7m @0.75m 高", fill=(120, 128, 138), font=f_small)

    # 局部放大：围绕可见目标包围盒裁剪 ×2（同一模拟帧的裁剪，非另一视角）
    if boxes:
        xs = [b[0] for b in boxes] + [b[2] for b in boxes]
        ys = [b[1] for b in boxes] + [b[3] for b in boxes]
        cx0, cy0 = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        half = max(max(xs) - min(xs), max(ys) - min(ys)) / 2 * 2.2 + 40
        half = max(80, min(half, 118))  # 保证放大倍率 ≥2×；内容过宽时取中心区域
        x0, y0 = max(0, int(cx0 - half)), max(0, int(cy0 - half))
        x1, y1 = min(img_px, int(cx0 + half)), min(img_px, int(cy0 + half))
        crop = img.crop((x0, y0, x1, y1))
        zw = panel_w - 48
        zratio = zw / crop.width
        crop = crop.resize((zw, int(crop.height * zratio)))
        zy = y + 40
        draw.rectangle([px0 - 8, zy - 8, px0 - 8 + crop.width, zy + crop.height + 8],
                       outline=(180, 186, 194), width=2)
        img.paste(crop, (px0 - 4, zy))
        draw.text((px0, min(zy + crop.height + 16, img_px - 30)),
                  f"局部放大 ×{zratio:.1f}（同帧裁剪中心区）", fill=(90, 98, 108), font=f_small)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    metrics = {}
    for (mark, name, pw, th, dist, ok, verdict, color), tgt in zip(legend, scen["targets"]):
        metrics[name] = {"visible": ok, "theta_deg": round(th, 1),
                         "distance_m": round(dist, 2), "px_width": pw,
                         "threshold_px": threshold_for(name),
                         "readable": bool(ok and pw >= threshold_for(name))}
    return metrics


def draw_topdown(scen_key: str, out: Path, height_seated: float = 1.10) -> None:
    """俯视几何图：桌子、家长/孩子位置、典型距离标注。"""
    scen = SCENARIOS[scen_key]
    W = 900
    scale = W / 3.2  # 世界 3.2m 宽映射到画布
    ox, oy = W / 2, W / 2
    img = Image.new("RGB", (W, W), BG)
    draw = ImageDraw.Draw(img)
    f_lab, f_small = _font(26), _font(20)

    def wx(x):
        return ox + x * scale

    def wy(z):
        return oy + z * scale

    t = TABLE
    draw.rectangle([wx(t["xmin"]), wy(t["zmin"]), wx(t["xmax"]), wy(t["zmax"])],
                   fill=(255, 255, 255), outline=(120, 128, 138), width=3)
    draw.text((wx(-0.55), wy(0) - 16), "桌面 1.2×0.7m @0.75m", fill=(90, 98, 108), font=f_small)

    pp = scen["parent_pos"]
    parent = (wx(pp[0]), wy(pp[2]))
    draw.ellipse([parent[0] - 16, parent[1] - 16, parent[0] + 16, parent[1] + 16],
                 fill=(90, 98, 108))
    draw.text((parent[0] - 40, parent[1] + 22), "家长（挂脖相机）", fill=INK, font=f_small)

    face = next(x for x in scen["targets"] if "面部" in x["name"])
    child = (wx(face["point"][0]), wy(face["point"][2]))
    draw.ellipse([child[0] - 14, child[1] - 14, child[0] + 14, child[1] + 14],
                 fill=(64, 122, 190))
    draw.text((child[0] - 30, child[1] + 20), "孩子", fill=(64, 122, 190), font=f_small)

    obj = scen["targets"][0]
    op = (wx(obj["point"][0]), wy(obj["point"][2]))
    draw.ellipse([op[0] - 10, op[1] - 10, op[0] + 10, op[1] + 10], outline=ACCENT, width=4)
    draw.text((op[0] + 14, op[1] - 30), obj["name"], fill=ACCENT, font=f_small)

    # 视线与距离
    draw.line([parent, child], fill=(64, 122, 190), width=2)
    dm = math.dist((pp[0], 0, pp[2]), (face["point"][0], 0, face["point"][2]))
    draw.text(((parent[0] + child[0]) / 2 + 10, (parent[1] + child[1]) / 2),
              f"水平距离≈{dm:.2f}m", fill=(64, 122, 190), font=f_small)
    draw.line([parent, op], fill=ACCENT, width=2)
    do = math.dist((pp[0], 0, pp[2]), (obj["point"][0], 0, obj["point"][2]))
    draw.text(((parent[0] + op[0]) / 2 + 10, (parent[1] + op[1]) / 2 - 26),
              f"≈{do:.2f}m", fill=ACCENT, font=f_small)

    draw.text((24, 16), f"模拟预测｜俯视几何假设｜{scen['title']}", fill=INK, font=f_lab)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="generated/framing_sim")
    args = ap.parse_args()
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    results = {"model": "equidistant fisheye (OpenCV fisheye 同口径): r_px=R·θ/θ_max",
               "label": "模拟预测：几何投影示意，非实拍；场景与阈值均为实验性假设",
               "thresholds": PX_THRESH, "runs": []}
    for scen_key in SCENARIOS:
        for h_key, h in HEIGHTS.items():
            for tilt in TILTS:
                for fov in FOVS:
                    label = f"{h_key}-tilt{tilt:02d}-fov{fov}"
                    png = out_root / f"{scen_key}_{label}.png"
                    metrics = draw_scene(label, scen_key, h, tilt, fov, png)
                    all_vis = all(m["visible"] for m in metrics.values())
                    all_readable = all(m["readable"] for m in metrics.values())
                    results["runs"].append({
                        "scenario": scen_key, "config": label,
                        "height_m": h, "tilt_deg": tilt, "fov_deg": fov,
                        "targets": metrics, "all_visible": all_vis,
                        "all_readable": all_readable,
                        "image": str(png)})

    for scen_key in SCENARIOS:
        draw_topdown(scen_key, out_root / f"{scen_key}_topdown.png")

    # 汇总：全场景全目标可见且可读的配置
    winners = []
    for cfg in {r["config"] for r in results["runs"]}:
        rows = [r for r in results["runs"] if r["config"] == cfg]
        if len(rows) == len(SCENARIOS) and all(r["all_visible"] for r in rows):
            readable = sum(r["all_readable"] for r in rows)
            min_px = min(m["px_width"] for r in rows for m in r["targets"].values()
                         if m["visible"])
            winners.append({"config": cfg, "scenarios_all_readable": readable,
                            "min_visible_px": min_px})
    winners.sort(key=lambda w: (-w["scenarios_all_readable"], -w["min_visible_px"]))
    results["configs_covering_all_scenarios"] = winners

    (out_root / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"runs": len(results["runs"]),
                      "covering_configs": winners[:4],
                      "out": str(out_root)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
