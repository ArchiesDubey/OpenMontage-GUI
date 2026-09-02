# Ink & Testimony — Style Lock

Do not re-derive. Reuse the validated blocks below verbatim. Source of record:
`scripts/e01_generate_assets.py` (blocks), `scripts/e02_regen_failures.py`
(reinforcement clauses), `styles/ink-testimony.yaml` (schema-valid copy).

## INK_STYLE (light register — the default)

```
Historical narrative illustration in black-and-white pen-and-ink with soft gray
brush washes on warm white paper, fine cross-hatching and dry-brush texture,
expressive hand-inked faces, 1920s editorial illustration style, high contrast,
matte paper grain. No text or numbers anywhere. Full-bleed image, no border, no
plate frame, no label.
```

## INK_STYLE_DARK (dark register — injury / forensic / danger / violence beats ONLY)

```
Historical narrative illustration rendered as fine white ink lines on a pure black
background, delicate cross-hatching, 1920s editorial style, high contrast. No text
or numbers anywhere. Full-bleed image, no border, no plate frame, no label.
```

The polarity flip is a **meaning**, not a mood. Use it for a wound, a postmortem
finding, an attack, a forensic detail. Never for variety.

## Prompt construction — order is load-bearing

```
"Pen-and-ink illustration with soft gray brush washes on warm white paper: "
  + <SCENE DESCRIPTION, one or two sentences>. "
  + <optional reinforcement clauses, see below>
  + <INK_STYLE or INK_STYLE_DARK block>
```

**State the MEDIUM FIRST, the scene second, the style block last.** Character-first or
style-first ordering caused a photographic-drift failure in E01 scene-08 (an empty
dentist's chair rendered as a photo). The medium sentence at the front anchors the
model before it reads the scene.

FLUX has **no negative prompts**. For a stubborn frame, append *positive* reinforcement
to the scene sentence (never a "no X" that names X in isolation):

- Signatures / borders / lettering creeping in:
  `Absolutely no artist signature, no monogram, no lettering, no banknote text, no
  drawn border line or picture frame anywhere in the image.`
- Dark-register frame coming back as a near-solid black rectangle:
  `The white ink linework must be clearly visible and legible against the black
  background — do not render a solid or near-solid black frame with no visible subject.`

## Seeds — one continuous band across ALL episodes

| Episode | Band used |
|---|---|
| E01 | 119000–119015 |
| E02 | 119020+ (119020/119021 were the rejected/approved s31 samples; batch started 119022) |
| E03+ | continue upward from the last seed E02 reached |

Never reset the band per episode. A regenerated frame gets a **fresh** seed (not the
failed one) and the seed + reason is logged in `decision_log.json` / the run's
`regen_log.json`.

## Model & size

`flux_image` → `model: "flux-pro/v1.1"`, `width: 1280`, `height: 720`. Validated in
E01 and E02. `image_selector` fallbacks (`google_imagen`, `recraft`) would lose style
continuity — re-gate with the user before switching.

Scale and framing are the loosest axes on `flux-pro/v1.1`. Budget a re-roll with a
fresh seed rather than fighting composition in prose.

## Anchor-frame reuse

Hold one generated frame across consecutive beats in the same location. E01 covered 17
beats with 8 frames; E02 scaled the same ratio up. Regenerate only when the location
or subject genuinely changes.

**E01's anchor frames are topic-specific** — the watch dial, the green glow, the
exhumed bones, the factory floor. They do not transfer to a new episode's subject.
For a new topic, generate fresh frames; only pull an E01/E02 asset forward when a beat
genuinely depicts the same thing.

## What never goes in an image

Text, numerals, labels, axis ticks, tally marks, signatures, monograms, drawn borders,
plate frames. Diffusion renders all of these as gibberish. Every on-screen element of
that kind — act-break cards, subtitles, stat callouts — is composited in the render
layer as real, correct, animatable type. Act-break cards use `ffmpeg drawtext`.
