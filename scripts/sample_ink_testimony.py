"""Sample-first production: Ink & Testimony E01 (Radium Girls) — 2 scenes.

Per skills/meta/video-reference-analyst.md Step 5. Pre-pipeline sample.
Layer 3 skills read: flux-best-practices, elevenlabs, music.
"""
import json
import os

from tools.tool_registry import registry

registry.discover()

OUT = "projects/ink-testimony-e01/assets/sample"
os.makedirs(OUT, exist_ok=True)

# Locked ink-style block (v0 — to be validated; scene text goes FIRST)
INK_STYLE = (
    "Historical narrative illustration in black-and-white pen-and-ink with soft "
    "gray brush washes on warm white paper, fine cross-hatching and dry-brush "
    "texture, expressive hand-inked faces, 1920s editorial illustration style, "
    "high contrast, matte paper grain. No text or numbers anywhere."
)

SCENES = [
    {
        "id": "sc01_hook",
        "image_prompt": (
            "A single dark unlit wristwatch dial lying in a museum display case, "
            "seen close-up at a slight angle, its numerals faded to shadow, a soft "
            "reflection on the glass above it. " + INK_STYLE
        ),
        "narration": (
            "In Orange, New Jersey, there is a watch dial painted in 1918.\n\n"
            "It hasn't glowed in a century.\n\n"
            "It is still radioactive. And so are the bones of the women who painted it."
        ),
        "subtitle": "It hasn't glowed in a century. It is still radioactive.",
    },
    {
        "id": "sc02_lippoint",
        "image_prompt": (
            "Close-up of a young woman in a 1920s factory blouse with a fine "
            "paintbrush held between her lips, the brush clamped in her mouth "
            "with its bristles pointing up, her hands free as she lowers a watch "
            "dial onto the workbench, an open jar of pale glowing paint beside "
            "her, rows of dials and factory windows soft in the background. "
            + INK_STYLE
        ),
        "narration": (
            "The paint was radium. The girls were told it was perfectly harmless.\n\n"
            "To keep the brush sharp, they shaped the bristles with their lips."
        ),
        "subtitle": "To keep the brush sharp, they shaped the bristles with their lips.",
    },
]

results = {}
registry.discover()

# 1) Images — flux-pro/v1.1, seed-matched for style consistency
flux = registry.get("flux_image")
for i, sc in enumerate(SCENES):
    r = flux.execute({
        "prompt": sc["image_prompt"],
        "model": "flux-pro/v1.1",
        "width": 1280,
        "height": 720,
        "seed": 118980 + i,  # matched seeds for style lock
        "output_path": f"{OUT}/{sc['id']}.png",
    })
    ok = getattr(r, "success", None)
    results[sc["id"] + "_image"] = str(r)[:300]
    print(sc["id"], "image:", ok)

# 2) Narration — ElevenLabs multilingual_v2, male documentary voice (Adam)
tts = registry.get("elevenlabs_tts")
for sc in SCENES:
    r = tts.execute({
        "text": sc["narration"],
        "voice_id": "pNInz6obpgDQGcFmaJgB",  # Adam
        "model_id": "eleven_multilingual_v2",
        "stability": 0.55,
        "similarity_boost": 0.85,
        "style": 0.25,
        "speed": 1.0,
        "output_path": f"{OUT}/{sc['id']}_narration.mp3",
    })
    results[sc["id"] + "_tts"] = str(r)[:300]
    print(sc["id"], "tts:", getattr(r, "success", None))

# 3) Music bed — pixabay (free)
mus = registry.get("pixabay_music")
r = mus.execute({
    "query": "dark ambient documentary piano somber",
    "min_duration": 45,
    "max_duration": 180,
    "output_path": f"{OUT}/music_bed.mp3",
})
results["music"] = str(r)[:300]
print("music:", getattr(r, "success", None))

json.dump(results, open(f"{OUT}/sample_gen_log.json", "w"), indent=2)
print("DONE")
