#!/usr/bin/env python3
"""亲子教学随身记录器｜录制链路软件验证（电脑环境，非设备实测）。

在本地电脑上验证「输入 → 录制/编码 → 分段 → 停止 → 回放」最小链路：
- 输入用合成信号（testsrc2 1080p30 + 440Hz 正弦），不代表真实摄像头画质；
- 编码用 Apple VideoToolbox 硬件 H.264（对应低功耗嵌入式方案的可行性量级）；
- 分段用 segment muxer（默认 60s 一段），正常停止发 SIGINT（等效按停止键）；
- 崩溃测试用 kill -9（等效软件进程崩溃），验证各分段文件是否仍可完整解码回放。

边界声明：
- 这是「电脑环境的软件验证」：只证明编码/分段/停止/崩溃恢复策略本身可用；
- 不等效于目标设备断电、拔电池、SD 卡写满等实机行为，那些属于目标设备实测。

用法：
  python3 recording_chain_test.py normal  --minutes 30            # 正常停止全链路
  python3 recording_chain_test.py crash   --format mp4|mpegts     # 进程崩溃恢复
  python3 recording_chain_test.py negative-test                   # 损坏分段门禁负向测试
  python3 recording_chain_test.py probe-camera                    # 摄像头设备探测（不保证可采集）

验收门禁（classify_segments）：无法探测（如 moov 缺失）、无法完整解码或缺失的
分段一律判失败；成功探测且确实不足 1 秒的正常尾段单独豁免记录（waived_short_segments），
不得因缺 duration 被静默过滤。

输出：stdout 一份 JSON 结果；媒体文件写到 /tmp/recorder-test/（不进 Git 仓库）。
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

OUT_ROOT = Path("/tmp/recorder-test")
WIDTH, HEIGHT, FPS = 1920, 1080, 30
VIDEO_BITRATE = "8M"  # 1080p30 H.264 常规码率档（估算载体，可调基线参数）
AUDIO_BITRATE = "128k"
CPU_SAMPLES = []


def ffmpeg_cmd(out_dir: Path, fmt: str) -> list[str]:
    """合成输入 1080p30 + 音频 → 硬件编码 → 60s 分段。"""
    ext = "mp4" if fmt == "mp4" else "ts"
    return [
        "ffmpeg", "-hide_banner", "-loglevel", "warning",
        # -re 让合成输入按真实时间出帧，等效实时录制压力
        "-re", "-f", "lavfi", "-i", f"testsrc2=size={WIDTH}x{HEIGHT}:rate={FPS}",
        "-re", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
        "-c:v", "h264_videotoolbox", "-b:v", VIDEO_BITRATE, "-pix_fmt", "yuv420p",
        # 每 60s 强制关键帧，保证分段在整分钟切开
        "-force_key_frames", "expr:gte(t,n_forced*60)",
        "-c:a", "aac", "-b:a", AUDIO_BITRATE,
        "-f", "segment", "-segment_time", "60", "-segment_format", fmt,
        "-reset_timestamps", "1",
        str(out_dir / f"seg_%03d.{ext}"),
    ]


def sample_cpu(pid: int) -> None:
    try:
        r = subprocess.run(["ps", "-p", str(pid), "-o", "pcpu="],
                           capture_output=True, text=True, timeout=5)
        CPU_SAMPLES.append(float(r.stdout.strip()))
    except (ValueError, subprocess.SubprocessError):
        pass


def probe_file(path: Path) -> dict:
    """单文件探测与全量解码：playable 只反映「可探测+可完整解码」，
    时长门禁在 classify_segments 里做（不足 1 秒的正常尾段单独豁免记录）。"""
    info: dict = {"file": path.name, "size_bytes": path.stat().st_size if path.exists() else 0}
    if not path.exists():
        info.update({"exists": False, "probe_ok": False, "playable": False,
                     "error": "segment missing"})
        return info
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format",
         "-show_streams", str(path)],
        capture_output=True, text=True)
    if r.returncode != 0:
        first = next((l for l in r.stderr.splitlines() if l.strip()), "unknown error")
        info.update({"exists": True, "probe_ok": False, "playable": False,
                     "error": first.strip()})
        return info
    meta = json.loads(r.stdout)
    fmt_d = meta.get("format", {})
    dur = float(fmt_d.get("duration") or 0)
    vstream = next((s for s in meta.get("streams", []) if s.get("codec_type") == "video"), {})
    d = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
        capture_output=True, text=True)
    errs = [l for l in d.stderr.splitlines() if l.strip()]
    probe_ok = True
    decode_ok = d.returncode == 0 and not errs
    info.update({
        "exists": True, "probe_ok": probe_ok,
        "duration_s": round(dur, 2),
        "codec": vstream.get("codec_name"),
        "decode_ok": decode_ok,
        "decode_errors": errs[:5],
        "playable": probe_ok and decode_ok,
    })
    return info


def classify_segments(files: list[dict]) -> dict:
    """验收门禁：无法探测 / 无法解码 / 缺失的片段一律失败；
    成功探测且确实不足 1 秒的正常尾段单独豁免记录（不计失败也不计通过）。"""
    passed, waived, failed = [], [], []
    for f in files:
        if not f.get("probe_ok") or not f.get("decode_ok") or not f.get("exists"):
            failed.append(f)
        elif f.get("duration_s", 0) < 1.0:
            waived.append(f)
        else:
            passed.append(f)
    return {"passed": passed, "waived_short": waived, "failed": failed}


def run_segmented(out_dir: Path, fmt: str, stop: str, seconds: int) -> tuple[int, int]:
    """跑一段录制；stop='sigint' 正常停止，'kill' 崩溃模拟。返回 (pid, 实际秒数)。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("seg_*"):
        old.unlink()
    proc = subprocess.Popen(ffmpeg_cmd(out_dir, fmt),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    while time.time() - t0 < seconds:
        time.sleep(min(30, max(1, seconds - (time.time() - t0))))
        sample_cpu(proc.pid)
    if stop == "sigint":
        proc.send_signal(signal.SIGINT)  # 等效用户按「停止」：写尾、收尾当前分段
    else:
        proc.kill()  # 等效软件进程崩溃：无收尾机会
    proc.wait(timeout=30)
    return proc.pid, int(time.time() - t0)


def report_normal(minutes: int) -> dict:
    out_dir = OUT_ROOT / "normal-mp4"
    pid, wall = run_segmented(out_dir, "mp4", "sigint", minutes * 60)
    segs = sorted(out_dir.glob("seg_*.mp4"))
    files = [probe_file(p) for p in segs]
    verdict = classify_segments(files)
    total = sum(f["size_bytes"] for f in files)
    content_s = sum(f.get("duration_s") or 0 for f in files)
    # 门禁：任何无法探测/无法解码的片段都失败；不足 1 秒的正常尾段单独豁免记录；
    # 另要求内容时长覆盖墙钟 ≥98%。
    all_playable = bool(files) and not verdict["failed"] \
        and wall > 0 and content_s / wall >= 0.98
    return {
        "test": "normal-stop",
        "label": "电脑环境的软件验证（合成输入；非目标设备实测）",
        "cmd": " ".join(ffmpeg_cmd(out_dir, "mp4")),
        "params": {"resolution": f"{WIDTH}x{HEIGHT}", "fps": FPS,
                   "video_bitrate": VIDEO_BITRATE, "audio_bitrate": AUDIO_BITRATE,
                   "segment_time_s": 60, "minutes": minutes},
        "pid": pid, "wall_seconds": wall,
        "segments": files,
        "segment_count": len(segs),
        "content_seconds": round(content_s, 2),
        "content_coverage_percent": round(100 * content_s / wall, 1) if wall else None,
        "passed_segments": [f["file"] for f in verdict["passed"]],
        "waived_short_segments": [
            {"file": f["file"], "duration_s": f.get("duration_s")}
            for f in verdict["waived_short"]],
        "failed_segments": [
            {"file": f["file"], "error": f.get("error") or (f.get("decode_errors") or ["decode"])[0]}
            for f in verdict["failed"]],
        "all_playable": all_playable,
        "total_bytes": total,
        "avg_bitrate_mbps": round(total * 8 / wall / 1e6, 2) if wall else None,
        "storage_gb_per_30min": round(total * (1800 / wall) / 1e9, 2) if wall else None,
        "avg_cpu_percent": round(sum(CPU_SAMPLES) / len(CPU_SAMPLES), 1) if CPU_SAMPLES else None,
    }


def report_crash(fmt: str, seconds: int = 150) -> dict:
    out_dir = OUT_ROOT / f"crash-{fmt}"
    pid, wall = run_segmented(out_dir, fmt, "kill", seconds)
    segs = sorted(out_dir.glob("seg_*"))
    files = [probe_file(p) for p in segs]
    verdict = classify_segments(files)
    usable = sum(1 for f in files if f.get("playable"))
    completed = files[:-1]
    return {
        "test": f"crash-kill9-{fmt}",
        "label": "进程崩溃（kill -9）≠ 设备断电；目标设备断电仍属目标设备实测",
        "cmd": " ".join(ffmpeg_cmd(out_dir, fmt)),
        "params": {"container": fmt, "segment_time_s": 60, "crash_at_s": seconds,
                   "signal": "SIGKILL"},
        "pid": pid, "wall_seconds": wall,
        "segments": files,
        "segment_count": len(segs),
        "usable_segments_after_crash": usable,
        "failed_segments": [
            {"file": f["file"], "error": f.get("error") or (f.get("decode_errors") or ["decode"])[0]}
            for f in verdict["failed"]],
        "all_completed_segments_usable": bool(completed) and all(
            f.get("playable") for f in completed),
        "last_segment_verdict": ("usable" if files and files[-1].get("playable")
                                 else (files[-1].get("error", "unusable") if files else "none")),
    }


def report_revalidate(out_dir: Path, wall_seconds: int, minutes: int) -> dict:
    """对已录制的分段媒体重新执行「探测+全量解码+门禁分类」。
    用于录制完成后仅报告层出错的补救：媒体与门禁结果与完整重跑等价
    （探测/解码是确定性操作），JSON 中显式标注 revalidated 标记。"""
    segs = sorted(out_dir.glob("seg_*.mp4"))
    files = [probe_file(p) for p in segs]
    verdict = classify_segments(files)
    total = sum(f["size_bytes"] for f in files)
    content_s = sum(f.get("duration_s") or 0 for f in files)
    all_playable = bool(files) and not verdict["failed"] \
        and wall_seconds > 0 and content_s / wall_seconds >= 0.98
    return {
        "test": "normal-stop",
        "label": "电脑环境的软件验证（合成输入；非目标设备实测）",
        "mode": "revalidate-existing-media",
        "revalidate_note": "录制已完成（SIGINT 停止）；本 JSON 为对既有分段媒体"
                          "重新探测+解码+门禁分类的结果，未重新录制",
        "cmd": " ".join(ffmpeg_cmd(out_dir, "mp4")),
        "params": {"resolution": f"{WIDTH}x{HEIGHT}", "fps": FPS,
                   "video_bitrate": VIDEO_BITRATE, "audio_bitrate": AUDIO_BITRATE,
                   "segment_time_s": 60, "minutes": minutes},
        "wall_seconds": wall_seconds,
        "segments": files,
        "segment_count": len(segs),
        "content_seconds": round(content_s, 2),
        "content_coverage_percent": round(100 * content_s / wall_seconds, 1)
        if wall_seconds else None,
        "passed_segments": [f["file"] for f in verdict["passed"]],
        "waived_short_segments": [
            {"file": f["file"], "duration_s": f.get("duration_s")}
            for f in verdict["waived_short"]],
        "failed_segments": [
            {"file": f["file"],
             "error": f.get("error") or (f.get("decode_errors") or ["decode"])[0]}
            for f in verdict["failed"]],
        "all_playable": all_playable,
        "total_bytes": total,
        "avg_bitrate_mbps": round(total * 8 / wall_seconds / 1e6, 2)
        if wall_seconds else None,
        "storage_gb_per_30min": round(total * (1800 / wall_seconds) / 1e9, 2)
        if wall_seconds else None,
    }


def negative_test() -> dict:
    """负向测试：故意截断一个正常分段，门禁必须判失败（防止误通过）。"""
    d = OUT_ROOT / "negative"
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("seg_*"):
        old.unlink()
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", f"testsrc2=size={WIDTH}x{HEIGHT}:rate={FPS}:duration=65",
         "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=65",
         "-c:v", "h264_videotoolbox", "-b:v", VIDEO_BITRATE, "-pix_fmt", "yuv420p",
         "-force_key_frames", "expr:gte(t,n_forced*60)",
         "-c:a", "aac", "-b:a", AUDIO_BITRATE,
         "-f", "segment", "-segment_time", "60", "-segment_format", "mp4",
         "-reset_timestamps", "1", str(d / "seg_%03d.mp4")],
        capture_output=True, timeout=300, check=True)
    segs = sorted(d.glob("seg_*.mp4"))
    target = segs[1] if len(segs) > 1 else segs[0]
    orig_size = target.stat().st_size
    raw = bytearray(target.read_bytes())
    with target.open("wb") as fh:  # 截断至 40%：moov（位于尾部）丢失
        fh.write(raw[: int(orig_size * 0.4)])
    files = [probe_file(p) for p in segs]
    verdict = classify_segments(files)
    gate_failed = bool(verdict["failed"]) and any(
        f["file"] == target.name for f in verdict["failed"])
    return {
        "test": "negative-corrupted-segment",
        "label": "负向测试：截断损坏的分段必须导致验收失败，不允许被静默过滤",
        "corrupted_file": target.name,
        "original_bytes": orig_size,
        "kept_bytes": int(orig_size * 0.4),
        "segments": files,
        "failed_segments": [
            {"file": f["file"], "error": f.get("error") or (f.get("decode_errors") or ["decode"])[0]}
            for f in verdict["failed"]],
        "gate_failed_as_expected": gate_failed,
        "gate_ok": gate_failed,
    }


def report_camera_probe(attempt: bool) -> dict:
    """列出 avfoundation 设备（无需授权）；可选尝试 2s 采集（需系统授权，失败即记录）。"""
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "info",
         "-f", "avfoundation", "-list_devices", "true", "-i", ""],
        capture_output=True, text=True, timeout=30)
    devices = []
    for line in r.stderr.splitlines():
        if "[" in line and "]" in line and ("video" in line.lower() or "audio" in line.lower()):
            devices.append(line.split("]", 1)[-1].strip())
    out: dict = {"test": "camera-probe", "label": "探测本机摄像头；采集授权属用户系统设置",
                 "devices": devices}
    if not attempt:
        out["capture_attempted"] = False
        return out
    cap = OUT_ROOT / "camera-probe"
    cap.mkdir(parents=True, exist_ok=True)
    target = cap / "probe.mp4"
    proc = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "warning",
         "-f", "avfoundation", "-framerate", "30", "-video_device", "0",
         "-audio_device", "none", "-i", "default", "-frames:v", "30",
         "-c:v", "h264_videotoolbox", "-y", str(target)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        proc.wait(timeout=10)
        got = target.exists() and target.stat().st_size > 1000
        out.update({"capture_attempted": True, "capture_ok": bool(got)})
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        out.update({"capture_attempted": True, "capture_ok": False,
                    "note": "10s 内未完成：通常为 macOS 未授予终端摄像头权限（TCC），采集路径本轮不可用"})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="mode", required=True)
    p_norm = sub.add_parser("normal")
    p_norm.add_argument("--minutes", type=int, default=30)
    p_crash = sub.add_parser("crash")
    p_crash.add_argument("--format", choices=["mp4", "mpegts"], default="mp4")
    p_crash.add_argument("--seconds", type=int, default=150)
    p_probe = sub.add_parser("probe-camera")
    p_probe.add_argument("--attempt", action="store_true",
                         help="除列设备外，尝试真实采集 1s（需要系统授权）")
    sub.add_parser("negative-test")
    p_rev = sub.add_parser("revalidate")
    p_rev.add_argument("--dir", required=True, help="已录制分段所在目录")
    p_rev.add_argument("--wall-seconds", type=int, required=True)
    p_rev.add_argument("--minutes", type=int, default=30)
    args = ap.parse_args()
    if args.mode == "normal":
        result = report_normal(args.minutes)
    elif args.mode == "crash":
        result = report_crash(args.format, args.seconds)
    elif args.mode == "negative-test":
        result = negative_test()
    elif args.mode == "revalidate":
        result = report_revalidate(Path(args.dir), args.wall_seconds, args.minutes)
    else:
        result = report_camera_probe(args.attempt)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
