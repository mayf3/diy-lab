#!/usr/bin/env python3
"""Render a transparent-evidence DIY tutorial sample from an authored storyboard.

Optional maker dependency: Pillow + FFmpeg. Not needed to build the website.
This renders existing, authorized project simulation images; it does not invent
physical tests or claim that an AI has verified real hardware.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWED_KINDS = {"digital-simulation", "real-screen-recording", "physical-observation"}
DEFAULT_STORYBOARD = ROOT / "source-data/christmas-magic-tent/video/g0-storyboard.json"


def load_and_check(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1", "unknown storyboard version"
    assert data["kind"] in ALLOWED_KINDS, "unknown evidence kind"
    assert data["width"] >= 640 and data["height"] >= 360, "video too small"
    assert 12 <= data["fps"] <= 60, "fps outside supported range"
    assert 0 <= data["transition_seconds"] <= 1, "invalid crossfade"
    assert data["scenes"], "no scenes"
    assert "不是实物" in data["display_notice"] or data["kind"] != "digital-simulation", "simulation must be clearly marked"
    assert data["source_page"].startswith("/projects/"), "must link to corresponding tutorial"
    seen = set()
    for scene in data["scenes"]:
        assert scene["id"] not in seen, "duplicate scene id"
        seen.add(scene["id"])
        assert 3 <= scene["seconds"] <= 25, "each scene must be readable"
        assert scene["title"] and scene["narration"] and scene["evidence"], "incomplete scene"
        assert scene.get("action_ref"), "scene must point to one DIY action"
        assert 1 <= len(scene["bullets"]) <= 4, "too many or no bullets"
        evidence_rel = Path(scene.get("evidence_ref", ""))
        assert evidence_rel.parts and not evidence_rel.is_absolute() and ".." not in evidence_rel.parts, "unsafe evidence path"
        evidence_path = (ROOT / evidence_rel).resolve()
        assert evidence_path.is_relative_to(ROOT.resolve()) and evidence_path.is_file(), "missing supporting evidence file"
        image_rel = Path(scene["visual"])
        assert not image_rel.is_absolute() and ".." not in image_rel.parts, "unsafe image path"
        image_path = (ROOT / image_rel).resolve()
        assert image_path.is_relative_to((ROOT / "public/media").resolve()), "only use project-owned public media"
        assert image_path.is_file(), f"missing image: {image_rel}"
    return data


def find_font(explicit: str | None):
    from PIL import ImageFont

    paths = [
        explicit,
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ]
    for p in paths:
        if p and Path(p).is_file():
            return lambda size: ImageFont.truetype(p, size)
    raise RuntimeError("Chinese font missing; install Noto Sans CJK or specify --font-file")


def wrap(text, font, max_width, drawer):
    """Wrap CJK captions based on actual glyph widths, without splitting bytes."""
    lines = []
    cur = ""
    for c in str(text):
        trial = cur + c
        if cur and drawer.textbbox((0, 0), trial, font=font)[2] > max_width:
            lines.append(cur)
            cur = c
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def text_lines(drawer, xy, text, font, color, width, leading=1.35, limit=7):
    x, y = xy
    lines = wrap(text, font, width, drawer)
    if len(lines) > limit:
        raise ValueError(f"too much text for slide: {text}")
    for line in lines:
        drawer.text((x, y), line, font=font, fill=color, stroke_width=0)
        y += int(font.size * leading)
    return y


def image_fit(im, size):
    from PIL import Image, ImageOps
    # Contain rather than crop: the Blender annotations contain measurements.
    small = ImageOps.contain(im.convert("RGB"), size, method=Image.Resampling.LANCZOS)
    bg = Image.new("RGB", size, (227, 231, 232))
    bg.paste(small, ((size[0] - small.width) // 2, (size[1] - small.height) // 2))
    return bg


def make_frame(data, scene, idx, font):
    from PIL import Image, ImageDraw

    w, h = data["width"], data["height"]
    bg = (14, 23, 34)
    offwhite = (244, 247, 248)
    muted = (172, 185, 195)
    accent = (106, 222, 188)
    gold = (247, 189, 104)

    page = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(page)
    pict = Image.open(ROOT / scene["visual"]).convert("RGB")

    if idx == 0:
        # Cover: distinct, readable hook, not an invented real-world image.
        cover = image_fit(pict, (w, h))
        page.paste(cover, (0, 0))
        page = Image.blend(page, Image.new("RGB", page.size, (8, 22, 28)), 0.66)
        d = ImageDraw.Draw(page)
        d.rounded_rectangle((65, 76, 505, 127), radius=23, fill=(17, 78, 72))
        d.text((89, 82), "MAKER LAB  /  数字模拟", font=font(24), fill=accent)
        title_lines = wrap(scene["title"], font(61), 990, d)
        if len(title_lines) > 3:
            raise ValueError("cover title too long")
        y = 215
        for line in title_lines:
            d.text((75, y), line, font=font(61), fill=offwhite, stroke_width=0)
            y += 86
        d.text((80, 530), "从真实的 Blender G0 模型与检查结果开始", font=font(27), fill=offwhite)
        d.text((80, 591), data["display_notice"], font=font(23), fill=(249, 204, 129))
    else:
        d.rounded_rectangle((45, 31, 430, 74), radius=20, fill=(28, 66, 68))
        d.text((64, 35), "MAKER LAB  ·  TUTORIAL", font=font(21), fill=accent)
        d.text((1030, 37), f"{idx + 1:02d} / {len(data['scenes']):02d}", font=font(25), fill=muted)
        d.text((46, 92), scene["title"], font=font(45), fill=offwhite)
        d.rounded_rectangle((45, 209, 810, 642), radius=22, fill=(234, 237, 238))
        im = image_fit(pict, (738, 405))
        page.paste(im, (58, 223))
        d = ImageDraw.Draw(page)
        d.rounded_rectangle((59, 580, 370, 617), radius=15, fill=(17, 29, 41))
        d.text((74, 583), "G0 数字模拟图 · 非实物", font=font(18), fill=gold)
        d.rounded_rectangle((835, 209, 1235, 642), radius=22, fill=(27, 41, 54))
        d.text((864, 241), scene["label"], font=font(23), fill=accent)
        y = 304
        for bullet in scene["bullets"]:
            d.rounded_rectangle((867, y + 11, 877, y + 22), radius=4, fill=accent)
            y = text_lines(d, (890, y), bullet, font(27), offwhite, 315, leading=1.23, limit=3) + 31
        if y > 645:
            raise ValueError(f"scene {scene['id']} bullets exceed card; simplify text")
        d.text((50, 654), f"依据：{scene['evidence']}", font=font(18), fill=muted)
        d.text((785, 654), "查看完整教程：Maker Lab / 圣诞帐篷 / G0", font=font(18), fill=muted)

    # Progress indicator shows the scene sequence, not physical test completion.
    d = ImageDraw.Draw(page)
    d.rounded_rectangle((44, 693, 1236, 701), radius=4, fill=(56, 76, 85))
    length = max(8, int((idx + 1) / len(data["scenes"]) * 1192))
    d.rounded_rectangle((44, 693, 44 + length, 701), radius=4, fill=accent)
    return page


def fmt_srt(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    hours, remain = divmod(ms, 3600000)
    minutes, remain = divmod(remain, 60000)
    secs, millis = divmod(remain, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(data: dict, path: Path) -> list[dict]:
    records = []
    start = 0.0
    fade = data["transition_seconds"]
    with path.open("w", encoding="utf-8") as f:
        for n, scene in enumerate(data["scenes"], 1):
            end = start + float(scene["seconds"]) - (fade if n < len(data["scenes"]) else 0)
            f.write(f"{n}\n{fmt_srt(start)} --> {fmt_srt(end)}\n{scene['narration']}\n\n")
            records.append({"id": scene["id"], "start_s": round(start, 2), "end_s": round(end, 2),
                            "action_ref": scene["action_ref"], "evidence_ref": scene["evidence_ref"],
                            "image": scene["visual"], "evidence": scene["evidence"]})
            start = end
    return records


def render(data, output: Path, cover: Path, font_file: str | None) -> None:
    from PIL import Image
    fonts = find_font(font_file)
    work = output.parent / (output.stem + "-work")
    work.mkdir(parents=True, exist_ok=True)
    inputs = []
    for idx, scene in enumerate(data["scenes"]):
        frame = make_frame(data, scene, idx, fonts)
        filename = work / f"slide-{idx+1:02d}.jpg"
        frame.save(filename, "JPEG", quality=90, optimize=True)
        inputs.extend(["-loop", "1", "-framerate", str(data["fps"]), "-t",
                       str(scene["seconds"]), "-i", str(filename)])
        if idx == 0:
            cover.parent.mkdir(parents=True, exist_ok=True)
            frame.save(cover, "WEBP", quality=82, method=6)
    filter_parts = [f"[{i}:v]settb=AVTB,fps={data['fps']},format=yuv420p[v{i}]"
                    for i in range(len(data["scenes"]))]
    fade = float(data["transition_seconds"])
    offset = 0.0
    current = "v0"
    for i in range(1, len(data["scenes"])):
        offset += float(data["scenes"][i-1]["seconds"]) - fade
        nxt = f"f{i}" if i < len(data["scenes"]) - 1 else "out"
        filter_parts.append(f"[{current}][v{i}]xfade=transition=fade:duration={fade}:offset={offset:.3f}[{nxt}]")
        current = nxt
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to render MP4; please install it separately")
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", *inputs,
           "-filter_complex", ";".join(filter_parts),
           "-map", f"[{current}]", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)]
    print(f"Rendering {len(data['scenes'])} scenes to {output}", flush=True)
    subprocess.run(cmd, check=True)
    subtitle = output.with_suffix(".srt")
    records = write_srt(data, subtitle)
    metadata = {
        "video_id": data["video_id"], "project": data["project"],
        "evidence_kind": data["kind"], "notice": data["display_notice"],
        "source_page": data["source_page"], "fps": data["fps"],
        "width": data["width"], "height": data["height"],
        "subtitle": subtitle.name, "frames": records,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }
    output.with_suffix(".manifest.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {output} ({output.stat().st_size/1024/1024:.1f} MiB); cover: {cover}; captions: {subtitle}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storyboard", type=Path, default=DEFAULT_STORYBOARD)
    parser.add_argument("--check", action="store_true", help="only validate sources; no Pillow/FFmpeg required")
    parser.add_argument("--output", type=Path, default=Path("/tmp/makerlab-g0-digital-tutorial.mp4"))
    parser.add_argument("--cover", type=Path, default=ROOT / "public/media/christmas-magic-tent/video/g0-tutorial-cover.webp")
    parser.add_argument("--font-file", type=str, default=None)
    args = parser.parse_args()
    try:
        data = load_and_check(args.storyboard)
        if args.check:
            print(f"Storyboard OK: {len(data['scenes'])} scenes; digital-only attribution checked")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            render(data, args.output, args.cover, args.font_file)
    except (AssertionError, RuntimeError, ValueError, KeyError, FileNotFoundError) as e:
        print("VIDEO QA FAILED:", e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
