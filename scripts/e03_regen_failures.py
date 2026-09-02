"""E03 guard-review regens.

Full-batch guard review (production-lesson 2) flagged 16 frames:
 - 10 legible text / signage (guard: 'No text or numbers anywhere')
 - 2 register violations (dramatic horror-poster winged figure vs the brief's
   restrained, wings-folded, distant treatment)
 - 4 weak reads (subject not legible / too abstract)

Each is regenerated MEDIUM-FIRST with a bespoke anti-text or restrained prompt
and a FRESH seed from 119135. The print-*texture* frames (book spines, pinned
wall clippings with no legible words) are kept: that is the E01/E02 accepted
compromise and re-rolling risks worse.
"""
import json, os
from tools.tool_registry import registry

registry.discover()
OUT = "projects/ink-testimony-e03/assets/e03"
flux = registry.get("flux_image")

INK = ("Historical narrative illustration in black-and-white pen-and-ink with soft gray brush "
       "washes on warm white paper, fine cross-hatching and dry-brush texture, expressive "
       "hand-inked faces, 1920s editorial illustration style, high contrast, matte paper grain. "
       "No text or numbers anywhere. Full-bleed image, no border, no plate frame, no label.")
INK_DARK = ("Historical narrative illustration rendered as fine white ink lines on a pure black "
            "background, delicate cross-hatching, 1920s editorial style, high contrast. No text or "
            "numbers anywhere. Full-bleed image, no border, no plate frame, no label.")
NOSIG = ("Absolutely no artist signature, no monogram, no lettering of any kind, no shop signs, "
         "no headlines, no masthead, no words, no numerals, no drawn border line or picture frame "
         "anywhere in the image.")
L = "Pen-and-ink illustration with soft gray brush washes on warm white paper: "
D = "Pen-and-ink illustration with fine white ink lines on a pure black background: "
NOBLACK = ("The white ink linework must be clearly visible and legible against the black "
           "background -- do not render a solid or near-solid black frame with no visible subject.")

REGENS = {
 # --- legible text / signage ---
 "a1_6":  (119135, L + "a lone newsboy standing on a street corner in the morning light with a "
           "thin stack of folded papers under one arm, few passers-by, a shuttered storefront "
           "behind him with a completely blank plain board above the door, no sign, no writing. "
           + NOSIG + " " + INK),
 "a3_8":  (119136, L + "a dozen folded newspapers stacked and fanned across a wooden table, seen "
           "from the side so only the folded edges and creases show, no printed page facing the "
           "viewer, a hand resting on the top one. " + NOSIG + " " + INK),
 "a3_10": (119137, L + "one wide frame divided by depth, not by panels: in the near ground a "
           "railway conductor on a platform tilting his head up to look at the sky; mid ground a "
           "postmaster leaning out through a service window; far ground a farm family clustered "
           "at a dark lamplit farmhouse window. Winter dusk. No signs, no lettering anywhere. "
           + NOSIG + " " + INK),
 "a4_4":  (119138, L + "a single folded local newspaper lying face down on a diner counter beside "
           "a coffee cup and saucer, only the blank grey underside and the fold showing, a "
           "waitress's hand setting down the cup. " + NOSIG + " " + INK),
 "a4_8":  (119139, L + "a thin closed manila folder squared up on a plain wooden desk under a "
           "reading lamp, its cover completely blank, nothing else on the desk, no tab, no label, "
           "no writing. " + NOSIG + " " + INK),
 "a4_9":  (119140, L + "the interior of a small storefront local-history museum: a curator "
           "standing with his back to us facing a wall of small framed clippings and a pinned "
           "map stuck with pins, every framed item and the map left completely blank, no writing "
           "on the walls. " + NOSIG + " " + INK),
 "a5_5":  (119141, L + "a souvenir-shop shelf holding a felt pennant, a glass bottle, a foam "
           "novelty hat and a rack of keychains, every graphic and label on every item left "
           "completely blank, plain surfaces only, no writing. " + NOSIG + " " + INK),
 "a5_10": (119142, L + "one crisp modern broadsheet newspaper laid across one yellowed brittle "
           "old newspaper on a bright light-table, both seen at a steep raking angle from the "
           "side so no printed face is legible, only paper tone, edges and the crease. "
           + NOSIG + " " + INK),
 "a5_15": (119143, L + "two aged hands lowering the heavy hard cover of a large bound volume "
           "shut, dust lifting off the closing edge, a grey archival box open and waiting beside "
           "it on the table, no loose printed paper visible, nothing legible. " + NOSIG + " " + INK),
 "a3_22": (119144, L + "a single small torn scrap of plain blank paper lying alone on a bare "
           "wooden desk beside a dip pen, the paper completely blank, no ruled lines, no grid, "
           "no calendar, no printing of any kind. " + NOSIG + " " + INK),
 # --- register violations: restrained, NOT a horror poster ---
 "a4_3":  (119145, L + "seen from behind the wheel of a parked car at night, a tall thin grey "
           "humanoid figure standing perfectly still and upright at the far edge of the headlight "
           "beam among low concrete bunkers, its wings closed flat and folded against its back, "
           "not flying, not spread, a small distant restrained silhouette, no dramatic pose. "
           + NOSIG + " " + INK),
 "a4_11": (119146, L + "three plain small ink silhouettes of the same simple standing "
           "winged figure set in a row across a blank sheet, like a diagram: the left one small "
           "and roughly sketched, the middle one larger, the right one largest and more heavily "
           "embellished, plain white ground, no scenery, no dramatic pose, no writing. "
           + NOSIG + " " + INK),
 # --- weak reads ---
 "s4":    (119147, L + "three folded newspapers fanned out side by side on a dark wooden desk "
           "under a single hanging lamp, only their folded edges and creases showing, no printed "
           "faces, no writing, deep shadow around them. " + NOSIG + " " + INK),
 "a5_7":  (119148, L + "a tall polished chrome statue of a winged humanoid figure on a low stone "
           "plinth on a small-town sidewalk, filling much of the frame, a couple standing before "
           "it raising a camera, plain blank storefronts behind with no signs. " + NOSIG + " " + INK),
 "a5_8":  (119149, L + "three distinct small creature emblems mounted in a row on a plain plaster "
           "wall and nothing else: a carved horned spiked beast plaque, a winged figure "
           "silhouette stitched on a hanging felt pennant, and a small polished metal winged "
           "figurine on a bracket. " + NOSIG + " " + INK),
 "a4_5":  (119150, L + "a tall cast-iron newsroom teletype machine spooling a narrow paper "
           "ribbon down into a wire basket, an editor's hand reaching in to tear the ribbon, "
           "other desks and figures blurred in the background, the ribbon and all paper blank, "
           "no writing. " + NOSIG + " " + INK),
}

regen_log = []
for sid, (seed, prompt) in REGENS.items():
    dst = f"{OUT}/e03_{sid}.png"
    old = f"{OUT}/_superseded_e03_{sid}.png"
    if os.path.exists(dst) and not os.path.exists(old):
        os.rename(dst, old)
    r = flux.execute({"prompt": prompt, "model": "flux-pro/v1.1",
                      "width": 1280, "height": 720, "seed": seed, "output_path": dst})
    regen_log.append({"scene": sid, "new_seed": seed, "success": r.success,
                      "error": r.error, "reason": "guard/register/weak-read regen", "prompt": prompt})
    print(sid, r.success, r.error or "", "seed", seed, flush=True)

json.dump(regen_log, open(f"{OUT}/regen_log.json", "w"), indent=2)
ok = sum(1 for x in regen_log if x["success"])
print(f"--- regen {ok}/{len(regen_log)} ok  (~${ok*0.05:.2f}) ---", flush=True)
