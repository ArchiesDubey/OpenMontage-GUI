"""Sample v2: per-beat imagery — one frame per narration beat, hard cuts.

Addresses user feedback: images held too long; cut on every narration beat.
Generates 3 new beat frames (glow, bones, studio floor) + 5 per-beat TTS clips.
Voice is a placeholder (Adam) until user supplies preferred voice_id.
"""
import json
import os

from tools.tool_registry import registry

registry.discover()

OUT = "projects/ink-testimony-e01/assets/sample"
os.makedirs(OUT, exist_ok=True)

# Locked ink-style block (validated in v1)
INK_STYLE = (
    "Historical narrative illustration in black-and-white pen-and-ink with soft "
    "gray brush washes on warm white paper, fine cross-hatching and dry-brush "
    "texture, expressive hand-inked faces, 1920s editorial illustration style, "
    "high contrast, matte paper grain. No text or numbers anywhere."
)

# b1/b5 reuse v1 frames (sc01_hook.png, sc02_lippoint.png)
BEATS = [
    {
        "id": "b2_glow",
        "image_prompt": (
            "A single wristwatch dial lying in a dark museum display case at "
            "night, its numerals and hands glowing with a faint pale luminous "
            "light, the glow rendered as delicate white ink radiating into "
            "dense black cross-hatched darkness around the case. " + INK_STYLE
        ),
        "narration": "It hasn't glowed in a century.",
    },
    {
        "id": "b3_bones",
        "image_prompt": (
            "A 1920s medical x-ray radiograph of a human jawbone riddled "
            "with crumbling holes and fractured bone, the destroyed cavities "
            "glowing pale against deep black, clinical, eerie and haunting, "
            "rendered as fine white ink lines on a pure black background, "
            "full-bleed image, no border, no plate frame, no label. " + INK_STYLE
        ),
        "narration": "It's still radioactive. And so are the bones of the women who painted it.",
    },
    {
        "id": "b4_floor",
        "image_prompt": (
            "Rows of young women in 1920s factory blouses seated at long "
            "workbenches painting small watch dials with fine brushes, jars of "
            "pale paint at each workstation, big industrial factory windows "
            "behind them, seen from a slight distance down the bench. "
            + INK_STYLE
        ),
        "narration": "The paint was radium. The girls were told it was perfectly harmless.",
    },
]

flux = registry.get("flux_image")
tts = registry.get("elevenlabs_tts")
results = {}

for i, b in enumerate(BEATS):
    r = flux.execute({
        "prompt": b["image_prompt"],
        "model": "flux-pro/v1.1",
        "width": 1280,
        "height": 720,
        "seed": 118997 if b["id"] == "b3_bones" else 118980 + 10 + i,  # near v1 seeds for style consistency
        "output_path": f"{OUT}/{b['id']}.png",
    })
    results[b["id"] + "_image"] = str(r)[:200]
    print(b["id"], "image:", getattr(r, "success", None))

    r = tts.execute({
        "text": b["narration"],
        "voice_id": "S9GPGBaMND8XWwwzxQXp",  # user's preferred voice
        "model_id": "eleven_multilingual_v2",
        "stability": 0.75,
        "similarity_boost": 0.9,
        "style": 0.1,
        "speed": 1.0,
        "output_path": f"{OUT}/{b['id']}_narration.mp3",
    })
    results[b["id"] + "_tts"] = str(r)[:200]
    print(b["id"], "tts:", getattr(r, "success", None))

# Also regenerate per-beat clips for the two reused frames so all cuts align
REUSE = [
    {
        "id": "b1_dial",
        "narration": "In Orange, New Jersey, there's a watch dial painted in 1918.",
    },
    {
        "id": "b5_lip",
        "narration": "To keep the brush sharp, they shaped the bristles with their lips.",
    },
]
for b in REUSE:
    r = tts.execute({
        "text": b["narration"],
        "voice_id": "S9GPGBaMND8XWwwzxQXp",  # user's preferred voice
        "model_id": "eleven_multilingual_v2",
        "stability": 0.75,
        "similarity_boost": 0.9,
        "style": 0.1,
        "speed": 1.0,
        "output_path": f"{OUT}/{b['id']}_narration.mp3",
    })
    results[b["id"] + "_tts"] = str(r)[:200]
    print(b["id"], "tts:", getattr(r, "success", None))

json.dump(results, open(f"{OUT}/v2_gen_log.json", "w"), indent=2)
print("DONE")
