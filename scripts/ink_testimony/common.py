"""Shared constants, config loading, seed-band, and preview helpers for the
standardised Ink & Testimony pipeline. LOCKED values (voice, style blocks,
model) live here verbatim -- see .claude/skills/ink-testimony/references/
style-lock.md and production-lessons.md."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PLAYBOOK = REPO / "styles" / "ink-testimony.yaml"

# ------------------------------------------------------------------ LOCKED
FLUX_MODEL = "flux-pro/v1.1"
FLUX_W, FLUX_H = 1280, 720
FLUX_UNIT_USD = 0.05                       # per frame, E01-E03 actuals

TTS_VOICE_ID = "S9GPGBaMND8XWwwzxQXp"      # series-continuity voice -- do NOT swap
TTS_MODEL = "eleven_multilingual_v2"
TTS_PARAMS = dict(stability=0.75, similarity_boost=0.9, style=0.1, speed=1.0)
TTS_USD_PER_1K_CHARS = 0.60               # ~E02 actual; size the budget off chars

INK_STYLE = (
    "Historical narrative illustration in black-and-white pen-and-ink with soft gray brush "
    "washes on warm white paper, fine cross-hatching and dry-brush texture, expressive "
    "hand-inked faces, 1920s editorial illustration style, high contrast, matte paper grain. "
    "No text or numbers anywhere. Full-bleed image, no border, no plate frame, no label."
)
INK_STYLE_DARK = (
    "Historical narrative illustration rendered as fine white ink lines on a pure black "
    "background, delicate cross-hatching, 1920s editorial style, high contrast. No text or "
    "numbers anywhere. Full-bleed image, no border, no plate frame, no label."
)
LIGHT_OPENER = "Pen-and-ink illustration with soft gray brush washes on warm white paper: "
DARK_OPENER = "Pen-and-ink illustration with fine white ink lines on a pure black background: "
NO_LETTERING = (
    "Absolutely no artist signature, no monogram, no lettering, no headline type, no banner "
    "text, no words, no numerals, no drawn border line or picture frame anywhere in the image."
)
NO_BLACKOUT = (
    "The white ink linework must be clearly visible and legible against the black background "
    "-- do not render a solid or near-solid black frame with no visible subject."
)
BLANK_PAPER = (
    "Every sheet of paper, every newspaper page, every book cover, spine and label in the "
    "frame is completely blank: no printing, no headlines, no words, no numerals, no masthead, "
    "no column text, only plain uniform paper tone and the texture of the ink drawing itself. "
    + NO_LETTERING
)
_PAPER_KEYS = (
    "paper", "press", "broadsheet", "headline", "clipping", "newsroom", "teletype", "notice",
    "letter", "type", "postcard", "book", "nameplate", "calendar", "layout", "newspaper",
    "masthead", "front page", "volume", "page", "pamphlet", "pigeonhole",
)
_MUSIC_QUERY = "sad somber dark ambient orchestral documentary"

# ------------------------------------------------------------------ config
DEFAULTS = {
    "seed_band_start": 119000,
    "burn_subtitles": True,
    "music_query": _MUSIC_QUERY,
    "timing": {"lead": 0.7, "gap": 0.5, "card_gap": 0.8, "tail": 5.0},
    "music": {"volume": 0.14, "fade_in": 1.5, "fade_out": 3.0},
    "fade": {"in_first": 0.8, "out_last": 2.5},
    "pacing": {"min_shot": 2.5, "max_shot": 5.8, "target_shot": 4.0},
    "fps": 25,
    "transcribe_model": "large-v3",
}


def _deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def _playbook_defaults() -> dict:
    """Pull the few numbers the playbook owns so config stays in one place."""
    try:
        import yaml  # noqa
        pb = yaml.safe_load(PLAYBOOK.read_text())
        m = pb.get("motion", {}).get("pacing_rules", {})
        a = pb.get("audio", {})
        return {
            "music_query": a.get("music_mood", _MUSIC_QUERY),
            "music": {"volume": a.get("music_volume", 0.14)},
            "pacing": {
                "min_shot": m.get("min_shot_hold_seconds", 2.5),
                "max_shot": m.get("max_shot_hold_seconds", 6.0),
                "target_shot": m.get("typical_shot_hold_seconds", 4.0),
            },
        }
    except Exception:
        return {}


def load_project(project: str | Path):
    """Return (proj, assets_dir, cfg, script, scene_plan, cut_plan)."""
    proj = Path(project).resolve()
    cfg = _deep_merge(DEFAULTS, _playbook_defaults())
    cfg_path = proj / "ink_config.json"
    if cfg_path.exists():
        cfg = _deep_merge(cfg, json.loads(cfg_path.read_text()))
    ep = cfg.get("episode") or proj.name.split("-")[-1]
    cfg["episode"] = ep
    assets_dir = proj / cfg.get("assets_dir", f"assets/{ep}")
    assets_dir.mkdir(parents=True, exist_ok=True)
    script = json.loads((proj / "artifacts" / "script.json").read_text())
    scene_plan = json.loads((proj / "artifacts" / "scene_plan.json").read_text())
    cp_path = proj / "cut_plan.json"
    cut_plan = json.loads(cp_path.read_text()) if cp_path.exists() else {}
    return proj, assets_dir, cfg, script, scene_plan, cut_plan


# ------------------------------------------------------------------ prompts
def build_prompt(scene: dict, dark: bool, paper_subject_ids: set[str]) -> str:
    """Reconstruct the medium-first FLUX prompt from a scene's description.
    scene_plan already stores the full prompt in required_assets[0].description
    (prefixed 'GENERATE: '); if present we use it verbatim. Otherwise we build
    it from the human 'description' text + the locked blocks."""
    ra = (scene.get("required_assets") or [{}])[0]
    desc = ra.get("description", "")
    if desc.startswith("GENERATE: "):
        return desc[len("GENERATE: "):]
    # fall back: build from the scene description sentence
    sid = scene.get("script_section_id", scene.get("id", ""))
    txt = scene.get("description", "").split(":", 1)[-1].strip().rstrip(".") + ". "
    if dark:
        return DARK_OPENER + txt + NO_BLACKOUT + " " + INK_STYLE_DARK
    paper = any(k in txt.lower() for k in _PAPER_KEYS)
    reinforce = (BLANK_PAPER + " ") if paper else ""
    framing = ""
    if sid in paper_subject_ids:
        framing = ("The printed face of the paper is turned away from the viewer or seen at a "
                   "steep raking angle, so no text surface is legible; focus on the paper's "
                   "edges, folds, brittleness and the hands. ")
    return LIGHT_OPENER + txt + framing + reinforce + INK_STYLE


# ------------------------------------------------------------------ seed band
def seed_iter(assets_dir: Path, cfg: dict, log_names=("generation_log.json", "regen_log.json",
                                                      "recut_frames_log.json", "sample_log.json")):
    """Continuous upward seed band across ALL episodes. Start = max(seen)+1 or
    cfg['seed_band_start']. Never resets."""
    seen = set()
    for name in log_names:
        p = assets_dir / name
        if not p.exists():
            continue
        try:
            blob = json.loads(p.read_text())
        except Exception:
            continue
        for v in _walk_seeds(blob):
            seen.add(v)
    start = max(seen) + 1 if seen else cfg["seed_band_start"]
    n = start
    while True:
        yield n
        n += 1


def _walk_seeds(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("seed", "new_seed") and isinstance(v, int):
                yield v
            else:
                yield from _walk_seeds(v)
    elif isinstance(o, list):
        for x in o:
            yield from _walk_seeds(x)


# ------------------------------------------------------------------ previews
def dur(path) -> float:
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True).stdout.strip() or 0.0)


def make_preview(png: Path, out: Path, width=480):
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(png),
                    "-vf", f"scale={width}:-1", "-q:v", "5", str(out)], check=True)


def contact_sheet(previews: list[Path], out: Path, order: list[str] | None = None,
                  cols=5, tw=320, th=180, per=15):
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return []
    files = list(previews)
    if order:
        rank = {sid: i for i, sid in enumerate(order)}
        files.sort(key=lambda p: rank.get(p.stem.replace("e03_", "").replace("_preview", ""), 999))
    sheets = []
    for gi in range(0, len(files), per):
        chunk = files[gi:gi + per]
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw, rows * (th + 16)), "#1c1c1c")
        d = ImageDraw.Draw(sheet)
        for i, f in enumerate(chunk):
            im = Image.open(f).convert("RGB").resize((tw, th))
            x, y = (i % cols) * tw, (i // cols) * (th + 16)
            sheet.paste(im, (x, y + 16))
            d.text((x + 3, y + 2), f.stem, fill="#eee")
        sp = out.parent / f"{out.stem}_{gi // per + 1}.jpg"
        sheet.save(sp, quality=82)
        sheets.append(sp)
    return sheets
