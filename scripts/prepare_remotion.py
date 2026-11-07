#!/usr/bin/env python3
"""Generate Remotion props from copyright-safe DIY storyboards.

This script intentionally does NOT render video; it ensures the same source
works across the previous FFmpeg demo and Remotion, with provenance safeguards.
"""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "video/remotion"
# One catalog entry per project video; no need to edit React components.
CATALOG = json.loads((ENGINE / "catalog.json").read_text(encoding="utf-8"))
assert len({item["id"] for item in CATALOG}) == len(CATALOG), "Duplicate composition ID"
SPEC = {item["id"]: ROOT / item["storyboard"] for item in CATALOG}
ALLOWED_KINDS = {"digital-simulation", "technical-schematic"}
MEDIA = (ROOT / "public/media").resolve()


def check_storyboard(name: str, doc: dict) -> dict:
    assert doc.get("kind") in ALLOWED_KINDS, f"{name}: invalid kind"
    assert doc.get("display_notice") and doc.get("source_page","").startswith("/projects/"), f"{name}: missing disclosure"
    assert doc.get("scenes"), f"{name}: missing scenes"
    assert 10 <= doc.get("fps", 0) <= 60
    ids=set()
    output_scenes=[]
    for scene in doc["scenes"]:
        assert scene["id"] not in ids, f"{name}: duplicate scene id"
        ids.add(scene["id"])
        assert 3 <= scene.get("seconds",0) <= 20, f"{name}: wrong duration"
        assert scene.get("action_ref") and scene.get("evidence_ref"), f"{name}: no action/evidence"
        assert scene.get("title") and scene.get("narration") and 1<=len(scene.get("bullets",[]))<=4
        evidence = Path(scene["evidence_ref"])
        assert not evidence.is_absolute() and ".." not in evidence.parts, f"{name}: invalid evidence path"
        evidence_path=(ROOT/evidence).resolve()
        assert evidence_path.is_relative_to(ROOT.resolve()) and evidence_path.is_file(), f"{name}: missing source {evidence}"
        s={k:scene[k] for k in ["id","seconds","label","title","bullets","narration","evidence","action_ref","evidence_ref"]}
        if "diagram" in scene:
            assert doc["kind"]=="technical-schematic" and scene["diagram"] in {"device","chip","ribbon","pcb","route","gate","check"}
            s["diagram"]=scene["diagram"]
        if "visual" in scene:
            src = Path(scene["visual"])
            assert doc["kind"] == "digital-simulation", "schematic cannot masquerade as real image"
            assert not src.is_absolute() and ".." not in src.parts, f"{name}: unsafe visual path"
            f=(ROOT/src).resolve()
            assert f.is_relative_to(MEDIA) and f.is_file(), f"{name}: missing visual"
            s["image_src"]=str(f.relative_to(MEDIA)).replace("\\","/")
            s["_source_visual"]=scene["visual"]
        assert "diagram" in s or "image_src" in s, f"{name}: scene has no owned visual"
        output_scenes.append(s)
    return {
        "project":doc["project"],"title":doc["title"],"video_id":doc["video_id"],
        "width":doc["width"],"height":doc["height"],"fps":doc["fps"],
        "kind":doc["kind"],"disclosure":doc["display_notice"],
        "source_page":doc["source_page"],"scenes":output_scenes,
    }


def prepare(write: bool):
    processed={}
    manifest=[]
    for composition, path in SPEC.items():
        data = json.loads(path.read_text(encoding="utf-8"))
        result=check_storyboard(composition,data)
        manifest.append({"composition":composition,"source":str(path.relative_to(ROOT)),
                         "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                         "kind":result["kind"],"scene_count":len(result["scenes"])})
        processed[composition]=result
        if write:
            dest=ENGINE/"props"/(composition+".json")
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        for scene in result["scenes"]:
            if "image_src" in scene and write:
                original=MEDIA/scene["image_src"]
                target=ENGINE/"public/images"/scene["image_src"]
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(original,target)
    if write:
        # React imports a single generated JSON catalog; new compositions
        # only need a catalog.json row and a source storyboard.
        (ENGINE/"props/catalog.json").write_text(
            json.dumps([{"id": key, "props": value} for key,value in processed.items()],
                       ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        (ENGINE/"props/_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Remotion provenance:", ", ".join(f"{k}: {len(v['scenes'])} scenes ({v['kind']})" for k,v in processed.items()))
    return processed


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--check",action="store_true")
    a=p.parse_args()
    prepare(not a.check)
