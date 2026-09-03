"""Project profiles: locked decisions, gate pre-authorization, audit trail."""

import json

import pytest
from tests.contracts.test_phase0_contracts import sample_artifact

from lib.checkpoint import CheckpointValidationError, init_project, write_checkpoint
from lib.profile import (
    ProfileError,
    auto_approve_stages,
    is_locked,
    load_profile,
    locked_decision,
    save_profile,
    stage_auto_approved,
)


def _script_artifact() -> dict:
    return {
        "version": "1.0",
        "title": "Smoke",
        "total_duration_seconds": 1,
        "sections": [
            {"id": "s1", "text": "One second.", "start_seconds": 0, "end_seconds": 1}
        ],
    }


def _profile(project_id: str, **over) -> dict:
    profile = {
        "version": "1.0",
        "project_id": project_id,
        "channel": "ink-testimony",
        "locked": True,
        "decisions": {"Narration TTS provider": "elevenlabs"},
        "gate_policy": {"auto_approve_stages": "all"},
        "runner": "scripts.ink_testimony",
    }
    profile.update(over)
    return profile


def test_missing_profile_keeps_gate_shut(tmp_path) -> None:
    init_project("run", title="Run", pipeline_type="framework-smoke", pipeline_dir=tmp_path)
    with pytest.raises(CheckpointValidationError, match="GATE VIOLATION"):
        write_checkpoint(
            tmp_path, "run", "script", "completed",
            {"script": _script_artifact()},
            pipeline_type="framework-smoke",
        )


def test_unlocked_profile_keeps_gate_shut(tmp_path) -> None:
    init_project("run", title="Run", pipeline_type="framework-smoke", pipeline_dir=tmp_path)
    save_profile(tmp_path, "run", _profile("run", locked=False))
    assert not is_locked(tmp_path, "run")
    with pytest.raises(CheckpointValidationError, match="GATE VIOLATION"):
        write_checkpoint(
            tmp_path, "run", "script", "completed",
            {"script": _script_artifact()},
            pipeline_type="framework-smoke",
        )


def test_stage_not_in_auto_approve_keeps_gate_shut(tmp_path) -> None:
    init_project("run", title="Run", pipeline_type="framework-smoke", pipeline_dir=tmp_path)
    save_profile(
        tmp_path, "run", _profile("run", gate_policy={"auto_approve_stages": ["research"]})
    )
    assert not stage_auto_approved(tmp_path, "run", "script")
    with pytest.raises(CheckpointValidationError, match="GATE VIOLATION"):
        write_checkpoint(
            tmp_path, "run", "script", "completed",
            {"script": _script_artifact()},
            pipeline_type="framework-smoke",
        )


def test_locked_profile_auto_approves_gated_stage(tmp_path) -> None:
    init_project("run", title="Run", pipeline_type="framework-smoke", pipeline_dir=tmp_path)
    save_profile(tmp_path, "run", _profile("run"))
    assert stage_auto_approved(tmp_path, "run", "research")
    path = write_checkpoint(
        tmp_path, "run", "research", "completed",
        {"research_brief": sample_artifact("research_brief")},
        pipeline_type="framework-smoke",
    )
    checkpoint = json.loads(path.read_text())
    assert checkpoint["human_approved"] is True
    assert "locked profile" in checkpoint["metadata"]["approval_source"]


def test_corrupt_locked_profile_fails_closed(tmp_path) -> None:
    init_project("run", title="Run", pipeline_type="framework-smoke", pipeline_dir=tmp_path)
    (tmp_path / "run" / "profile.json").write_text("{not json")
    assert load_profile(tmp_path, "run") is None
    with pytest.raises(CheckpointValidationError, match="GATE VIOLATION"):
        write_checkpoint(
            tmp_path, "run", "script", "completed",
            {"script": _script_artifact()},
            pipeline_type="framework-smoke",
        )


def test_locked_profile_without_decisions_rejected(tmp_path) -> None:
    with pytest.raises(ProfileError, match="decisions"):
        save_profile(tmp_path, "run", _profile("run", decisions={}))


def test_save_profile_records_approval_policy_decision(tmp_path) -> None:
    init_project("run", title="Run", pipeline_type="framework-smoke", pipeline_dir=tmp_path)
    save_profile(tmp_path, "run", _profile("run"))
    log = json.loads((tmp_path / "run" / "decision_log.json").read_text())
    approval = [
        d for d in log["decisions"] if d["category"] == "approval_policy"
    ]
    assert len(approval) == 1
    assert "locked profile" in approval[0]["subject"]
    assert approval[0]["options_considered"]


def test_relocking_replaces_not_stacks_approval_decision(tmp_path) -> None:
    init_project("run", title="Run", pipeline_type="framework-smoke", pipeline_dir=tmp_path)
    save_profile(tmp_path, "run", _profile("run"))
    save_profile(
        tmp_path, "run",
        _profile("run", gate_policy={"auto_approve_stages": ["assets", "compose"]}),
    )
    log = json.loads((tmp_path / "run" / "decision_log.json").read_text())
    approval = [
        d for d in log["decisions"] if d["category"] == "approval_policy"
    ]
    assert len(approval) == 1
    assert "compose" in approval[0]["selected"]["label"]


def test_auto_approve_all_and_stage_lists(tmp_path) -> None:
    assert auto_approve_stages(tmp_path, "ghost") == []
    save_profile(tmp_path, "ghost", _profile("ghost"))
    assert len(auto_approve_stages(tmp_path, "ghost")) == 9
    save_profile(
        tmp_path, "ghost",
        _profile("ghost", gate_policy={"auto_approve_stages": ["assets", "compose"]}),
    )
    assert auto_approve_stages(tmp_path, "ghost") == ["assets", "compose"]


def test_locked_decision_lookup(tmp_path) -> None:
    save_profile(tmp_path, "run", _profile("run"))
    assert locked_decision(tmp_path, "run", "Narration TTS provider") == "elevenlabs"
    assert locked_decision(tmp_path, "run", "Music provider") is None
    save_profile(tmp_path, "run", _profile("run", locked=False))
    assert locked_decision(tmp_path, "run", "Narration TTS provider") is None
