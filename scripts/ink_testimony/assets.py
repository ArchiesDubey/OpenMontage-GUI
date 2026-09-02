"""Ink & Testimony asset generation -- sample / batch / regen.

    python -m scripts.ink_testimony.assets --project projects/ink-testimony-eNN --mode batch
    python -m scripts.ink_testimony.assets --project ... --mode sample --frames s1 a2_2 --clips a4_19
    python -m scripts.ink_testimony.assets --project ... --mode regen  s3 a4_18 --reason "guard: legible text"

Reads artifacts/scene_plan.json (frame prompts, source) + artifacts/script.json
(narration provider_text). Seeds continue the single upward band. Idempotent:
any output that already exists is skipped unless --force. After any frame
generation, writes 480px previews and contact sheets.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.tool_registry import registry  # noqa: E402
from scripts.ink_testimony import common as C  # noqa: E402


def _gen_frame(flux, prompt, seed, out_path):
    r = flux.execute({"prompt": prompt, "model": C.FLUX_MODEL,
                      "width": C.FLUX_W, "height": C.FLUX_H, "seed": seed,
                      "output_path": str(out_path)})
    return r


def _tts(tts, text, out_path):
    return tts.execute({"text": text, "voice_id": C.TTS_VOICE_ID, "model_id": C.TTS_MODEL,
                        **C.TTS_PARAMS, "output_path": str(out_path)})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--mode", choices=["sample", "batch", "regen"], default="batch")
    ap.add_argument("--frames", nargs="*", default=[], help="sample mode: scene ids to render")
    ap.add_argument("--clips", nargs="*", default=[], help="sample mode: script section ids to voice")
    ap.add_argument("regen_ids", nargs="*", help="regen mode: scene ids to regenerate")
    ap.add_argument("--reason", default="regen", help="regen mode: logged reason")
    ap.add_argument("--force", action="store_true", help="overwrite existing outputs")
    ap.add_argument("--no-music", action="store_true")
    a = ap.parse_args(argv)

    registry.discover()
    flux = registry.get("flux_image")
    tts = registry.get("elevenlabs_tts")
    music = registry.get("pixabay_music")

    proj, AD, cfg, script, plan, cut_plan = C.load_project(a.project)
    ep = cfg["episode"]
    sections = {s["id"]: s for s in script["sections"]}
    dark_beats = set(script.get("metadata", {}).get("dark_register_beats", []))
    paper_ids = set(cut_plan.get("paper_subject_ids", []))
    scenes = {s["script_section_id"]: s for s in plan["scenes"]}
    seeds = C.seed_iter(AD, cfg)

    log_path = AD / "generation_log.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {"images": {}, "narration": {}, "music": {}, "cost_usd": {}}
    log.setdefault("images", {}); log.setdefault("narration", {}); log.setdefault("cost_usd", {})
    img_cost = float(log["cost_usd"].get("images", 0.0))
    tts_cost = float(log["cost_usd"].get("narration", 0.0))
    touched_frames = []

    # ---- which frames / clips this run does ----
    gen_scenes = [s for s in sorted(plan["scenes"], key=lambda x: x["start_seconds"])
                  if s["type"] != "text_card"
                  and (s.get("required_assets") or [{}])[0].get("source") == "generate"]
    if a.mode == "sample":
        want_frames = set(a.frames)
        gen_scenes = [s for s in gen_scenes if s["script_section_id"] in want_frames]
        clip_ids = list(a.clips)
    elif a.mode == "regen":
        want = set(a.regen_ids)
        gen_scenes = [scenes[i] for i in a.regen_ids if i in scenes]
        clip_ids = []
    else:  # batch
        clip_ids = [s["id"] for s in sorted(script["sections"], key=lambda x: x["start_seconds"])]

    prefix = "SAMPLE_" if a.mode == "sample" else ""
    regen_log = json.loads((AD / "regen_log.json").read_text()) if (AD / "regen_log.json").exists() else []

    # ---- frames ----
    for scene in gen_scenes:
        sid = scene["script_section_id"]
        fname = f"{prefix}{ep}_{sid}.png" if a.mode == "sample" else f"{ep}_{sid}.png"
        out = AD / fname
        if out.exists() and not a.force and a.mode != "regen":
            log["images"].setdefault(sid, {"file": fname, "success": True, "note": "exists, skipped"})
            print(sid, "image: exists, skipped", flush=True)
            continue
        if a.mode == "regen" and out.exists():
            n = len([p for p in AD.glob(f"_superseded*_{ep}_{sid}.png")]) + 1
            out.rename(AD / f"_superseded{n}_{ep}_{sid}.png")
        dark = sid in dark_beats
        prompt = C.build_prompt(scene, dark, paper_ids)
        seed = next(seeds)
        r = _gen_frame(flux, prompt, seed, out)
        entry = {"file": fname, "seed": seed, "success": r.success, "error": r.error,
                 "scene_id": scene["id"], "prompt": prompt}
        log["images"][sid] = entry
        if r.success:
            img_cost += C.FLUX_UNIT_USD
            touched_frames.append(out)
        if a.mode == "regen":
            regen_log.append({"scene": sid, "new_seed": seed, "success": r.success,
                              "error": r.error, "reason": a.reason, "prompt": prompt})
        print(sid, "image:", r.success, r.error or "", "seed", seed, flush=True)
        log["cost_usd"]["images"] = round(img_cost, 2)
        log_path.write_text(json.dumps(log, indent=2))

    if a.mode == "regen":
        (AD / "regen_log.json").write_text(json.dumps(regen_log, indent=2))

    # ---- narration ----
    for sid in clip_ids:
        sec = sections[sid]
        fname = f"{prefix}{sid}_narration.mp3" if a.mode == "sample" else f"{sid}_narration.mp3"
        out = AD / fname
        if out.exists() and not a.force:
            log["narration"].setdefault(sid, {"file": fname, "success": True, "note": "exists, skipped"})
            print(sid, "tts: exists, skipped", flush=True)
            continue
        text = sec["delivery_cues"]["provider_text"]
        r = _tts(tts, text, out)
        log["narration"][sid] = {"file": fname, "success": r.success, "error": r.error, "chars": len(text)}
        if r.success:
            tts_cost += len(text) / 1000 * C.TTS_USD_PER_1K_CHARS
        print(sid, "tts:", r.success, r.error or "", f"({len(text)} chars)", flush=True)
        log["cost_usd"]["narration"] = round(tts_cost, 2)
        log_path.write_text(json.dumps(log, indent=2))

    # ---- music ----
    if a.mode == "batch" and not a.no_music:
        mp = AD / "music_bed.mp3"
        if mp.exists() and not a.force:
            log["music"] = {"success": True, "note": "exists, skipped"}
        else:
            q = cfg["music_query"]
            r = music.execute({"query": q, "min_duration": 600, "max_duration": 1200, "output_path": str(mp)})
            log["music"] = {"success": r.success, "error": r.error, "query": q}
            print("music:", r.success, r.error or "", flush=True)

    log["cost_usd"]["total"] = round(img_cost + tts_cost, 2)
    log["cost_usd"]["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    log_path.write_text(json.dumps(log, indent=2))

    # ---- previews + contact sheets ----
    if touched_frames or a.mode in ("batch", "sample"):
        pv = AD / "_preview"
        all_pngs = sorted(AD.glob(f"{prefix}{ep}_*.png")) if a.mode == "sample" else sorted(AD.glob(f"{ep}_*.png"))
        previews = []
        for png in all_pngs:
            jpg = pv / f"{png.stem}.jpg"
            if not jpg.exists() or png in touched_frames or a.force:
                C.make_preview(png, jpg)
            previews.append(jpg)
        order = [s["script_section_id"] for s in sorted(plan["scenes"], key=lambda x: x["start_seconds"])]
        sheets = C.contact_sheet(previews, pv / "SHEET", order=order)
        print("contact sheets:", ", ".join(str(s.name) for s in sheets), flush=True)

    ni = sum(1 for v in log["images"].values() if v.get("success"))
    nn = sum(1 for v in log["narration"].values() if v.get("success"))
    print("---", flush=True)
    print(f"images {ni}/{len(log['images'])} ~${img_cost:.2f} | narration {nn}/{len(log['narration'])} "
          f"~${tts_cost:.2f} | total ~${img_cost + tts_cost:.2f}", flush=True)


if __name__ == "__main__":
    main()
