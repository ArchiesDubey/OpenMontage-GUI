"""E02 sample preview: 1 image + 1 TTS clip, for user approval before batch generation.

Per asset-director.md Step 2b -- prevents wasted spend on the full 29-image /
86-clip batch. Uses the exact same INK_STYLE blocks and voice params validated
in E01 (scripts/e01_generate_assets.py).
"""
import json
import os

from tools.tool_registry import registry

registry.discover()

OUT = "projects/ink-testimony-e02/assets/e02"
os.makedirs(OUT, exist_ok=True)
os.makedirs(f"{OUT}/_preview", exist_ok=True)

INK_STYLE_DARK = (
    "Historical narrative illustration rendered as fine white ink lines on a "
    "pure black background, delicate cross-hatching, 1920s editorial style, "
    "high contrast. No text or numbers anywhere. "
    "Full-bleed image, no border, no plate frame, no label."
)

flux = registry.get("flux_image")
tts = registry.get("elevenlabs_tts")

script = json.load(open("projects/ink-testimony-e02/artifacts/script.json"))
s31 = next(s for s in script["sections"] if s["id"] == "s31")

# Image sample: s31, the hero forensic reveal (dark treatment) -- the most
# representative/highest-risk frame (extreme close-up, must not drift photographic).
prompt = (
    "Pen-and-ink illustration with fine white ink lines on a pure black background: "
    "extreme close-up detail of a broken tiger canine tooth, shattered to the gum, "
    "delicate cross-hatching, 1920s editorial illustration style, high contrast. "
    + INK_STYLE_DARK
)
seed = 119020
r_img = flux.execute({
    "prompt": prompt,
    "model": "flux-pro/v1.1",
    "width": 1280,
    "height": 720,
    "seed": seed,
    "output_path": f"{OUT}/SAMPLE_s31_canine.png",
})
print("image sample:", r_img.success, r_img.error or "", "seed", seed)

# TTS sample: s31, the designated sample_section_id in script.voice_performance.
r_tts = tts.execute({
    "text": s31["delivery_cues"]["provider_text"],
    "voice_id": "S9GPGBaMND8XWwwzxQXp",
    "model_id": "eleven_multilingual_v2",
    "stability": 0.75,
    "similarity_boost": 0.9,
    "style": 0.1,
    "speed": 1.0,
    "output_path": f"{OUT}/SAMPLE_s31_narration.mp3",
})
print("tts sample:", r_tts.success, r_tts.error or "")

log = {
    "image_sample": {"file": "SAMPLE_s31_canine.png", "seed": seed, "success": r_img.success, "error": r_img.error, "prompt": prompt},
    "tts_sample": {"file": "SAMPLE_s31_narration.mp3", "success": r_tts.success, "error": r_tts.error, "text": s31["delivery_cues"]["provider_text"]},
}
json.dump(log, open(f"{OUT}/sample_log.json", "w"), indent=2)
print(json.dumps(log, indent=2))
