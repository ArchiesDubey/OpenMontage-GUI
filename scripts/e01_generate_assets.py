"""E01 asset generation: 8 ink frames + 14 narration clips + music bed.

Per scene_plan.json + script.json + proposal_packet production plan.
Reuses 6 approved sample frames; text_card scenes (11, 13) get no image —
compose renders drawtext overlays natively.
"""
import json
import os

from tools.tool_registry import registry

registry.discover()

OUT = "projects/ink-testimony-e01/assets/e01"
os.makedirs(OUT, exist_ok=True)

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

# scene_id -> (filename, prompt, dark_treatment)
FRAMES = {
    "scene-03": ("e01_undark_jars.png",
        "A 1920s factory shelf still life: small ceramic paint jars, tin boxes, "
        "and a fine camel-hair brush resting across an open jar, eye-level.", False),
    "scene-06": ("e01_foreman.png",
        "Seen past the shoulder of a 1920s factory foreman standing with folded "
        "arms at the end of a long workbench, rows of young women painting watch "
        "dials beyond him.", False),
    "scene-07": ("e01_lead_screen.png",
        "A 1920s chemist seen through the viewing window of a heavy lead screen, "
        "long tongs holding a faintly glowing sample, protective gear, laboratory "
        "darkness around him.", True),
    "scene-08": ("e01_dentist_chair.png",
        "An empty 1920s dentist's chair in a dark room, a single glass x-ray plate "
        "leaning against the wall catching thin light, heavy cross-hatched shadow.", False),
    "scene-10": ("e01_courtroom.png",
        "Five young women in dark 1920s coats and hats seated in a courtroom bench "
        "row, one leaning her head on another's shoulder, gallery shadows behind "
        "them, seen slightly from the side.", False),
    "scene-12": ("e01_settlement_desk.png",
        "A lawyer's desk insert: folded legal documents, a fountain pen, and a "
        "single watch dial face beside them under harsh window light.", False),
    "scene-14": ("e01_lab_ledgers.png",
        "Stacked laboratory ledger books beside brass measurement instruments on "
        "a workbench, decades of records, soft window light.", False),
    "scene-15": ("e01_brush_sill.png",
        "A single worn fine paint brush resting on a wooden windowsill, bristles "
        "frayed, long soft shadow, quiet emptiness.", False),
}

SCRIPT = json.load(open("projects/ink-testimony-e01/artifacts/script.json"))
SECTIONS = {s["id"]: s for s in SCRIPT["sections"]}

flux = registry.get("flux_image")
tts = registry.get("elevenlabs_tts")
music = registry.get("pixabay_music")

log = {"images": {}, "narration": {}, "music": {}}

for scene_id, (fname, desc, dark) in FRAMES.items():
    style = INK_STYLE_DARK if dark else INK_STYLE
    seed = 119000 + len(log["images"])
    r = flux.execute({
        "prompt": desc + " " + style,
        "model": "flux-pro/v1.1",
        "width": 1280,
        "height": 720,
        "seed": seed,
        "output_path": f"{OUT}/{fname}",
    })
    log["images"][scene_id] = {"file": fname, "seed": seed, "success": r.success,
                               "error": r.error}
    print(scene_id, "image:", r.success, r.error or "")

for sid in sorted(SECTIONS):
    sec = SECTIONS[sid]
    r = tts.execute({
        "text": sec["delivery_cues"]["provider_text"],
        "voice_id": "S9GPGBaMND8XWwwzxQXp",
        "model_id": "eleven_multilingual_v2",
        "stability": 0.75,
        "similarity_boost": 0.9,
        "style": 0.1,
        "speed": 1.0,
        "output_path": f"{OUT}/{sid}_narration.mp3",
    })
    log["narration"][sid] = {"success": r.success, "error": r.error}
    print(sid, "tts:", r.success, r.error or "")

r = music.execute({
    "query": "sad somber dark ambient piano documentary",
    "min_duration": 90,
    "max_duration": 300,
    "output_path": f"{OUT}/music_bed.mp3",
})
log["music"] = {"success": r.success, "error": r.error}
print("music:", r.success, r.error or "")

json.dump(log, open(f"{OUT}/generation_log.json", "w"), indent=2)
ok = (all(v["success"] for v in log["images"].values())
      and all(v["success"] for v in log["narration"].values())
      and log["music"]["success"])
print("DONE" if ok else "PARTIAL/FAILED — see generation_log.json")
