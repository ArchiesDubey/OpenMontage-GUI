"""Backlot control — the write path that turns the board into a cockpit.

Two concerns, both deliberately thin:

1. **Human decisions.** When you approve a gate or request changes from the
   UI, we record a canonical ``projects/<id>/decisions/<stage>.json`` file.
   The AGENT (not this server) applies it: approved gates become
   ``write_checkpoint(status="completed", human_approved=True)``; change
   requests loop back through the stage director skill with your feedback.
   This keeps PROJECT_CONTEXT's contract intact — the agent drives the
   pipeline; Backlot records what the human decided.

2. **Agent runs.** Spawn/resume a production by launching a headless
   ``claude`` session rooted in this repo, pointed at the project. Output is
   captured line-by-line for SSE streaming into the board console.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import threading
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

from lib.paths import PROJECTS_DIR, REPO_ROOT

from backlot import agents

DECISIONS_DIRNAME = "decisions"

VALID_DECISIONS = ("approved", "changes_requested", "abort")

# Overridable so tests never spawn a real agent binary.
AGENT_CMD_ENV = "BACKLOT_AGENT_CMD"


# ---------------------------------------------------------------------------
# Decisions
# ---------------------------------------------------------------------------

def _atomic_write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(f".{uuid.uuid4().hex[:8]}.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _decisions_dir(project_dir: Path) -> Path:
    return Path(project_dir) / DECISIONS_DIRNAME


def decision_path(project_dir: Path, stage: str) -> Path:
    return _decisions_dir(project_dir) / f"{stage}.json"


def write_decision(
    project_dir: Path,
    stage: str,
    decision: str,
    *,
    feedback: str = "",
    source: str = "backlot-ui",
) -> dict:
    """Record a human gate decision. Raises ValueError on bad input."""
    if decision not in VALID_DECISIONS:
        raise ValueError(f"decision must be one of {VALID_DECISIONS}, got {decision!r}")
    if not stage or any(c in stage for c in "/\\:."):
        raise ValueError(f"invalid stage name: {stage!r}")
    path = decision_path(project_dir, stage)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "version": "1.0",
        "project_id": Path(project_dir).name,
        "stage": stage,
        "decision": decision,
        "feedback": str(feedback or "").strip(),
        "source": source,
        "checkpoint_status_at_decision": None,
        "decided_at_epoch": time.time(),
        "decided_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    cp = Path(project_dir) / f"checkpoint_{stage}.json"
    if cp.is_file():
        try:
            record["checkpoint_status_at_decision"] = json.loads(
                cp.read_text(encoding="utf-8")
            ).get("status")
        except Exception:
            pass
    _atomic_write_json(path, record)
    return record


def read_decisions(project_dir: Path) -> Dict[str, dict]:
    """All recorded decisions for a project, keyed by stage (latest wins)."""
    out: Dict[str, dict] = {}
    d = _decisions_dir(project_dir)
    if not d.is_dir():
        return out
    for entry in sorted(d.glob("*.json")):
        try:
            data = json.loads(entry.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and data.get("stage") and data.get("decision"):
            out[data["stage"]] = data
    return out


def pending_decisions(
    project_dir: Path, decisions: Optional[Dict[str, dict]] = None
) -> List[dict]:
    """Decisions not yet applied to their stage checkpoint.

    A decision counts as applied when the checkpoint's ``human_decisions``
    echo (written by the agent on apply) carries its ``decided_at_epoch``.

    Pass an already-loaded ``decisions`` mapping (from ``read_decisions``) to
    avoid re-scanning the decisions directory when the caller already has it.
    """
    pending = []
    source = decisions if decisions is not None else read_decisions(project_dir)
    for stage, rec in sorted(source.items()):
        cp_file = Path(project_dir) / f"checkpoint_{stage}.json"
        try:
            cp = json.loads(cp_file.read_text(encoding="utf-8"))
        except Exception:
            # No (readable) checkpoint yet — the decision cannot have been
            # applied anywhere, so it is pending by definition.
            pending.append(rec)
            continue
        echo = (cp.get("metadata") or {}).get("human_decisions") or []
        if any(e.get("decided_at_epoch") == rec.get("decided_at_epoch") for e in echo):
            continue
        pending.append(rec)
    return pending


# ---------------------------------------------------------------------------
# Agent runs
# ---------------------------------------------------------------------------

def build_prompt(project_id: str, instruction: str = "") -> str:
    parts = [
        f"You are driving the OpenMontage production '{project_id}' end-to-end.",
        "Read AGENT_GUIDE.md first and follow it exactly (Rule Zero: all",
        "production goes through pipeline stages with director skills).",
        f"The project lives at projects/{project_id}/. Run the next incomplete",
        "stage per skills/meta/checkpoint-protocol.md (resume protocol:",
        "get_next_stage). Before doing stage work, check",
        f"projects/{project_id}/{DECISIONS_DIRNAME}/ for pending human decisions",
        "recorded from the Backlot UI and apply them: 'approved' -> re-write the",
        "checkpoint as completed with human_approved=True (echo the decision in",
        "metadata.human_decisions); 'changes_requested' -> revise per its",
        "feedback through the stage director skill; 'abort' -> stop and report.",
        "End your turn at every human approval gate - present and wait, never",
        "continue past a gate.",
    ]
    if instruction:
        parts.append(f"\nAdditional direction from the human:\n{instruction}")
    return "\n".join(parts)


class AgentRun:
    """One headless agent session. Thread-safe append-only output buffer."""

    def __init__(self, project_id: str, instruction: str = "",
                 agent: str = "auto") -> None:
        self.run_id = uuid.uuid4().hex[:12]
        self.project_id = project_id
        self.instruction = instruction
        self.agent_request = agent or "auto"
        self.agent_id: Optional[str] = None
        self.agent_label: Optional[str] = None
        self.status = "running"
        self.exit_code: Optional[int] = None
        self.started_at = time.time()
        self.ended_at: Optional[float] = None
        self.buffer: Deque[dict] = deque(maxlen=800)
        self._seq = 0
        self._cond = threading.Condition()
        self._proc: Optional[subprocess.Popen] = None
        self._stop_requested = False

    def summary(self) -> dict:
        return {
            "run_id": self.run_id,
            "project_id": self.project_id,
            "instruction": self.instruction,
            "agent": self.agent_id or self.agent_request,
            "agent_label": self.agent_label,
            "status": self.status,
            "exit_code": self.exit_code,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "lines": len(self.buffer),
            "last_seq": self._seq,
        }

    def lines_since(self, seq: int) -> List[dict]:
        with self._cond:
            return [line for line in self.buffer if line["seq"] > seq]

    def stop(self) -> bool:
        if self._proc and self._proc.poll() is None:
            self._stop_requested = True
            self._proc.terminate()
            return True
        return False

    def _append(self, extra: dict) -> None:
        with self._cond:
            self._seq += 1
            self.buffer.append({"seq": self._seq, "ts": time.time(), **extra})
            self._cond.notify_all()

    def start(self) -> None:
        cmd_override = os.environ.get(AGENT_CMD_ENV)
        if cmd_override:
            # Test/debug escape hatch: run this exact command instead of a
            # registry agent (the prompt is still appended).
            base = shlex.split(cmd_override)
            self.agent_id = self.agent_id or "custom"
            self.agent_label = self.agent_label or "custom command"
        else:
            try:
                spec = agents.resolve(self.agent_request)
            except Exception as exc:
                self._append({
                    "kind": "error",
                    "text": f"failed to resolve agent {self.agent_request!r}: {exc}",
                })
                self.status = "failed"
                self.ended_at = time.time()
                return
            if spec is None:
                self._append({
                    "kind": "error",
                    "text": "no agent CLI available — install claude/gemini "
                            "or define one in backlot/agents.yaml",
                })
                self.status = "failed"
                self.ended_at = time.time()
                return
            base = spec.build_command(build_prompt(self.project_id, self.instruction))
            self.agent_id = spec.id
            self.agent_label = spec.label
        self._append({"kind": "system", "text": f"$ {base[0]} · agent={self.agent_id} …"})
        threading.Thread(target=self._run, args=(cmd_override is not None, base), daemon=True).start()

    def _run(self, has_prompt: bool, base_or_cmd: List[str]) -> None:
        try:
            if has_prompt:
                # Override mode: base command + prompt as final argument.
                cmd = base_or_cmd + [build_prompt(self.project_id, self.instruction)]
            else:
                cmd = base_or_cmd  # registry agents already embed the prompt
            self._proc = subprocess.Popen(
                cmd, cwd=str(REPO_ROOT),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            assert self._proc.stdout is not None
            for raw in self._proc.stdout:
                text = raw.rstrip("\n")
                kind = "json" if text.lstrip().startswith("{") else "out"
                self._append({"kind": kind, "text": text})
            self.exit_code = self._proc.wait()
            if self._stop_requested:
                self.status = "stopped"
            else:
                self.status = "completed" if self.exit_code == 0 else "failed"
        except FileNotFoundError as exc:
            self._append({"kind": "error", "text": f"agent binary not found: {exc}"})
            self.status = "failed"
        except Exception as exc:  # never let the runner crash the server
            self._append({"kind": "error", "text": f"runner error: {exc}"})
            self.status = "failed"
        finally:
            self.ended_at = time.time()
            label = {"completed": "run finished", "failed": "run failed"}.get(
                self.status, "run stopped"
            )
            self._append({"kind": "system", "text": f"— {label} —"})


# ---------------------------------------------------------------------------
# Project kickoff
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    slug = "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")
    slug = "-".join(part for part in slug.split("-") if part)
    return slug[:60] or "production"


def create_project(
    title: str,
    pipeline_type: str,
    brief: str = "",
    project_id: str | None = None,
) -> dict:
    """Initialize a production workspace the way the agent would.

    Uses lib.checkpoint.init_project (canonical layout + project.json marker)
    and records the kickoff brief alongside it, then returns enough info to
    launch a first run.
    """
    title = (title or "").strip()
    if not title:
        raise ValueError("title is required")
    if not pipeline_type:
        raise ValueError("pipeline_type is required")
    pid = slugify(project_id or title)
    target = PROJECTS_DIR / pid
    if target.exists():
        raise ValueError(f"project id already exists: {pid}")
    from lib.checkpoint import init_project
    init_project(pid, title=title, pipeline_type=pipeline_type,
                 pipeline_dir=PROJECTS_DIR)
    record = {
        "version": "1.0",
        "project_id": pid,
        "title": title,
        "pipeline_type": pipeline_type,
        "brief": (brief or "").strip(),
        "created_via": "backlot-ui",
        "created_at_epoch": time.time(),
    }
    try:
        _atomic_write_json(PROJECTS_DIR / pid / "kickoff.json", record)
    except Exception:
        pass  # board must never block on its own bookkeeping
    return record


def kickoff_instruction(brief: str) -> str:
    b = (brief or "").strip()
    parts = ["New production kickoff from the Backlot UI."]
    if b:
        parts.append(f"The human's creative brief:\n\n{b}")
    parts.append(
        "Start at the first pipeline stage and follow AGENT_GUIDE.md; stop at "
        "every approval gate."
    )
    return "\n\n".join(parts)


class RunManager:
    """In-memory registry of agent runs. One active run per project."""

    def __init__(self) -> None:
        self._runs: Dict[str, AgentRun] = {}
        self._lock = threading.Lock()

    def start(self, project_id: str, instruction: str = "",
              agent: str = "auto") -> AgentRun:
        run = AgentRun(project_id, instruction, agent)
        with self._lock:
            for existing in self._runs.values():
                if existing.project_id == project_id and existing.status == "running":
                    raise RuntimeError(
                        f"a run is already active for {project_id}: {existing.run_id}"
                    )
            self._runs[run.run_id] = run
        run.start()
        return run

    def get(self, run_id: str) -> Optional[AgentRun]:
        return self._runs.get(run_id)

    def latest_for_project(self, project_id: str) -> Optional[AgentRun]:
        matches = [r for r in self._runs.values() if r.project_id == project_id]
        return matches[-1] if matches else None

    def all(self) -> List[dict]:
        return [
            r.summary()
            for r in sorted(self._runs.values(), key=lambda r: r.started_at)
        ]


runs = RunManager()

