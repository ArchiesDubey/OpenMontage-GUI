# Image Generation Usage for OpenMontage

> Sources: OpenAI GPT Image documentation, FLUX/BFL API documentation, existing Layer 3 skills
> at `.agents/skills/flux-best-practices/` and `.agents/skills/bfl-api/`

## Quick Reference Card

```
FLUX RESOLUTION:  1920x1088 (16:9) | 1088x1920 (9:16) — must be multiples of 16
MAX TOTAL:        4 megapixels (width x height)
CONSISTENCY:      Use hero image as input_image for subsequent frames
STYLE SYSTEM:     Derive from subject + audience + tone, then adapt per scene
BATCH STRATEGY:   Hero at max quality → iterate with klein → final pass with pro
```

## Resolution for Video Frames

All FLUX dimensions **must be multiples of 16**. Maximum total is 4MP.

| Target | FLUX Resolution | Cost (FLUX.2 pro) |
|--------|----------------|-------------------|
| YouTube 16:9 | `1920x1088` | $0.03/image |
| YouTube 4K | `3840x2160` | Requires pro/max |
| TikTok/Reels 9:16 | `1088x1920` | $0.03/image |
| Square 1:1 | `1024x1024` | $0.03/image |
| Thumbnail | `1280x720` | $0.03/image |

## Maintaining Visual Consistency

The biggest challenge: making 8-12 generated images look like they belong in the same video.

### Strategy 1 — Shared Visual System (Always Use)

Define a shared visual system for the project first, then adapt it per scene.
Capture the project's:

- dominant mood and texture,
- palette direction,
- lighting bias,
- rendering medium,
- character/environment consistency anchors.

The playbook's `image_prompt_prefix` is source material, not something to paste
verbatim into every prompt. Distill it into a shorter scene-appropriate anchor.

### Strategy 2 — Hero Reference Image (Recommended)

1. Generate one "hero" image at maximum quality (`FLUX.2 [max]`, $0.07)
2. Use it as `input_image` for all subsequent frames:

```
Frame 1: T2I with detailed prompt → hero.png
Frame 2: I2I with hero.png + "Same style, camera pans right to show..."
Frame 3: I2I with hero.png + "Same style, zoomed in on..."
```

FLUX.2 supports up to 4 references (klein) or 8 references (pro/max/flex). Reference by number: "The character from image 1 in the environment from image 2."

### Strategy 3 — Seed Locking

Use the same `seed` parameter across generations with similar prompts. Produces similar compositions but is fragile to prompt changes — use as supplement, not primary strategy.

### Strategy 4 — Locked Style Block, Scene Text First

Strategies 1-3 are for a single video. A **series** — a channel with a recurring character or
a house look that must survive dozens of images across many episodes — needs the opposite of
Strategy 1's "distill, don't paste": a short block that is prepended **verbatim** to every
prompt and never re-authored per scene. The `witness-archive` playbook is the reference
implementation (`asset_generation.image_prompt_prefix`, plus a separate `diagram_style` block
for its second register).

When a playbook supplies a locked block, the order is:

```
<scene description, 1-2 sentences>  +  <playbook image_prompt_prefix>
```

**Scene text goes first. Ordering is load-bearing, not cosmetic.** In a matched-seed A/B across
8 environments, scene-first scored 7/8 on-model with rich, distinct environments. A
character-first variant scored 6/8 with weak silhouettes and palette drift.

**Never stack negations upstream of the thing you want.** A third variant put a wall of negations
("no highlights, no rim light, darkest value") immediately before "glowing amber lantern." It
wiped the environments to empty fog *and* deleted the lantern. FLUX has no negative-prompt field —
everything you write is content the model tries to honor, and a negation adjacent to a positive
clause reads as a modifier of it. Describe what should be present, not what should be absent.

**Do not anchor scale proportionally.** "One fifth of frame height" held on no FLUX endpoint
tested. Use qualitative wording ("full-body, never cropped, never dominating the frame"), expect
roughly 1 in 8 frames to come back oversized, and re-roll rather than re-prompt — scale is the
loosest axis and re-prompting for it costs the environments.

Keep locked blocks short. The 582-character block outperformed the 807-character one.

## Prompt Construction — 3-Part Contextual Approach

**Do NOT copy the playbook's `image_prompt_prefix` verbatim into every prompt.** That's what makes all scenes look the same. Instead, build each prompt from 3 contextual layers:

### Part 1: Scene-Specific Style Direction (from shot_language + texture_keywords)

Use the scene's `shot_language` fields to set camera and lighting:
```
[SHOT SIZE from shot_language.shot_size, e.g., "medium close-up"].
[LIGHTING from shot_language.lighting_key, e.g., "golden hour warm light"].
[DEPTH from shot_language.depth_of_field, e.g., "shallow depth of field with bokeh"].
[TEXTURE from scene.texture_keywords, e.g., "film grain, warm tones"].
```

If the scene has no shot_language, fall back to the template below.

### Part 2: Playbook Consistency Anchor (adapted, not verbatim)

Extract the ESSENCE of the playbook's visual language — don't copy the prefix. For example:
- Playbook says "Clean, minimal illustration with soft shadows, muted color palette" → Adapt to: "muted color palette, soft shadows"
- Playbook says "Bold flat motion graphics, vibrant gradients" → Adapt to: "vibrant flat style"

The anchor keeps scenes visually coherent without making them identical.

### Part 3: Scene Description

The actual content of the scene. Be specific — replace generic words with concrete details.

**BAD:** "A person using a computer in a modern office"
**GOOD:** "Software developer in a dimly lit home office, blue monitor glow reflecting off glasses, desk cluttered with energy drinks and sticky notes"

### Full Prompt Example (with shot_language)

```
Medium close-up, golden hour warm lighting, shallow depth of field.
Muted earth tones, soft shadows.
Beekeeper in white protective gear lifting a frame dripping with honey,
late afternoon sun catching golden droplets, lavender field blurred
in the background. Film grain, warm amber tones.
16:9 aspect ratio.
```

### Fallback Template (when no shot_language is available)

```
[ADAPTED STYLE ANCHOR from playbook — 5-10 words, not the full prefix].
[SCENE DESCRIPTION: specific subject, action, environment].
[LIGHTING: golden hour / overcast / studio softbox / dramatic side-light].
[COMPOSITION: wide shot / medium shot / close-up / overhead / isometric].
[CAMERA: Shot on [camera] with [lens] at [aperture]] (for photorealistic only).
16:9 aspect ratio.
```

### Using lib/shot_prompt_builder.py

For programmatic prompt construction, use the shot prompt builder which automates the 3-part approach:

```python
from lib.shot_prompt_builder import build_shot_prompt
prompt = build_shot_prompt(scene, style_context=playbook_data)
```

This converts the structured shot_language fields into natural-language prompts
optimized for image/video generation providers.

### Style-Specific Prompt Patterns

| Style | Prompt Pattern |
|-------|---------------|
| **Flat illustration** | "Flat vector illustration, bold colors, clean edges, no gradients, white background" |
| **Isometric** | "Isometric 3D illustration, 30-degree angle, clean geometric shapes, soft shadows" |
| **Photorealistic** | "Photorealistic, shot on Canon EOS R5 with 85mm f/1.4, shallow depth of field" |
| **Diagram-style** | "Technical diagram, labeled components, clean lines, minimal color, white background" |
| **Watercolor** | "Soft watercolor illustration, muted tones, visible brush strokes, paper texture" |

## Text In Images — Hard Rule

**Never ask a diffusion model for on-screen text.** Not titles, not labels, not axis ticks, not
dates, not numbers. The output is gibberish, it is gibberish inconsistently, and it cannot be
corrected by re-rolling or by better prompting. Every generated frame should carry the instruction
`No text or numbers anywhere.`

All on-screen type composites in the render layer — Remotion `text_card` / overlays, HyperFrames
blocks, or FFmpeg subtitle burn. Type added there is crisp, correct, animatable, translatable,
and editable after the image is final.

**Diagram-style frames are the highest-risk case.** Anything that *resembles* type — chart axes,
tally marks, timeline ticks, callout leaders, unit markers — pulls the model toward rendering
nonsense digits even when no text was requested. Design diagram frames **label-free**: generate
the marks, lines, and schematic shapes only, and composite every label as real type. If a diagram
cannot carry its meaning without labels baked in, it is the wrong tool — use `diagram_gen` or a
Remotion chart scene instead.

## Batch Generation Strategy

### FLUX endpoint routing (fal.ai, via `flux_image`)

Route by what the frame actually needs, not by a single project-wide default. `flux_image`
exposes `model` — `flux-pro/v1.1` (default), `flux/dev`, `flux-pro`:

| Endpoint | Approx cost | Use for |
|----------|------------|---------|
| `flux-pro/v1.1` | ~$0.04/MP | Frames where composition and figure scale must hold — a small subject staged inside a large environment |
| `flux/dev` | ~$0.025/MP | General narrative frames. ~37% cheaper, near-equivalent on painterly/illustrative styles |
| `flux/schnell` | ~$0.003/MP | High-volume, low-complexity frames (flat diagrams, chalk boards, texture plates). **Not in the `flux_image` `model` enum today** — reachable only by extending the tool |

**fal.ai bills FLUX by megapixel, not per image**, and the dashboard reports no image count.
Budget from total megapixels: a 1344x768 frame is ~1.03 MP. Long-form reference point — a
~10-minute episode at 93 images on mixed routing came to ~$3.15 including re-rolls.

Always route paid generation through the pipeline's `cost_tracker`. Calling `flux_image`
directly bypasses cost logging and leaves `cost_usd: 0.0` in the manifests.

### FLUX.2 quality tiers

| Phase | Model | Cost/Image | Purpose |
|-------|-------|-----------|---------|
| 1. Style guide | FLUX.2 [max] | $0.07 | One hero image, maximum quality |
| 2. Storyboard iteration | FLUX.2 [klein] 9B | $0.015 | Rapid variations during planning |
| 3. Final frames | FLUX.2 [pro] | $0.03 | Re-generate finals with hero as reference |

**Rate limit:** 24 concurrent requests max. Pipeline accordingly.

**Budget for 8-image explainer:** $0.07 (hero) + $0.12 (8x klein iterations) + $0.24 (8x pro finals) = ~$0.43

## Common Pitfalls

1. **Text in images** — never request it, and add `No text or numbers anywhere` to the prompt. See "Text In Images — Hard Rule" above; diagram-style frames are the trap
2. **Hands and fingers** — AI image models still struggle. Avoid prompts requiring detailed hand poses
3. **Inconsistent characters** — Without reference images, the same character will look different each time. Always use the hero reference strategy
4. **Over-prompting** — Long, complex prompts produce unpredictable results. Keep to 2-3 sentences
5. **Over-unifying prompts** — Forcing the exact same style phrase into every prompt makes scenes look samey. Keep the visual system consistent, but let each scene express its own subject, shot, and emotional beat.

## Applying to OpenMontage

When using the `image_selector` tool in the asset stage:

1. **Design the visual system first** from the proposal or custom playbook: mood, palette, texture, motion energy
2. **Generate a hero image first** at highest quality, use as reference for all others
3. **Use `1920x1088`** for 16:9 video frames (FLUX multiple-of-16 requirement)
4. **Never request text in images** — add text overlays in the compose stage
5. **Budget check** — estimate total image cost before generating; switch to local diffusers if over budget
6. **Iterate with klein** during planning, finalize with pro
7. **Keep prompts to 2-3 sentences** — scene-specific camera/lighting + adapted visual anchor + concrete subject
8. **Match the scene plan** — each image maps to a specific scene in the script
