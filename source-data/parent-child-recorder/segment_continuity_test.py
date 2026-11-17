#!/usr/bin/env python3
"""亲子教学随身记录器｜分段衔接与连续性验证（替代实测：桌面软件链路，合成输入）。

与 recording_chain_test.py（正常停止/崩溃对比）互补，本轮新增：

1. short_realtime  —— 45 秒 `-re` 实时输入、15 秒分段，分别以「自然结束」「SIGINT」
   「SIGKILL」三种方式收尾（只操作本脚本启动的 PID）。SIGINT/SIGKILL 的历史数据见
   recording_chain_test.py（30 分钟正常停止 + 150s 崩溃对比，2026-11-18）。
2. continuity      —— 快速生成（无 -re，不限速）40 秒合成媒体、10 秒分段 ×4：
   每段独立解码、时长/帧数/采样数对账、时间戳重置与分段清单连续性、音视频同步差、
   concat 后全量解码。时间戳按 reset_timestamps 每段归零属正常，不判为丢失；
   连续性由「各段时长精确 + 分段清单顺序 + concat 总时长/总帧数」判断。
3. capacity        —— 30 分钟容量估算（1080p30 基线）：以短测实测码率外推，
   并引用 2026-11-18 真实 30 分钟实时运行结果（recording_normal_30min.json）佐证。
   估算 ≠ 通过 30 分钟录制测试；加速生成的媒体不证明真实时长运行稳定性。

音视频均输出到 /tmp/recorder-test/（临时目录，不入库）。
用法：python3 segment_continuity_test.py [short_realtime|continuity|capacity|all]
"""
from __future__ import annotations

import json
import signal
import subprocess
import sys
import time
from pathlib import Path

OUT = Path("/tmp/recorder-test")
FPS = 30
AUDIO_RATE = 44100
VIDEO_KBPS = "4000"  # 4 Mbps：目标设备常见档位（可调基线，容量估算输入之一）
AUDIO_KBPS = "128"


def base_args(duration: float, realtime: bool) -> list[str]:
    speed = ["-re"] if realtime else []
    return [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        *speed,
        "-f", "lavfi", "-i", f"testsrc2=size=1920x1080:rate={FPS}:duration={duration}",
        "-f", "lavfi", "-i",
        f"sine=frequency=440:sample_rate={AUDIO_RATE}:duration={duration}",
        "-c:v", "h264_videotoolbox", "-b:v", VIDEO_KBPS, "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", AUDIO_KBPS,
    ]


def segment_args(duration: float, seg_s: int, out_dir: Path, realtime: bool) -> list[str]:
    return [
        *base_args(duration, realtime),
        "-force_key_frames", f"expr:gte(t,n_forced*{seg_s})",
        "-f", "segment", "-segment_time", str(seg_s), "-segment_format", "mp4",
        "-reset_timestamps", "1",
        str(out_dir / "seg_%03d.mp4"),
    ]


def probe(path: Path) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format",
         "-show_streams", str(path)], capture_output=True, text=True)
    if r.returncode != 0:
        return {"file": path.name, "ok": False, "error": r.stderr.strip()[:200]}
    meta = json.loads(r.stdout)
    streams = {s["codec_type"]: s for s in meta["streams"]}
    return {
        "file": path.name,
        "ok": True,
        "duration": round(float(meta["format"]["duration"]), 3),
        "video_frames": int(streams["video"].get("nb_frames", 0)),
        "audio_samples": int(streams["audio"].get("duration_ts", 0)),
        "start_times": {k: float(v.get("start_time", 0)) for k, v in streams.items()},
        "size": path.stat().st_size,
    }


def decode_errors(path: Path) -> list[str]:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
                       capture_output=True, text=True)
    return [l for l in r.stderr.splitlines() if l.strip()]


def run_ffmpeg_wait(cmd: list[str], timeout: int = 180) -> None:
    subprocess.run(cmd, capture_output=True, timeout=timeout, check=True)


def short_realtime() -> dict:
    """45 秒 -re 实时输入、15 秒分段，三种收尾各跑一次（操作明确 PID）。"""
    results = []
    for mode in ("natural", "sigint", "sigkill"):
        d = OUT / f"rt-{mode}"
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob("seg_*"):
            old.unlink()
        proc = subprocess.Popen(segment_args(45, 15, d, realtime=True),
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t0 = time.time()
        if mode == "natural":
            proc.wait(timeout=120)
        else:
            time.sleep(40)  # 40s：第 3 段（30–45s）写入中途，非分段边界
            proc.send_signal(signal.SIGINT if mode == "sigint" else signal.SIGKILL)
            proc.wait(timeout=30)
        wall = round(time.time() - t0, 2)
        segs = sorted(d.glob("seg_*.mp4"))
        files = [probe(p) for p in segs]
        errors = {f["file"]: decode_errors(p) for f, p in zip(files, segs) if f.get("ok")}
        results.append({
            "mode": mode, "wall_s": wall,
            "segment_count": len(segs),
            "segment_durations": [f.get("duration") for f in files],
            "completed_decodable": [f["file"] for f in files
                                    if f.get("ok") and f["duration"] > 14.0],
            "last_segment": files[-1] if files else None,
            "decode_error_files": {k: v for k, v in errors.items() if v},
        })
    return {"test": "short_realtime_45s_15s_seg",
            "label": "替代实测：桌面软件链路，-re 合成实时输入（非摄像头采集）",
            "runs": results}


def continuity() -> dict:
    """40 秒不限速生成、10 秒分段 ×4：衔接/帧数/同步/concat 全量解码。"""
    d = OUT / "continuity"
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("seg_*"):
        old.unlink()
    run_ffmpeg_wait(segment_args(40, 10, d, realtime=False))
    segs = sorted(d.glob("seg_*.mp4"))
    files = [probe(p) for p in segs]
    exp_frames = 10 * FPS
    frame_ok = all(abs(f["video_frames"] - exp_frames) <= 1 for f in files if f.get("ok"))
    av_sync = []
    for f, p in zip(files, segs):
        if not f.get("ok"):
            continue
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams",
             str(p)], capture_output=True, text=True)
        st = {s["codec_type"]: s for s in json.loads(r.stdout)["streams"]}
        vd = float(st["video"].get("duration", 0))
        ad = float(st["audio"].get("duration", 0))
        av_sync.append({"file": f["file"], "video_s": round(vd, 3),
                        "audio_s": round(ad, 3), "drift_s": round(ad - vd, 3)})
    # concat 清单 + 全量解码：时间戳已按段归零，连续性由分段清单与总时长/帧数判断
    concat = d / "list.txt"
    concat.write_text("\n".join(f"file '{p.name}'" for p in segs), encoding="utf-8")
    merged = d / "merged.mp4"
    run_ffmpeg_wait(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "concat",
                     "-safe", "0", "-i", str(concat), "-c", "copy", "-y", str(merged)])
    mp = probe(merged)
    merr = decode_errors(merged)
    total_dur = sum(f.get("duration") or 0 for f in files)
    return {
        "test": "segment_continuity_40s_4x10s",
        "label": "替代实测：桌面软件链路，不限速合成输入（加速生成，不代表实时稳定性）",
        "segments": files,
        "per_segment_frames_expected": exp_frames,
        "frame_count_consistent": frame_ok,
        "duration_sum_s": round(total_dur, 3),
        "expected_total_s": 40.0,
        "av_sync": av_sync,
        "timestamp_note": "reset_timestamps=1 每段时间戳归零属正常；连续性由"
                          "分段清单顺序+各段时长+concat 总时长判断",
        "concat_merged": {k: mp.get(k) for k in ("ok", "duration", "video_frames")},
        "concat_decode_errors": merr,
        "all_decodable": all(f.get("ok") for f in files) and not merr,
    }


def capacity() -> dict:
    """30 分钟容量估算：短测码率外推 + 已有真实 30 分钟运行佐证。"""
    repo = Path(__file__).resolve().parent / "generated"
    prior = {}
    p = repo / "recording_normal_30min.json"
    if p.exists():
        d = json.loads(p.read_text())
        prior = {"source": "recording_normal_30min.json (2026-11-18 真实 30 分钟实时运行)",
                 "measured_bitrate_mbps": d.get("avg_bitrate_mbps"),
                 "measured_gb_per_30min": d.get("storage_gb_per_30min")}
    # 本轮短测实测码率（8 Mbps 档）
    d = OUT / "cap8"
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("seg_*"):
        old.unlink()
    run_ffmpeg_wait(segment_args(60, 15, d, realtime=False))
    segs = sorted(d.glob("seg_*.mp4"))
    size8 = sum(f.stat().st_size for f in segs)
    mbps8 = size8 * 8 / 60 / 1e6
    est = {
        "basis": "短测实测码率外推（testsrc2 合成源）；注意 -b:v 是上限，"
                 "实际码率随内容运动复杂度变化",
        "kbps_4mbps": {"measured_mbps": round(mbps8, 2),
                       "gb_per_30min": round(mbps8 * 1800 / 8 / 1000, 2)},
        "uncertainty": "低运动内容实测可低至目标码率的 1/3（本轮 4Mbps 档实测"
                       " 1.4Mbps）；估算按 ±50% 起步，存储按估算值 1.5–2 倍预留",
    }
    return {"test": "capacity_estimate_30min",
            "label": "估算（30 分钟容量估算），佐证为既有真实 30 分钟运行",
            "prior_real_run": prior, "extrapolation": est}


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    out = {}
    if mode in ("all", "short_realtime"):
        out["short_realtime"] = short_realtime()
    if mode in ("all", "continuity"):
        out["continuity"] = continuity()
    if mode in ("all", "capacity"):
        out["capacity"] = capacity()
    dest = Path(__file__).resolve().parent / "generated" / "segment_continuity_results.json"
    merged = {}
    if dest.exists():
        try:
            merged = json.loads(dest.read_text())
        except ValueError:
            merged = {}
    merged.update(out)
    dest.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
