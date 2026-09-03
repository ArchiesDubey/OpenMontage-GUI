# Script Director - Character Animation Pipeline

## Goal

Write scripts as performable animation beats, not just narration.

## References

- `skills/meta/no-ai-slop.md`
- `.agents/skills/no-ai-slop/` (slash command `/no-ai-slop`)

## Process

1. Lock audio architecture:
   - music-only,
   - narrator,
   - character dialogue,
   - narrator plus character sounds/dialogue.
2. Break the story into beats that can be acted with poses.
3. For each beat, state what changes visually:
   - emotion,
   - gaze,
   - body pose,
   - prop interaction,
   - camera,
   - environment.
4. Run the mandatory `/no-ai-slop` editing pass (`skills/meta/no-ai-slop.md`):
   - Dialogue and narration must feel like authentic human speech, not corporate AI.
   - Strip banned AI words (*delve, tapestry, robust, streamline, leverage, utilize, cutting-edge*).
   - Eliminate binary contrasts (*"not X, but Y"*) and throat-clearing openers.
   - Remove em dashes (`—`) in spoken dialogue to keep lip-sync and phoneme timing clean.

## Writing Rules

- Prefer short visual beats with readable holds.
- Avoid action that needs many unique hand-drawn poses unless approved.
- Dialogue should be short enough for mouth-shape approximation and stripped of all AI slop.
- Silent/music-led scenes need stronger physical acting notes.

## Output Notes

In the `script` artifact metadata, include:

- `audio_architecture`,
- `character_beats`,
- `required_emotions`,
- `required_actions`.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact), and **END YOUR TURN**. Do not start the next stage in the same response.
Approval is per-gate — an earlier "go ahead" does not cover this gate.
