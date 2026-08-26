"""Unit tests for Backlot cockpit control (backlot/control.py)."""

import json
import time
from pathlib import Path

import pytest

from backlot import control


@pytest.fixture
def project_dir(tmp_path) -> Path:
    p = tmp_path / "projects" / "film"
    (p / "artifacts").mkdir(parents=True)
    return p


def _checkpoint(p: Path, stage: str, status: str, echo: list | None = None) -> None:
    data = {
        "version": "1.0", "project_id": "film", "pipeline_type": "cinematic",
        "stage": stage, "status": status, "human_approved": False,
        "timestamp_epoch": time.time(), "artifacts": {},
    }
    if echo is not None:
        data["metadata"] = {"human_decisions": echo}
    (p / f"checkpoint_{stage}.json").write_text(json.dumps(data), encoding="utf-8")


class TestDecisions:
    def test_write_and_read_roundtrip(self, project_dir):
        rec = control.write_decision(project_dir, "idea", "approved", feedback="love it")
        assert rec["decision"] == "approved"
        assert rec["feedback"] == "love it"
        assert rec["source"] == "backlot-ui"
        path = control.decision_path(project_dir, "idea")
        assert path.is_file()
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["stage"] == "idea"
        assert control.read_decisions(project_dir)["idea"]["decision"] == "approved"

    def test_invalid_decision_rejected(self, project_dir):
        with pytest.raises(ValueError):
            control.write_decision(project_dir, "idea", "maybe")

    def test_invalid_stage_rejected(self, project_dir):
        for bad in ("../escape", "", "a/b", "."):
            with pytest.raises(ValueError):
                control.write_decision(project_dir, bad, "approved")

    def test_records_checkpoint_status_at_decision(self, project_dir):
        _checkpoint(project_dir, "idea", "awaiting_human")
        rec = control.write_decision(project_dir, "idea", "changes_requested",
                                     feedback="make the hook colder")
        assert rec["checkpoint_status_at_decision"] == "awaiting_human"

    def test_latest_wins(self, project_dir):
        control.write_decision(project_dir, "idea", "changes_requested")
        control.write_decision(project_dir, "idea", "approved")
        assert control.read_decisions(project_dir)["idea"]["decision"] == "approved"

    def test_read_missing_dir_is_empty(self, tmp_path):
        assert control.read_decisions(tmp_path / "nothing") == {}


class TestPendingDecisions:
    def test_approved_on_awaiting_gate_is_pending(self, project_dir):
        _checkpoint(project_dir, "idea", "awaiting_human")
        control.write_decision(project_dir, "idea", "approved")
        pending = control.pending_decisions(project_dir)
        assert [p["stage"] for p in pending] == ["idea"]

    def test_changes_requested_on_awaiting_gate_is_pending(self, project_dir):
        _checkpoint(project_dir, "script", "awaiting_human")
        control.write_decision(project_dir, "script", "changes_requested", feedback="x")
        assert len(control.pending_decisions(project_dir)) == 1

    def test_echo_marks_applied(self, project_dir):
        _checkpoint(project_dir, "idea", "completed")
        rec = control.write_decision(project_dir, "idea", "approved")
        # Agent applied it: echoed the decided_at_epoch into the checkpoint.
        (project_dir / "checkpoint_idea.json").write_text(json.dumps({
            "version": "1.0", "stage": "idea", "status": "completed",
            "metadata": {"human_decisions": [
                {"decided_at_epoch": rec["decided_at_epoch"], "decision": "approved"}]},
        }), encoding="utf-8")
        assert control.pending_decisions(project_dir) == []

    def test_decision_without_checkpoint_is_pending(self, project_dir):
        control.write_decision(project_dir, "idea", "abort")
        assert [p["decision"] for p in control.pending_decisions(project_dir)] == ["abort"]


class TestPrompt:
    def test_prompt_mentions_decisions_and_gates(self):
        prompt = control.build_prompt("my-film")
        assert "my-film" in prompt
        assert f"projects/my-film/{control.DECISIONS_DIRNAME}/" in prompt
        assert "AGENT_GUIDE.md" in prompt

    def test_instruction_appended(self):
        prompt = control.build_prompt("f", instruction="keep the pacing tight")
        assert "keep the pacing tight" in prompt


class TestRunManager:
    def test_start_runs_fake_agent_to_completion(self, project_dir, monkeypatch):
        # /bin/echo ignores args and exits 0 — a stand-in agent binary.
        monkeypatch.setenv(control.AGENT_CMD_ENV, "/bin/echo")
        run = control.runs.start(project_dir.name)
        deadline = time.time() + 10
        while run.status == "running" and time.time() < deadline:
            time.sleep(0.05)
        assert run.status == "completed"
        assert run.exit_code == 0
        kinds = {line["kind"] for line in run.buffer}
        assert "system" in kinds

    def test_double_start_conflicts(self, monkeypatch):
        monkeypatch.setenv(
            control.AGENT_CMD_ENV,
            '/bin/sh -c "sleep 30"',
        )
        run = control.runs.start("slow-project")
        try:
            with pytest.raises(RuntimeError):
                control.runs.start("slow-project")
        finally:
            run.stop()
            deadline = time.time() + 5
            while run.status == "running" and time.time() < deadline:
                time.sleep(0.05)

    def test_missing_binary_fails_gracefully(self, monkeypatch):
        monkeypatch.setenv(control.AGENT_CMD_ENV, "/nonexistent/agent-binary-xyz")
        run = control.runs.start("ghost-project")
        deadline = time.time() + 10
        while run.status == "running" and time.time() < deadline:
            time.sleep(0.05)
        assert run.status == "failed"
        assert any(line["kind"] == "error" for line in run.buffer)

    def test_lines_since_filters_by_seq(self, project_dir, monkeypatch):
        monkeypatch.setenv(control.AGENT_CMD_ENV, "/bin/echo")
        run = control.runs.start(project_dir.name)
        deadline = time.time() + 10
        while run.status == "running" and time.time() < deadline:
            time.sleep(0.05)
        lines = control.runs.get(run.run_id).lines_since(0)
        assert lines
        tail = control.runs.get(run.run_id).lines_since(lines[0]["seq"])
        assert all(l["seq"] > lines[0]["seq"] for l in tail)


class TestKickoff:
    def test_slugify(self):
        assert control.slugify("Why Octopuses Are Basically Aliens!") == \
            "why-octopuses-are-basically-aliens"
        assert control.slugify("  --weird   title--  ") == "weird-title"
        assert control.slugify("!!!") == "production"

    def test_create_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr(control, "PROJECTS_DIR", tmp_path)
        record = control.create_project(
            "My Test Film", "cinematic", brief="a short mood piece",
            project_id="my-test-film",
        )
        pdir = tmp_path / "my-test-film"
        assert (pdir / "project.json").is_file()
        assert (pdir / "renders").is_dir()
        kick = json.loads((pdir / "kickoff.json").read_text(encoding="utf-8"))
        assert kick["brief"] == "a short mood piece"
        assert kick["created_via"] == "backlot-ui"
        assert record["project_id"] == "my-test-film"

    def test_create_duplicate_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr(control, "PROJECTS_DIR", tmp_path)
        control.create_project("Film", "cinematic")
        with pytest.raises(ValueError, match="already exists"):
            control.create_project("Film", "cinematic")

    def test_create_requires_title_and_pipeline(self, tmp_path, monkeypatch):
        monkeypatch.setattr(control, "PROJECTS_DIR", tmp_path)
        with pytest.raises(ValueError):
            control.create_project("", "cinematic")
        with pytest.raises(ValueError):
            control.create_project("X", "")

    def test_kickoff_instruction_carries_brief(self):
        instr = control.kickoff_instruction("make it moody, 60s max")
        assert "make it moody" in instr
        assert "approval gate" in instr


class TestDeliverableDiscovery:
    def test_project_named_mp4_found_anywhere(self, tmp_path):
        from backlot.state import _scan_media
        p = tmp_path / "ink-e02"
        (p / "assets" / "e02").mkdir(parents=True)
        (p / "assets" / "e02" / "seg_001.mp4").write_bytes(b"x")       # clip: no
        (p / "assets" / "e02" / "ink-e02_episode.mp4").write_bytes(b"x")  # cut: yes
        media = _scan_media(p)
        paths = [r["path"] for r in media["renders"]]
        assert "assets/e02/ink-e02_episode.mp4" in paths
        assert not any("seg_001" in path for path in paths)

    def test_no_false_positive_without_pid_name(self, tmp_path):
        from backlot.state import _scan_media
        p = tmp_path / "other-film"
        (p / "assets").mkdir(parents=True)
        (p / "assets" / "random_render.mp4").write_bytes(b"x")
        assert _scan_media(p)["renders"] == []


