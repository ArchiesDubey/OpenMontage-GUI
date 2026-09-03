# No AI Slop — Script Humanizer (Meta Skill)

## When to Use

Use this meta skill whenever an agent writes, edits, reviews, or translates scripts, narration voiceover, character dialogue, or on-screen text across any OpenMontage pipeline.

You are directing voiceover and spoken copy for human ears. Left to defaults, LLM drafts inevitably exhibit predictable, robotic AI patterns — jargon, binary contrasts, throat-clearing openers, em-dash cadence crutches, and fake-profound kickers — that sound jarring and artificial when read aloud by TTS or a human speaker.

This skill bridges OpenMontage's pipeline stage directors to the Layer 3 skill [`.agents/skills/no-ai-slop/SKILL.md`](../../.agents/skills/no-ai-slop/SKILL.md) (and slash command `/no-ai-slop`).

---

## Why Video Narration Demands Stricter Anti-Slop Discipline

In a written article or blog post, a reader's eyes can skim past filler words or mental tics. In a video:
1. **TTS voices amplify every structural tic.** Text-to-speech models synthesize every syllable faithfully. A phrase like *"This is not just X, it's Y"* or a colon reveal sounds stilted and theatrical when spoken.
2. **Pacing is finite.** A 60-second video has a strict budget of ~130-150 words. Every filler phrase ("it's important to note", "delve into the intricacies") steals time from actual explanation and visual synchronization.
3. **Em dashes break TTS prosody.** In written copy, em dashes (`—`) are common. In TTS engines (ElevenLabs, OpenAI, Azure, Google TTS), em dashes cause unpredictable long pauses, glottal stops, or broken rhythm.
4. **Humans smell AI scripts instantly.** Audiences recognize corporate AI tropes immediately. Eliminating slop is what makes an OpenMontage video feel handcrafted, authoritative, and engaging.

---

## Banned Words List for Scripts

These words are banned outright in narration, dialogue, and on-screen text. If an LLM draft produces any of these, replace or cut them immediately:

| Banned Words | Problem | Spoken Replacement |
|--------------|---------|--------------------|
| `delve` / `delving` | Overused AI cliché | look at, explore, test, inspect |
| `tapestry` | Abstract AI puffery | mix, combination, collection, network |
| `robust` | Empty corporate filler | reliable, fast, tested, strong |
| `streamline` / `streamlined` | Meaningless buzzword | speed up, simplify, cut |
| `leverage` / `leveraging` | Stilted corporate verb | use, run, apply |
| `utilize` / `utilization` | Clunky synonym for "use" | use |
| `facilitate` | Bureaucratic abstraction | help, allow, enable |
| `empower` | Marketing fluff | let, give |
| `cutting-edge` | Hollow claim | new, fast, state-of-the-art (or state the spec) |
| `game-changer` / `game changer` | Sensationalist hype | Cut it; show the concrete capability |
| `paradigm shift` | Vague hyperbole | change, shift, new method |
| `pivotal` | Unearned importance claim | key, big, first, turning point |
| `beacon` / `realm` | Abstract poetic slop | Cut or name the concrete place/tool |
| `multifaceted` / `intricate` | Pretending complexity | complex, layered, or explain the parts |
| `paramount` / `paramount importance` | Pompous qualifier | crucial, vital, or just state the requirement |
| `transformative` / `elevate` | Marketing puffery | improve, change, speed up |
| `supercharge` / `harness` | Tech-bro cliché | run, power, drive |
| `ever-evolving` | Generic filler | changing, modern, new |

### Often-Empty Phrases to Cut
- "It's important to note that..." → Cut; state the fact directly.
- "It's worth noting..." → Cut.
- "At its core..." / "At the end of the day..." → Cut; state the premise.
- "In today's fast-paced world..." / "In the age of..." → Cut; start with the subject.
- "Without further ado..." / "Let's dive in..." → Cut; jump straight to the point.
- "The reality is..." / "The truth is..." → Cut.

---

## The 10 Script Anti-Patterns to Cut

### 1. Binary Contrasts ("Not X, but Y")
**The Pattern:** "This is not just a tool. It's an operating system." / "The question isn't whether it works, but how fast."  
**Why it fails spoken audio:** It sounds like a generic commercial voiceover.  
- **Before:** "Postgres isn't just a database. It's an entire ecosystem."
- **After:** "Postgres handles relational data, vectors, and documents in one engine."

### 2. Throat-Clearing Openers
**The Pattern:** "Here's the thing:" / "Let me be clear:" / "The uncomfortable truth is:"  
**Why it fails spoken audio:** It wastes 2-3 precious hook seconds before any substance lands.  
- **Before:** "Here's what nobody tells you about fine-tuning LLMs: data quality beats parameter count every time."
- **After:** "Data quality matters more than model size when fine-tuning."

### 3. Faux-Insight Setups
**The Pattern:** "What most people get wrong about X:" / "The part everyone misses:"  
**Why it fails spoken audio:** Flattery pretending to be unique wisdom. State the claim directly.  
- **Before:** "The part everyone misses: cache invalidation is where most microservices crash."
- **After:** "Most microservice outages trace back to stale cache entries."

### 4. Colon Reveals for Fake Drama
**The Pattern:** Noun phrase + colon + dramatic lowercase reveal.  
**Why it fails spoken audio:** Spoken English does not have colons. When TTS encounters colons, it creates awkward pauses or flat pitch drops.  
- **Before:** "The secret to 60 frames per second: offloading physics to a Web Worker."
- **After:** "Offloading physics calculations to a Web Worker keeps the frame rate locked at 60."

### 5. Superficial Trailing `-ing` Clauses
**The Pattern:** Ending a sentence with ", highlighting...", ", underscoring...", ", showcasing...".  
**Why it fails spoken audio:** Artificial editorializing that tells the audience how to react instead of showing proof.  
- **Before:** "The compiler optimizes nested loops, underscoring the team's commitment to low-latency execution."
- **After:** "The compiler flattens nested loops, cutting run time by forty percent."

### 6. Importance Puffery & Weasel Attribution
**The Pattern:** "Stands as a testament to...", "plays a pivotal role...", "experts agree that...", "studies suggest...".  
**Why it fails spoken audio:** Vague claims without names, numbers, or sources.  
- **Before:** "Experts agree that distributed consensus plays a crucial role in modern finance."
- **After:** "Banks use Raft consensus to guarantee that account balances match across three continents."

### 7. Em-Dash Cadence Crutches (`—`)
**The Pattern:** Sprinkling em dashes across script text to fake conversational rhythm.  
**Why it fails spoken audio:** In TTS engines (ElevenLabs, OpenAI, Google, Azure), em dashes produce arbitrary long pauses or glottal stops. Use periods for sentence boundaries, commas for natural clauses, or structured SSML break tags (`<break time="0.4s"/>`).  
- **Before:** "Instead of matching keywords — which fails on synonyms — vector search compares meaning."
- **After:** "Keyword search fails on synonyms. Vector search compares meaning instead."

### 8. Fake-Strong Verbs
**The Pattern:** Avoiding simple verbs like "is" and "has" by substituting pretentious phrasing.  
- **Before:** "The dashboard serves as a central hub that boasts real-time analytics."
- **After:** "The dashboard displays live traffic and error rates."

### 9. Summary-Recap Endings
**The Pattern:** "In conclusion...", "Ultimately...", "As we have seen...".  
**Why it fails spoken audio:** The viewer was just there. Summarizing what you said 40 seconds ago wastes the outro. End on the last concrete fact, a punchy takeaway, or a direct call to action.

### 10. Fake-Profound Kickers
**The Pattern:** The final mic-drop philosophical sentence ("Because in the end, code is poetry written in silicon.").  
**Why it fails spoken audio:** Cringe-inducing. Cut the deep metaphor. End on a clear, grounded takeaway.

---

## Two Operational Modes

### Mode 1: Edit (Default for Script Directors)
When drafting or revising a script:
1. **Draft the narration** guided by the proposal's narrative arc and research facts.
2. **Run the `/no-ai-slop` editing pass:**
   - Scan for every banned word and replace with plain language.
   - Convert binary contrasts into direct assertions.
   - Delete throat-clearing and faux-insight openers.
   - Replace em dashes with proper punctuation or SSML breaks.
   - Ensure every claim passes the **Portability Test**: *If this line could appear in any competitor's video unchanged, it's filler — cut or specify.*
3. **Run the Read-Aloud Test:**
   - Read the line aloud in a normal speaking tempo.
   - Does it sound like an articulate human colleague explaining a concept over coffee?
   - If it sounds like a brochure, an AI assistant, or a conference hype video, rewrite it.

### Mode 2: Detect (For Reviewers and Executive Producers)
When reviewing a script artifact:
1. Scan `script.sections[].text` and `script.sections[].delivery_cues.provider_text`.
2. Check for banned words, binary contrasts, colon reveals, and em dashes.
3. If violations exist:
   - Identify the exact section and quote the line.
   - State the specific named pattern violated.
   - Provide the concrete human rewrite in the finding.
   - Rate severity per the Reviewer protocol (Banned words / binary contrasts = CRITICAL; em-dash clusters = CRITICAL; minor qualifier = SUGGESTION).

---

## Coordination with Voice Performance Director

The anti-slop pass happens **BEFORE** locking voice delivery cues:
```
Draft Narration
  ↳ Step 1: Run /no-ai-slop editing pass (strip banned words, fix cadence, remove em dashes)
  ↳ Step 2: Apply Voice Performance Cues (set pace, energy, emphasis_words, purposeful SSML pauses)
  ↳ Step 3: Self-Evaluate against No-AI-Slop Rubric
  ↳ Step 4: Checkpoint for Review
```

When this sequence is followed, TTS narration sounds crisp, intelligent, and natural.
