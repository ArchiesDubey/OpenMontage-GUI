# Technical Motion Explainer: Scripting & Cadence Engine

The writing grammar, hook archetypes, sentence length constraints, and rhythmic pacing rules that drive 70%+ retention in high-performance technical YouTube videos.

---

## 1. Quantitative Writing Rules

### The 11–14 Words Per Sentence Rule
Empirical analysis of top-performing scripts (Kai: 11.6 words/sentence, Devsplainers: 11.9 words/sentence, RepoChad: 14.5 words/sentence) reveals that retention is destroyed by complex, multi-clause academic sentences.

```
❌ WRONG (31 words - sprawl):
"When you consider running a massive frontier-scale model locally, you will quickly discover that due to extreme memory constraints and PCIe bandwidth limitations, your consumer GPUs simply will not hold the weights."

✅ CORRECT (23 words across 2 sentences - avg 11.5 words):
"Frontier models won't fit on your local machine. The bottleneck isn't just raw compute—it's memory bandwidth and PCIe latency."
```

## Pacing & Cadence Standards

### 1. Delivery Cadence
* **Target Speed**: 140–165 WPM (Words Per Minute).
* **Sentence Length**: 11–14 words per sentence maximum. Short, declarative, confident.
* **No Artificial Pauses**: Micro-pauses (300–500ms) only at major thematic shifts.

### 2. Sub-Beat Motion Cadence Rule (3–5s Maximum Static Hold)
* **Zero Extended Freezes**: No single visual frame or text card may remain completely static for longer than 5 seconds.
* **3–5 Second Micro-Events**: Within any extended scene (e.g. 15–30s), trigger continuous visual progression every 3 to 5 seconds:
  - Numerical rollups or live count-ups (`$0` -> `$2.3M / HR`).
  - Secondary card slide-ins or comparison split views.
  - Stamped alert badges slamming in (`[ASSUMPTION: FALSE ❌]`, `[SACRIFICED]`).
  - Highlight pulses and border glow escalations.
  - Metric bar surges and inventory collapses.

### 3. Entity-Lock Visual Sync (Context-Aware Grounding)
* **Synchronized Name & Term Cues**: Whenever specific companies, hardware models, or industry institutions are named in the script, they must appear on-screen simultaneously:
  - Foundries named (*Samsung, SK Hynix, Micron*) -> Explicit brand status cards reveal with capacity metrics.
  - Research firms (*Gartner, TrendForce, JPMorgan*) -> Monospace analyst bulletin cards or receipts.
  - Hardware specifications (*61.44TB QLC, 16GB VRAM wall, 300mm wafer*) -> Dedicated technical callouts with architectural tags.

### Sentence Distribution Contract
* **50% Short Punches (5–10 words)**: Deliver assertions, numbers, and hard stops.
* **35% Medium Bridges (11–16 words)**: Connect technical cause to effect.
* **15% Technical Compound Clauses (17–22 words)**: Define specific hardware/software configurations.

---

## 2. Pacing & WPM Calibration

Spoken cadence must be calibrated to the density of the visuals:

| Dialect | Target Spoken WPM | Sentence Length | Best Suited For |
| :--- | :--- | :--- | :--- |
| **Dialect A (Cyber-Minimalist / Kai / Devsplainers)** | **155 – 175 WPM** *(Peak opening min: 195 WPM)* | **11.0 – 12.5 words** | High-stakes debunking, architecture exposés, AI industry economics |
| **Dialect B (Dark Blueprint / RepoChad)** | **130 – 145 WPM** *(Steady throughout)* | **13.5 – 15.0 words** | Step-by-step GPU sizing, quant testing, VRAM budgeting, tutorial runs |

---

## 3. The 3 Hook Archetypes (Seconds 0:00 – 0:30)

Every video must open on **Second 0:01 with a tension trigger**. Zero introductory greetings, zero channel branding, zero preamble.

### Archetype A: The Myth-Buster Hook (Kai Style)
* **Goal**: Call out a ubiquitous, optimistic claim in the community, validate the small grain of truth, then drop the crushing reality.
* **Formula**:
  1. *Acknowledge the widespread claim:* "You have probably seen videos claiming you can replace [Frontier Model / Tool] with a local model."
  2. *Grant the partial truth:* "For simple tasks, that's true. Small models can grep files, write scripts, and summarize notes."
  3. *Drop the pivot:* "But what if you want true frontier parity? The math gets impossible fast."

### Archetype B: The Hardware Constraint Hook (RepoChad Style)
* **Goal**: Lead with an intimidating specification or memory requirement, then offer the engineering solution.
* **Formula**:
  1. *The brutal reality:* "[Model Name] takes roughly 54 gigabytes in full precision."
  2. *The democratization promise:* "But you don't need an enterprise cluster to run it."
  3. *The technical unlock:* "With the right quantization and KV-cache allocation, it fits on consumer GPUs from 8GB to 32GB. Here's the exact setup."

### Archetype C: The Smoking Gun Receipt Hook (Devsplainers Style)
* **Goal**: Open with an indisputable data point, benchmark anomaly, or documented bug report from an industry insider.
* **Formula**:
  1. *The specific actor and sample size:* "A director at [Company] tracked nearly 7,000 coding sessions and filed a public report."
  2. *The visceral finding:* "The model had been quietly degraded—reading code three times less, and rewriting entire files twice as often."
  3. *The corporate indifference:* "The company's response? They closed the bug report without comment."

---

## 4. The 4-Beat Narrative Arc

```
[Beat 1: The Tension] ──> [Beat 2: The Physical Constraint]
  (0:00 - 0:45)                 (0:45 - 3:00)
        │                              │
        ▼                              ▼
[Beat 4: The Takeaway] <── [Beat 3: The Economic Mechanism]
  (6:30 - End)                  (3:00 - 6:30)
```

### Beat 1: The Tension / The Hook (0:00 – 0:45)
* Hook the viewer with one of the 3 archetypes.
* Establish the stakes: why does this matter right now?

### Beat 2: The Physical Constraint / The Math (0:45 – 3:00)
* Ground abstract concepts in concrete physics and mathematics.
* Explain the weight footprint:
  $$\text{VRAM (GB)} = \text{Parameters (Billions)} \times \left(\frac{\text{Bitwidth}}{8}\right) \times 1.25 \text{ (KV Overhead)}$$
* Compare consumer hardware (Mac Studio, 4090) against server requirements (DGX B200 cluster).

### Beat 3: The Mechanism / The Trade-Off (3:00 – 6:30)
* Unpack how engineers cope with the constraint:
  * **Routing**: Why prompts get downgraded to cheaper models.
  * **Quantization**: What happens to perplexity when squeezing from FP16 down to Q4 or 3-bit.
  * **Headroom**: Why 80% capacity causes latency spikes or OOM errors.

### Beat 4: The Reality & The Setup Verdict (6:30 – End)
* Give the viewer the final actionable takeaway:
  * What hardware is actually worth buying.
  * Which quantization tier hits the sweet spot.
  * How to detect if your provider is silently downgrading your inference.
* Conclude cleanly without begging for subscribers.

---

## 5. Rhetorical Patterns & Voice Style

1. **"Receipts Over Opinions"**:
   * Replace *"I feel the model got dumber"* with *"Context recall dropped from 94% to 68% in multi-turn reasoning."*
   * Replace *"It's really expensive"* with *"At $2.30 per million output tokens, a 10-person team burns $4,200 a month."*
2. **Micro-Questions (Socratic Guidance)**:
   * Use rhetorical questions to guide transitions: *"Why does this matter?", "Where does the memory actually go?", "What is the real cost?"*
3. **Conversational Skepticism**:
   * Treat the audience as competent developers. Use industry vocabulary naturally: *KV cache, RoPE embeddings, FP8 GEMM, PCIe Gen 4 lanes, speculative decoding, GGUF.*
