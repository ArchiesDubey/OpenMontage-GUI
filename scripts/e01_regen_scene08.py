"""Regenerate scene-08 (e01_dentist_chair.png): first attempt drifted photographic.

Fix: lead with the illustration medium and strengthen ink-style language,
fresh seed (119010) to escape the photographic basin of seed 119003.
"""
import json

from tools.tool_registry import registry

registry.discover()

OUT = "projects/ink-testimony-e01/assets/e01"

INK_STYLE = (
    "Historical narrative illustration in black-and-white pen-and-ink with soft "
    "gray brush washes on warm white paper, fine cross-hatching and dry-brush "
    "texture, expressive hand-inked faces, 1920s editorial illustration style, "
    "high contrast, matte paper grain. No text or numbers anywhere. "
    "Full-bleed image, no border, no plate frame, no label."
)

PROMPT = (
    "Pen-and-ink illustration with soft gray brush washes on warm white paper: "
    "an empty 1920s dentist's chair, no people, nobody in the frame, standing "
    "in a dark treatment room, a single glass x-ray plate leaning against the "
    "wall catching thin light, heavy cross-hatched shadows, large areas of "
    "light paper tone. Drawn in hand-inked editorial illustration style, "
    "visible hatching strokes and paper grain, not a photograph, not a silhouette. "
    + INK_STYLE
)

flux = registry.get("flux_image")
SEED = 119011
r = flux.execute({
    "prompt": PROMPT,
    "model": "flux-pro/v1.1",
    "width": 1280,
    "height": 720,
    "seed": SEED,
    "output_path": f"{OUT}/e01_dentist_chair.png",
})
print("scene-08 regen:", r.success, r.error or "")

log = json.load(open(f"{OUT}/generation_log.json"))
log["images"]["scene-08"] = {
    "file": "e01_dentist_chair.png",
    "seed": SEED,
    "success": r.success,
    "error": r.error,
    "regen": "attempt 2 — medium-first prompt, seed 119010 (attempt 1 seed "
             "119003 drifted photographic, failed style review)",
}
json.dump(log, open(f"{OUT}/generation_log.json", "w"), indent=2)
print("DONE" if r.success else "FAILED")
