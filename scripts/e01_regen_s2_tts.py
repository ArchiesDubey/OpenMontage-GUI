"""Regenerate s2 narration: '1,600' misnormalized to 'section' by TTS.

Spells out 'sixteen hundred' in provider_text (script.json updated); same
voice/settings as the batch run so it matches the other 13 clips.
"""
import json

from tools.tool_registry import registry

registry.discover()

OUT = "projects/ink-testimony-e01/assets/e01"
text = json.load(open("projects/ink-testimony-e01/artifacts/script.json"))
s2 = next(s for s in text["sections"] if s["id"] == "s2")

tts = registry.get("elevenlabs_tts")
r = tts.execute({
    "text": s2["delivery_cues"]["provider_text"],
    "voice_id": "S9GPGBaMND8XWwwzxQXp",
    "model_id": "eleven_multilingual_v2",
    "stability": 0.75,
    "similarity_boost": 0.9,
    "style": 0.1,
    "speed": 1.0,
    "output_path": f"{OUT}/s2_narration.mp3",
})
print("s2 tts regen:", r.success, r.error or "")

log = json.load(open(f"{OUT}/generation_log.json"))
log["narration"]["s2"] = {
    "success": r.success,
    "error": r.error,
    "regen": "provider_text '1,600' -> 'sixteen hundred' (TTS misnormalization fix)",
}
json.dump(log, open(f"{OUT}/generation_log.json", "w"), indent=2)
print("DONE" if r.success else "FAILED")
