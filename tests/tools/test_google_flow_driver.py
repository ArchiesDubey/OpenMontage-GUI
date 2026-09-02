"""Tests for Google Flow Driver (pure logic + orchestration with a fake session)."""

import io
import json
import time
from pathlib import Path

import pytest
from PIL import Image

import tools.graphics.google_flow_driver as driver_mod
from tools.graphics.google_flow_driver import (
    DriverState,
    FlowSession,
    GenerationTimeout,
    GoogleFlowDriver,
    RateLimiter,
    RateLimitError,
    _save_image_bytes,
    classify_alert_text,
    run_driver,
    upsize_media_url,
)
from tools.tool_registry import ToolRegistry


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def queue_project(tmp_path: Path):
    """Project dir with an exported queue of two prompts."""
    project_id = "driver-test-project"
    project_dir = tmp_path / project_id
    export_dir = project_dir / "exports" / "google_flow"
    export_dir.mkdir(parents=True)
    queue = [
        {
            "index": 1,
            "scene_id": "scene-1",
            "target_filename": "01_scene-1.png",
            "prompt": "An astronaut on a red planet. /wide_angle --ar 16:9",
            "description": "Astronaut on red planet",
        },
        {
            "index": 2,
            "scene_id": "scene-2",
            "target_filename": "02_scene-2.png",
            "prompt": "Futuristic control room. /bokeh --ar 16:9",
            "description": "Futuristic control room",
        },
    ]
    (export_dir / "queue.json").write_text(json.dumps(queue), encoding="utf-8")
    return project_dir


def _png_bytes(size=(2048, 1152)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (120, 40, 90)).save(buf, format="PNG")
    return buf.getvalue()


class FakeSession:
    """Mimics FlowSession without any browser or network."""

    instances: list["FakeSession"] = []
    fail_scene_ids: set[str] = set()

    def __init__(self, profile_dir=None, headless=False, cdp_url=None, logger=None):
        self.profile_dir = profile_dir
        self.closed = False
        self.keep_open_arg = None
        FakeSession.instances.append(self)
        self.snap_calls = 0

    # lifecycle
    def start(self):
        pass

    def close(self, keep_open=False):
        self.closed = True
        self.keep_open_arg = keep_open

    def open_flow(self):
        pass

    def wait_for_login(self, timeout_s=600.0):
        return True

    def new_project_if_needed(self):
        return True

    # session setup
    def setup_generation_settings(self, model_hint="Nano Banana", aspect_ratio="16:9",
                                  outputs=1):
        return {"panel_opened": True, "aspect": aspect_ratio, "outputs": outputs,
                "model_options_seen": [], "saved": True}

    def settings_diagnostics(self):
        return ["Create", "Nano Banana 2"]

    # per-prompt
    def snapshot(self):
        return {"imgs": [], "busy": 0, "alerts": [], "createReady": True,
                "hasPromptBox": True, "hasAppShell": True, "dialogTexts": []}

    def submit_and_wait(self, prompt, before_imgs, timeout_s=240.0, poll_s=1.5,
                        auto_confirm=True):
        self.snap_calls += 1
        scene_num = int(self.snap_calls)
        if scene_num in FakeSession.fail_scene_ids:
            raise GenerationTimeout("simulated timeout")
        # Flow's real post-generation media URLs are same-origin tRPC redirects
        return {"url": ("https://labs.google/fx/api/trpc/media.getMediaUrlRedirect"
                        f"?name=00000000-0000-0000-0000-{scene_num:012d}")}

    def download_media_2k(self, img_url, dest, resolution="2K", debug=False):
        dest.write_bytes(_png_bytes())
        return {"path": "download-dialog", "resolution": "2048x1152"}

    def fetch_media_bytes(self, url):
        return _png_bytes(), url

    def capture_master_fast(self, media_url, dest, resolution="2K", min_width=1900):
        dest.write_bytes(_png_bytes())
        return {"path": "local-2x-upscale", "resolution": "2048x1152"}


@pytest.fixture
def fake_session(monkeypatch):
    FakeSession.instances = []
    FakeSession.fail_scene_ids = set()
    monkeypatch.setattr(driver_mod, "FlowSession", FakeSession)
    return FakeSession


# -----------------------------------------------------------------------------
# Pure logic
# -----------------------------------------------------------------------------


class TestUpsizeMediaUrl:
    def test_s_suffix(self):
        assert upsize_media_url("https://lh3.googleusercontent.com/abc=s1632") == \
            "https://lh3.googleusercontent.com/abc=s0"

    def test_wh_suffix(self):
        assert upsize_media_url("https://lh3.googleusercontent.com/abc=w4032-h2268-p-k-no-nu") == \
            "https://lh3.googleusercontent.com/abc=s0"

    def test_no_suffix(self):
        assert upsize_media_url("https://lh3.googleusercontent.com/abc") is None


class TestClassifyAlertText:
    def test_rate_limit_variants(self):
        for text in [
            "You've reached your daily limit",
            "Generation quota exceeded",
            "You're out of credits",
            "Too many requests, try again later",
        ]:
            assert classify_alert_text(text) == "rate_limit", text

    def test_transient(self):
        assert classify_alert_text("Something went wrong. Please try again.") == "transient"

    def test_benign(self):
        assert classify_alert_text("Image generated") is None
        assert classify_alert_text("") is None


class TestRateLimiter:
    def test_jitter_bounds(self):
        rng = type("R", (), {"uniform": staticmethod(lambda a, b: (a + b) / 2)})()
        rl = RateLimiter(min_delay_s=10.0, max_delay_s=20.0, rng=rng, chunk_every=0)
        assert rl.success_delay() == 15.0

    def test_min_le_max_validation(self):
        with pytest.raises(ValueError):
            RateLimiter(min_delay_s=50.0, max_delay_s=20.0)

    def test_chunk_cooldown_appended(self):
        max_rng = type("R", (), {"uniform": staticmethod(lambda a, b: b)})
        rl = RateLimiter(min_delay_s=10.0, max_delay_s=20.0, rng=max_rng(),
                         chunk_every=2, chunk_cooldown_s=240.0)
        rl.success_delay()  # 1st success: no chunk
        delay = rl.success_delay()  # 2nd success: chunk cooldown added
        assert delay >= 20.0 + 120.0  # max delay + >=0.5*cooldown

    def test_backoff_grows_and_caps(self):
        rl = RateLimiter(backoff_base_s=300.0, backoff_cap_s=2700.0,
                         rng=type("R", (), {"uniform": staticmethod(lambda a, b: (a + b) / 2)})())
        delays = [rl.backoff_delay() for _ in range(4)]
        assert delays[0] == 300.0  # 300 * midpoint jitter 1.0
        assert delays[1] > delays[0]
        assert delays[3] <= 2700.0 * 1.5

    def test_backoff_aborts_after_max(self):
        rl = RateLimiter(max_consecutive_backoffs=3)
        for _ in range(3):
            rl.backoff_delay()
        with pytest.raises(RateLimitError):
            rl.backoff_delay()

    def test_success_resets_backoff(self):
        rl = RateLimiter(max_consecutive_backoffs=2, chunk_every=0)
        rl.backoff_delay()
        rl.success_delay()
        rl.backoff_delay()  # consecutive count was reset, must not raise
        assert rl.consecutive_backoffs == 1


class TestDriverState:
    def test_mark_and_reload(self, tmp_path):
        path = tmp_path / "state.json"
        st = DriverState(path, "proj")
        st.mark("01_scene-1.png", "succeeded", resolution="2048x1152")
        reloaded = DriverState(path, "proj")
        assert reloaded.status_of("01_scene-1.png") == "succeeded"
        assert reloaded.items["01_scene-1.png"]["resolution"] == "2048x1152"

    def test_project_mismatch_starts_fresh(self, tmp_path):
        path = tmp_path / "state.json"
        st = DriverState(path, "proj-a")
        st.mark("01.png", "succeeded")
        fresh = DriverState(path, "proj-b")
        assert fresh.status_of("01.png") is None

    def test_corrupt_state_does_not_wedge(self, tmp_path):
        path = tmp_path / "state.json"
        path.write_text("{not json", encoding="utf-8")
        st = DriverState(path, "proj")
        assert st.items == {}
        st.mark("01.png", "succeeded")  # still usable
        assert DriverState(path, "proj").status_of("01.png") == "succeeded"

    def test_reset(self, tmp_path):
        path = tmp_path / "state.json"
        st = DriverState(path, "proj")
        st.mark("01.png", "succeeded")
        st.reset()
        assert DriverState(path, "proj").status_of("01.png") is None


class TestSaveImageBytes:
    def test_png_passthrough_records_resolution(self, tmp_path):
        dest = tmp_path / "img.png"
        res = _save_image_bytes(_png_bytes((2048, 1152)), dest)
        assert res == "2048x1152"
        with Image.open(dest) as im:
            assert im.size == (2048, 1152)

    def test_jpeg_converted_to_png(self, tmp_path):
        buf = io.BytesIO()
        Image.new("RGB", (512, 288), (10, 200, 30)).save(buf, format="JPEG")
        dest = tmp_path / "img.png"
        res = _save_image_bytes(buf.getvalue(), dest)
        assert res == "512x288"
        with Image.open(dest) as im:
            assert im.format == "PNG"


# -----------------------------------------------------------------------------
# Orchestration (fake session)
# -----------------------------------------------------------------------------


class TestRunDriver:
    def test_missing_queue_errors(self, tmp_path):
        (tmp_path / "lonely-project").mkdir()
        res = run_driver("lonely-project", projects_root=tmp_path)
        assert res.success is False
        assert "queue.json" in res.error

    def test_skips_completed_without_starting_browser(self, queue_project, fake_session):
        drop = queue_project / "drop_images"
        drop.mkdir()
        (drop / "01_scene-1.png").write_bytes(_png_bytes())
        state = DriverState(
            queue_project / "exports" / "google_flow" / "driver_state.json",
            "driver-test-project",
        )
        state.mark("01_scene-1.png", "succeeded")

        res = run_driver("driver-test-project", projects_root=queue_project.parent,
                         upscale_mode="flow")
        assert res.success
        assert res.data["succeeded"] == 1
        assert res.data["pending"] == 0
        # Only the one not-yet-done scene was submitted to (fake) Flow
        assert fake_session.instances[-1].snap_calls == 1
        # Second run: everything done -> nothing to do, no browser launched
        (drop / "02_scene-2.png").write_bytes(_png_bytes())
        sessions_before = len(fake_session.instances)
        res2 = run_driver("driver-test-project", projects_root=queue_project.parent,
                          upscale_mode="flow")
        assert res2.success
        assert "Nothing to do" in res2.data["message"]
        assert len(fake_session.instances) == sessions_before

    def test_full_run_saves_images_and_state(self, queue_project, fake_session, monkeypatch):
        monkeypatch.setattr(driver_mod.time, "sleep", lambda s: None)
        res = run_driver(
            "driver-test-project",
            projects_root=queue_project.parent,
            upscale_mode="flow",
            min_delay_s=0.0,
            max_delay_s=0.0,
        )
        assert res.success, res.error
        drop = queue_project / "drop_images"
        assert (drop / "01_scene-1.png").is_file()
        assert (drop / "02_scene-2.png").is_file()
        state = DriverState(
            queue_project / "exports" / "google_flow" / "driver_state.json",
            "driver-test-project",
        )
        assert state.status_of("01_scene-1.png") == "succeeded"
        assert state.status_of("02_scene-2.png") == "succeeded"
        # 2K dimensions recorded from the actual pixels
        assert state.items["01_scene-1.png"]["resolution"] == "2048x1152"
        assert fake_session.instances[-1].closed

    def test_generation_timeout_marks_failed_and_continues(
        self, queue_project, fake_session, monkeypatch
    ):
        fake_session.fail_scene_ids = {1}
        monkeypatch.setattr(driver_mod.time, "sleep", lambda s: None)
        res = run_driver(
            "driver-test-project",
            projects_root=queue_project.parent,
            upscale_mode="flow",
            min_delay_s=0.0,
            max_delay_s=0.0,
        )
        state = DriverState(
            queue_project / "exports" / "google_flow" / "driver_state.json",
            "driver-test-project",
        )
        assert state.status_of("01_scene-1.png") == "failed"
        assert state.status_of("02_scene-2.png") == "succeeded"
        assert res.success is False
        assert res.data["failed"] == 1
        assert res.data["succeeded"] == 1

    def test_full_run_fast_mode(self, queue_project, fake_session, monkeypatch):
        monkeypatch.setattr(driver_mod.time, "sleep", lambda s: None)
        res = run_driver(
            "driver-test-project",
            projects_root=queue_project.parent,
            upscale_mode="fast",
            min_delay_s=0.0,
            max_delay_s=0.0,
        )
        assert res.success, res.error
        drop = queue_project / "drop_images"
        assert (drop / "01_scene-1.png").is_file()
        state = DriverState(
            queue_project / "exports" / "google_flow" / "driver_state.json",
            "driver-test-project",
        )
        assert state.items["01_scene-1.png"]["capture"] == "local-2x-upscale"
        assert state.items["01_scene-1.png"]["media_id"]  # recorded for `capture`

    def test_only_filter_restricts_queue(self, queue_project, fake_session, monkeypatch):
        monkeypatch.setattr(driver_mod.time, "sleep", lambda s: None)
        res = run_driver(
            "driver-test-project",
            projects_root=queue_project.parent,
            only_scene_ids=["scene-2"],
            upscale_mode="flow",
            min_delay_s=0.0,
            max_delay_s=0.0,
        )
        assert res.success
        assert (queue_project / "drop_images" / "02_scene-2.png").is_file()
        assert not (queue_project / "drop_images" / "01_scene-1.png").exists()

    def test_missing_project(self, tmp_path):
        res = run_driver("no-such-project", projects_root=tmp_path)
        assert res.success is False
        assert "not found" in res.error


# -----------------------------------------------------------------------------
# BaseTool integration
# -----------------------------------------------------------------------------


class TestFastCapture:
    def test_extract_media_id(self):
        from tools.graphics.google_flow_driver import extract_media_id

        url = ("https://labs.google/fx/api/trpc/media.getMediaUrlRedirect"
               "?name=c036fc29-1f5b-4dd0-aa5d-ee87b2876759")
        assert extract_media_id(url) == "c036fc29-1f5b-4dd0-aa5d-ee87b2876759"
        assert extract_media_id("") is None
        assert extract_media_id("https://example.com/nothing") is None

    def test_local_upscale_2x_doubles_size(self):
        from tools.graphics.google_flow_driver import local_upscale_2x

        im = Image.new("RGB", (688, 384), (10, 20, 30))
        up = local_upscale_2x(im)
        assert up.size == (1376, 768)

    def test_capture_only_skips_items_without_media_id(self, queue_project):
        from tools.graphics.google_flow_driver import capture_only

        res = capture_only("driver-test-project",
                           projects_root=queue_project.parent)
        assert res.success
        assert res.data["skipped"] == 2  # no media ids recorded in state
        assert res.data["succeeded"] == 0


class TestGoogleFlowDriverTool:
    def test_registry_discovery(self):
        registry = ToolRegistry()
        registry.discover()
        tool = registry.get("google_flow_driver")
        assert tool is not None
        assert tool.capability == "google_flow_driver"

    def test_status_operation(self, tmp_path):
        project = tmp_path / "p"
        (project / "exports" / "google_flow").mkdir(parents=True)
        state = DriverState(
            project / "exports" / "google_flow" / "driver_state.json", "p"
        )
        state.mark("01.png", "succeeded")
        state.mark("02.png", "failed")
        tool = GoogleFlowDriver()
        res = tool.execute({
            "operation": "status", "project_id": "p", "projects_root": str(tmp_path)
        })
        assert res.success
        assert res.data["counts"] == {"succeeded": 1, "failed": 1}

    def test_reset_operation(self, tmp_path):
        project = tmp_path / "p"
        (project / "exports" / "google_flow").mkdir(parents=True)
        state = DriverState(
            project / "exports" / "google_flow" / "driver_state.json", "p"
        )
        state.mark("01.png", "succeeded")
        tool = GoogleFlowDriver()
        res = tool.execute({
            "operation": "reset", "project_id": "p", "projects_root": str(tmp_path)
        })
        assert res.success
        assert DriverState(
            project / "exports" / "google_flow" / "driver_state.json", "p"
        ).items == {}

    def test_run_requires_project_id(self):
        res = GoogleFlowDriver().execute({"operation": "run"})
        assert res.success is False
        assert "project_id" in res.error


# -----------------------------------------------------------------------------
# Login detection (regression: signed-out landing page shares the Flow URL)
# -----------------------------------------------------------------------------


_LANDING_SNAP = {  # what the smoke test saw while signed out at /fx/tools/flow
    "imgs": [], "busy": 0, "alerts": [], "createReady": True,
    "hasPromptBox": False, "hasAppShell": False,
}
_APP_SNAP = {
    "imgs": [], "busy": 0, "alerts": [], "createReady": True,
    "hasPromptBox": True, "hasAppShell": True,
}


class _FakePage:
    def __init__(self, snapshot_result, url="https://labs.google/fx/tools/flow",
                 second_eval_result=None):
        self._snap = snapshot_result
        self.url = url
        self._second = second_eval_result
        self.calls = 0

    def evaluate(self, js):
        self.calls += 1
        if self.calls == 1:
            return self._snap
        return self._second


def _bare_session(page) -> FlowSession:
    sess = FlowSession.__new__(FlowSession)
    sess.page = page
    sess._log = lambda msg: None
    return sess


class TestLoginDetection:
    def test_signed_out_landing_page_is_not_signed_in(self):
        # The landing "Create" tab must not be mistaken for the app composer.
        assert _bare_session(_FakePage(_LANDING_SNAP)).is_signed_in() is False

    def test_app_shell_is_signed_in(self):
        assert _bare_session(_FakePage(_APP_SNAP)).is_signed_in() is True

    def test_wait_for_login_returns_false_when_never_signed_in(self, monkeypatch):
        monkeypatch.setattr(driver_mod.time, "sleep", lambda s: None)
        sess = _bare_session(_FakePage(_LANDING_SNAP))
        assert sess.wait_for_login(timeout_s=0.2) is False

    def test_wait_for_login_detects_login(self, monkeypatch):
        monkeypatch.setattr(driver_mod.time, "sleep", lambda s: None)

        class SeqPage:
            calls = 0

            def evaluate(self, js):
                SeqPage.calls += 1
                return _APP_SNAP if SeqPage.calls >= 2 else _LANDING_SNAP

        assert _bare_session(SeqPage()).wait_for_login(timeout_s=5.0) is True


class _FlakyPage:
    """Page whose evaluate raises navigation errors before succeeding."""

    def __init__(self, script, url="https://labs.google/fx/tools/flow"):
        self.script = script  # callable(call_number) -> value or raises
        self.calls = 0
        self.url = url

    def evaluate(self, js):
        self.calls += 1
        return self.script(self.calls)

    def wait_for_load_state(self, *args, **kwargs):
        return None


class TestNavigationResilience:
    """Regressions: 'Execution context was destroyed' during login redirects."""

    def test_eval_retries_through_navigation_destroyed_context(self):
        def script(n):
            if n == 1:
                raise RuntimeError("Page.evaluate: Execution context was destroyed, "
                                   "most likely because of a navigation")
            return {"hasAppShell": True}

        assert _bare_session(_FlakyPage(script)).is_signed_in() is True

    def test_eval_reraises_unrelated_errors(self):
        def script(n):
            raise TypeError("Cannot read properties of null")

        with pytest.raises(TypeError):
            _bare_session(_FlakyPage(script)).is_signed_in()

    def test_wait_for_login_survives_redirect_churn(self, monkeypatch):
        monkeypatch.setattr(driver_mod.time, "sleep", lambda s: None)

        def script(n):
            if n % 2 == 1:  # every other check lands mid-navigation
                raise RuntimeError("Execution context was destroyed, most likely "
                                   "because of a navigation")
            return dict(_LANDING_SNAP)

        sess = _bare_session(_FlakyPage(script))
        assert sess.wait_for_login(timeout_s=0.2) is False  # never signed in, no crash

    def test_wait_for_login_detects_login_after_navigation(self, monkeypatch):
        monkeypatch.setattr(driver_mod.time, "sleep", lambda s: None)

        def script(n):
            if n <= 2:
                raise RuntimeError("Execution context was destroyed")
            return dict(_APP_SNAP)

        sess = _bare_session(_FlakyPage(script))
        assert sess.wait_for_login(timeout_s=5.0) is True


class TestLoginState:
    def test_accounts_url_is_signed_out(self):
        sess = _bare_session(_FakePage(_APP_SNAP, url="https://accounts.google.com/v3/signin/…"))
        assert sess.login_state() == "out"

    def test_app_shell_is_in(self):
        assert _bare_session(_FakePage(_APP_SNAP)).login_state() == "in"

    def test_landing_with_sign_in_button_is_out(self):
        # 1st eval = snapshot (no app shell), 2nd eval = Sign-in button check
        sess = _bare_session(_FakePage(_LANDING_SNAP, second_eval_result=True))
        assert sess.login_state() == "out"

    def test_signed_in_landing_without_composer_is_pending(self):
        landing_no_signin = dict(_LANDING_SNAP)
        sess = _bare_session(_FakePage(landing_no_signin, second_eval_result=False))
        assert sess.login_state() == "pending"

    def test_wait_for_login_opens_project_from_signed_in_landing(self, monkeypatch):
        """'pending' must trigger a new-project attempt, not wait out the clock."""
        monkeypatch.setattr(driver_mod.time, "sleep", lambda s: None)

        class LandingThenProjectPage:
            calls = 0
            url = "https://labs.google/fx/tools/flow"

            def evaluate(self, js):
                LandingThenProjectPage.calls += 1
                n = LandingThenProjectPage.calls
                if n == 1:   # snapshot: no app shell yet
                    return dict(_LANDING_SNAP)
                if n == 2:   # sign-in check: signed in
                    return False
                if n == 3:   # new-project button click attempt
                    return True
                return dict(_APP_SNAP)  # snapshot after opening the project

        sess = _bare_session(LandingThenProjectPage())
        assert sess.wait_for_login(timeout_s=5.0) is True


# -----------------------------------------------------------------------------
# In-page JS snippet sanity (compile as JS-ish where cheap)
# -----------------------------------------------------------------------------


class TestJsSnippets:
    def test_regex_literals_in_python_strings_are_valid(self):
        from tools.graphics.google_flow_driver import (
            _js_click_create,
            _js_media_snapshot,
            _js_pick_visible_option,
            _JS_COMPOSER_TEXT,
            _JS_INSTALL_BLOB_HOOK,
            _JS_OPTION_TEXTS,
            _JS_READ_CAPTURED_BLOB,
            _JS_RELEASE_BLOBS,
            _js_settings_context,
        )

        for js in (
            _js_media_snapshot(),
            _js_click_create(),
            _js_pick_visible_option("Nano Banana Pro"),
            _js_settings_context(),
            _JS_OPTION_TEXTS,
            _JS_COMPOSER_TEXT,
            _JS_INSTALL_BLOB_HOOK,
            _JS_READ_CAPTURED_BLOB.replace("(minSize)", "(100000)"),
            _JS_RELEASE_BLOBS,
        ):
            assert "undefined" not in js
            assert js.count("{") == js.count("}")

    def test_flow_session_helpers_exist(self):
        for method in (
            "start", "close", "open_flow", "wait_for_login", "login_state",
            "open_settings_panel", "close_settings_panel",
            "setup_generation_settings", "submit_and_wait", "_confirm_agent_dialog",
            "_find_img_locator", "_click_tile_more",
            "download_media_2k",
            "fetch_media_bytes", "new_project_if_needed",
        ):
            assert callable(getattr(FlowSession, method))
