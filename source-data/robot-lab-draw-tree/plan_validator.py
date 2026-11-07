#!/usr/bin/env python3
"""Offline-only stroke plan validator and SVG preview. NEVER opens a robot device."""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

SCHEMA = "robot-lab.stroke-plan.v1"
SIZE_MM = 80
MIN_XY = 0.10
MAX_XY = 0.90
MAX_STROKES = 12
MAX_POINTS_PER_STROKE = 32
MAX_SEGMENT = 0.65
MAX_TOTAL_LENGTH = 8.0


def validate(plan: object) -> float:
    if not isinstance(plan, dict) or set(plan) != {"schema", "canvas", "strokes"}:
        raise ValueError("root fields must be schema, canvas, strokes only")
    if plan["schema"] != SCHEMA:
        raise ValueError("wrong schema version")
    if plan["canvas"] != {"width_mm": SIZE_MM, "height_mm": SIZE_MM}:
        raise ValueError("V1 canvas must be 80x80 mm; change in reviewed code only")
    strokes = plan["strokes"]
    if not isinstance(strokes, list) or not 1 <= len(strokes) <= MAX_STROKES:
        raise ValueError("invalid stroke count")
    names = set()
    total = 0.0
    for stroke in strokes:
        if not isinstance(stroke, dict) or set(stroke) != {"id", "points"}:
            raise ValueError("stroke fields must be id and points only")
        name = stroke["id"]
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", name) or name in names:
            raise ValueError("invalid or duplicate stroke id")
        names.add(name)
        points = stroke["points"]
        if not isinstance(points, list) or not 2 <= len(points) <= MAX_POINTS_PER_STROKE:
            raise ValueError("each stroke needs 2..32 points")
        previous = None
        for xy in points:
            if not isinstance(xy, list) or len(xy) != 2:
                raise ValueError("point must be an [x,y] array")
            if any(type(v) not in (int, float) or not math.isfinite(v) or not MIN_XY <= v <= MAX_XY for v in xy):
                raise ValueError("coordinates must be finite numbers within 0.10..0.90")
            if previous is not None:
                segment = math.dist(previous, xy)
                if segment == 0.0 or segment > MAX_SEGMENT:
                    raise ValueError("zero-length or overly long segment")
                total += segment
            previous = xy
    if total > MAX_TOTAL_LENGTH:
        raise ValueError("total pen-down path too long")
    return total * SIZE_MM


def svg_preview(plan: dict) -> str:
    paths = []
    for stroke in plan["strokes"]:
        coords = stroke["points"]
        commands = [f"M {coords[0][0] * 100:.2f} {coords[0][1] * 100:.2f}"]
        commands.extend(f"L {x * 100:.2f} {y * 100:.2f}" for x, y in coords[1:])
        paths.append('  <path d="' + " ".join(commands) + '" />')
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
        'width="400" height="400">\n'
        '  <rect x="0" y="0" width="100" height="100" fill="white" />\n'
        '  <g fill="none" stroke="#406a3f" stroke-width="1.4" stroke-linecap="round">\n'
        + "\n".join(paths) + "\n  </g>\n</svg>\n"
    )


def self_test() -> None:
    sample = {
        "schema": SCHEMA, "canvas": {"width_mm": 80, "height_mm": 80},
        "strokes": [{"id": "ok", "points": [[0.2, 0.2], [0.5, 0.5]]}],
    }
    assert validate(sample) > 0
    for bad in [
        {**sample, "unexpected": "do this"},
        {**sample, "strokes": [{"id": "bad", "points": [[0.2, 0.2], [1.5, 0.3]]}]},
        {**sample, "strokes": [{"id": "bad", "points": [[0.2, 0.2], [0.2, 0.2]]}]},
    ]:
        try:
            validate(bad)
        except ValueError:
            continue
        raise AssertionError("unsafe plan accepted")
    print("PASS: offline validator accepts sample and rejects invalid cases (NO hardware access)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a drawing plan (offline only)")
    parser.add_argument("--plan", type=Path, default=Path(__file__).with_name("demo_plan.json"))
    parser.add_argument("--svg", type=Path, help="optional SVG output path; no robot connection")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    length_mm = validate(plan)
    print(f"PASS: {len(plan['strokes'])} strokes, {length_mm:.1f} mm pen-down in an 80x80 mm PLAN")
    if args.svg:
        args.svg.parent.mkdir(parents=True, exist_ok=True)
        args.svg.write_text(svg_preview(plan), encoding="utf-8")
        print(f"Saved preview: {args.svg} (software-only, NOT proof of robot reachability)")


if __name__ == "__main__":
    main()
