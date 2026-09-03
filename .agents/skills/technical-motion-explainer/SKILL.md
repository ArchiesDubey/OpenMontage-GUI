---
name: technical-motion-explainer
description: Produce high-retention dark technical explainer and video essay videos in the style of Kai, RepoChad, and Devsplainers. Emulates their unique pitch-black/charcoal cyber-minimalist and dark-blueprint vector art styles, 135-175 WPM cadence, short punchy syntax (11-14 words/sentence), receipt-driven storytelling, and 100% vector Remotion/HyperFrames motion graphics (zero AI image generation required).
---

# Technical Motion Explainer Production Skill

This skill codifies the complete production system behind top-performing dark technical explainers, system architecture breakdowns, and hardware/AI video essays (as seen on **Kai** `@kaiexplainsYT`, **RepoChad** `@RepoChad`, and **Devsplainers** `@devsplainers`).

It allows you to produce high-retention, authoritative, data-backed technical videos on **hardware, AI architectures, distributed systems, developer tools, and tech economics** without needing generative AI image or video models. Every visual is 100% vector SVG, HTML/CSS, and procedural motion graphics natively renderable via **Remotion (React)** or **HyperFrames (GSAP/HTML)**.

---

## 1. Quick Reference & Core Files

* **Visual Design System & Code Snippets:** See [visual-design-system.md](visual-design-system.md) for color tokens, typography scales, SVG assets, and ready-to-render Remotion/HyperFrames components (`StatCounter`, `CapacityBar`, `ArchitectureRouter`, `HardwareCard`, `GlitchTerminal`, `CompareDeck`).
* **Scripting Engine & Cadence:** See [script-and-cadence.md](script-and-cadence.md) for the 3 Hook Formulas (Myth-Buster, Direct Hardware Constraint, The Smoking Gun Receipt), the 11–14 words/sentence syntax rule, and the 4-Beat Narrative Arc.
* **Audio & Sound Design:** See [audio-and-music.md](audio-and-music.md) for voiceover mastering targets (-16 LUFS), sidechain ducking (-22dB), low-frequency EQ carving, and tactile micro-SFX grammar.
* **Workflows & Generation Prompts:** See [prompts-and-workflows.md](prompts-and-workflows.md) for copy-paste prompts that convert any technical brief or research paper into a production-ready script and composition.

---

## 2. Dialect Selection: Pick Your Aesthetic

The system supports two complementary dialects. Select the dialect in your project brief:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ DIALECT A: Cyber-Minimalist Architecture (Kai & Devsplainers)            │
├──────────────────────────────────────────────────────────────────────────┤
│ • Background: Pitch Black (#0A0A0A) with subtle horizontal guides        │
│ • Typography: Heavy modern sans (Inter / SF Pro Display) + Monospace     │
│ • Key Visuals: Glowing neon pill cards, massive yellow/blue counters,    │
│   routing flowcharts, capacity threshold bars, glitched terminal cards   │
│ • Target Pacing: 155 – 175 WPM | Sentence Length: 11 – 12 words          │
│ • Mood: Authoritative, surgical, investigative, high-velocity            │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ DIALECT B: Dark Blueprint / Chalk-Vector Engineering (RepoChad)          │
├──────────────────────────────────────────────────────────────────────────┤
│ • Background: Midnight Charcoal / Deep Slate (#0B0E14) with soft vignette│
│ • Typography: Architectural casual marker font (Excalidraw / Comic Neue) │
│ • Key Visuals: Hatched diagonal memory bars, vector dual-fan GPU cards,  │
│   context sliders with red collapse zones, stepped control cards         │
│ • Target Pacing: 130 – 145 WPM | Sentence Length: 14 – 15 words          │
│ • Mood: Pragmatic, instructional, engineer-peer, benchmark-focused       │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. End-to-End Production Pipeline

```
[Phase 1: Receipt Research & Core Claim]
                 │
                 ▼
[Phase 2: Scripting & 12-Word Sentence Calibration]
                 │
                 ▼
[Phase 3: Visual Scene Mapping (Vector Only)]
                 │
                 ▼
[Phase 4: Narration & Audio Bed Integration]
                 │
                 ▼
[Phase 5: Remotion / HyperFrames Composition]
                 │
                 ▼
[Phase 6: Quality Gate & Verification]
```

### Phase 1: Receipt Research & Core Claim
1. **Identify the Core Friction**:
   * Is it a debunking? (*"YouTube says you can run this locally; the VRAM math says otherwise."*)
   * Is it a practical unlock? (*"54GB model on an 8GB card: here's the exact memory budgeting."*)
   * Is it an investigative revelation? (*"7,000 tracked sessions prove the model was silently lobotomized."*)
2. **Collect Concrete Receipts**:
   * Exact parameter count & precision bitwidth.
   * VRAM calculation table in GB.
   * Public bug report, PR, or commit hash.
   * Real dollar costs (e.g. `$2.3M compute bill`, `$0.03 per 1k tokens`).

### Phase 2: Scripting & Cadence Calibration
1. Open on **Second 0:01 with the Hook** (zero intro fluff, no channel greeting).
2. Enforce the **11–14 words/sentence rule**:
   * Break multi-clause compound sentences into punchy declarative statements.
3. Calibrate target spoken speed:
   * **Dialect A**: 170–180 WPM (hook minute at ~195 WPM).
   * **Dialect B**: 130–145 WPM (leaves visual dwell time for technical tables).
4. Follow the **4-Beat Narrative Arc**:
   * **Beat 1 (0:00–0:45)**: The Tension / The Myth / The Receipt.
   * **Beat 2 (0:45–3:00)**: The Architectural Constraint (The Math).
   * **Beat 3 (3:00–6:30)**: The Mechanism / The Trade-off (Routing, Quantization, Headroom).
   * **Beat 4 (6:30–End)**: The Hard Reality & The Setup Verdict.

### Phase 3: Visual Scene Mapping (Vector-First)
1. Every 2.5–3.5 seconds must trigger a visual state transition:
   * Value counter rolling up.
   * Capacity bar sliding from baseline to threshold.
   * Step indicator incrementing (`• CONTROL 1 OF 3 •` -> `• CONTROL 2 OF 3 •`).
   * Arrow flow pulsing from router to destination.
2. Select appropriate vector components from [visual-design-system.md](visual-design-system.md).
3. **No AI Images**: Never inject Midjourney/FLUX raster art. Clean UI and SVG graphics preserve the crisp, authentic technical aesthetic.

### Phase 4: Voiceover & Audio Design
1. **Vocal Tone**:
   * Direct, articulate, calm, conversational with mild skepticism.
   * Recommended TTS Voices:
     * Google Chirp3-HD (expressive, natural pacing).
     * ElevenLabs "Brian", "George", or "Adam" (low warmth, zero radio-announcer hype).
2. **Music Bed**:
   * Low, driving synth pulse or dark electronic ambient drone.
   * Mastered at **-22dB to -24dB** beneath dialogue.
   * Notch cut at 120Hz–300Hz so the bass never muddies voice fundamentals.
3. **Micro-SFX**:
   * Soft mechanical keyboard tick on stat increments.
   * Subdued UI pop on card reveals.
   * Muted glitch/static hit on failure/alert moments.

### Phase 5: Remotion / HyperFrames Composition
* **Remotion**: Render via React components using spring physics (`damping: 18, stiffness: 140`).
* **HyperFrames**: Render via HTML/CSS/GSAP paused deterministic timelines with `power3.out` and `back.out(1.2)` eases.

---

## 4. Verification & Quality Checklist

Before approving any technical motion explainer deliverable, verify:
* [ ] **First 5 Seconds**: Does the script drop the core tension or number immediately without a greeting?
* [ ] **Sentence Rhythm**: Is the average sentence length between 11 and 14 words?
* [ ] **Pacing**: Is spoken WPM within target range (155–175 WPM for Dialect A, 130–145 WPM for Dialect B)?
* [ ] **Receipt Density**: Does the piece cite at least 3 concrete numbers, formulas, or verifiable sources?
* [ ] **Visual Purity**: Are all assets 100% vector SVG, CSS cards, or typography? (Zero generic stock photos/AI images).
* [ ] **Visual State Frequency**: Does a visual state change, highlight, or motion occur at least every 3.5 seconds?
* [ ] **Watermark**: Is the channel tag (`<channelname>`) anchored unobtrusively in the bottom-right corner in muted monospace?
* [ ] **Audio Balance**: Is the voice integrated at -14 to -16 LUFS with music cleanly ducked beneath?
