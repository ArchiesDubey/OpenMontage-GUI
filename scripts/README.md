# scripts/ — Standardized Runners

This directory holds **reusable, artifact-driven runner modules** — not
per-project scripts. The Ink & Testimony runner is the reference
implementation; a new channel clones it and changes config/prompt blocks only.

## The contract

A runner module:

1. Is driven entirely by a project's artifacts (`artifacts/script.json`,
   `artifacts/scene_plan.json`) plus one config file (`<channel>_config.json`,
   falling back to the style playbook in `styles/`). No hardcoded episode data.
2. Exposes idempotent entry points:
   ```bash
   python -m scripts.<channel>.assets  --project projects/<id> --mode sample|batch|regen
   python -m scripts.<channel>.compose --project projects/<id>
   ```
   Re-running never double-generates; `--mode regen` retries failed units in
   place instead of spawning a new script.
3. Writes everything under `projects/<project_id>/` so the Backlot board and
   the checkpoint contract see it.
4. Keeps LOCKED constants (voice, style blocks, model, seed band) in one
   place and records them in the project profile
   (`python -m lib.profile`).

## The rule

**Never write `eNN_*.py` / per-project one-off scripts.** They are how token
budget leaked on E01–E03: three near-identical asset generators, three
composers, and a regen script per failure — then a full session to
standardize them (commit `6a7b4e7`). Failure recovery is a runner flag,
not a new file.

When a stage genuinely needs new capability, extend the *runner* (or the
underlying tool), validated by reproducing a prior episode from artifacts
alone — as `scripts/ink_testimony/compose.py` reproduced E03 (643.19s,
165 shots) before replacing the per-episode scripts.

## Current runners

| Module | Channel | Notes |
|--------|---------|-------|
| `ink_testimony/` | ink-testimony | `common.py` (locked constants, config, seed band), `assets.py`, `compose.py` |
| `explainer_compose.py` | explainer-family | Reusable composition primitives; consumed by channel runners |
