#!/usr/bin/env python3
"""Export Remotion captions and render manifest after the video has rendered."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
ENG=ROOT/"video/remotion/props"

def tc(t:float)->str:
    n=round(t*1000)
    h,n=divmod(n,3600000)
    m,n=divmod(n,60000)
    s,ms=divmod(n,1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def build(composition:str, mp4:Path):
    data=json.loads((ENG/(composition+".json")).read_text(encoding="utf-8"))
    assert mp4.is_file(),f"missing rendered video {mp4}"
    # Remotion uses nearest integer frame duration per scene (no overlaps).
    frames=0
    captions=[]
    timeline=[]
    for i,s in enumerate(data["scenes"],1):
        start=frames/data["fps"]
        frames+=round(s["seconds"]*data["fps"])
        end=frames/data["fps"]
        captions.append(f"{i}\n{tc(start)} --> {tc(end)}\n{s['narration']}\n")
        timeline.append({"id":s["id"],"start_s":start,"end_s":end,"action_ref":s["action_ref"],
                         "evidence_ref":s["evidence_ref"],"visual":s.get("image_src") or ("diagram:"+s.get("diagram",""))})
    probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration:stream=width,height,codec_name","-of","json",str(mp4)],
                         check=True,capture_output=True,text=True)
    info=json.loads(probe.stdout)
    duration=float(info["format"]["duration"])
    assert abs(duration-frames/data["fps"])<0.3, f"rendered duration {duration} differs from timeline {frames/data['fps']}"
    subs=mp4.with_suffix(".srt")
    subs.write_text("\n".join(captions)+"\n",encoding="utf-8")
    manifest={"composition":composition,"project":data["project"],"evidence_kind":data["kind"],"disclosure":data["disclosure"],
              "source_page":data["source_page"],"duration_s":duration,"fps":data["fps"],
              "video_sha256":hashlib.sha256(mp4.read_bytes()).hexdigest(),"frames":timeline}
    target=mp4.with_suffix(".manifest.json")
    target.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"video":str(mp4),"duration":duration,"srt":str(subs),"manifest":str(target),"sha256":manifest["video_sha256"]},ensure_ascii=False))
    return manifest

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("composition",choices=["ChristmasTentG0","HachimoPrepurchase"])
    p.add_argument("video",type=Path)
    args=p.parse_args()
    build(args.composition,args.video)
