# Standardized Prompts: [STYLE: INK-EXPLAINER / 2D VECTOR]

> [!IMPORTANT]
> **STYLE BOUNDARY NOTICE**
> These prompts are strictly bound to the **Ink Explainer / 2D Minimalist Vector ("Egghead")** visual identity. 
> * **Style ID:** `minimalist-explainer`
> * **Visual Signature:** Pure white round head, bold black ink outlines, flat color fills, stick/tube limbs, 3-element yellow-text thumbnails.
> * If you want to create or use a *different* visual style in the future (e.g., 3D Cinematic, Motion Graphics, or Realistic Documentary), create a separate skill and **do not** use the `minimalist-explainer` tag.

---

## Prompt 1: [STYLE: INK-EXPLAINER] URL Reference $\rightarrow$ Standardized Re-Skin

Use this when you have an existing YouTube video and want to transpose its narrative structure into the **Ink Explainer 2D Vector style** without back-and-forth style negotiations.

```markdown
[STYLE LOCK: INK-EXPLAINER / 2D MINIMALIST VECTOR]
Skill: minimalist-explainer

I want to adapt this reference video into our standardized Ink Explainer (2D Vector Egghead) format:
- Reference URL: [PASTE YOUTUBE URL HERE]
- Target Topic: [SAME AS VIDEO / OR YOUR NEW TOPIC HERE]
- Target Length: [e.g., 10 minutes / ~1,600 words]

Strict Production Instructions:
1. Activate the `minimalist-explainer` skill.
2. Extract the core paradox, hook mechanic, and beat pacing from the reference URL.
3. Transpose that narrative momentum strictly into the Ink Explainer style:
   - Apply the 4-Act Explainer Architecture from `script-blueprints.md`.
   - Voice cadence: 40-40-20 sentence rhythm (target 180 WPM for history/society, 130 WPM for deep science).
   - Character Rig: Configure the topic-agnostic "Egghead" avatar (define headwear, outfit, and prop using `character-system.md`).
4. Output Deliverables:
   - Complete Narration Script with bracketed visual cue tags: [Visual: Character State / Prop / Cut].
   - 6-8 Keyframe Image Prompts formatted with the exact FLUX/Midjourney tokens from `visual-prompts.md`.
   - The 3-Element Thumbnail Blueprint (Emotive Face + Striking Prop + 1-3 Word Bold Yellow Title).

Do not deviate into realistic, 3D, or other styles. Maintain 100% fidelity to the minimalist-explainer specification.
```

---

## Prompt 2: [STYLE: INK-EXPLAINER] Raw Topic $\rightarrow$ Full Production Package

Use this when you have a fresh idea or topic and want a complete, ready-to-produce package in the **Ink Explainer 2D Vector style** in a single autonomous run.

```markdown
[STYLE LOCK: INK-EXPLAINER / 2D MINIMALIST VECTOR]
Skill: minimalist-explainer

Produce a complete video production package for this topic in our standardized Ink Explainer (2D Vector Egghead) style:
- Topic: "[INSERT YOUR TOPIC HERE]" (e.g., "Why Airplanes Dim the Cabin Lights During Landing")
- Primary Angle: [e.g., The counter-intuitive evolutionary and safety mechanism]
- Target Length: [e.g., 10 minutes / ~1,600 words]

Execution Requirements:
1. Hook Selection: Evaluate whether Hook Archetype A (Sensory Relatability), B (Human Absurdity), or C (Staggering Reality) fits best from `script-blueprints.md`. State your selection and write the first 30 seconds.
2. Character Rigging: Define the "Egghead" character's modular wardrobe and key prop for this specific niche using `character-system.md`.
3. Scriptwriting: Write the complete 4-Act script with 40-40-20 sentence rhythm, direct 2nd-person address ("you"), and rhetorical checkpoints every 90 seconds.
4. Visual Storyboard: Provide 6 keyframe image prompts using the exact 2D vector style tokens from `visual-prompts.md`.
5. Thumbnail Concept: Design the 3-element thumbnail spec (Emotive Face + Striking Prop + 1-3 Word Bold Yellow text).

Run autonomously and output the finalized production package.
```

---

## Prompt 3: [STYLE: INK-EXPLAINER] Rapid Script Only

Use this when you only need the high-retention narration script written to the exact **Ink Explainer cadence**:

```markdown
[STYLE LOCK: INK-EXPLAINER / 2D MINIMALIST VECTOR]
Skill: minimalist-explainer

Write a complete high-retention script on "[INSERT TOPIC]" using the `minimalist-explainer` skill.

Requirements:
- Target WPM: [180 WPM for snappy history/culture | 135 WPM for contemplative science]
- Target Word Count: [e.g., 1,500 words]
- Hook Archetype: [Archetype A: Sensory Relatable | Archetype B: Human Absurdity | Archetype C: Staggering Statistic]
- Rhythm: Strict 40% short (3-7 words), 40% medium (8-16 words), 20% compound sentences.
- Visual Tags: Include bracketed visual cue notes every 15-20 seconds indicating the Egghead character's emotion state (from `character-system.md`) and action.
```

---

## Prompt 4: [STYLE: INK-EXPLAINER] Visual Asset & Thumbnail Storyboard

Use this when you already have a script and want to generate all matching 2D vector visual prompts and thumbnail art:

```markdown
[STYLE LOCK: INK-EXPLAINER / 2D MINIMALIST VECTOR]
Skill: minimalist-explainer

Generate the visual asset storyboard for the following script scenes using the `visual-prompts.md` guidelines in `minimalist-explainer`:

Script / Scenes:
[PASTE SCENES OR TOPIC SUMMARY]

Requirements:
1. Generate ready-to-use FLUX / Midjourney prompts for each scene using the standardized positive/negative style tokens.
2. Ensure the "Egghead" character retains exact visual consistency (pure white circular head, thick ink outline, modular clothing).
3. Generate 3 high-clickrate Thumbnail concepts adhering strictly to the 3-Element Rule (Emotive Face + Bizarre Prop + 1-3 Word Bold Yellow Text).
```

---

## How to Keep Styles Separate in the Future

When you decide to build a second or third visual style (e.g., a *3D Isometric* style, or a *Documentary Collage* style):

```
.agents/skills/
  ├── minimalist-explainer/      <-- [STYLE: INK-EXPLAINER / 2D VECTOR] (This one)
  │     └── prompts-and-workflows.md
  │
  ├── cinematic-3d-explainer/    <-- [STYLE: 3D ISOMETRIC / CINEMATIC] (Future style)
  │     └── prompts-and-workflows.md
  │
  └── collage-documentary/       <-- [STYLE: ARCHIVAL COLLAGE / PAPER CUTOUT] (Future style)
        └── prompts-and-workflows.md
```

Each style skill will have its own `[STYLE LOCK: ...]` identifier at the top of its prompts. This guarantees that when you copy-paste a prompt, the agent will **never** mix up rules, characters, or aesthetics between different channels or visual formats.
