"""Unit tests for the Backlot agent registry (backlot/agents.py)."""

import textwrap

import pytest

from backlot import agents


@pytest.fixture
def fake_which(monkeypatch):
    """Make shutil.which report only the given binaries as present."""
    def _set(*present):
        known = set(present)

        def which(name, *a, **k):
            return "/fake/bin/" + name if name in known else None

        monkeypatch.setattr(agents.shutil, "which", which)

    return _set


class TestCatalog:
    def test_builtins_present(self):
        ids = {row["id"] for row in agents.catalog()}
        assert {"claude", "gemini"} <= ids

    def test_full_capability_picture(self, fake_which):
        fake_which("claude")  # gemini missing on purpose
        rows = {r["id"]: r for r in agents.catalog()}
        assert rows["claude"]["available"] is True
        assert rows["gemini"]["available"] is False
        assert rows["gemini"]["reason"]


class TestResolve:
    def test_auto_prefers_claude(self, fake_which):
        fake_which("claude", "gemini")
        spec = agents.resolve("auto")
        assert spec.id == "claude"

    def test_auto_falls_back_to_gemini(self, fake_which):
        fake_which("gemini")
        spec = agents.resolve(None)
        assert spec.id == "gemini"

    def test_named_agent_selected(self, fake_which):
        fake_which("claude", "gemini")
        assert agents.resolve("gemini").id == "gemini"

    def test_unavailable_named_agent_raises(self, fake_which):
        fake_which()  # nothing installed
        with pytest.raises(RuntimeError):
            agents.resolve("gemini")

    def test_unknown_agent_raises(self):
        with pytest.raises(ValueError):
            agents.resolve("not-a-thing")


class TestCommands:
    def test_claude_command_shape(self):
        cmd = agents.all_specs()["claude"].build_command("PROMPT")
        assert cmd[0] == "claude"
        assert "-p" in cmd and "PROMPT" in cmd
        assert "stream-json" in " ".join(cmd)

    def test_gemini_command_shape(self):
        cmd = agents.all_specs()["gemini"].build_command("PROMPT")
        assert cmd[0] == "gemini"
        assert "-p" in cmd and "PROMPT" in cmd
        assert "stream-json" in " ".join(cmd)


class TestCustomAgents:
    def test_load_from_yaml(self, monkeypatch, tmp_path):
        agents_file = tmp_path / "agents.yaml"
        agents_file.write_text(textwrap.dedent("""
            agents:
              openrouter-aider:
                label: Aider · OpenRouter
                command: 'aider --yes-always --model openrouter/x --message "{prompt}"'
                requires_env: BACKLOT_TEST_SECRET_XYZ
        """), encoding="utf-8")
        monkeypatch.setattr(agents, "AGENTS_FILE", agents_file)
        specs = agents.load_custom_specs()
        assert "openrouter-aider" in specs
        spec = specs["openrouter-aider"]
        # Env gate: not available without the key.
        ok, reason = spec.availability()
        assert not ok and "BACKLOT_TEST_SECRET_XYZ" in reason
        monkeypatch.setenv("BACKLOT_TEST_SECRET_XYZ", "sk-test")
        monkeypatch.setattr(agents.shutil, "which",
                            lambda n, *a, **k: "/fake/aider" if n == "aider" else None)
        ok, _ = spec.availability()
        assert ok is True
        cmd = spec.build_command("DO THE THING")
        joined = " ".join(cmd)
        assert "openrouter/x" in joined
        assert "DO THE THING" in joined

    def test_malformed_entries_degrade(self, monkeypatch, tmp_path):
        agents_file = tmp_path / "agents.yaml"
        agents_file.write_text(textwrap.dedent("""
            agents:
              broken:
                label: no command key
              also-broken:
                command: 'no-prompt-placeholder here'
              : : :
        """), encoding="utf-8")
        monkeypatch.setattr(agents, "AGENTS_FILE", agents_file)
        assert agents.load_custom_specs() == {}

    def test_custom_agent_resolvable_and_selectable(self, monkeypatch, tmp_path):
        agents_file = tmp_path / "agents.yaml"
        agents_file.write_text(textwrap.dedent("""
            agents:
              echo-agent:
                label: Echo
                command: '/bin/echo "{prompt}"'
        """), encoding="utf-8")
        monkeypatch.setattr(agents, "AGENTS_FILE", agents_file)
        spec = agents.resolve("echo-agent")
        assert spec.id == "echo-agent"
