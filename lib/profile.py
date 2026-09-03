"""Project profiles: locked decisions that remove per-run re-gating.

A profile is ``projects/<project_id>/profile.json``. It records the choices a
project (or series/channel) has already made — provider, voice, style playbook,
render runtime, runner module, and an approval policy — so a returning run can
skip preflight menus, provider gates, music re-planning, and per-stage approval
presentations WITHOUT dropping any guidance: the agent still reads stage-level
guidance when it does that stage's work, and still escalates blockers.

Token-efficiency contract (progressive disclosure, not guidance removal):
a locked profile means "stop re-asking decided questions", never
"skip reading guidance relevant to the decision at hand".

Gate semantics (fail-closed):

- Auto-approval requires ``locked: true`` AND the stage listed in
  ``gate_policy.auto_approve_stages``. A missing, corrupt, or unlocked profile
  degrades to the normal gated flow — never to silent approval.
- When a profile with auto-approval is saved, an ``approval_policy`` decision is
  appended to the project's ``decision_log.json`` — the audit trail the
  Human Checkpoint Protocol requires for full-run pre-authorization.
- Any decision change (provider swap, voice swap, ...) MUST go through
  ``set_decision`` / re-``save_profile`` so the log entry is refreshed; editing
  the JSON by hand leaves the audit trail stale.

CLI::

    python -m lib.profile init <project_id> --auto-approve all --runner scripts.ink_testimony
    python -m lib.profile show <project_id>
    python -m lib.profile set <project_id> "provider_selection/Image generation provider" flux_pro
    python -m lib.profile lock <project_id>    # enables gate skipping
    python -m lib.profile unlock <project_id>  # back to full gated flow
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from lib.paths import PROJECTS_DIR

PROFILE_FILENAME = "profile.json"

# Stages whose work is mechanical once the artifacts exist (assets/compose run
# through a standardized runner). Creative stages stay in auto_approve only if
# the user explicitly listed them — the default init does NOT include them.
MECHANICAL_STAGES = ["assets", "edit", "compose", "publish"]

ALL_STAGES = [
    "research", "proposal", "idea", "script", "scene_plan",
    "assets", "edit", "compose", "publish",
]


class ProfileError(ValueError):
    """Raised when a profile is structurally invalid for its intended use."""


def profile_path(pipeline_dir: Path, project_id: str) -> Path:
    return Path(pipeline_dir) / project_id / PROFILE_FILENAME


def load_profile(pipeline_dir: Path, project_id: str) -> Optional[dict[str, Any]]:
    """Load a project profile, or None when absent.

    Corrupt or structurally invalid profiles return None (gates stay ON).
    A profile that claims to be locked but violates the lock invariants
    raises — silently ignoring a corrupt *locked* profile would fail-open.
    """
    path = profile_path(pipeline_dir, project_id)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            profile = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(profile, dict):
        return None
    if profile.get("locked"):
        _validate_locked(profile)
    return profile


def _validate_locked(profile: dict[str, Any]) -> None:
    decisions = profile.get("decisions")
    if not isinstance(decisions, dict) or not decisions:
        raise ProfileError(
            "Locked profile must carry a non-empty 'decisions' object — a "
            "locked profile with no recorded decisions is an audit-trail defect."
        )


def is_locked(pipeline_dir: Path, project_id: str) -> bool:
    profile = load_profile(pipeline_dir, project_id)
    return bool(profile and profile.get("locked"))


def auto_approve_stages(pipeline_dir: Path, project_id: str) -> list[str]:
    """Stages a locked profile pre-approves. Empty list = fully manual."""
    profile = load_profile(pipeline_dir, project_id)
    if not profile or not profile.get("locked"):
        return []
    policy = profile.get("gate_policy", {}) or {}
    stages = policy.get("auto_approve_stages", [])
    if stages == "all":
        return list(ALL_STAGES)
    if not isinstance(stages, list):
        return []
    return [s for s in stages if s in ALL_STAGES]


def stage_auto_approved(pipeline_dir: Path, project_id: str, stage: str) -> bool:
    """True when a locked profile pre-authorizes this stage's approval gate.

    This is the ONLY query checkpoint enforcement consults; everything else in
    the profile is advisory context for the agent.
    """
    return stage in auto_approve_stages(pipeline_dir, project_id)


def locked_decision(
    pipeline_dir: Path, project_id: str, subject: str
) -> Optional[Any]:
    """Look up a locked choice by decision subject (e.g. 'Narration TTS provider').

    Decisions are stored flat: ``decisions[subject] = selected_value``. Returns
    None when no profile, unlocked, or subject unknown — callers then run the
    normal gate (ask the user).
    """
    profile = load_profile(pipeline_dir, project_id)
    if not profile or not profile.get("locked"):
        return None
    return (profile.get("decisions") or {}).get(subject)


def runner_module(pipeline_dir: Path, project_id: str) -> Optional[str]:
    """The standardized runner this project drives (e.g. 'scripts.ink_testimony')."""
    profile = load_profile(pipeline_dir, project_id)
    if not profile:
        return None
    return profile.get("runner")


def _append_approval_policy_decision(
    pipeline_dir: Path, project_id: str, stages: list[str], source: str
) -> None:
    """Record full-run pre-authorization as an approval_policy decision.

    The Human Checkpoint Protocol requires explicit full-run pre-authorization
    to be logged; a profile that skips gates without this entry is invalid.
    """
    log_path = Path(pipeline_dir) / project_id / "decision_log.json"
    if log_path.exists():
        try:
            with open(log_path, encoding="utf-8") as f:
                log = json.load(f)
        except (json.JSONDecodeError, OSError):
            log = {}
    else:
        log = {}
    log.setdefault("version", "1.0")
    log.setdefault("project_id", project_id)
    decisions = log.setdefault("decisions", [])
    decision = {
        "decision_id": f"d-{uuid.uuid4().hex[:8]}",
        "stage": "proposal",
        "category": "approval_policy",
        "subject": "Full-run approval via locked profile",
        "options_considered": [
            {
                "option_id": "per_gate_approval",
                "label": "Present each gated stage and wait",
                "score": 5,
                "reason": "Default, but re-asks decided questions every episode.",
            },
            {
                "option_id": "locked_profile",
                "label": f"Auto-approve {', '.join(stages)}",
                "score": 8,
                "reason": "Choices are locked in the profile; escalations still surface blockers.",
            },
        ],
        "selected": {"option_id": "locked_profile", "label": f"Auto-approve {', '.join(stages)}"},
        "reason": f"Pre-authorized by locked profile ({source}). Blockers still escalate.",
    }
    # Replace any previous profile-based approval_policy decision rather than
    # stacking superseded ones; unrelated approval_policy entries stay intact.
    decisions[:] = [
        d for d in decisions
        if not (
            d.get("category") == "approval_policy"
            and "locked profile" in str(d.get("subject", "")).lower()
        )
    ]
    decisions.append(decision)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)


def save_profile(
    pipeline_dir: Path,
    project_id: str,
    profile: dict[str, Any],
    *,
    record_decision: bool = True,
) -> Path:
    """Write a project profile; stamps updated_at and logs approval policy."""
    project_dir = Path(pipeline_dir) / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    profile = dict(profile)
    profile.setdefault("version", "1.0")
    profile.setdefault("project_id", project_id)
    profile["updated_at"] = datetime.now(timezone.utc).isoformat()
    if profile.get("locked"):
        _validate_locked(profile)
    if record_decision and profile.get("locked"):
        stages = auto_approve_stages_from(profile)
        if stages:
            _append_approval_policy_decision(
                pipeline_dir, project_id, stages, profile.get("channel", "unspecified channel")
            )
    path = project_dir / PROFILE_FILENAME
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)
    return path


def auto_approve_stages_from(profile: dict[str, Any]) -> list[str]:
    """auto_approve_stages for a not-yet-saved profile dict (used by save_profile)."""
    if not profile.get("locked"):
        return []
    policy = profile.get("gate_policy", {}) or {}
    stages = policy.get("auto_approve_stages", [])
    if stages == "all":
        return list(ALL_STAGES)
    if not isinstance(stages, list):
        return []
    return [s for s in stages if s in ALL_STAGES]


# --------------------------------------------------------------------- CLI


def _resolve(project_id: str) -> tuple[Path, str]:
    return PROJECTS_DIR, project_id


def _cmd_init(args) -> None:
    pipeline_dir, project_id = _resolve(args.project_id)
    if args.auto_approve == "none":
        stages: list[str] | str = []
    elif args.auto_approve == "all":
        stages = "all"
    else:
        stages = [s.strip() for s in args.auto_approve.split(",") if s.strip()]
        unknown = [s for s in stages if s not in ALL_STAGES]
        if unknown:
            raise SystemExit(f"Unknown stages: {unknown}. Valid: {ALL_STAGES}")
    profile = {
        "version": "1.0",
        "project_id": project_id,
        "channel": args.channel,
        "locked": not args.unlocked,
        "decisions": dict(d.split("=", 1) for d in (args.decision or [])),
        "gate_policy": {"auto_approve_stages": stages},
        "runner": args.runner,
        "notes": args.note or [],
    }
    path = save_profile(pipeline_dir, project_id, profile)
    print(f"profile written: {path}")
    print(f"  locked: {profile['locked']}")
    print(f"  auto-approve: {stages or '(none)'}")
    print(f"  runner: {args.runner or '(none)'}")


def _cmd_show(args) -> None:
    pipeline_dir, project_id = _resolve(args.project_id)
    profile = load_profile(pipeline_dir, project_id)
    if profile is None:
        print(f"no profile for {project_id} (normal gated flow applies)")
        return
    print(json.dumps(profile, indent=2))


def _cmd_set(args) -> None:
    pipeline_dir, project_id = _resolve(args.project_id)
    profile = load_profile(pipeline_dir, project_id) or {
        "version": "1.0", "project_id": project_id, "locked": False,
        "decisions": {}, "gate_policy": {"auto_approve_stages": []},
    }
    profile.setdefault("decisions", {})[args.subject] = _parse_value(args.value)
    if profile.get("locked"):
        _validate_locked(profile)
    save_profile(pipeline_dir, project_id, profile)
    print(f"decision locked: {args.subject} = {args.value}")


def _cmd_lock(args) -> None:
    _set_lock(args.project_id, True)


def _cmd_unlock(args) -> None:
    _set_lock(args.project_id, False)


def _set_lock(project_id: str, locked: bool) -> None:
    pipeline_dir, project_id = _resolve(project_id)
    profile = load_profile(pipeline_dir, project_id)
    if profile is None:
        raise SystemExit(
            f"no profile for {project_id} — create one with "
            f"`python -m lib.profile init {project_id}` first"
        )
    profile["locked"] = locked
    save_profile(pipeline_dir, project_id, profile)
    state = "LOCKED — gates pre-authorized per gate_policy" if locked \
        else "UNLOCKED — full gated flow applies"
    print(f"profile {project_id}: {state}")


def _parse_value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m lib.profile",
        description="Project profiles: locked decisions that remove per-run re-gating.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="create/overwrite a project profile")
    p_init.add_argument("project_id")
    p_init.add_argument("--channel", default=None, help="series/channel name, e.g. ink-testimony")
    p_init.add_argument(
        "--auto-approve", default="none",
        help="'none', 'all', or comma-separated stages (creative stages should be listed "
             "only deliberately)",
    )
    p_init.add_argument("--runner", default=None, help="standardized runner module, e.g. scripts.ink_testimony")
    p_init.add_argument("--decision", action="append", metavar="SUBJECT=VALUE",
                        help="locked decision, e.g. 'TTS provider=elevenlabs'")
    p_init.add_argument("--note", action="append", help="free-text note surfaced to the agent")
    p_init.add_argument("--unlocked", action="store_true", help="save without locking (draft)")
    p_init.set_defaults(func=_cmd_init)

    p_show = sub.add_parser("show", help="print a project profile")
    p_show.add_argument("project_id")
    p_show.set_defaults(func=_cmd_show)

    p_set = sub.add_parser("set", help="lock one decision (provider, voice, runtime, ...)")
    p_set.add_argument("project_id")
    p_set.add_argument("subject", help="decision subject, e.g. 'Narration TTS provider'")
    p_set.add_argument("value")
    p_set.set_defaults(func=_cmd_set)

    p_lock = sub.add_parser("lock", help="enable gate pre-authorization")
    p_lock.add_argument("project_id")
    p_lock.set_defaults(func=_cmd_lock)

    p_unlock = sub.add_parser("unlock", help="return to the full gated flow")
    p_unlock.add_argument("project_id")
    p_unlock.set_defaults(func=_cmd_unlock)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
