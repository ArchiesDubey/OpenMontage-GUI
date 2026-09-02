"""E03 sample assets: 1 TTS clip + 3 ink frames, for pre-batch approval.

Per skills/pipelines/explainer/asset-director.md Step 2b -- generate one sample
of each expensive asset type before the full batch. Voice + ink style are both
locked and validated across E01/E02, so this is a rendering sanity check
(numeral spelling in the read; the E03 prompts land as pen-and-ink), not a
style-approval round.

Seeds 119060-119062 open the E03 band (E02 topped out at 119055).
"""
import json, os
from tools.tool_registry import registry

registry.discover()
OUT = "projects/ink-testimony-e03/assets/e03"
PREVIEW = f"{OUT}/_preview"
os.makedirs(PREVIEW, exist_ok=True)

sp = json.load(open("projects/ink-testimony-e03/artifacts/scene_plan.json"))
sc = json.load(open("projects/ink-testimony-e03/artifacts/script.json"))
scenes = {s["id"]: s for s in sp["scenes"]}
secs = {s["id"]: s for s in sc["sections"]}

flux = registry.get("flux_image")
tts = registry.get("elevenlabs_tts")

log = {"images": {}, "narration": {}}

# --- 3 representative frames: light establishing/hero, ink portrait, dark forensic
SAMPLES = [("s1", 119060), ("a2_2", 119061), ("a4_17", 119062)]
for sid, seed in SAMPLES:
    scene = scenes[sid]
    prompt = scene["required_assets"][0]["description"].replace("GENERATE: ", "", 1)
    out_path = f"{OUT}/SAMPLE_{sid}.png"
    r = flux.execute({
        "prompt": prompt, "model": "flux-pro/v1.1",
        "width": 1280, "height": 720, "seed": seed, "output_path": out_path,
    })
    log["images"][sid] = {"file": os.path.basename(out_path), "seed": seed,
                          "success": r.success, "error": r.error, "prompt": prompt}
    print(sid, "image:", r.success, r.error or "", "seed", seed)

# --- 1 TTS clip: the most performance-sensitive beat (four words, dates around it)
sid = sc["voice_performance"]["sample_section_id"]  # a4_19
r = tts.execute({
    "text": secs[sid]["delivery_cues"]["provider_text"],
    "voice_id": "S9GPGBaMND8XWwwzxQXp",
    "model_id": "eleven_multilingual_v2",
    "stability": 0.75, "similarity_boost": 0.9, "style": 0.1, "speed": 1.0,
    "output_path": f"{OUT}/SAMPLE_{sid}_narration.mp3",
})
log["narration"][sid] = {"file": f"SAMPLE_{sid}_narration.mp3",
                         "success": r.success, "error": r.error,
                         "text": secs[sid]["delivery_cues"]["provider_text"]}
print(sid, "tts:", r.success, r.error or "")

# also a short line with a spelled-out date, to check numeral read
sid2 = "a2_7"
r2 = tts.execute({
    "text": secs[sid2]["delivery_cues"]["provider_text"],
    "voice_id": "S9GPGBaMND8XWwwzxQXp",
    "model_id": "eleven_multilingual_v2",
    "stability": 0.75, "similarity_boost": 0.9, "style": 0.1, "speed": 1.0,
    "output_path": f"{OUT}/SAMPLE_{sid2}_narration.mp3",
})
log["narration"][sid2] = {"file": f"SAMPLE_{sid2}_narration.mp3",
                          "success": r2.success, "error": r2.error,
                          "text": secs[sid2]["delivery_cues"]["provider_text"]}
print(sid2, "tts:", r2.success, r2.error or "")

json.dump(log, open(f"{OUT}/sample_log.json", "w"), indent=2)
print("--- sample_log.json written ---")
