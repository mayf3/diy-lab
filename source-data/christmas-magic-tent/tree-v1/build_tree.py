#!/usr/bin/env python3
"""Printable cross-panel Christmas tree. Original parametric CAD, not physical verification.

Default: 235mm tall, 192mm wide crossed PETG panels and 175mm base.
Parts fit a Bambu P1S 256mm square bed. No supports intended.
Requires cadquery for generating STL/STEP. Printer fit and structural stability
must be physically checked before placing near children.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cadquery as cq

ROOT = Path(__file__).resolve().parent
THICKNESS_MM = 3.6
SLOT_CLEARANCE_MM = 0.5
SLOT_WIDTH_MM = THICKNESS_MM + SLOT_CLEARANCE_MM
WIDTH_MM = 192
HEIGHT_MM = 235
BASE_FOOTSPAN_MM = 175


def outline(height_mm: float, width_mm: float) -> list[tuple[float, float]]:
    # Deliberately sturdy outline; no hair-thin top tip or snap-off ornaments.
    right = [
        (0, HEIGHT_MM),
        (34, 185), (21, 185),
        (64, 125), (44, 125),
        (96, 54), (70, 54),
        (70, 35), (36, 35), (36, 0),
    ]
    both = right + [(-x, y) for x, y in reversed(right)]
    return [(x * width_mm / WIDTH_MM, y * height_mm / HEIGHT_MM) for x, y in both]


def hanging_holes(height_mm: float, width_mm: float) -> list[tuple[float, float]]:
    # Holes are for reusable adult-fitted thin ties, not threading entire LED bulbs.
    rows = [(48, 43), (49, 70), (35, 105), (25, 144), (13, 194)]
    return [(sign * x * width_mm / WIDTH_MM, y * height_mm / HEIGHT_MM) for x, y in rows for sign in (-1, 1)]


def panel(top_open: bool, height_mm: float, width_mm: float) -> cq.Workplane:
    piece = cq.Workplane("XY").polyline(outline(height_mm, width_mm)).close().extrude(THICKNESS_MM)
    xwidth = SLOT_WIDTH_MM
    if top_open:
        y0, y1 = 117 * height_mm / HEIGHT_MM, height_mm + 2
    else:
        y0, y1 = -2, 120 * height_mm / HEIGHT_MM
    slit = (
        cq.Workplane("XY").center(0, (y0 + y1) / 2)
        .rect(xwidth, y1 - y0).extrude(THICKNESS_MM + 1)
    )
    piece = piece.cut(slit)
    drill = cq.Workplane("XY").pushPoints(hanging_holes(height_mm, width_mm)).circle(3.0).extrude(THICKNESS_MM + 1)
    return piece.cut(drill)


def base(footspan_mm: float, width_mm: float) -> cq.Workplane:
    # Flat four-spoke base rather than a wasteful solid disc. Each arm is 175mm
    # wide tip-to-tip, allowing stable tabletop placement with less filament.
    arm_a = cq.Workplane("XY").rect(footspan_mm, 18).extrude(12)
    arm_b = cq.Workplane("XY").rect(18, footspan_mm).extrude(12)
    cross = arm_a.union(arm_b)
    # Two perpendicular 4.1mm channels, 8mm deep, 76mm wide across foot.
    slot_a = cq.Workplane("XY").workplane(offset=4).rect(76 * width_mm / WIDTH_MM, SLOT_WIDTH_MM).extrude(9)
    slot_b = cq.Workplane("XY").workplane(offset=4).rect(SLOT_WIDTH_MM, 76 * width_mm / WIDTH_MM).extrude(9)
    return cross.cut(slot_a.union(slot_b))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "generated")
    ap.add_argument("--height-mm", type=float, default=HEIGHT_MM)
    ap.add_argument("--width-mm", type=float, default=WIDTH_MM)
    ap.add_argument("--footspan-mm", type=float, default=BASE_FOOTSPAN_MM)
    args = ap.parse_args()
    if not 180 <= args.height_mm <= 245 or not 160 <= args.width_mm <= 240:
        ap.error("Panels must fit P1S: height 180–245mm, width 160–240mm")
    if not args.width_mm * 0.75 <= args.footspan_mm <= 245:
        ap.error("Footspan must be stable and printable (>=75% tree width, <=245mm)")
    args.output.mkdir(parents=True, exist_ok=True)
    pieces = {
        "tree_panel_top_slot": panel(top_open=True, height_mm=args.height_mm, width_mm=args.width_mm),
        "tree_panel_bottom_slot": panel(top_open=False, height_mm=args.height_mm, width_mm=args.width_mm),
        "tree_cross_base": base(footspan_mm=args.footspan_mm, width_mm=args.width_mm),
    }
    meta = {}
    for name, shape in pieces.items():
        cq.exporters.export(shape, str(args.output / f"{name}.stl"))
        stepfile = args.output / f"{name}.step"
        cq.exporters.export(shape, str(stepfile))
        # OpenCascade emits trailing spaces in STEP records; strip for clean review.
        stepfile.write_text(
            "\n".join(line.rstrip() for line in stepfile.read_text().splitlines()) + "\n",
            encoding="utf-8",
        )
        solid = shape.val()
        bb = solid.BoundingBox()
        meta[name] = {
            "stl": f"{name}.stl", "step": f"{name}.step",
            "extents_mm": [round(bb.xlen, 2), round(bb.ylen, 2), round(bb.zlen, 2)],
            "approx_solid_volume_cm3": round(solid.Volume() / 1000, 2),
        }
        assert bb.xlen <= 250 and bb.ylen <= 250 and bb.zlen <= 20, name
    meta["parameters"] = {"height_mm": args.height_mm, "width_mm": args.width_mm,
                          "footspan_mm": args.footspan_mm, "thickness_mm": THICKNESS_MM}
    meta["design_notes"] = {
        "status": "parametric CAD only; no printed fit/stability testing",
        "clearance_mm": SLOT_CLEARANCE_MM,
        "assembly": "print both panels flat; join at the central cross-slit, insert both feet into grooved base",
        "illumination": "wrap removable 5V prewired LED seed string around silhouette and use loose reusable ties through holes; do not pinch conductors",
        "placement": "tabletop, outside children's reach, independent of tent; no overnight unattended use",
    }
    (args.output / "geometry-report.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
