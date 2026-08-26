"""A/B test: emotional delivery options for the bones beat.

altA: current model (multilingual_v2), emotion via settings only
      (lower stability + higher style = more expressive variation)
altB: eleven_v3 alpha with an inline audio tag ([whispers] hushed take)
Current approved take stays untouched as b3_bones_narration.mp3.
"""
import json
import os

from tools.tool_registry import registry

registry.discover()

OUT = "projects/ink-testimony-e01/assets/sample"
VOICE_ID = "S9GPGBaMND8XWwwzxQXp"
TEXT = "It's still radioactive. And so are the bones of the women who painted it."

tts = registry.get("elevenlabs_tts")
results = {}

r = tts.execute({
    "text": TEXT, "voice_id": VOICE_ID,
    "model_id": "eleven_multilingual_v2",
    "stability": 0.35, "similarity_boost": 0.9, "style": 0.45, "speed": 0.95,
    "output_path": f"{OUT}/b3_bones_narration_altA.mp3",
})
results["altA_v2_emotional_settings"] = {"success": r.success, "error": r.error}
print("altA (v2, emotional settings):", r.success, r.error or "")

r = tts.execute({
    "text": "[whispers] " + TEXT, "voice_id": VOICE_ID,
    "model_id": "eleven_v3",
    "stability": 0.5, "similarity_boost": 0.9, "style": 0.3, "speed": 1.0,
    "output_path": f"{OUT}/b3_bones_narration_altB.mp3",
})
results["altB_v3_whisper_tag"] = {"success": r.success, "error": r.error}
print("altB (v3, [whispers] tag):", r.success, r.error or "")

json.dump(results, open(f"{OUT}/v3_emotion_ab_log.json", "w"), indent=2)
