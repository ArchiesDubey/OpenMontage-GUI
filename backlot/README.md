# Backlot — the living storyboard + cockpit

A local board that shows a production happening: pipeline stages lighting up,
the script as a screenplay page, the scene plan as a filmstrip that fills in
as assets generate, decisions, spend, and activity — all derived from what the
pipeline already writes to `projects/<id>/`.

**And it drives.** Since the cockpit update, the board is also the control
surface:

- **Gate decisions in the UI** — when a stage is `awaiting_human`, approve or
  request changes (with guidance) right on the review gate. The decision is
  recorded to `projects/<id>/decisions/<stage>.json`; the agent applies it on
  its next turn/run (`skills/meta/checkpoint-protocol.md`, Step 5b).
- **Agent runs from the board** — "▶ RUN AGENT" launches a headless agent
  session that resumes the project's next pipeline stage; live output streams
  into the console panel. Stop it any time.
- **Any agent CLI, not just Claude** — the runner is pluggable. Built-in
  adapters: **Claude Code** (`stream-json`, acceptEdits) and **Gemini CLI**
  (`stream-json`, auto_edit). Anything else — e.g. an OpenRouter-backed CLI
  like `aider --model openrouter/...` or `opencode` — plugs in via
  `backlot/agents.yaml` with a `{prompt}` command template (see that file for
  examples). The agent menu always shows the full picture: ready agents plus
  greyed-out ones with the exact reason (missing binary / env key).

The architecture contract still holds: the agent drives production; Backlot
records what the human decided and never writes checkpoints itself.

```bash
python -m backlot open <project-id>   # start server if needed + open browser
python -m backlot open                # library view (all projects)
python -m backlot serve --port 4750   # run the server in the foreground
```

## How it stays live

No agent involvement. A `watchfiles` watcher on `projects/` publishes change
notifications over SSE; the browser refetches board state. State sources:

| Board element | Disk source |
|---|---|
| identity / rail order | `project.json` + `pipeline_defs/<type>.yaml` |
| stage states, gates, versions | `checkpoint_<stage>.json` + `history/` |
| script card / modal | `artifacts/script.json` |
| filmstrip cards | `scene_plan × script × asset_manifest` join |
| generating shimmer, activity | `events.jsonl` (written by `BaseTool` instrumentation) |
| cost meter | checkpoint `cost_snapshot` |
| renders | `renders/*.mp4` (+ root-level mp4 heuristic) |

Projects without checkpoints degrade gracefully to a "what the watcher
found" view — media, snapshots, renders.

**Replay**: a completed run can be scrubbed end-to-end (▶ REPLAY RUN on the
board) — reconstructed from checkpoint history and event timestamps.

Try it without a real production:

```bash
python scripts/backlot_simulate_run.py          # live demo run (~1 min)
python -m backlot open backlot-demo-run
```

Design doc: `internal/design/LIVING_STORYBOARD.md`.
