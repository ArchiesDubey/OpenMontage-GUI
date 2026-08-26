"""Backlot agent registry — which CLI brains can drive a production.

The cockpit is agent-agnostic: any CLI that can run a prompt headlessly and
edit files can drive a pipeline. Built-in adapters cover Claude Code and the
Gemini CLI (both speak newline-delimited stream-json in headless mode).
Anything else — e.g. an OpenRouter-backed CLI like ``aider --model
openrouter/...`` or ``opencode`` — plugs in through ``backlot/agents.yaml``
with a ``{prompt}`` command template, no code required:

    agents:
      openrouter-aider:
        label: Aider · OpenRouter
        command: 'aider --yes-always --model openrouter/anthropic/claude-sonnet-4 --message "{prompt}"'
        requires_env: OPENROUTER_API_KEY   # optional availability gate

Selection order: explicit request > BACKLOT_AGENT_CMD (tests/debug) >
first AVAILABLE built-in in preference order (claude, gemini) > first
available custom. Unavailable agents are reported with the reason why, so
the UI always shows what you have AND what you could unlock.
"""

from __future__ import annotations

import os
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

AGENTS_FILE = Path(__file__).resolve().parent / "agents.yaml"

# Preference order for "auto" selection (built-ins first).
PREFERENCE_ORDER = ["claude", "gemini"]

AGENT_CMD_ENV = "BACKLOT_AGENT_CMD"


@dataclass(frozen=True)
class AgentSpec:
    id: str
    label: str
    hint: str = ""
    requires_env: Optional[str] = None
    build_fn: Optional[object] = None   # callable(prompt) -> list[str]
    template: Optional[str] = None

    def build_command(self, prompt: str) -> List[str]:
        if self.build_fn is not None:
            return list(self.build_fn(prompt))
        assert self.template
        # Tokenize the template FIRST (its quoting is fixed, trusted YAML),
        # then substitute the arbitrary prompt into the resulting argv
        # tokens. Substituting before shlex.split would let quote/backslash
        # characters in the prompt reshape argument boundaries.
        return [tok.replace("{prompt}", prompt) for tok in shlex.split(self.template)]

    @property
    def binary(self) -> str:
        if self.build_fn is not None:
            return self.id
        assert self.template
        return shlex.split(self.template)[0]

    def availability(self) -> tuple[bool, str]:
        """(available, reason-if-not). Full capability picture, never silent."""
        if self.requires_env and not os.environ.get(self.requires_env):
            return False, f"set {self.requires_env} to enable"
        found = shutil.which(self.binary)
        if not found:
            return False, f"'{self.binary}' not found on PATH"
        return True, ""


def _build_claude(prompt: str) -> List[str]:
    return [
        "claude", "-p", prompt,
        "--output-format", "stream-json",
        "--verbose",
        "--permission-mode", "acceptEdits",
    ]


def _build_gemini(prompt: str) -> List[str]:
    return [
        "gemini", "-p", prompt,
        "-o", "stream-json",
        "--approval-mode", "auto_edit",
    ]


_BUILT_INS = {
    "claude": AgentSpec(
        id="claude",
        label="Claude Code",
        hint="anthropic · stream-json · acceptEdits",
        build_fn=_build_claude,
    ),
    "gemini": AgentSpec(
        id="gemini",
        label="Gemini CLI",
        hint="google · stream-json · auto_edit",
        build_fn=_build_gemini,
    ),
}


def load_custom_specs() -> Dict[str, AgentSpec]:
    """Custom agents from backlot/agents.yaml. Malformed entries degrade."""
    specs: Dict[str, AgentSpec] = {}
    if not AGENTS_FILE.is_file():
        return specs
    try:
        import yaml
        data = yaml.safe_load(AGENTS_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        return specs
    for agent_id, cfg in (data.get("agents") or {}).items():
        if not isinstance(cfg, dict) or not cfg.get("command"):
            continue
        template = str(cfg["command"])
        if "{prompt}" not in template:
            continue
        specs[str(agent_id)] = AgentSpec(
            id=str(agent_id),
            label=str(cfg.get("label") or agent_id),
            hint=str(cfg.get("hint") or ""),
            requires_env=cfg.get("requires_env"),
            template=template,
        )
    return specs


def all_specs() -> Dict[str, AgentSpec]:
    """Built-ins + custom file entries."""
    specs = dict(_BUILT_INS)
    specs.update(load_custom_specs())
    return specs


def catalog() -> List[dict]:
    """Every known agent with its availability — the full honest menu."""
    rows = []
    for spec in all_specs().values():
        ok, reason = spec.availability()
        rows.append({
            "id": spec.id,
            "label": spec.label,
            "hint": spec.hint,
            "available": ok,
            "reason": reason,
        })
    return rows


def resolve(agent: Optional[str] = None) -> Optional[AgentSpec]:
    """Pick the requested agent, or the best available one for 'auto'/None.

    Raises ValueError for unknown agents and RuntimeError when a named
    agent is not usable on this machine.
    """
    specs = all_specs()
    if agent and agent != "auto":
        spec = specs.get(agent)
        if spec is None:
            raise ValueError(f"unknown agent: {agent!r}")
        ok, reason = spec.availability()
        if not ok:
            raise RuntimeError(f"agent {agent!r} unavailable: {reason}")
        return spec
    order = PREFERENCE_ORDER + [aid for aid in specs if aid not in PREFERENCE_ORDER]
    for agent_id in order:
        spec = specs[agent_id]
        ok, _ = spec.availability()
        if ok:
            return spec
    return None

