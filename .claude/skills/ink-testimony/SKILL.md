---
name: ink-testimony
description: "Produce an episode of the Ink & Testimony narrative-history YouTube channel — faceless, 8-12 minute, narrated, hand-inked stills. Locks the custom ink visual style, the medium-first prompt contract, the continuous seed band, the narrator voice, the fast-cut scale model (2-6s per shot, ~130-170 shots), and the E01-E03 production lessons, then drives the animated-explainer pipeline end to end. Trigger: /ink-testimony. Use when the user wants a new episode, an episode idea, or anything for this channel."
trigger: /ink-testimony
---

# /ink-testimony

Production system for a **faceless narrative-history YouTube channel** rendered as
1920s pen-and-ink illustration. Everything here is **locked and validated** across
`sample_v2`, E01 (99 s, $1.73), E02 (~10 min, 81 beats) and E03 (~10.7 min, ~165
shots, ~$12). Do not re-derive it, re-litigate it, or "improve" it without the user
explicitly asking.

**Read before doing anything:**
- `references/style-lock.md` — the verbatim INK_STYLE / INK_STYLE_DARK blocks, the
  medium-first prompt contract, the seed band, anchor-frame reuse.
- `references/production-lessons.md` — the E01–E03 lessons to **apply without being
  asked**: TTS numerals, guard review + subject-accuracy pass on hero frames, FLUX
  writing text on anything paper-shaped, **2–6 s per shot pacing**, the
  explainer_compose traps + bespoke `eNN_compose.py`, MP3-padding desync, sidecar vs
  burned subtitles, composited date/place cards, pre-delivery verification.
- `../../../styles/ink-testimony.yaml` — the schema-valid playbook (authoritative for
  prompt blocks). Load with `load_playbook("ink-testimony")`.

Prior runs to mine for reusable assets: `projects/ink-testimony-e01/`,
`projects/ink-testimony-e02/`.

---

## 1. The channel in one line

> One physical object or record is treated as a **witness**; the episode reconstructs
> the dark history behind it and returns to the object at the close.

E01: a radium watch dial as the witness to the Radium Girls. E02: the postmortem
examination table as the witness across five man-eating-tiger cases and the colonial
bounty system behind them. The **device** (object-as-witness, chronological spine,
present-tense landing beat) is what stays fixed; the topic is open within
narrative/dark history.

## 2. Visual style (LOCKED — see `references/style-lock.md`)

Black-and-white pen-and-ink with soft gray brush washes on warm white paper, fine
cross-hatching, dry-brush texture, expressive hand-inked faces, 1920s editorial
illustration style, high contrast, matte paper grain.

- **The guard, verbatim, on every prompt:** `Full-bleed image, no border, no plate
  frame, no label. No text or numbers anywhere.`
- **Medium-first prompt order** (load-bearing): `"Pen-and-ink illustration with soft
  gray brush washes on warm white paper: <SCENE>. " + <optional reinforcement> +
  <INK_STYLE block>`. Character-/style-first ordering drifted to photographic in E01
  scene-08.
- **Dark register** (`INK_STYLE_DARK`, white ink on pure black) is a **meaning, not a
  mood** — injury, forensic, danger, violence beats only.
- **One continuous seed band across all episodes.** E01: 119000–119015. E02: 119020+.
  Continue upward; never reset.
- **Model:** `flux_image` → `flux-pro/v1.1` at 1280×720. Validated; `image_selector`
  fallbacks are `google_imagen` / `recraft` and would re-gate with the user.
- **Google Flow alternative (`google_flow_driver`) — opt-in only, never a silent
  swap.** Approved when the user explicitly asks for Flow or declines FLUX spend;
  read `skills/core/google-flow.md` and log the provider change in `decision_log`.
  The bridge export forwards this channel's `GENERATE: ` scene prompts **verbatim**
  — medium-first ordering and the full-bleed guard stay intact; never append
  cinematic slash commands or `--ar`. FLUX-only disciplines that do NOT transfer:
  the seed band (Nano Banana takes no seeds — anchor-frame reuse carries
  continuity instead) and the $0.05/frame cost line (Flow spends the user's
  Google AI plan credits; confirm with the user before batching). Output is 2752×1536, which
  is *better* for crop shots than FLUX's 1280×720.
- **Anchor-frame reuse:** hold one frame across consecutive same-location beats (E01
  held 17 beats on 8 frames). E01's anchors are topic-specific (dial / glow / bones /
  factory floor) — generate fresh for a new topic, don't force-fit them.
- **All on-screen text is composited in the render layer.** Act-break cards via
  `ffmpeg drawtext`, never AI-generated.

## 3. Narration (LOCKED)

ElevenLabs voice **`S9GPGBaMND8XWwwzxQXp`**, `eleven_multilingual_v2`, `stability
0.75`, `similarity_boost 0.9`, `style 0.1`, `speed 1.0`. Reused verbatim across
episodes for series continuity — do not swap without re-gating with the user.

**Spell out every number, date and figure in `provider_text`** ("nineteen thirty",
"four hundred and thirty-six", "ten thousand dollars"). `eleven_multilingual_v2`
misreads comma-grouped numerals — in E01 "1,600" was read aloud as "section".
Display and subtitle text keep proper numerals. **No audio tags.**

Kokoro local (`am_michael` / `bm_george`) is the free draft/sample voice; the
ElevenLabs voice above is the final cut only.

## 4. Scale & budget model

| Metric | Value |
|---|---|
| Pacing | **2–4 s per SHOT typical, 5–6 s hard max** (E03). The grammar is one still per shot, hard cut on the next narration start, so the narration clip length *is* the cut rhythm. |
| Beats | **short single sentences** (~2–5 s of speech). NEVER merge sentences into one clip — an 8–18 s clip on one still is the failure mode (E03 v1 shipped 59/87 shots over 6 s). |
| 10-minute episode | **~130–170 shots.** Multiple shots per narration clip are expected: cut to a new frame or a hard crop into a *different region* of the same still (reads as a separate shot; only works inside its own beat). |
| Structure | 5 acts, act-break title cards (`ffmpeg drawtext`); composited date/place cards for every cold date-and-place line (E02 device — plan them into the scene plan, don't bolt on later) |
| Frames generated | **~70–95** (crops + anchor reuse absorb the rest). Three eras/locations → the high end. |
| Narration clips | one per beat; decode to WAV before deriving any timing (MP3 LAME padding → ~3 s desync otherwise) |
| Cost (10 min) | **~$10–12** — `flux-pro/v1.1` ≈ $0.05/frame, regens inflate the call count ~1.3×; ElevenLabs ≈ **$0.60 / 1k characters** (size off characters, not words); music bed `pixabay_music` free |
| Cost reference | E01 $1.73 (99 s); E02 ~$8.20; E03 ~$12.0 (10.7 min, ~95 frames incl. regens + a re-cut) |
| Budget cap | **$12.00** unless the user says otherwise |

**Provider gate (binding)**: before the first image / music / TTS generation call —
samples included — present the provider options for that capability and get explicit
user confirmation (see `AGENT_GUIDE.md` → "Ask Before Generation Starts"). The locked
defaults above (FLUX, the ElevenLabs voice, pixabay music) count as confirmed only
while unchanged; any swap re-gates. Announce model and sample-vs-batch before any
paid call. Report spend at every gate; if a gate projects over the cap, pause and
tell the user before generating.

## 5. Pipeline

Use **`animated-explainer`** (`pipeline_defs/animated-explainer.yaml`,
production-stable).

```
research → proposal → script → scene_plan → assets → edit → compose → publish
```

**PAUSE AND ASK FOR APPROVAL at each gate — do not batch through them:**
research brief, **proposal packet, script, scene plan**, assets, publish. Approval is
per-gate; an early "go ahead" never covers later gates. Report spend at each gate and
stay under the cap. Read each stage's director skill in `skills/pipelines/explainer/`
**before** working that stage.

Composition runtime: this is a stills + zoompan + hard-cut + music render — **FFmpeg**.
Remotion/HyperFrames are installed; present them at proposal per `AGENT_GUIDE.md` but
the validated path for this channel is FFmpeg.

**Standardised runner (E04+):** `scripts/ink_testimony/` — two artifact-driven modules,
no per-episode Python:

```
python -m scripts.ink_testimony.assets  --project projects/ink-testimony-eNN --mode sample|batch|regen
python -m scripts.ink_testimony.compose --project projects/ink-testimony-eNN
```

`assets.py` reads `scene_plan.json` (prompts, `source`) + `script.json`
(`provider_text`); seeds continue the band automatically; idempotent; writes previews
+ contact sheets. `compose.py` reads `scene_plan.json` + `script.json` + `ink_config.json`
(+ optional `cut_plan.json` for `detail_frames` / `date_cards`), builds the timeline,
**slices every beat to 2–6 s sub-shots by default** (the re-cut behaviour is built in),
handles act-cards-have-their-own-narration, burns or sidecars subtitles per config, and
runs the timing assertion + ffprobe + per-shot hold report. It reuses
`explainer_compose.py`'s primitives (`zoompan_segment`, `card_segment`, `dur`,
`transcribe_section`) but not its broken `main()`. Validated by reproducing E03
(643.19 s, 165 shots, mean 3.9 s, 0 over 6 s) from artifacts alone.

The `scripts/e0N_*.py` scripts are the pre-standardisation reference, kept for history.
Config: `ink_config.json` per episode (`seed_band_start`, `burn_subtitles`, timing);
defaults fall back to `styles/ink-testimony.yaml`. See `references/production-lessons.md` §5.

## 6. Artifacts & logging

Project dir `projects/ink-testimony-eNN/` with the E01/E02 artifact layout —
`research_brief`, `proposal_packet`, `script`, `scene_plan`, `decision_log`, all
schema-validated against `schemas/artifacts/`. Log every gate approval, every
regeneration (with **seed + reason**), and every cost event in `decision_log.json`.

## 7. Deliverable

Full episode MP4 (720p; zoompan stills, hard cuts, music bed, fade-in/out bookends;
subtitles burned OR a sidecar `subtitles.srt` per the episode brief) + all artifacts +
a spot-check contact sheet (opening frame, one per act, each act-break card, closing
fade, each hero/dark-register frame) for the user's review.

## 8. Quality gates

Before any frame ships:
1. Does it obey the guard — full-bleed, no border, no plate frame, no label, no text
   or numbers? (FLUX writes faux headlines on any newspaper/storefront/wall/calendar —
   remove the object, crop it out, or composite real text; see production-lessons §3.)
2. Is it pen-and-ink with gray washes on warm white paper, not photographic or 3D?
3. If it's white-on-black, is the beat genuinely an injury / forensic / danger beat —
   and is the white line work clearly legible (not a near-solid black frame)?
4. **Hero frames (the 3–5 highest-stakes beats): is this actually the subject the
   narration describes?** The guard checklist does not catch "wrong thing" — E03
   shipped a *sinking ocean liner* for the Silver Bridge collapse in v1.
5. Any generated signature, monogram, caption or drawn border? Regenerate.

Before the episode ships:
6. `ffprobe` duration/streams sane; segment-duration sum == audio timeline; when
   sidecar subtitles, confirm **no subtitle stream** and no burned caption on any
   spot frame.
7. Spot-check frames extracted and eyeballed: opening, one per act, each card,
   closing fade, each hero frame.
8. **Per-shot hold report: mean 3–4 s, max ≤ 6 s, zero over 6 s. No image repeated
   across a beat boundary.** (E03 v1 failed this — 59/87 shots over 6 s.)
9. Every number in the narration audio is spoken as words, not letters or "section".
