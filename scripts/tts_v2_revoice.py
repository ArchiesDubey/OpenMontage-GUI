"""Re-voice the 5 sample v2 narration clips with the user's preferred voice.

TTS-only companion to sample_v2_beats.py — images are already approved, so
this regenerates just the narration mp3s. Run compose_ink_sample_v2.py after.
"""
import json
import os

from tools.tool_registry import registry

registry.discover()

OUT = "projects/ink-testimony-e01/assets/sample"
VOICE_ID = "S9GPGBaMND8XWwwzxQXp"  # user's preferred voice

CLIPS = [
    ("b1_dial", "In Orange, New Jersey, there's a watch dial painted in 1918."),
    ("b2_glow", "It hasn't glowed in a century."),
    ("b3_bones", "It's still radioactive. And so are the bones of the women who painted it."),
    ("b4_floor", "The paint was radium. The girls were told it was perfectly harmless."),
    ("b5_lip", "To keep the brush sharp, they shaped the bristles with their lips."),
]

tts = registry.get("elevenlabs_tts")
results = {}
for clip_id, text in CLIPS:
    r = tts.execute({
        "text": text,
        "voice_id": VOICE_ID,
        "model_id": "eleven_multilingual_v2",
        "stability": 0.75,
        "similarity_boost": 0.9,
        "style": 0.1,
        "speed": 1.0,
        "output_path": f"{OUT}/{clip_id}_narration.mp3",
    })
    results[clip_id] = {"success": r.success, "error": r.error}
    print(clip_id, "tts:", r.success, r.error or "")

json.dump(results, open(f"{OUT}/v2_revoice_log.json", "w"), indent=2)
print("DONE" if all(v["success"] for v in results.values()) else "FAILED")
