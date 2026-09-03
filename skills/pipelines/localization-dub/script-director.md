# Script Director - Localization Dub Pipeline

## When To Use

Turn the approved localization brief into a transcript-backed, reviewable script package for every target language. This stage should create text truth before any dubbing audio is generated.

## Reference Inputs

- `docs/localization-dubbing-best-practices.md`
- `skills/creative/storytelling.md`
- `skills/meta/no-ai-slop.md`
- `.agents/skills/no-ai-slop/` (slash command `/no-ai-slop`)

## Process

### 1. Build Source Transcript Truth

Start with the source transcript and fix obvious errors in:

- names,
- terminology,
- speaker allocation,
- numbers,
- CTA phrasing.

### 2. Produce Reviewable Target Copy

For each target language, generate text that can be reviewed before synthesis. Record where terms should remain unchanged.

### 3. Translate For Natural Spoken Flow, Not Machine Slop (`/no-ai-slop`)

Machine translation and LLM localization frequently inject robotic clichés, passive constructions, and unnatural syntax:
- Run `/no-ai-slop` principles (`skills/meta/no-ai-slop.md`) adapted to the target language.
- Ensure phrasing is idiomatic spoken language, not literal word-for-word translation.
- Eliminate binary contrasts (*"not X, but Y"*) and throat-clearing openers.
- Strip em dashes (`—`) to prevent unnatural pauses or cadence breakage in the target TTS voice.
- Verify timing fits naturally into the section window without rushing or dragging.

### 4. Preserve Structure Where Practical

Keep section timing and sequence aligned to the source unless the translation clearly needs a different pacing strategy.

### 5. Use Metadata For Localization Control

Recommended metadata keys:

- `source_transcript_status`
- `target_language_sections`
- `glossary_terms`
- `protected_terms`
- `pronunciation_notes`
- `review_status_by_language`

### 6. Quality Gate

- the source transcript is strong enough to trust,
- target-language copy exists for every planned deliverable,
- translated copy sounds natural and human, free of machine-translation slop and awkward cadence,
- glossary terms are preserved,
- the script package can be reviewed before audio generation.

### Mid-Production Fact Verification

If you encounter uncertainty during script writing:
- Use `web_search` to verify factual claims before committing them to the script
- Use `web_search` to find reference images for visual accuracy
- Log verification in the decision log: `category="visual_accuracy_check"`

Every factual claim in the script should be traceable to the `research_brief`.
If you make a claim that isn't in the research, do additional research and
add the source. Do not invent statistics, dates, or attributions.

## Common Pitfalls

- Generating audio from an unreviewed transcript.
- Letting product names drift across languages.
- Treating translation text as final timing without acknowledging length drift.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact), and **END YOUR TURN**. Do not start the next stage in the same response.
Approval is per-gate — an earlier "go ahead" does not cover this gate.
