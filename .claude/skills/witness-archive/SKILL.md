---
name: witness-archive
description: "Produce an episode of the Witness Archive dark-history YouTube channel — faceless, 8-20 minute, narrated. Locks the recurring character (The Witness), the two-register visual system, the cold-open-on-an-object device, the narration voice, and the validated image-generation contract, then drives the animated-explainer pipeline end to end. Trigger: /witness-archive. Use when the user wants a new episode, an episode idea, or anything for this channel."
trigger: /witness-archive
---

# /witness-archive

Production system for a **faceless dark-history YouTube channel**. Everything here is
locked and validated — do not re-derive it, re-litigate it, or "improve" it without
the user explicitly asking.

**Read these before doing anything:**
- `references/writing-style.md` — narration voice, hook formula, beat discipline
- `references/idea-generation.md` — how to find episodes that fit the device
- `references/stills/` — the locked visual targets. Look at them if present. **These are
  gitignored**, so on a fresh clone they will be absent; regenerate them by running the
  prompt recipe in §4 against the reference scenes, or pull them from a prior project run.
- `../../../styles/witness-archive.yaml` — the schema-valid playbook (authoritative for prompts)

---

## 1. The channel in one line

> Every episode opens on **one real physical object that still exists**, then pulls back
> to the dark history behind it.

Topic scope is deliberately **broad** — atrocities, industrial and engineering disasters,
human experimentation, origins of dangerous things. What stays narrow is the **device**.
The user pushed back on niching down and was right: none of the reference channels are
topically narrow either. Do not propose narrowing the niche.

**Reference channels analysed** (for calibration, never to copy):
| Channel | Format | Verdict |
|---|---|---|
| Ink Explainer | ink illustration, single narrator, 6-8 min, 200 wpm | closest model |
| Chat History | archival collage / crude cartoon, gamified counters | good hooks, wrong tone |
| Historically | full studio 2D character animation, 38-75 min | **out of reach — never chase** |

## 2. The Witness (character contract — INVIOLABLE)

A small faceless hooded spectral figure. Void hood, tattered cloak, hem above the ankles,
dark boots visible below it, carrying one amber lantern (`#E8A24B`).

- **Never** gains a face, eyes, or a mouth. The hood interior is pure void.
- **Never** speaks. It observes; the narrator narrates.
- **Never** changes silhouette between episodes.
- The lantern is the **only** saturated colour in any narrative frame, and it is always
  *emitted light*, never a painted fill.
- Staged **side-on**, off to one side, always **full-body from head to boots, never cropped
  and never dominating the frame**. A fixed proportional anchor ("one fifth of frame height")
  was tried and **no model holds it** — do not reintroduce one.

The user chose the spectral/wraith read **knowingly**, after being warned it may read as
fiction rather than factual history. That decision is made. Do not raise it again.

See `references/stills/character_sheet.png`.

## 3. Two registers

**Narrative register** — painterly ash-and-sepia environments, fresh per scene.
See `stills/narrative_tomb.png`, `narrative_ice.png`, `narrative_mine.png`.

**Explainer register** — white chalk on black slate, for any mechanism, map, timeline or
chain of causation. **Pure diagram — NO characters.** The Witness never appears here.
Rendering it as a white chalk outline was attempted twice and failed both times: the model
returned a shaded human being in a coat, not a drawing. Dropped 2026-07-28.
See `stills/chalk_diagram.png`.

Chalk scenes must also be **label-free by construction** — no numbered axes, no tally grids,
nothing that reads as data. Anything resembling a label renders as gibberish digits. Draw
curves, bars, outlines and shapes; composite every real label in the render layer.

The polarity inversion between registers is the channel's signature and the only hard cut
in the edit. Cut to chalk on a genuine explanatory beat — never for variety.

## 4. Image generation (VALIDATED — do not reorder)

**Model routing — split by register**, via `flux_image` at 1344×768:

| Register | Model | Rate | Why |
|---|---|---|---|
| Narrative | `flux-pro/v1.1` | $0.04/MP | holds the small-figure staging better than `dev` on interiors |
| Chalk | `flux/schnell` | $0.003/MP | line drawings need no more; 13× cheaper than `dev` |

`flux/dev` ($0.025/MP) was the earlier default, chosen on a landscape-only drift test; it
renders the Witness too large in interior scenes. `google_imagen` returns **HTTP 404 on every
call** — broken as of 2026-07, do not route to it.

**Prompt construction — order is load-bearing:**

```
<SCENE DESCRIPTION, one or two sentences>  +  <image_prompt_prefix from the playbook>
```

Scene text goes **FIRST**. This is not stylistic preference — it was established
empirically:

| Version | Result |
|---|---|
| v1 (character-first, 807 chars) | 6/8 on-model, weak silhouette, palette slid green |
| v2 (character-first + negation walls) | **catastrophic** — environments wiped to empty fog, lantern vanished entirely |
| **v3 (scene-first, 582 chars)** | **7/8 on-model, rich environments, lantern present in all 8** ✅ |

v2's failure mode is instructive: "no highlights, no rim light, darkest value" sat directly
upstream of "glowing amber lantern" and cancelled it. **Never stack negations near the
lantern clause.** FLUX has no negative prompts — describe what you want.

**Hard rules:**
- **Never generate text into an image.** Diffusion output is always gibberish. All on-screen
  type is composited in the render layer — crisp, correct, animatable, translatable.
- Scale is the loosest axis on every model. Budget re-rolls rather than fighting it in prose.
- **Don't demand a specific hero prop in a wide shot.** A wide establishes the room; an insert
  identifies the object. Asking for a legible "1918 wristwatch" in a wide produced a mantel
  clock, a pocket watch, a light bulb and a teapot across three rounds. Close-ups render it
  correctly first time — let them carry the identity.

## 5. Narration

**Two-phase, locked:** Kokoro `am_michael` (male, local, free) for drafts and samples so
iteration costs nothing → **ElevenLabs for the final cut**, for which the user has an API key
configured. Do not ship the draft voice. Worth sampling `bm_george` (UK male) against
`am_michael` — the British register suits the hushed documentary tone.

Target **~200 wpm** (matches the closest reference). An 8-minute episode is ~1,600 words;
a 20-minute episode ~4,000.

## 6. Pipeline

Use **`animated-explainer`** (`pipeline_defs/animated-explainer.yaml`, production-stable).

```
research → proposal → script → scene_plan → assets → edit → compose → publish
```

Gated (`human_approval_default: true`): **proposal, script, scene_plan, assets, publish.**
Approval is per-gate — an early "go ahead" never covers later gates. Read each stage's
director skill in `skills/pipelines/explainer/` **before** working that stage.

Composition runtime: both Remotion and HyperFrames are installed. Present both at proposal
and let the user lock it — silently defaulting is forbidden by `AGENT_GUIDE.md`.

## 7. Cost model (per 8-minute episode)

| Line | Cost |
|---|---|
| ~75 narrative frames @ 1.03 MP on `flux-pro/v1.1` | ~$3.09 |
| ~18 chalk frames @ 1.03 MP on `flux/schnell` | ~$0.06 |
| Narration (Kokoro `am_michael`, local) | $0.00 |
| Music bed (`pixabay_music`, no API key) | $0.00 |
| Re-rolls | ~$0.30 |
| **Total** | **~$3.15–3.50** |

ElevenLabs for the final-cut narration is additional and not costed here.

Announce provider, model, and sample-vs-batch before any paid call. Route through the
pipeline's `cost_tracker` — calling `flux_image` directly bypasses cost logging, which is
why every `cost_usd` in the existing manifests reads `0.0`.

## 8. Tooling gotchas (learned the hard way)

- **`character_rig_renderer` is a stub.** It hardcodes a smiley-face placeholder and ignores
  `rig_plan` artwork entirely. The `character_spec_generator → svg_rig_builder →
  pose_library_builder` chain produces valid artifacts but cannot render The Witness. The
  channel runs on generated characters, not rigs. Do not promise rigged animation.
- **`svg_rig_builder` returns wrapped output** (`{"rig_plan": {...}}`) and silently yields
  `characters: []` if you pass the wrapper back in, while still reporting `success: True`.
- **fal.ai bills FLUX by megapixel, not per image** — the dashboard reports no image count.
- `pose_library_builder` fills only face poses and stubs everything else.

## 9. Quality gates

Before any frame ships:
1. Could this belong to Ink Explainer? If yes, redo it.
2. Is the lantern the warmest thing in frame?
3. Is the Witness readable as a pure silhouette at thumbnail scale — and absent entirely
   from every chalk frame?
4. Is there any generated text in the image? If yes, regenerate.
5. Does the episode open on one concrete physical object that still exists?

## 10. Episode backlog

`.claude/skills/witness-archive/IDEAS.md` holds the running candidate list with the
artifact, territory, and a monetisation-risk note for each. Add to it whenever a
candidate surfaces; pull from it when starting an episode.
