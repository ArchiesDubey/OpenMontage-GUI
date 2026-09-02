# Asset Director - Character Animation Pipeline

## Goal

Produce `asset_manifest` with character parts, backgrounds, props, audio, music,
and preview artifacts.

## Layer 3 Gate

Before authoring or generating animation assets, read the relevant Layer 3 skills:

- `character-rigging`
- `svg-character-animation`
- `pose-library-design`
- `canvas-procedural-animation` when p5/canvas effects are used
- `character-animation-qa` before review
- `gsap-core`, `gsap-timeline`, and `gsap-react` for GSAP/Remotion work
- `remotion` and `remotion-best-practices` for Remotion render work
- `hyperframes` and `hyperframes-cli` for HyperFrames work

Before image/TTS/music generation, read the tool's `agent_skills` from the
registry.

## Asset Organization

Write character assets under:

```text
projects/<project-name>/assets/characters/<character-id>/
```

Use subfolders:

```text
parts/
poses/
previews/
```

Generated backgrounds go under:

```text
projects/<project-name>/assets/backgrounds/
```

**Provider gate (binding — `AGENT_GUIDE.md` → "Ask Before Generation Starts")**: before the first **image / music / sound / TTS** generation call of the run — **samples included** — present the configured providers for that capability (registry `provider_menu()`; for images the Google Flow path is one of the options) with a one-line recommendation and get explicit user confirmation. Log the confirmed choice in `decision_log`. Locked-style defaults count as confirmed only while unchanged.

## Process

1. Produce or source only the parts required by `rig_plan`.
2. Keep each moving part separate.
3. Preserve transparent backgrounds for parts.
4. Record prompts, seeds, providers, and model names.
5. Build a small preview before full asset expansion.

**Google Flow image path (plug-n-play)**: when the user chooses Google Flow, or paid
image APIs are unavailable/declined, run the `google_flow_bridge` +
`google_flow_driver` loop instead of `image_selector` — **read
`skills/core/google-flow.md` first**. Short form: `bridge export` (style-aware
prompts → `exports/google_flow/`) → `driver dry_run` → `driver run` (drives
flow.google in the user's own Chrome, 2K capture, jitter + backoff; spends the
user's Flow credits — confirm with the user before batching: provider gate) → `bridge ingest`. Transparent-background
rig parts are NOT a Flow deliverable — use Flow only for full-bleed painted backdrops
or props; layered parts still come from the rig pipeline.

## Quality Bar

All parts referenced by `rig_plan` must exist before compose. Missing parts are a
blocker unless the action timeline removes the action requiring them.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact), and **END YOUR TURN**. Do not start the next stage in the same response.
Approval is per-gate — an earlier "go ahead" does not cover this gate.
