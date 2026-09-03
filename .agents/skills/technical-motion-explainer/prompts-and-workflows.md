# Technical Motion Explainer: Prompts & Production Workflows

Turn-key workflows and copy-paste prompts to transform any complex technical topic, benchmark report, or research paper into a production-ready Dark Technical Explainer video.

---

## Workflow 1: Raw Topic / Paper ──> Production Script

Use this prompt to generate a high-retention, 12-word-average-sentence script following the exact cadence of Kai, RepoChad, or Devsplainers.

```markdown
You are an elite technical video essayist and motion director specializing in high-retention YouTube explainers (in the style of Kai @kaiexplainsYT, RepoChad, and Devsplainers).

Your task is to write an authoritative, data-backed technical script on the following topic:
TOPIC: [Insert Topic / Paper / Hardware Setup]
TARGET DURATION: [e.g. 5 to 8 minutes / 800 - 1,200 words]
CHOSEN DIALECT: [Dialect A: Cyber-Minimalist Architecture OR Dialect B: Dark Blueprint Engineering]
TARGET AUDIENCE: Experienced software engineers, AI researchers, and hardware builders.

### Strict Scriptwriting Constraints:
1. **The Hook (0:00 - 0:30)**: Open on SECOND 0:01 with a tension trigger (Myth-Buster, Hardware Bottleneck, or Documented Bug Receipt). Zero greeting, zero fluff, zero "in this video".
2. **The 11–14 Word Sentence Rule**: Keep sentences short, declarative, and punchy. Average sentence length MUST be between 11 and 14 words. Eliminate filler phrases ("as you can see", "in order to", "needless to say").
3. **Receipt-Driven Storytelling**: Every major claim must feature a concrete number (parameters, VRAM in GB, dollar amounts, benchmark percentages, or commit hashes).
4. **4-Beat Narrative Structure**:
   - Beat 1: The Tension / The Myth / The Receipt
   - Beat 2: The Physical Constraint (The Memory / Compute Math)
   - Beat 3: The Architectural Mechanism (Routing / Quantization / Headroom)
   - Beat 4: The Hard Reality & The Setup Verdict
5. **Visual Directives**: For every 1-2 sentences, include a [VISUAL: ...] tag indicating which vector component to render (StatCounter, CapacityBar, ArchitectureRouter, HardwareCard, GlitchTerminal, or CompareDeck) and what data values to display.

Output the script with timestamps and exact word count calculations per section.
```

---

## Workflow 2: Script ──> Vector Scene Plan (Remotion / HyperFrames)

Use this prompt to convert a script into an exact Remotion (React) or HyperFrames (HTML/GSAP) composition spec with zero AI image dependencies.

```markdown
You are a technical motion graphics engineer specializing in code-driven vector composition using Remotion (React) and HyperFrames (HTML/GSAP).

Convert the following technical script into an executable scene plan:
SCRIPT: [Paste Script Here]
RUNTIME TARGET: [Remotion / HyperFrames]
COLOR PALETTE: [Pitch Black #0A0A0A, Cyan #38BDF8, Yellow #FFD600, Green #22C55E, Red #EF4444]

### Composition Contract:
1. **Zero Raster AI Images**: All scenes must use pure vector SVG, CSS cards, data sliders, stat rollups, and monospace typography.
2. **Visual Rhythm**: Trigger a state change or motion event every 2.5 to 3.5 seconds.
3. **Component Bindings**: Map every beat to one of the canonical components:
   - `StatCounter`: for metrics and benchmarks.
   - `CapacityBar`: for memory headroom, context windows, and allocation limits.
   - `ArchitectureRouter`: for flowcharts, prompt routers, and model dispatch.
   - `HardwareCard`: for GPU/CPU hardware cards with vector dual fans.
   - `GlitchTerminal`: for diagnostics, bug reports, and monospace code blocks.
   - `CompareDeck`: for side-by-side hardware/model tiers.

### Deliverable:
Provide a structured JSON scene list containing:
- `scene_id`
- `duration_seconds`
- `component_type`
- `props` (eyebrow, headline, values, labels, colors)
- `motion_entrance` (spring / gsap ease)
- `sfx_cue` (counter_tick, card_pop, sub_impact)
```

---

## Workflow 3: The Pre-Render Quality Gate

Run this audit on any generated script and scene plan before committing to final rendering:

```markdown
Audit the following technical video package against the Technical Motion Explainer quality bar:

Checklist:
1. [ ] Hook Test: Does word 1-15 drop a concrete contradiction, tension, or shocking number?
2. [ ] Sentence Length: Is the average word count between 11.0 and 14.0 words per sentence?
3. [ ] Spoken Speed: Does the total word count divided by duration yield 150-175 WPM (Dialect A) or 130-145 WPM (Dialect B)?
4. [ ] Concrete Anchors: Are abstract claims backed by exact VRAM formulas, benchmark deltas, or dollar costs?
5. [ ] Vector Purity: Are 100% of the visual assets code-driven SVG/CSS without raster image placeholders?
6. [ ] Watermark: Is the channel watermark tag placed in the bottom right in muted monospace?

Report all violations as [CRITICAL], [SUGGESTION], or [PASS].
```
