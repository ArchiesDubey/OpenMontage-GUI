# Google Flow Image Generation Path (plug-n-play, any pipeline/style)

Canonical Layer-2 doc for generating a project's images with **Google Flow**
([labs.google/fx](https://labs.google/fx), Nano Banana models) through the
`google_flow_bridge` + `google_flow_driver` tool pair. Any pipeline whose assets
stage can use `image_selector` can swap or supplement it with this path — explainer,
cinematic, animation, hybrid, screen-demo, avatar, podcast, talking-head,
character-animation, and style-playbook channels (ink-testimony, witness-archive, …).

Referenced by the pipeline asset-director skills. Read this before running any part
of the loop.

## Why this path exists

- **Free/credits-based frontier image generation** on the user's own Google AI plan
  (no per-frame API bill; FLUX ≈ $0.05/frame is the paid alternative).
- **2K output** (native 1376×768 master → 2752×1536 after 2× upscale) — better than
  1280×720 FLUX frames for crop-heavy shot grammars.
- **First-party automation**: the driver operates the user's own logged-in Chrome.
  No third-party extension code is involved.

## Security contract (non-negotiable)

- The user **never** pastes Google credentials into chat or into any script.
- Login happens once, interactively, in the dedicated Chrome profile window the
  driver opens (`~/.openmontage/flow-driver-profile`). The session cookie lives only
  in that profile.
- The driver spends **the user's Flow credits**. Choosing this path is a **provider-gate
  decision** (`AGENT_GUIDE.md` → "Ask Before Generation Starts"): present it as an image
  provider option with the alternatives and get explicit user confirmation before any
  batch run.
  The driver auto-confirms Flow's spend dialog unless `--no-auto-confirm` is passed.

## Prerequisites

- Playwright Chrome channel installed (`playwright install chrome` if missing).
- One-time interactive login: `python -m tools.graphics.google_flow_driver login`.
- Nothing else — no API keys.

## The loop

```
google_flow_bridge export  →  driver dry_run  →  driver run  →  [driver capture]  →  bridge ingest
```

1. **Export prompts** — `google_flow_bridge` with
   `{"operation": "export", "project_id": "<id>", "aspect_ratio": "16:9"}`.
   Reads `artifacts/scene_plan.json`, writes `exports/google_flow/prompts.md`,
   `queue.csv`, `queue.json`. Style-aware — see *Prompt style modes* below.
2. **Dry run (no credits)** — `python -m tools.graphics.google_flow_driver dry_run <id>`
   verifies login state and Flow UI selectors before spending anything.
3. **Generate + capture** — `python -m tools.graphics.google_flow_driver run <id>`
   (add `--upscale fast|flow`, `--only <scene_id>`, `--force`, `--no-auto-confirm`).
   Opens Flow in the user's Chrome (dedicated profile), sets model/aspect/outputs in
   the settings panel, then per prompt: jittered 20–55 s delay → submit → detect the
   finished render via the tRPC network listener → capture the image under the
   correct target filename into `drop_images/`.
4. **Credit-free refetch (optional)** — `python -m tools.graphics.google_flow_driver
   capture <id>` re-downloads images for renders that generated but failed capture
   (media IDs are recorded even on capture failure). Use after any interrupted run.
5. **Ingest** — `google_flow_bridge` with `{"operation": "ingest", "project_id": "<id>"}`:
   sequence-safe mapping, resolution validation, `assets/images/scene_<id>.png`,
   480px previews, schema-valid `asset_manifest.json`. Then continue the pipeline
   (edit → compose) normally.

Tool JSON equivalents exist for both tools (`execute()`); the CLI form above is the
quickest path for the driver.

## Capture modes (`--upscale`)

| Mode | What it does | Use when |
|------|--------------|----------|
| `fast` (default) | One authenticated fetch of the native master + local 2× Lanczos upscale | **Bulk runs (10+ frames)** — crash-proof, no download manager |
| `flow` | Clicks Flow's download flyout for Google's true in-browser SR 2K | Few hero frames; includes `.crdownload` crash salvage |

Chrome 152+ can crash (EXC_BREAKPOINT in the download manager) when Flow's `blob:`
downloads happen under automation — the `fast` mode avoids the download manager
entirely, which is why it is the default.

## Rate limits & resilience

- Jittered 20–55 s inter-prompt delays; cooldown after chunks; exponential backoff
  (5 min → 45 min cap) on limit toasts. A 99-prompt queue is expected to take
  ~1–2 hours wall-clock.
- Runs are resumable: state lives in `exports/google_flow/driver_state.json`;
  re-running `run` skips already-succeeded scenes.
- Status/reset: `python -m tools.graphics.google_flow_driver status <id>` / `reset <id>`.

## Prompt style modes (style-safe by construction)

The export resolves, per scene, the first mode that applies:

| Mode | Trigger | What the exported prompt looks like |
|------|---------|--------------------------------------|
| `verbatim` | The scene plan authors the full prompt: `required_assets[0].description` starts with `GENERATE: ` (ink-testimony does this) | Forwarded **untouched** — the playbook's prompt contract (medium-first ordering, full-bleed guard) is already baked in. Never append slash commands. |
| `playbook` | The project's style playbook defines `asset_generation.image_prompt_prefix` | Scene text first, then the playbook's own style block **copied verbatim**; no slash commands, no `--ar`. |
| `cinematic` | Neither of the above | Cinematography layers + Flow slash commands (`/bokeh`, `/volumetric_lighting`) + `--ar <ratio>`. |

The playbook name resolves from the explicit `style_playbook` input, else the
scene_plan's `style_playbook` field; an explicit `style_context` wins over both.
Aspect ratio for verbatim/playbook prompts is set by the driver in Flow's settings
panel — do not add `--ar` tags to those.

**Style fidelity rule:** never hand-edit a playbook's style block or guard to
"improve" a Flow prompt. If a frame misses the style, regenerate or fix the scene
sentence — the blocks are locked per playbook.

## Manual fallback

If the driver can't run (no Chrome, login blocked, user prefers hands-on), set the
assets checkpoint to `awaiting_human`, point the user at
`exports/google_flow/prompts.md`, and have them drop downloads into
`projects/<id>/drop_images/` (named `01_scene-1.png` … or raw batch order). Then
`ingest` sorts them exactly the same way. This is how `physical-limit-of-silicon`
was produced pre-automation.

## Registry note

`google_flow_bridge` and `google_flow_driver` are registered under their own
capability names (not `image_generation`), so preflight's image count won't include
them and `image_selector` will never auto-route to the driver — switching a project
to this path is always an explicit decision: confirm it with the user (provider gate)
and log it in
`decision_log` when it changes an approved provider).
