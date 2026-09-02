"""E03 re-cut: ~16 new detail / second-angle frames so the faster edit (every
visual 2.5-6s) has real picture changes, not just zoom variants of one still.
Seeds 119159-119174 continue the band. flux-pro/v1.1, 1280x720.
"""
import json, os
from tools.tool_registry import registry
registry.discover()
OUT = "projects/ink-testimony-e03/assets/e03"
flux = registry.get("flux_image")

INK = ("Historical narrative illustration in black-and-white pen-and-ink with soft gray brush washes on warm white "
       "paper, fine cross-hatching and dry-brush texture, expressive hand-inked faces, 1920s editorial illustration "
       "style, high contrast, matte paper grain. No text or numbers anywhere. Full-bleed image, no border, no plate "
       "frame, no label.")
INK_DARK = ("Historical narrative illustration rendered as fine white ink lines on a pure black background, delicate "
            "cross-hatching, 1920s editorial style, high contrast. No text or numbers anywhere. Full-bleed image, no "
            "border, no plate frame, no label.")
NOSIG = ("Absolutely no artist signature, no monogram, no lettering, no words, no numerals, no headline, no masthead, "
         "no drawn border line or picture frame anywhere in the image.")
NOBLACK = ("The white ink linework must be clearly visible and legible against the black background -- not a solid "
           "black frame.")
L = "Pen-and-ink illustration with soft gray brush washes on warm white paper: "
D = "Pen-and-ink illustration with fine white ink lines on a pure black background: "

NEW = {
 "n_s2":   (119159, L + "close on an open browned brittle broadsheet page being pressed flat, gloved fingertips at the "
            "curling edge, the page surface a plain uniform grey with no printing. " + NOSIG + " " + INK),
 "n_a2_4": (119160, L + "a staged old photograph of a dark, unreadable charred shape propped on a wooden easel beside a "
            "large plate camera on a tripod, lamplit study. " + NOSIG + " " + INK),
 "n_a3_2": (119161, L + "a single lit window of a colonial Pine Barrens cabin at night, a faint winged shape just "
            "clearing the sill, bare branches around it. " + NOSIG + " " + INK),
 "n_a3_12":(119162, D + "a chained and padlocked schoolhouse door at night in winter, snow untouched on the steps, "
            "black empty windows above. " + NOSIG + " " + NOBLACK + " " + INK_DARK),
 "n_a3_18":(119163, L + "close on the face of a frightened kangaroo in a cage, crude painted stripes on its cheek, a "
            "leather harness strap crossing its shoulder carrying a limp paper wing. " + NOSIG + " " + INK),
 "n_a3_23":(119164, L + "close on a sandhill crane's head and long straight beak, tilted up and open in a call, blurred "
            "frozen reeds behind. " + NOSIG + " " + INK),
 "n_a3_25":(119165, L + "the surface of a wide slow river close up, grey water moving, the long dark shadow of a steel "
            "bridge falling across it. " + NOSIG + " " + INK),
 "n_a4_2": (119166, L + "a low grassed-over concrete munitions bunker close up at night, its dark open doorway, a car "
            "headlight raking across the curved concrete. " + NOSIG + " " + INK),
 "n_a4_9": (119167, L + "close on a museum wall: rows of small blank pinned clippings and a paper map stuck with pins, "
            "every surface blank, a curator's shoulder at the edge of frame. " + NOSIG + " " + INK),
 "n_a4_15":(119168, D + "a driver's point of view along a packed eyebar suspension-bridge deck at dusk, cars bumper to "
            "bumper, headlights as white points, towers and cables above. " + NOSIG + " " + NOBLACK + " " + INK_DARK),
 "n_a4_18":(119169, D + "a severed steel suspension chain whipping loose against the sky as the bridge deck drops away "
            "beneath it, cars sliding, motion lines. " + NOSIG + " " + NOBLACK + " " + INK_DARK),
 "n_a4_20":(119170, L + "close on a recovered forged steel eyebar link laid on a tarp, its broken fracture face turned "
            "up, an investigator's gloved hand and a notebook beside it, daylight. " + NOSIG + " " + INK),
 "n_a5_2a":(119171, L + "extreme close on a brittle browned newspaper page corner flaking apart between gloved "
            "fingertips, tiny paper fragments falling, the page surface plain with no print. " + NOSIG + " " + INK),
 "n_a5_2b":(119172, L + "a heavy bound newspaper volume closed flat inside an open grey archival box on a reading "
            "table, the lid propped beside it, a foam cradle. " + NOSIG + " " + INK),
 "n_a5_10":(119173, L + "two hands smoothing a crisp modern broadsheet flat on a bright light table, a yellowed brittle "
            "old newspaper lying beneath it, both pages seen edge-on with no printed face visible. " + NOSIG + " " + INK),
 "n_a5_12":(119174, L + "a printing-press cylinder mid-turn, a blank paper web feeding through the rollers, two "
            "pressmen in aprons behind it in the dark. " + NOSIG + " " + INK),
}

log = []
for nid, (seed, prompt) in NEW.items():
    dst = f"{OUT}/e03_{nid}.png"
    if os.path.exists(dst):
        log.append({"id": nid, "seed": seed, "success": True, "note": "exists, skipped"}); print(nid, "skip"); continue
    r = flux.execute({"prompt": prompt, "model": "flux-pro/v1.1", "width": 1280, "height": 720,
                      "seed": seed, "output_path": dst})
    log.append({"id": nid, "seed": seed, "success": r.success, "error": r.error, "prompt": prompt})
    print(nid, r.success, r.error or "", "seed", seed, flush=True)
json.dump(log, open(f"{OUT}/recut_frames_log.json", "w"), indent=2)
ok = sum(1 for x in log if x["success"])
print(f"--- {ok}/{len(log)} new detail frames (~${ok*0.05:.2f}) ---", flush=True)
