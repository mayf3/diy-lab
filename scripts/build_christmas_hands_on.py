#!/usr/bin/env python3
"""Derive the novice animated walkthrough from one versioned maker workflow."""
from __future__ import annotations
import base64
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "source-data/christmas-magic-tent/workflow.json"
TARGET = ROOT / "assets/christmas-steps/course.generated.mjs"
SELECTED = ("A02", "A03", "A04")
EXPECTED_SCENES = {
    "parts", "usb", "ideBoard", "ideUpload", "blink", "unplug",
    "wireGround", "wireButton", "buttonCheck", "ideButton", "buttonTest",
    "idePixels", "pixelParts", "pixelGround", "pixelPower",
    "capacitor", "pixelData", "pixelCheck", "pixelTest"
}


def build() -> str:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    assert source["project"] == "christmas-magic-tent"
    assert len({t["id"] for t in source["tasks"]}) == len(source["tasks"])
    reference_ids = {r["id"] for r in source["references"]}
    lessons = []
    for task in source["tasks"]:
        if task["id"] not in SELECTED:
            continue
        assert task["status"] == "planned", "Do not pass physical tests by default"
        lesson = task["teaching"].copy()
        assert lesson["action_ref"] == task["id"]
        assert lesson["refs"] and set(lesson["refs"]) <= reference_ids
        seen = set()
        for step in lesson["steps"]:
            assert step["id"] not in seen
            seen.add(step["id"])
            assert step["scene"] in EXPECTED_SCENES
            assert 4 <= step["seconds"] <= 30
            for field in ("title", "do", "expected", "stop", "check", "caption"):
                assert step.get(field), f"{task['id']} {step['id']} missing {field}"
        assert lesson["steps"] and lesson["code_files"]
        files = []
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            def write_fixed(name, body):
                zi = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(zi, body)
            for code_path in lesson.pop("code_files"):
                path = (ROOT / "source-data/christmas-magic-tent" / code_path).resolve()
                assert path.is_relative_to(ROOT) and path.is_file(), code_path
                body = path.read_text(encoding="utf-8")
                name = path.name
                folder = path.parent.name if path.parent.name in {"FirstBlink", "ButtonLamp"} else "ChristmasStar"
                arcname = f"{folder}/{name}"
                write_fixed(arcname, body)
                files.append({"name": name, "content": body})
            write_fixed("README-开始之前.txt",
                "本教程只针对 UNO R3。接线前先断开电源。\n"
                "新手先做第1关板载灯，然后第2关两线按钮，最后第3关四灯桌面测试。\n"
                "动画仅为原创示意，并非用户实物验证。发现异常发热/异味立即断电。\n")
        lesson["files"] = files
        lesson["bundle_b64"] = base64.b64encode(archive.getvalue()).decode("ascii")
        lessons.append(lesson)
    assert tuple(x["action_ref"] for x in lessons) == SELECTED
    doc = {
        "version": source["tutorial_version"],
        "notice": source["tutorial_notice"],
        "references": source["references"],
        "lessons": lessons,
    }
    return "// GENERATED; edit source-data/christmas-magic-tent/workflow.json\nexport const COURSE = " + json.dumps(doc, ensure_ascii=False, indent=2) + ";\n"


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build()
    if args.check:
        assert TARGET.is_file() and TARGET.read_text(encoding="utf-8") == expected, "Walkthrough differs from workflow; regenerate"
        print("Christmas hands-on workflow, code packages and 19 scenes: PASS")
    else:
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        TARGET.write_text(expected, encoding="utf-8")
        print("Generated", TARGET.relative_to(ROOT))

if __name__ == "__main__":
    main()
