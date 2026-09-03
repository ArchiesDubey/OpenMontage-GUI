---
name: minimalist-explainer
description: Produce high-retention 2D animated explainer videos in the Ink Explainer / minimalist vector stickman style. Covers scriptwriting cadence, universal topic-agnostic character rigging, visual prompt formulas, and editing grammar.
---

# Minimalist Explainer Production Skill

This skill codifies the complete production system behind top-performing 2D minimalist explainer videos (e.g., *Ink Explainer*, *Robert Like's History*, *OverSimplified*). It allows you to rapidly produce high-retention, educational, and essay-style videos on **any topic or era** without starting from scratch.

---

## 1. Quick Reference & Core Files

* **Character Rigging:** See [character-system.md](file:///Users/archiesdubey/Desktop/Code.nosync/OpenMontage/.agents/skills/minimalist-explainer/character-system.md) for the universal "Egghead" avatar, emotion states, and wardrobe swapping guide across niches.
* **Scripting Engine:** See [script-blueprints.md](file:///Users/archiesdubey/Desktop/Code.nosync/OpenMontage/.agents/skills/minimalist-explainer/script-blueprints.md) for hook formulas (Sensory, Absurdity, Staggering Reality), 4-Act architecture, and cadence rules.
* **Visual Generation:** See [visual-prompts.md](file:///Users/archiesdubey/Desktop/Code.nosync/OpenMontage/.agents/skills/minimalist-explainer/visual-prompts.md) for Midjourney/FLUX/Gemini prompts, SVG code snippets, color palettes, and the 3-element thumbnail formula.
* **Standard Workflows & Prompts:** See [prompts-and-workflows.md](file:///Users/archiesdubey/Desktop/Code.nosync/OpenMontage/.agents/skills/minimalist-explainer/prompts-and-workflows.md) for copy-paste prompt templates for URL Re-skins and Raw Topic generation.

---

## 2. End-to-End Production Pipeline

```
[Phase 1: Concept & Hook] ──> [Phase 2: Scripting & Cadence] ──> [Phase 3: Character & Assets]
            │                                                                │
            ▼                                                                ▼
   [Phase 6: Thumbnail]    <── [Phase 5: Motion & Editing]   <── [Phase 4: Voice & Audio]
```

### Phase 1: Topic & Hook Selection
1. Identify the core paradox or counter-intuitive truth of the topic.
2. Select one of the 3 Hook Archetypes (from [script-blueprints.md](file:///Users/archiesdubey/Desktop/Code.nosync/OpenMontage/.agents/skills/minimalist-explainer/script-blueprints.md)):
   * **Archetype A (Sensory Relatability):** Best for history, lifestyle, economics (*"This morning, a machine screamed at you..."*).
   * **Archetype B (Human Absurdity):** Best for neuroscience, psychology, biology (*"Picture this... performing the act of sleeping for nobody..."*).
   * **Archetype C (Staggering Reality):** Best for ethics, industrial deep-dives, environmental crises (*"19 million chicks killed every day..."*).

### Phase 2: Scripting & Rhythmic Calibration
1. Follow the **4-Act Structure**:
   * **Act I (0:00–1:15):** The Anchor & The Core Paradox.
   * **Act II (1:15–4:00):** Historical / Evolutionary Deconstruction.
   * **Act III (4:00–8:00):** The Hidden Mechanism / Economic Engine.
   * **Act IV (8:00–End):** The Modern Mirror & Existential Resolution.
2. Apply the **40-40-20 Sentence Rhythm**:
   * 40% short punchy sentences (3–7 words).
   * 40% medium narrative sentences (8–16 words).
   * 20% compound flow clauses (17–25 words).
3. Calibrate Target WPM:
   * Snappy / historical / comedic pace: **175–195 WPM**.
   * Contemplative / scientific / somber pace: **125–140 WPM**.

### Phase 3: Character Rigging & Visual Assets
1. Use the **Universal "Egghead" Rig** (see [character-system.md](file:///Users/archiesdubey/Desktop/Code.nosync/OpenMontage/.agents/skills/minimalist-explainer/character-system.md)):
   * Head is pure white `#FFFFFF` with bold black outline `#121212`.
   * Never change the core facial structure; swap only **Hair/Headwear**, **Torso Outfit**, and **Key Prop** to match the video's theme.
2. Generate background plates and character poses using prompt templates from [visual-prompts.md](file:///Users/archiesdubey/Desktop/Code.nosync/OpenMontage/.agents/skills/minimalist-explainer/visual-prompts.md).
3. Ensure backgrounds remain clean and decluttered to focus the eye on character emotions.

### Phase 4: Voiceover & Audio Design
1. **Vocal Profile:**
   * Warm, conversational, slightly dry, introspective, articulate (e.g., ElevenLabs "Adam", "Brian", or "George").
   * Zero hype-beast inflection; treat the listener like an intelligent peer.
2. **Music & Ambience:**
   * **Hook (0:00–0:45):** Minimalist pulsing bass or subtle ambient drone.
   * **Deconstruction & Beats:** Light, inquisitive lo-fi, acoustic strings, or ambient mallet percussion.
   * **Climax / Twist:** Swell with a warm synth or piano chord progression.
3. **Sound Effects (SFX) Grammar:**
   * Place subtle tactile SFX on key visual events: soft pencil sketch, pop on text hits, clock ticking, subtle whoosh on scene pans. Never use loud jarring meme SFX.

### Phase 5: Editing Tempo & Motion Grammar
1. **Average Shot Length (ASL):** **2.5 to 4.0 seconds**.
2. **Visual Pattern Interrupts:** Every 3 seconds, introduce one of:
   * Slight camera scale-punch (zoom in 1.1x onto character face).
   * Pop-in prop or secondary character.
   * Animated text label or highlighted arrow.
   * Emotional state change (e.g., character flips from deadpan to shock).
3. **Transitions:** Quick hard cuts or simple linear horizontal wipes. Avoid flashy 3D transitions.

### Phase 6: Thumbnail Creation
* Route thumbnail design to the dedicated companion skill: [**`minimalist-thumbnail-craft`**](file:///Users/archiesdubey/Desktop/Code.nosync/OpenMontage/.agents/skills/minimalist-thumbnail-craft/SKILL.md).
* Strictly enforce:
  1. **Zero Title Duplication:** Never repeat the video title in thumbnail text.
  2. **The 3-Element Rule:** (1) Emotive white egghead character, (2) One striking contextual prop/paradox, (3) 1–3 words of high-impact Canary Yellow text (`#FFEE00`) with thick black outline (`"NO JOBS"`, `"FAKE SLEEP?"`, `"WHY?"`, `"NOT IN CHARGE"`).
  3. **Headless Render:** Use `render_thumbnail.py` to produce pixel-perfect 1280x720 thumbnails and pass the 120px mobile squint test.

---

## 3. Verification & Quality Checklist

Before finalizing any video in this style, verify:
* [ ] **First 5 Seconds:** Does the script hook with sensory or visceral imagery rather than a generic introduction?
* [ ] **Character Portability:** Is the character built on the neutral white egghead rig with appropriate niche-specific props?
* [ ] **Speech Cadence:** Is the spoken WPM between 125–195 WPM with distinct micro-pauses after major revelations?
* [ ] **Visual Hierarchy:** Does every frame have a clear foreground subject without visual clutter?
* [ ] **Thumbnail:** Does the thumbnail contain 3 words or fewer in bold yellow text with an expressive character face?
