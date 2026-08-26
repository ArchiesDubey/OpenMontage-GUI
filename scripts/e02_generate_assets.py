"""E02 batch asset generation: remaining ink frames + narration + music.

Driven directly from scene_plan.json (anchor frame descriptions, already
embedded with INK_STYLE/INK_STYLE_DARK + guard text) and script.json
(narration text + delivery cues). Reuses the already-approved s31 sample
(seed 119021) instead of regenerating it. Seeds continue the E01 band from
119022 (119020/119021 already used by the rejected/approved samples).
"""
import json
import os
import shutil

from tools.tool_registry import registry

registry.discover()

OUT = "projects/ink-testimony-e02/assets/e02"
PREVIEW = f"{OUT}/_preview"
os.makedirs(PREVIEW, exist_ok=True)

scene_plan = json.load(open("projects/ink-testimony-e02/artifacts/scene_plan.json"))
script = json.load(open("projects/ink-testimony-e02/artifacts/script.json"))
sections = {s["id"]: s for s in script["sections"]}

flux = registry.get("flux_image")
tts = registry.get("elevenlabs_tts")
music = registry.get("pixabay_music")

log = {"images": {}, "narration": {}, "music": {}}

# --- Images: ONLY scenes whose required_assets source=="generate" (true anchors).
# BUGFIX: previously filtered on scene["type"] in ("generated","diagram"), which also
# matched REUSE/held beats (source=="provided") -- those got the literal string
# "REUSE sN's generated frame..." sent to FLUX as a prompt, producing unrelated
# garbage images (confirmed: random anime art). 36 bogus files were generated and
# deleted; this run is idempotent (skips any file that already exists on disk).
seed = 119022
for scene in sorted(scene_plan["scenes"], key=lambda s: s["start_seconds"]):
    if scene["type"] not in ("generated", "diagram"):
        continue
    if scene["required_assets"][0]["source"] != "generate":
        continue  # held/reuse beat -- must NOT call the image generator
    sec_id = scene["script_section_id"]
    fname = f"e02_{sec_id}.png"
    out_path = f"{OUT}/{fname}"
    if sec_id == "s31":
        if not os.path.exists(out_path):
            shutil.copyfile(f"{OUT}/SAMPLE_s31_canine_v2.png", out_path)
        log["images"][sec_id] = {"file": fname, "seed": 119021, "success": True, "error": None, "note": "reused approved sample (regenerated v2)"}
        print(sec_id, "image: reused approved sample")
        continue
    if os.path.exists(out_path):
        log["images"][sec_id] = {"file": fname, "seed": None, "success": True, "error": None, "note": "already generated, skipped"}
        print(sec_id, "image: already exists, skipped")
        continue
    prompt_desc = scene["required_assets"][0]["description"].replace("GENERATE: ", "", 1)
    r = flux.execute({
        "prompt": prompt_desc,
        "model": "flux-pro/v1.1",
        "width": 1280,
        "height": 720,
        "seed": seed,
        "output_path": out_path,
    })
    log["images"][sec_id] = {"file": fname, "seed": seed, "success": r.success, "error": r.error, "scene_id": scene["id"], "prompt": prompt_desc}
    print(sec_id, "image:", r.success, r.error or "", "seed", seed)
    seed += 1

# --- Narration: every script section, skip s31 (already generated as SAMPLE) ---
for sid in sorted(sections, key=lambda k: sections[k]["start_seconds"]):
    sec = sections[sid]
    fname = f"{sid}_narration.mp3"
    out_path = f"{OUT}/{fname}"
    if sid == "s31":
        if not os.path.exists(out_path):
            shutil.copyfile(f"{OUT}/SAMPLE_s31_narration.mp3", out_path)
        log["narration"][sid] = {"file": fname, "success": True, "error": None, "note": "reused approved sample"}
        print(sid, "tts: reused approved sample")
        continue
    if os.path.exists(out_path):
        log["narration"][sid] = {"file": fname, "success": True, "error": None, "note": "already generated, skipped"}
        print(sid, "tts: already exists, skipped")
        continue
    r = tts.execute({
        "text": sec["delivery_cues"]["provider_text"],
        "voice_id": "S9GPGBaMND8XWwwzxQXp",
        "model_id": "eleven_multilingual_v2",
        "stability": 0.75,
        "similarity_boost": 0.9,
        "style": 0.1,
        "speed": 1.0,
        "output_path": f"{OUT}/{fname}",
    })
    log["narration"][sid] = {"file": fname, "success": r.success, "error": r.error}
    print(sid, "tts:", r.success, r.error or "")

# --- Music ---
if os.path.exists(f"{OUT}/music_bed.mp3"):
    log["music"] = {"success": True, "error": None, "note": "already generated, skipped"}
    print("music: already exists, skipped")
else:
    r = music.execute({
        "query": "sad somber dark ambient orchestral documentary",
        "min_duration": 600,
        "max_duration": 900,
        "output_path": f"{OUT}/music_bed.mp3",
    })
    log["music"] = {"success": r.success, "error": r.error}
    print("music:", r.success, r.error or "")

json.dump(log, open(f"{OUT}/generation_log.json", "w"), indent=2)

ok_images = all(v["success"] for v in log["images"].values())
ok_narr = all(v["success"] for v in log["narration"].values())
ok_music = log["music"]["success"]
print("---")
print("images:", sum(1 for v in log['images'].values() if v['success']), "/", len(log["images"]))
print("narration:", sum(1 for v in log['narration'].values() if v['success']), "/", len(log["narration"]))
print("music:", ok_music)
print("DONE" if (ok_images and ok_narr and ok_music) else "PARTIAL/FAILED -- see generation_log.json")
