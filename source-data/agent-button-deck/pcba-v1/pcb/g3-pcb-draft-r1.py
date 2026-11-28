#!/usr/bin/env python3
"""Space Buddy R1 · PCB Layout 草案（G3 前置，不冻结、不导 Gerber）。

产物（source-data/agent-button-deck/pcba-v1/pcb/draft/）：
  pcb-draft-r1.json  机器可读草案几何（每项尺寸带 source/freeze 状态）
  pcb-draft-r1.svg   布局图（外部评审用；非 EDA 截图——EDA 画布阻断见 project.json）

内容：
  A. DevKitC 插座子布局（官方数字，可复查）
     - J1/J3 两排 1×22P 母排焊盘：间距 2.54mm（官方标注），排距 22.86mm
       （= 板宽 25.40 − 2×1.27，三个数字均出自 PCB_ESP32-S3-DevKitC-1_V1.1_20220429.pdf
       第 1 页标注，SHA256 3f6716…；pdftotext bbox 复核 ≈22.82）
     - 每排长 53.34mm；DevKitC 板框 25.40×62.74；USB 区 8.00mm 在板底
     - 编号方向：pin1(3V3) 远离 USB 端、pin22(GND) 近 USB 端（官方 J1 表）
     - 载板底边切过 DevKitC USB 区 → 连接器悬出载板边缘（注册表既定意图）
  B. 四键 2×2 区域（壳体 provisional 映射，标记 unfrozen）
     - 键距 33×33 来自壳体 dims.json（status=placeholder，等样轴）
  C. 联合可行性数字：当前壳体内腔 83.2×73.2 与"插座+2×2 键"共面布置冲突——
     记为 G4 联合检查项（双层载板 / 调键距 / 竖置 DevKitC 三选一），草案不隐瞒。

运行：python3 g3-pcb-draft-r1.py   （无第三方依赖，标准库生成 JSON+SVG）
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "draft"

# ── 官方数字（confirmed-official，PDF SHA256 3f6716…）────────────────────────
PITCH = 2.54                 # 焊盘间距（官方标注 2.54mm）
BOARD_W = 25.40              # DevKitC 板宽（官方标注）
BOARD_L = 62.74              # DevKitC 板长（官方标注）
EDGE_TO_PAD = 1.27           # 板边→焊排中心（官方标注 1.27mm）
ROW_SPACING = BOARD_W - 2 * EDGE_TO_PAD   # 22.86mm 两焊排中心距
PAD_COUNT = 22
ROW_LEN = (PAD_COUNT - 1) * PITCH         # 53.34mm
USB_ZONE = 8.00              # DevKitC 板内 USB 区段（官方标注）
DEV_TOP_GAP = round(BOARD_L - USB_ZONE - ROW_LEN - 4.40, 2)  # 顶部余量倒推（草案值 1.40）

# ── 壳体 provisional（dims.json placeholder / awaiting-measure）─────────────
KEY_PITCH = 33.0             # provisional（壳体参数设定，等样轴）
KEY_HOLE = 15.6              # MX 通称孔位占位（无 datasheet，awaiting）
CASE_INNER_W = 83.2          # 壳体内腔（body 88 − wall 2.4×2，provisional）
CASE_INNER_D = 73.2          # （body 78 − wall 2.4×2，provisional）

# ── 载板草案（DRAFT-UNFROZEN：本文件自定草案值，待联合检查定稿）──────────────
CARRIER_W = 76.0             # 载板宽（草案）
CARRIER_D = 62.0             # 载板长（草案；底边切过 DevKitC USB 区）
J1_X = 6.0                   # J1 焊排 x（草案内缩）
PADS_Y0 = 4.0                # pin22(近 USB 端) y 起点（草案；编号向远离 USB 增）
DEV_KIT_X0 = J1_X - EDGE_TO_PAD          # DevKitC 板左缘 4.73
DEV_KIT_X1 = DEV_KIT_X0 + BOARD_W        # 30.13（= J3 排 + 1.27）
DEV_KIT_Y0 = 2.0                         # DevKitC 板顶缘（草案）
DEV_KIT_Y1 = DEV_KIT_Y0 + BOARD_L        # 64.74 → 悬出载板底边 62.0 约 2.74mm
USB_ZONE_Y0 = DEV_KIT_Y1 - USB_ZONE      # 56.74（USB 区在 DevKitC 板内底部）

def pads(x_col: float) -> list[dict]:
    """焊盘坐标；pin1(3V3)=远离 USB 端（y 小，顶部）→ pin22(GND)=近 USB 端（y 大，底部）。"""
    out = []
    for n in range(1, PAD_COUNT + 1):
        y = PADS_Y0 + (n - 1) * PITCH
        out.append({"pin": n, "x": round(x_col, 2), "y": round(y, 2)})
    return out

j1_pads = pads(J1_X)
j3_pads = pads(J1_X + ROW_SPACING)

# 2×2 键区（壳体 provisional：中心按 33 键距对称于载板可用区右半）
KEY_CENTERS = [
    {"key": "K1", "x": 52.0, "y": 14.5},
    {"key": "K2", "x": 52.0, "y": 47.5},
    {"key": "K3", "x": 19.0, "y": 47.5},
    {"key": "K4", "x": 19.0, "y": 14.5},
]

# 与 DevKitC 区域的冲突检测（草案必须自曝）
def overlap(a, b) -> bool:
    return not (a["x1"] >= b["x2"] or b["x1"] >= a["x2"] or
                a["y1"] >= b["y2"] or b["y1"] >= a["y2"])

dev_zone = {"x1": DEV_KIT_X0, "x2": DEV_KIT_X1, "y1": DEV_KIT_Y0, "y2": DEV_KIT_Y1}
conflicts = []
for kc in KEY_CENTERS:
    kr = {"x1": kc["x"] - KEY_HOLE / 2, "x2": kc["x"] + KEY_HOLE / 2,
          "y1": kc["y"] - KEY_HOLE / 2, "y2": kc["y"] + KEY_HOLE / 2}
    if overlap(kr, dev_zone):
        conflicts.append({"key": kc["key"], "with": "DevKitC 插座区"})

draft = {
    "schema": "pcb-draft-r1",
    "status": "DRAFT-UNFROZEN（不冻结、不导 Gerber、不下单；EDA 原生放置待画布可用）",
    "generated_by": "g3-pcb-draft-r1.py (2026-11-29)",
    "coordinate_note": "mm；原点=载板草案左上角；y 向下增大（SVG 同系）",
    "official_basis": {
        "doc": "PCB_ESP32-S3-DevKitC-1_V1.1_20220429.pdf 第 1 页标注",
        "sha256": "3f67160841a5a730297b754b…（与注册表记录 3f6716… 一致，2026-11-29 重下载核验）",
        "values": {"pitch_mm": PITCH, "board_w_mm": BOARD_W, "board_l_mm": BOARD_L,
                    "edge_to_pad_mm": EDGE_TO_PAD, "usb_zone_mm": USB_ZONE},
        "derived": {"row_spacing_mm": ROW_SPACING,
                     "row_len_mm": ROW_LEN,
                     "cross_check": "53.34(排长)+8.00(USB区)=61.34 ≈ 62.74−顶部余量；pdftotext bbox 比例复核 ≈22.82"}
    },
    "socket": {
        "j1_pads": j1_pads,
        "j3_pads": j3_pads,
        "row_spacing_mm": ROW_SPACING,
        "pin_numbering": "pin1(3V3)=远离 USB 端；pin22(GND)=近 USB 端（官方 J1 表）",
        "devkitc_envelope": {"x0": DEV_KIT_X0, "x1": DEV_KIT_X1, "y0": DEV_KIT_Y0, "y1": DEV_KIT_Y1,
                              "usb_zone_y0": USB_ZONE_Y0,
                              "overhang_beyond_carrier": round(DEV_KIT_Y1 - CARRIER_D, 2)},
        "gpio_pads": {str(n): [p for p in j1_pads if p["pin"] == n][0] for n in (4, 5, 6, 7)},
        "gnd_pads": {f"{c}-{n}": [p for p in ps if p["pin"] == n][0]
                      for c, ps in (("J1", j1_pads), ("J3", j3_pads)) for n in ((22,) if c == "J1" else (1, 21, 22))},
    },
    "keys_2x2": {"centers": KEY_CENTERS, "pitch_mm": KEY_PITCH, "hole_mm": KEY_HOLE,
                  "source": "壳体 dims.json placeholder（等样轴实测；不得冻结）"},
    "carrier_outline_draft": {"w": CARRIER_W, "d": CARRIER_D,
                               "note": "草案矩形；真实板框待联合检查（螺柱/键距/USB 开孔联动）"},
    "joint_conflicts_exposed": {
        "case_inner_mm": {"w": CASE_INNER_W, "d": CASE_INNER_D},
        "conflicts": conflicts,
        "statement": "当前草案坐标下 K3/K4 与 DevKitC 插座区重叠——共面布置不可行；"
                      "G4 联合检查须三选一：双层载板（插座下沉）/ 调整键距 / DevKitC 竖置。"
                      "本草案不隐瞒该冲突，不冻结任何解除方案。",
    },
    "reservations": {
        "usb": "DevKitC 双 USB 口位于其板底 USB 区（中心距 ≈12.5 awaiting-measure）；载板底边让位",
        "boss": "螺柱位置为壳体 placeholder（dims.json 明示『当前坐标不得用于 PCB 布局』）——草案未布置螺柱",
        "switch_footprint": "K1–K4 无 PCB 封装（Convert to PCB=no）；样轴确认后绑定真正机械轴封装，不复用 YD-3410",
    },
    "unfrozen_dimensions": [
        "载板外形 76×62（草案自定）", "焊排起点 x=6.0/y0=4.0（草案自定）",
        "键距 33×33（壳体 placeholder）", "键孔 15.6（MX 通称，无 datasheet）",
        "螺柱全部（壳体 placeholder）", "USB 中心距 12.5（awaiting-measure）",
        "DevKitC 全部（到货实测终判）", "排距 22.86（official，但到货实测终判）",
    ],
}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "pcb-draft-r1.json").write_text(json.dumps(draft, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

# ── SVG 渲染（评审图；非 EDA 截图）──────────────────────────────────────────
W, H = 940, 860
sx = sy = 9.0   # 9 px/mm
ox, oy = 40, 64
def X(v): return ox + v * sx
def Y(v): return oy + v * sy
s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
s.append(f'<rect width="{W}" height="{H}" fill="#fafafa"/>')
s.append(f'<text x="{ox}" y="18" font-size="15" font-weight="bold">Space Buddy R1 · PCB Layout 草案（DRAFT-UNFROZEN，不导 Gerber）</text>')
# 载板
s.append(f'<rect x="{X(0)}" y="{Y(0)}" width="{CARRIER_W*sx}" height="{CARRIER_D*sy}" fill="#eef2e6" stroke="#5a7" stroke-width="2"/>')
s.append(f'<text x="{X(1)}" y="{Y(0)-4}" font-size="11" fill="#363">载板草案 {CARRIER_W}×{CARRIER_D}（未冻结）</text>')
# DevKitC 包络 + USB 区
s.append(f'<rect x="{X(dev_zone["x1"])}" y="{Y(dev_zone["y1"])}" width="{(dev_zone["x2"]-dev_zone["x1"])*sx}" height="{(dev_zone["y2"]-dev_zone["y1"])*sy}" fill="#e7ecf5" stroke="#48a" stroke-width="1.5" stroke-dasharray="6,3"/>')
s.append(f'<rect x="{X(dev_zone["x1"])}" y="{Y(USB_ZONE_Y0)}" width="{(dev_zone["x2"]-dev_zone["x1"])*sx}" height="{(DEV_KIT_Y1-USB_ZONE_Y0)*sy}" fill="#f5e7e7" stroke="#a55" stroke-width="1.2"/>')
s.append(f'<text x="{X(dev_zone["x1"])+4}" y="{Y(dev_zone["y1"])+14}" font-size="11" fill="#36a">DevKitC 25.40×62.74（官方）</text>')
s.append(f'<text x="{X(dev_zone["x1"])+4}" y="{Y(USB_ZONE_Y0)+14}" font-size="11" fill="#a44">USB 区 8.00（悬出载板底边 {round(DEV_KIT_Y1-CARRIER_D,2)}）</text>')
# 焊盘
for name, pads_, col in (("J1", j1_pads, "#263"), ("J3", j3_pads, "#263")):
    for p in pads_:
        s.append(f'<circle cx="{X(p["x"])}" cy="{Y(p["y"])}" r="3.2" fill="#d80" stroke="{col}"/>')
    top, bot = pads_[0], pads_[-1]
    s.append(f'<text x="{X(pads_[0]["x"])+6}" y="{Y(top["y"])+4}" font-size="11" fill="#248">{name}1(3V3)</text>')
    s.append(f'<text x="{X(pads_[-1]["x"])+6}" y="{Y(bot["y"])+4}" font-size="11" fill="#248">{name}22(GND)</text>')
# 排距标注
s.append(f'<line x1="{X(J1_X)}" y1="{Y(-2.2)}" x2="{X(J1_X+ROW_SPACING)}" y2="{Y(-2.2)}" stroke="#333" marker-start="url(#a)" marker-end="url(#a)"/>')
s.append(f'<text x="{X(J1_X+ROW_SPACING/2)-26}" y="{Y(-2.8)}" font-size="11">排距 {ROW_SPACING}（官方 25.40−2×1.27）</text>')
s.append('<defs><marker id="a" markerWidth="8" markerHeight="8" refX="4" refY="4"><circle cx="4" cy="4" r="2.5" fill="#333"/></marker></defs>')
# 键区
for kc in KEY_CENTERS:
    hit = any(c["key"] == kc["key"] for c in conflicts)
    col = "#c33" if hit else "#373"
    s.append(f'<rect x="{X(kc["x"]-KEY_HOLE/2)}" y="{Y(kc["y"]-KEY_HOLE/2)}" width="{KEY_HOLE*sx}" height="{KEY_HOLE*sy}" fill="none" stroke="{col}" stroke-width="1.6" stroke-dasharray="5,3"/>')
    s.append(f'<text x="{X(kc["x"]-KEY_HOLE/2)+2}" y="{Y(kc["y"]-KEY_HOLE/2)+12}" font-size="11" fill="{col}">{kc["key"]}区15.6×15.6{"（与插座冲突）" if hit else ""}</text>')
# GPIO/GND 标注（草案走线意图：从 J1.4-7 向键区短引出）
import json as _j
gp = draft["socket"]["gpio_pads"]
for n in (4, 5, 6, 7):
    p = gp[str(n)]
    s.append(f'<line x1="{X(p["x"])}" y1="{Y(p["y"])}" x2="{X(p["x"])-18}" y2="{Y(p["y"])}" stroke="#c60" stroke-width="2"/>')
    s.append(f'<text x="{X(p["x"])-64}" y="{Y(p["y"])+4}" font-size="10" fill="#c60">GPIO{n}</text>')
s.append(f'<text x="{X(38)}" y="{Y(60)}" font-size="11" fill="#a33">⚠ K3/K4 与插座区冲突（G4 联合检查项：双层载板/调键距/竖置三选一）</text>')
s.append(f'<text x="{ox}" y="{H-8}" font-size="10" fill="#666">依据：PCB_ESP32-S3-DevKitC-1_V1.1_20220429.pdf（SHA256 3f6716…）官方标注 25.40/62.74/1.27/8.00/2.54 · 本图非 EDA 截图 · 全部尺寸未冻结</text>')
s.append('</svg>')
(OUT / "pcb-draft-r1.svg").write_text("\n".join(s), encoding="utf-8")
print(json.dumps({"conflicts": conflicts, "row_spacing": ROW_SPACING,
                   "outputs": [str(OUT / 'pcb-draft-r1.json'), str(OUT / 'pcb-draft-r1.svg')]},
                  ensure_ascii=False, indent=1))
