"""E03 batch asset generation: ink frames + narration + music bed.

Driven from scene_plan.json (prompts already embedded with the medium-first
opener + INK_STYLE / INK_STYLE_DARK + blank-paper reinforcement + guard) and
script.json (provider_text). Mirrors scripts/e02_generate_assets.py.

- Images: ONLY scenes with required_assets[0].source == "generate" (held beats
  carry source == "provided" and must never hit the image model).
- Idempotent: any output file that already exists is skipped.
- Approved samples are reused in place: s1 <- SAMPLE_s1_v2.png (seed 119063),
  a2_2 <- SAMPLE_a2_2.png (119061), a4_17 <- SAMPLE_a4_17.png (119062),
  a4_19 / a2_7 narration <- the approved SAMPLE clips.
- Fresh seeds continue the single band from 119064 (119060-119063 used by the
  sample round).
"""
import json, os, shutil
from tools.tool_registry import registry

registry.discover()
OUT = "projects/ink-testimony-e03/assets/e03"
PREVIEW = f"{OUT}/_preview"
os.makedirs(PREVIEW, exist_ok=True)

scene_plan = json.load(open("projects/ink-testimony-e03/artifacts/scene_plan.json"))
script = json.load(open("projects/ink-testimony-e03/artifacts/script.json"))
sections = {s["id"]: s for s in script["sections"]}

flux = registry.get("flux_image")
tts = registry.get("elevenlabs_tts")
music = registry.get("pixabay_music")

log = {"images": {}, "narration": {}, "music": {}, "cost_usd": {"images": 0.0, "narration": 0.0}}

SAMPLE_IMG = {"s1": ("SAMPLE_s1_v2.png", 119063),
              "a2_2": ("SAMPLE_a2_2.png", 119061),
              "a4_17": ("SAMPLE_a4_17.png", 119062)}
SAMPLE_TTS = {"a4_19": "SAMPLE_a4_19_narration.mp3", "a2_7": "SAMPLE_a2_7_narration.mp3"}

FLUX_UNIT = 0.05          # flux-pro/v1.1 per-frame, E01/E02 actuals
TTS_PER_1K = 0.30         # ~ eleven_multilingual_v2 per 1k chars, E01/E02 rate

# ---------------------------------------------------------------- images
seed = 119064
for scene in sorted(scene_plan["scenes"], key=lambda s: s["start_seconds"]):
    if scene["type"] != "generated":
        continue
    if scene["required_assets"][0]["source"] != "generate":
        continue  # held / reuse beat
    sid = scene["script_section_id"]
    fname = f"e03_{sid}.png"
    out_path = f"{OUT}/{fname}"

    if sid in SAMPLE_IMG:
        src, s = SAMPLE_IMG[sid]
        if not os.path.exists(out_path):
            shutil.copyfile(f"{OUT}/{src}", out_path)
        log["images"][sid] = {"file": fname, "seed": s, "success": True, "error": None,
                              "note": f"reused approved sample {src}"}
        print(sid, "image: reused approved sample", src, flush=True)
        continue
    if os.path.exists(out_path):
        log["images"][sid] = {"file": fname, "seed": None, "success": True, "error": None,
                              "note": "already on disk, skipped"}
        print(sid, "image: exists, skipped", flush=True)
        continue

    prompt = scene["required_assets"][0]["description"].replace("GENERATE: ", "", 1)
    r = flux.execute({"prompt": prompt, "model": "flux-pro/v1.1",
                      "width": 1280, "height": 720, "seed": seed, "output_path": out_path})
    log["images"][sid] = {"file": fname, "seed": seed, "success": r.success,
                          "error": r.error, "scene_id": scene["id"], "prompt": prompt}
    if r.success:
        log["cost_usd"]["images"] += FLUX_UNIT
    print(sid, "image:", r.success, r.error or "", "seed", seed, flush=True)
    seed += 1
    json.dump(log, open(f"{OUT}/generation_log.json", "w"), indent=2)

# ---------------------------------------------------------------- narration
for sid in sorted(sections, key=lambda k: sections[k]["start_seconds"]):
    sec = sections[sid]
    fname = f"{sid}_narration.mp3"
    out_path = f"{OUT}/{fname}"
    if sid in SAMPLE_TTS:
        if not os.path.exists(out_path):
            shutil.copyfile(f"{OUT}/{SAMPLE_TTS[sid]}", out_path)
        log["narration"][sid] = {"file": fname, "success": True, "error": None,
                                 "note": "reused approved sample"}
        print(sid, "tts: reused approved sample", flush=True)
        continue
    if os.path.exists(out_path):
        log["narration"][sid] = {"file": fname, "success": True, "error": None,
                                 "note": "already on disk, skipped"}
        print(sid, "tts: exists, skipped", flush=True)
        continue
    text = sec["delivery_cues"]["provider_text"]
    r = tts.execute({"text": text, "voice_id": "S9GPGBaMND8XWwwzxQXp",
                     "model_id": "eleven_multilingual_v2", "stability": 0.75,
                     "similarity_boost": 0.9, "style": 0.1, "speed": 1.0,
                     "output_path": out_path})
    log["narration"][sid] = {"file": fname, "success": r.success, "error": r.error,
                             "chars": len(text)}
    if r.success:
        log["cost_usd"]["narration"] += len(text) / 1000 * TTS_PER_1K
    print(sid, "tts:", r.success, r.error or "", f"({len(text)} chars)", flush=True)
    json.dump(log, open(f"{OUT}/generation_log.json", "w"), indent=2)

# ---------------------------------------------------------------- music
if os.path.exists(f"{OUT}/music_bed.mp3"):
    log["music"] = {"success": True, "error": None, "note": "exists, skipped"}
    print("music: exists, skipped", flush=True)
else:
    r = music.execute({"query": "sad somber dark ambient orchestral documentary",
                       "min_duration": 600, "max_duration": 900,
                       "output_path": f"{OUT}/music_bed.mp3"})
    log["music"] = {"success": r.success, "error": r.error}
    print("music:", r.success, r.error or "", flush=True)

log["cost_usd"]["total"] = round(log["cost_usd"]["images"] + log["cost_usd"]["narration"], 2)
json.dump(log, open(f"{OUT}/generation_log.json", "w"), indent=2)

oi = sum(1 for v in log["images"].values() if v["success"])
on = sum(1 for v in log["narration"].values() if v["success"])
print("---", flush=True)
print(f"images:   {oi}/{len(log['images'])}   ~${log['cost_usd']['images']:.2f}", flush=True)
print(f"narration:{on}/{len(log['narration'])}   ~${log['cost_usd']['narration']:.2f}", flush=True)
print(f"music:    {log['music']['success']}", flush=True)
print(f"batch cost so far ~${log['cost_usd']['total']:.2f}  (+ ~$0.19 sample round)", flush=True)
ok = oi == len(log["images"]) and on == len(log["narration"]) and log["music"]["success"]
print("BATCH DONE" if ok else "PARTIAL/FAILED -- see generation_log.json", flush=True)
