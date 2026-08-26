# Backlot — the OpenMontage GUI

**Backlot is the OpenMontage GUI**: a local, browser-based control panel for
[OpenMontage](../README.md), the open-source agentic video production
system. It replaces "read the chat log to see what happened" with a live
board you can watch, approve, and drive a production from — no terminal
required once it's running.

Two things it does, together:

1. **Shows** a production happening live — pipeline stages lighting up, the
   script as a screenplay page, the scene plan as a filmstrip that fills in
   as assets generate, decisions, spend, and activity — all derived from
   what the pipeline already writes to `projects/<id>/`.
2. **Drives** it — pick and launch an agent, approve or reject a gate, stop
   a run, all from the browser. The architecture contract still holds: the
   agent drives production; Backlot records what the human decided and
   never writes checkpoints itself.

---

## Launch the GUI

```bash
python -m backlot open                # library view — every project on disk
python -m backlot open <project-id>   # one production's live board
python -m backlot serve --port 4750   # run the server only (no browser tab)
```

`open` starts the local server if it isn't already running and opens your
default browser to it. No separate install step — it uses the same Python
environment as the rest of OpenMontage (`make setup` / see the [root
README](../README.md#quick-start)).

No production yet? Watch a simulated one live in under a minute:

```bash
python scripts/backlot_simulate_run.py
python -m backlot open backlot-demo-run
```

## Operate a production from the GUI

Once a project's board is open:

- **Pick an agent.** The agent dropdown lists every agent CLI Backlot
  knows about — ready ones are selectable, unavailable ones are visible
  with the exact reason (missing binary or API key), so you always see the
  full picture. Built in: **Claude Code** and **Gemini CLI**. Anything else
  — `aider`, `opencode`, an OpenRouter-backed CLI — plugs in via
  [`backlot/agents.yaml`](agents.yaml) with a `{prompt}` command template;
  no code changes needed.
- **Run it.** Hit **▶ RUN AGENT**, optionally add a steering note (tone,
  scope, "skip music this time"), and the board launches a headless agent
  session that resumes the project's next pipeline stage. Output streams
  live into the console panel.
- **Stop it.** **■ STOP RUN** ends the session cleanly at any point; the
  board reflects the stop immediately.
- **Approve or redirect at a gate.** When a stage is `awaiting_human`,
  approve or request changes (with feedback) right on the review card. The
  decision is written to `projects/<id>/decisions/<stage>.json`; the agent
  applies it on its next turn
  ([`skills/meta/checkpoint-protocol.md`](../skills/meta/checkpoint-protocol.md),
  Step 5b).
- **Replay a finished run.** **▶ REPLAY RUN** scrubs the whole production
  end-to-end, reconstructed from checkpoint history and event timestamps.

## How it stays live

No agent involvement required to watch. A `watchfiles` watcher on
`projects/` publishes change notifications over SSE; the browser refetches
board state. State sources:

| Board element | Disk source |
|---|---|
| identity / rail order | `project.json` + `pipeline_defs/<type>.yaml` |
| stage states, gates, versions | `checkpoint_<stage>.json` + `history/` |
| script card / modal | `artifacts/script.json` |
| filmstrip cards | `scene_plan × script × asset_manifest` join |
| generating shimmer, activity | `events.jsonl` (written by `BaseTool` instrumentation) |
| cost meter | checkpoint `cost_snapshot` |
| renders | `renders/*.mp4` (+ root-level mp4 heuristic) |
| agent runs | in-memory (`backlot/control.py`), streamed over SSE while live |

Projects without checkpoints degrade gracefully to a "what the watcher
found" view — media, snapshots, renders.

Design doc: `internal/design/LIVING_STORYBOARD.md`.
