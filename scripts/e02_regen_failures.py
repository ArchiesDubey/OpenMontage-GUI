"""Regenerate 5 E02 frames that failed the mandatory guard / legibility review:
s9 (color drift + readable text on banknotes), s56 & s64 (drawn border + corner
signature text), s58 & s61 (solid black, no visible content -- s61 is a hero
forensic image). Fresh seeds, reinforced anti-text/anti-border/anti-signature
and (for s58/s61) anti-all-black guidance.
"""
import json
import os

from tools.tool_registry import registry

registry.discover()
flux = registry.get("flux_image")
OUT = "projects/ink-testimony-e02/assets/e02"

INK_STYLE = (
    "Historical narrative illustration in black-and-white pen-and-ink with soft "
    "gray brush washes on warm white paper, fine cross-hatching and dry-brush "
    "texture, expressive hand-inked faces, 1920s editorial illustration style, "
    "high contrast, matte paper grain. No text or numbers anywhere. "
    "Full-bleed image, no border, no plate frame, no label."
)
INK_STYLE_DARK = (
    "Historical narrative illustration rendered as fine white ink lines on a "
    "pure black background, delicate cross-hatching, 1920s editorial style, "
    "high contrast. No text or numbers anywhere. "
    "Full-bleed image, no border, no plate frame, no label."
)
NO_SIG = "Absolutely no artist signature, no monogram, no lettering, no banknote text, no drawn border line or picture frame anywhere in the image."
NO_BLACKOUT = "The white ink linework must be clearly visible and legible against the black background -- do not render a solid or near-solid black frame with no visible subject."

REGEN = {
    "s9": dict(
        prompt="Pen-and-ink illustration with soft gray brush washes on warm white paper: a stack of plain unmarked paper notes and a small trophy cup on a district officer's wooden desk, no printing or lettering on the notes, blank paper surfaces only. " + NO_SIG + " " + INK_STYLE,
        dark=False,
    ),
    "s56": dict(
        prompt="Pen-and-ink illustration with soft gray brush washes on warm white paper: a small hillside village at dusk, doors shut, no figures visible, silhouetted against a dusk sky. " + NO_SIG + " " + INK_STYLE,
        dark=False,
    ),
    "s58": dict(
        prompt="Pen-and-ink illustration with soft gray brush washes on warm white paper, dusk blue-gray tones: a faint blood trail across leaf litter on a forest floor, disappearing into dense undergrowth, visible dappled dusk light through the canopy above. " + NO_SIG + " " + INK_STYLE,
        dark=False,
    ),
    "s61": dict(
        prompt="Pen-and-ink illustration rendered as fine white ink lines on a black background: close-up detail of an old healed wound scar on a tiger's flank, clearly visible white linework showing torn fur and scar tissue, examination table edge visible beneath in white outline. " + NO_SIG + " " + NO_BLACKOUT + " " + INK_STYLE_DARK,
        dark=True,
    ),
    "s64": dict(
        prompt="Pen-and-ink illustration with soft gray brush washes on warm white paper: a worn hardcover book with a blank unmarked spine and cover, resting on a wooden table beside an oil lamp, title area left blank. " + NO_SIG + " " + INK_STYLE,
        dark=False,
    ),
}

log = {}
seed = 119051
for sec_id, cfg in REGEN.items():
    r = flux.execute({
        "prompt": cfg["prompt"],
        "model": "flux-pro/v1.1",
        "width": 1280,
        "height": 720,
        "seed": seed,
        "output_path": f"{OUT}/e02_{sec_id}.png",
    })
    log[sec_id] = {"success": r.success, "error": r.error, "seed": seed, "prompt": cfg["prompt"]}
    print(sec_id, "regen:", r.success, r.error or "", "seed", seed)
    seed += 1

json.dump(log, open(f"{OUT}/regen_log.json", "w"), indent=2)
