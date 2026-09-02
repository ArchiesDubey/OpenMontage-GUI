"""Google Flow Driver — local browser automation that closes the Flow generation loop.

Where `google_flow_bridge` handles the edges of the workflow (prompt export before,
image ingestion after), this tool automates the middle that used to be manual:

    export prompts (bridge) -> [THIS DRIVER: paste prompt, generate, save 2K image
    straight into drop_images/ with the correct filename] -> ingest (bridge)

It drives the user's own Google Chrome via Playwright/CDP against flow.google using
a dedicated, persistent browser profile (login once, cookies reused). No third-party
extension is involved: all automation is this auditable file.

Key behaviors that the closed-source extensions get wrong:

1. 2K output — two capture modes. `--upscale fast` (default, bulk-safe):
   generation runs under CDP but touches no downloads; each finished media is
   captured with a single cookie-authed HTTP fetch of the native master plus a
   local 2x Lanczos upscale (measured ~7/255 mean-channel difference from
   Flow's own SR). `--upscale flow`: clicks Flow's download flyout for its
   true in-browser SR, capturing via an in-page Blob hook and a CDP watch
   folder with crash salvage — Chrome 152 crashes (EXC_BREAKPOINT) on Flow's
   blob downloads under DevTools automation, but the completed bytes survive
   on disk as `.crdownload` and are picked up either way. Every capture
   records which path was used and the actual pixel size.

2. Rate limits — every prompt is followed by a randomized jitter delay, batches
   get chunk cooldowns, and any limit/quota toast triggers exponential backoff
   with a cap instead of hammering the endpoint until it locks the account.

3. Security — no closed-source code, no extension permissions. The only network
   traffic is the user's own flow.google session from their own Chrome profile.

Runs are resumable: `driver_state.json` records per-prompt status and media
ids, so an interrupted or failed run continues where it left off — and
`capture` re-fetches already-generated images without spending new credits.

CLI:
    python -m tools.graphics.google_flow_driver run <project_id> [options]
    python -m tools.graphics.google_flow_driver dry_run <project_id>   # selector check only
    python -m tools.graphics.google_flow_driver status <project_id>
    python -m tools.graphics.google_flow_driver reset <project_id>
    python -m tools.graphics.google_flow_driver login                  # one-time profile login
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import random
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional

from PIL import Image

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_FLOW_URL = "https://labs.google/fx/tools/flow"
_DEFAULT_PROFILE_DIR = Path.home() / ".openmontage" / "flow-driver-profile"
_STATE_FILENAME = "driver_state.json"
# Scope for tile-menu items (Download and its 1K/2K/4K flyout render as a mix
# of role=menuitem elements and plain buttons across Flow releases).
MENU_SCOPE = '[role="menuitem"], [role="option"], button'


# =============================================================================
# PURE LOGIC (no browser) — rate limiting, state persistence, URL munging
# =============================================================================


class RateLimitError(RuntimeError):
    """Raised when Flow shows a limit/quota/credits message."""


class GenerationTimeout(RuntimeError):
    """Raised when a generation did not finish within the allotted window."""


class RateLimiter:
    """Jittered pacing between prompts plus exponential backoff on rate limits.

    Purely computational so it can be unit-tested without a browser.
    """

    def __init__(
        self,
        min_delay_s: float = 20.0,
        max_delay_s: float = 55.0,
        backoff_base_s: float = 300.0,
        backoff_cap_s: float = 2700.0,
        backoff_factor: float = 2.0,
        max_consecutive_backoffs: int = 6,
        chunk_every: int = 25,
        chunk_cooldown_s: float = 240.0,
        rng: Optional[random.Random] = None,
    ) -> None:
        if min_delay_s > max_delay_s:
            raise ValueError("min_delay_s must be <= max_delay_s")
        self.min_delay_s = min_delay_s
        self.max_delay_s = max_delay_s
        self.backoff_base_s = backoff_base_s
        self.backoff_cap_s = backoff_cap_s
        self.backoff_factor = backoff_factor
        self.max_consecutive_backoffs = max_consecutive_backoffs
        self.chunk_every = max(0, chunk_every)
        self.chunk_cooldown_s = chunk_cooldown_s
        self._rng = rng or random.Random()
        self.consecutive_backoffs = 0
        self.successes_since_start = 0

    def success_delay(self) -> float:
        """Jittered wait after a successful generation (organic pacing)."""
        self.consecutive_backoffs = 0
        self.successes_since_start += 1
        delay = self._rng.uniform(self.min_delay_s, self.max_delay_s)
        if (
            self.chunk_every
            and self.successes_since_start % self.chunk_every == 0
        ):
            delay += self._rng.uniform(0.5, 1.0) * self.chunk_cooldown_s
        return delay

    def backoff_delay(self) -> float:
        """Wait after hitting a rate limit; grows exponentially, aborts when stuck."""
        self.consecutive_backoffs += 1
        if self.consecutive_backoffs > self.max_consecutive_backoffs:
            raise RateLimitError(
                "Rate limit persisted after "
                f"{self.max_consecutive_backoffs} backoffs — stopping the run. "
                "Re-run later; completed prompts are preserved by the resume state."
            )
        raw = min(
            self.backoff_base_s * (self.backoff_factor ** (self.consecutive_backoffs - 1)),
            self.backoff_cap_s,
        )
        return raw * self._rng.uniform(0.5, 1.5)


_RATE_LIMIT_RE = re.compile(
    r"(limit|quota|credit|exceeded|too many|out of|daily cap|try again (later|tomorrow))",
    re.IGNORECASE,
)
_TRANSIENT_ERROR_RE = re.compile(
    r"(something went wrong|failed to generate|couldn't generate|could not generate)",
    re.IGNORECASE,
)


def classify_alert_text(text: str) -> Optional[str]:
    """Map a visible toast/alert text to 'rate_limit' | 'transient' | None."""
    if not text:
        return None
    if _RATE_LIMIT_RE.search(text):
        return "rate_limit"
    if _TRANSIENT_ERROR_RE.search(text):
        return "transient"
    return None


def upsize_media_url(url: str) -> Optional[str]:
    """Rewrite a googleusercontent URL's size suffix to request original bytes.

    Flow media URLs end with a size directive like `=s1632` or `=w4032-h2268`.
    Replacing it with `=s0` asks the server for the unmodified original, which is
    how the driver obtains the true 2K file rather than the preview-rendered copy.
    Returns None when the URL does not carry a recognizable size suffix.
    """
    m = re.search(r"=(?:[swh][0-9].*)$", url)
    if not m:
        return None
    return url[: m.start()] + "=s0"


class DriverState:
    """Resumable per-prompt state, persisted next to the exported queue."""

    def __init__(self, path: Path, project_id: str) -> None:
        self.path = path
        self.project_id = project_id
        self.items: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            # Corrupt state must not wedge the project — start fresh, keep a copy.
            try:
                self.path.rename(self.path.with_suffix(".corrupt"))
            except Exception:
                pass
            return
        if data.get("project_id") != self.project_id:
            return
        self.items = data.get("items", {})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "project_id": self.project_id,
            "saved_at": time.time(),
            "items": self.items,
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def status_of(self, target_filename: str) -> Optional[str]:
        return (self.items.get(target_filename) or {}).get("status")

    def mark(self, target_filename: str, status: str, **extra: Any) -> None:
        entry = self.items.setdefault(target_filename, {})
        entry.update({"status": status, "ts": time.time()})
        entry.update(extra)
        self.save()

    def reset(self) -> None:
        self.items = {}
        self.save()


# =============================================================================
# IN-PAGE JS HELPERS
# =============================================================================
# Flow is a React app (radix comboboxes, styled-components classes) whose class
# names churn between releases. Selectors therefore rely on stable landmarks:
# the prompt textarea id, role attributes, icon glyph names, and visible text —
# the same strategy the maintained open-source Flow extensions use.


_JS_HELPERS = """
() => {
  const isVisible = (el) => {
    if (!el || !el.isConnected) return false;
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 1 && rect.height > 1;
  };
  return { isVisible };
}
"""


def _js_media_snapshot() -> str:
    return """
() => {
  const isVisible = (el) => {
    if (!el || !el.isConnected) return false;
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 1 && rect.height > 1;
  };
  // Media candidates: Google's media CDNs, or any reasonably sized loaded
  // image (Flow shifts CDNs between releases — usercontent.goog today,
  // googleusercontent.com historically). The before/after diff per prompt is
  // what actually attributes a new image, so breadth here is safe.
  const isMedia = (i) => {
    const s = i.currentSrc || i.src || '';
    if (!s.startsWith('http')) return false;
    if (/googleusercontent\\.com|usercontent\\.goog|googleapis\\.com|ggpht\\.com/.test(s)) return true;
    return i.naturalWidth >= 200;
  };
  const imgs = Array.from(document.querySelectorAll('img'))
    .filter(isMedia)
    .map(i => i.currentSrc || i.src);
  const busy = Array.from(document.querySelectorAll(
      '[role="progressbar"], [aria-busy="true"], .animate-spin'))
    .filter(isVisible).length;
  const alertEls = Array.from(document.querySelectorAll(
      '[role="alert"], [class*="toast" i], [class*="snackbar" i], [class*="banner" i]'))
    .filter(isVisible);
  const alerts = Array.from(new Set(alertEls.map(e => (e.textContent || '')
      .trim().replace(/\\s+/g, ' ').slice(0, 300)))).filter(t => t.length > 3);
  const createReady = Array.from(document.querySelectorAll('button')).some(b => {
    if (!isVisible(b) || b.disabled) return false;
    const t = (b.textContent || '').toLowerCase();
    return (b.innerHTML.includes('arrow_forward') && t.includes('create')) ||
           t.trim() === 'create' || t.trim() === 'generate';
  });
  // Legacy UI: textarea#PINHOLE_TEXT_AREA_ELEMENT_ID. Current UI: the agent
  // composer is a contenteditable div ("What do you want to create?").
  const hasPromptBox = !!document.querySelector('#PINHOLE_TEXT_AREA_ELEMENT_ID') ||
    !!Array.from(document.querySelectorAll('textarea')).find(isVisible) ||
    !!Array.from(document.querySelectorAll('[contenteditable="true"]')).find(isVisible);
  // The signed-out landing page shares the /fx/tools/flow URL but has no composer:
  // detect the app shell via the mode combobox ("Text to Video" / "Create Image")
  // or the model picker ("Nano Banana" / "Veo"), never the marketing buttons.
  const hasAppShell = hasPromptBox ||
    !!Array.from(document.querySelectorAll('[role="combobox"]')).filter(isVisible)
      .find(b => /video|image/i.test(b.textContent || '')) ||
    !!Array.from(document.querySelectorAll('button')).filter(isVisible)
      .find(b => /nano banana|imagen|veo \\d/i.test(b.textContent || ''));
  const dialogTexts = Array.from(document.querySelectorAll('[role="dialog"]'))
    .filter(isVisible)
    .map(d => (d.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 400));
  return { imgs, busy, alerts, createReady, hasPromptBox, hasAppShell, dialogTexts };
}
"""


def _js_click_create() -> str:
    return """
() => {
  const isVisible = (el) => {
    if (!el || !el.isConnected) return false;
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 1 && rect.height > 1;
  };
  const avoid = ['expand', 'edit', 'settings', 'more', 'menu', 'copy',
                 'download', 'new project', 'tune'];
  const buttons = Array.from(document.querySelectorAll('button:not([disabled])'))
    .filter(isVisible)
    .filter(b => !avoid.some(a => (b.textContent || '').toLowerCase().includes(a)));
  for (const b of buttons) {
    const t = (b.textContent || '').toLowerCase();
    if (b.innerHTML.includes('arrow_forward') && t.includes('create')) {
      b.click(); return true;
    }
  }
  for (const b of buttons) {
    const t = (b.textContent || '').toLowerCase().trim();
    if (t === 'create' || t === 'generate') { b.click(); return true; }
  }
  for (const b of buttons) {
    if (b.innerHTML.includes('arrow_forward')) { b.click(); return true; }
  }
  return false;
}
"""


def _js_pick_visible_option(option_text_re: str) -> str:
    """Pick the currently-open dropdown option whose text matches `option_text_re`."""
    return f"""
() => {{
  const isVisible = (el) => {{
    if (!el || !el.isConnected) return false;
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 1 && rect.height > 1;
  }};
  const re = new RegExp({option_text_re!r}, 'i');
  const opts = Array.from(document.querySelectorAll('[role="option"], [role="menuitemradio"], [role="menuitem"]'))
    .filter(isVisible);
  const match = opts.find(o => re.test((o.textContent || '').trim()));
  if (!match) return {{ ok: false, options: opts.map(o => (o.textContent || '').trim().slice(0, 60)) }};
  match.click();
  return {{ ok: true, picked: (match.textContent || '').trim().slice(0, 60) }};
}}
"""


_JS_HAS_SIGN_IN = """
() => {
  const isVisible = (el) => {
    if (!el || !el.isConnected) return false;
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 1 && rect.height > 1;
  };
  return Array.from(document.querySelectorAll('a, button'))
    .filter(isVisible)
    .some(el => /^sign in$|sign in with google/i.test((el.textContent || '').trim()));
}
"""

_JS_OPTION_TEXTS = """
() => Array.from(document.querySelectorAll(
      '[role="option"], [role="radio"], [role="menuitemradio"], [role="menuitem"]'))
  .filter(el => el.getBoundingClientRect().width > 1)
  .map(el => (el.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 80))
  .filter(t => t.length > 0)
"""


_JS_COMPOSER_TEXT = """
() => {
  const ed = Array.from(document.querySelectorAll('[contenteditable="true"]'))
    .find(el => el.getBoundingClientRect().width > 1);
  return ed ? (ed.textContent || '').trim() : null;
}
"""

_JS_INSTALL_BLOB_HOOK = """
() => {
  if (window.__om_blob_hook) return true;
  window.__om_blob_hook = true;
  window.__om_blobs = [];
  const origCreate = URL.createObjectURL.bind(URL);
  URL.createObjectURL = function(obj) {
    const url = origCreate(obj);
    try {
      const size = (obj && typeof obj.size === 'number') ? obj.size : -1;
      window.__om_blobs.push({ url: url, size: size, obj: obj });
    } catch (e) {}
    return url;
  };
  // Flow downloads the generated file via an <a download href="blob:...">
  // click. Chrome 152's download manager crashes (EXC_BREAKPOINT in the
  // browser process) handling that blob download while DevTools automation
  // is attached — so the click is swallowed and the Blob is read directly.
  const origClick = HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click = function(...args) {
    try {
      const href = this.getAttribute('href') || '';
      if (this.hasAttribute('download') && href.startsWith('blob:')) {
        return;
      }
    } catch (e) {}
    return origClick.apply(this, args);
  };
  document.addEventListener('click', (ev) => {
    const a = ev.target && ev.target.closest && ev.target.closest('a[download]');
    if (a) {
      const href = a.getAttribute('href') || '';
      if (href.startsWith('blob:')) {
        ev.preventDefault();
        ev.stopPropagation();
      }
    }
  }, true);
  return true;
}
"""

_JS_READ_CAPTURED_BLOB = """
async (minSize) => {
  const arr = window.__om_blobs || [];
  for (let i = arr.length - 1; i >= 0; i--) {
    const entry = arr[i];
    if (entry.consumed || (entry.size !== -1 && entry.size < minSize)) continue;
    try {
      const buf = await entry.obj.arrayBuffer();
      const bytes = new Uint8Array(buf);
      let binary = '';
      const chunk = 0x8000;
      for (let j = 0; j < bytes.length; j += chunk) {
        binary += String.fromCharCode.apply(null, bytes.subarray(j, j + chunk));
      }
      entry.consumed = true;
      return { ok: true, b64: btoa(binary), size: bytes.length };
    } catch (e) {
      entry.error = String(e);
    }
  }
  return { ok: false, captured: arr.length };
}
"""

_JS_RELEASE_BLOBS = """
() => {
  const arr = window.__om_blobs || [];
  arr.forEach(e => { try { if (e.url) URL.revokeObjectURL(e.url); } catch (err) {} });
  window.__om_blobs = [];
  return arr.length;
}
"""


def _js_settings_context() -> str:
    """Report visible button texts + option-panel labels for diagnostics."""
    return """
() => {
  const isVisible = (el) => {
    if (!el || !el.isConnected) return false;
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 1 && rect.height > 1;
  };
  const buttons = Array.from(document.querySelectorAll('button, [role="combobox"]'))
    .filter(isVisible)
    .map(b => (b.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 80))
    .filter(t => t.length > 0);
  return Array.from(new Set(buttons)).slice(0, 40);
}
"""


def _js_fetch_media_b64(url: str) -> str:
    return f"""
async () => {{
  const res = await fetch({url!r}, {{ credentials: 'include' }});
  if (!res.ok) return {{ ok: false, status: res.status }};
  const buf = await res.arrayBuffer();
  let binary = '';
  const bytes = new Uint8Array(buf);
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {{
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
  }}
  return {{ ok: true, b64: btoa(binary) }};
}}
"""


# =============================================================================
# BROWSER SESSION
# =============================================================================


class FlowSession:
    """Owns the Playwright browser context and drives the Flow UI."""

    def __init__(
        self,
        profile_dir: Path,
        headless: bool = False,
        cdp_url: Optional[str] = None,
        logger: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.profile_dir = profile_dir
        self.headless = headless
        self.cdp_url = cdp_url
        self._log = logger or (lambda msg: None)
        self._pw = None
        self._context = None
        self.page = None
        self._owns_browser = True
        # Passive network observation (CDP): every image response the page
        # receives, newest last. Detecting a finished generation via the network
        # is far more robust than DOM-diffing <img> elements, and — unlike
        # crafting API requests — it is indistinguishable from the user's own
        # browsing, so there is nothing for anti-automation to flag.
        self.network_media: list[dict[str, Any]] = []
        self._download_dir: Optional[Path] = None
        self._cdp = None

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        if self.cdp_url:
            self._log(f"Attaching to existing Chrome via CDP: {self.cdp_url}")
            browser = self._pw.chromium.connect_over_cdp(self.cdp_url)
            self._context = browser.contexts[0] if browser.contexts else browser.new_context()
            self._owns_browser = False
        else:
            self.profile_dir.mkdir(parents=True, exist_ok=True)
            args = [
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
                "--no-first-run",
            ]
            launch_kwargs: dict[str, Any] = {
                "user_data_dir": str(self.profile_dir),
                "headless": self.headless,
                "args": args,
                "accept_downloads": True,
                "no_viewport": True,
            }
            try:
                self._context = self._pw.chromium.launch_persistent_context(
                    channel="chrome", **launch_kwargs
                )
                self._log("Launched Google Chrome with dedicated Flow profile.")
            except Exception:
                self._log("Google Chrome channel unavailable — falling back to bundled Chromium.")
                self._context = self._pw.chromium.launch_persistent_context(**launch_kwargs)
        if not self._context.pages:
            self.page = self._context.new_page()
        else:
            self.page = self._context.pages[0]
        self.page.set_default_timeout(30_000)
        self.page.on("response", self._on_response)
        self.page.on("close", lambda _p: self._log("EVENT: page closed"))
        try:
            self._context.on("close", lambda _c: self._log("EVENT: context closed"))
        except Exception:
            pass
        # Route downloads natively via CDP. Playwright's own download
        # interception of Flow's blob: downloads crashes Chrome 152's browser
        # process (EXC_BREAKPOINT in CrBrowserMain); a plain native download
        # into a watch folder avoids that code path entirely.
        self._download_dir = self.profile_dir.parent / "flow-downloads"
        self._download_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._cdp = self._context.new_cdp_session(self.page)
            self._cdp.send("Browser.setDownloadBehavior", {
                "behavior": "allowAndName",
                "downloadPath": str(self._download_dir),
                "eventsEnabled": False,
            })
            self._log(f"Native download capture → {self._download_dir}")
        except Exception as exc:
            self._cdp = None
            self._log(f"[!] CDP download-behavior setup failed: {exc}")

    def _on_response(self, response: Any) -> None:
        """Record image responses passively — the generation-done signal."""
        try:
            url = response.url
            content_type = (response.headers or {}).get("content-type", "")
        except Exception:
            return
        if "image/" not in content_type:
            return
        if not re.search(r"usercontent\.goog|googleusercontent\.com|googleapis\.com|ggpht\.com", url):
            return
        if self.network_media and self.network_media[-1]["url"] == url:
            return
        self.network_media.append({"url": url, "ts": time.time()})

    def close(self, keep_open: bool = False) -> None:
        if keep_open:
            self._log("Browser left open (profile keeps the login).")
            return
        try:
            if self._context is not None:
                self._context.close()
        finally:
            if self._pw is not None:
                self._pw.stop()

    # -- page helpers -------------------------------------------------------

    def _eval(self, js: str) -> Any:
        """Evaluate JS, retrying through navigation-destroyed execution contexts.

        Flow bounces between landing/login/app URLs, so any evaluate can land
        mid-redirect; that is transient, not fatal.
        """
        last_exc: Optional[Exception] = None
        for _ in range(3):
            try:
                return self.page.evaluate(js)
            except Exception as exc:
                msg = str(exc)
                if "Execution context was destroyed" not in msg and "navigation" not in msg.lower():
                    raise
                last_exc = exc
                try:
                    self.page.wait_for_load_state("domcontentloaded", timeout=15_000)
                except Exception:
                    pass
                time.sleep(1.0)
        raise last_exc  # type: ignore[misc]

    def open_flow(self) -> None:
        self._log(f"Opening {_FLOW_URL}")
        self.page.goto(_FLOW_URL, wait_until="domcontentloaded")
        try:
            self.page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass  # in-flight redirects (login bounce, consent screens) are expected

    def is_signed_in(self) -> bool:
        """True only when the Flow app composer is present.

        The signed-out landing page sits at the same URL, so neither the URL nor
        marketing buttons are usable signals — the mode combobox / prompt box are.
        """
        snap = self._eval(_js_media_snapshot()) or {}
        return bool(snap.get("hasAppShell"))

    def login_state(self) -> str:
        """Classify the current page: 'in', 'out', or 'pending'.

        'in'      — Flow composer is present; ready to generate.
        'out'     — sign-in wall (accounts.google.com or a visible Sign in button).
        'pending' — signed-in surface without a composer yet (e.g. project grid),
                    or a transient state; callers should try opening a project.
        """
        try:
            url = self.page.url or ""
        except Exception:
            return "pending"
        if "accounts.google" in url:
            return "out"
        try:
            snap = self._eval(_js_media_snapshot()) or {}
        except Exception:
            return "pending"
        if snap.get("hasAppShell"):
            return "in"
        try:
            has_sign_in = bool(self._eval(_JS_HAS_SIGN_IN))
        except Exception:
            has_sign_in = False
        if has_sign_in and not snap.get("hasPromptBox"):
            return "out"
        return "pending"

    def wait_for_login(self, timeout_s: float = 600.0) -> bool:
        """Wait until the session can generate: signed in AND a composer open.

        After sign-in Google often lands on a signed-in landing page rather than
        an open composer, so 'pending' states trigger a new-project attempt
        inside the loop instead of waiting out the clock.
        """
        announced = False
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                state = self.login_state()
            except Exception:
                state = "pending"  # mid-navigation; inconclusive
            if state == "in":
                return True
            if state == "pending":
                try:
                    if self.new_project_if_needed():
                        return True
                except Exception:
                    pass
            if not announced:
                self._log(
                    "Sign-in required: please log into your Google account in the "
                    "opened Chrome window (the profile remembers it). If you are "
                    "already signed in, open or create a Flow project — the driver "
                    "takes over automatically."
                )
                announced = True
            time.sleep(5.0)
        return False

    # -- generic interaction helpers ----------------------------------------

    def _real_click(self, pattern: str, scope: str = "button",
                    timeout_ms: int = 4000) -> bool:
        """Real (pointer-event) click on the first visible element matching pattern.

        Real clicks are required for radix menus/popovers, which ignore synthetic
        JS .click() on their triggers.
        """
        loc = self.page.locator(scope).filter(has_text=re.compile(pattern, re.I))
        for i in range(loc.count()):
            el = loc.nth(i)
            try:
                if el.is_visible():
                    el.click(timeout=timeout_ms)
                    return True
            except Exception:
                continue
        return False

    def _pick_option(self, pattern: str) -> bool:
        """Real click on the first visible dropdown/radio/option matching pattern.

        Flow renders some pickers as radix options and others (aspect ratio,
        output count) as plain buttons, so both are in scope. The Nano Banana
        card renders before the others, so first-match lands inside it.
        """
        scope = ('[role="option"], [role="radio"], [role="menuitemradio"], '
                 '[role="menuitem"], button')
        return self._real_click(pattern, scope=scope)

    def _real_hover(self, pattern: str, scope: str = "button") -> bool:
        """Real pointer hover on the first visible element matching pattern.

        Hover keeps hover-mounted UI alive — e.g. the Download item's 1K/2K/4K
        flyout submenu, which unmounts the moment the pointer leaves.
        """
        loc = self.page.locator(scope).filter(has_text=re.compile(pattern, re.I))
        for i in range(loc.count()):
            el = loc.nth(i)
            try:
                if el.is_visible():
                    el.hover(timeout=2000)
                    return True
            except Exception:
                continue
        return False

    # -- session-level UI setup ---------------------------------------------

    def open_settings_panel(self) -> bool:
        """Open the composer settings panel (tuneSettings button)."""
        if not self._real_click(r"tune"):
            return False
        time.sleep(1.2)
        return True

    def close_settings_panel(self) -> bool:
        """Close the settings panel and wait for the composer to remount.

        While the panel is open the agent composer is unmounted entirely. The
        panel's Back ('arrow_backBack') must be matched exactly — the app-level
        'Go Back' nav ('arrow_backGo Back') shares the glyph text and would
        navigate away from the project instead.
        """
        try:
            self._real_click(r"^arrow_backBack$|^closeClose$", timeout_ms=2000)
        except Exception:
            pass
        if self._wait_for_composer(12.0):
            return True
        try:
            self.page.keyboard.press("Escape")
        except Exception:
            pass
        return self._wait_for_composer(6.0)

    def _wait_for_composer(self, timeout_s: float) -> bool:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                if self.snapshot().get("hasPromptBox"):
                    time.sleep(0.5)
                    return True
            except Exception:
                pass
            time.sleep(1.0)
        return False

    def setup_generation_settings(
        self,
        model_hint: str = "Nano Banana",
        aspect_ratio: str = "16:9",
        outputs: int = 1,
    ) -> dict[str, Any]:
        """Best-effort project settings: model, aspect ratio, outputs per generation.

        The settings panel groups options per model card (the Nano Banana card
        renders before the others, so first-match lands inside it). Aspect-ratio
        and output-count here are conveniences only — Flow applies the 2K upscale
        at DOWNLOAD time, so resolution is handled by `download_media_2k`.
        Every step is reported; none is fatal — the run proceeds with whatever
        the panel currently has, and the report makes deviations visible.
        """
        report: dict[str, Any] = {
            "panel_opened": False, "aspect": None, "outputs": None,
            "model_options_seen": [], "saved": False, "composer_ready": False,
        }
        try:
            report["panel_opened"] = self.open_settings_panel()
            if not report["panel_opened"]:
                report["error"] = "settings button not found"
                return report

            if self._pick_option(re.escape(aspect_ratio)):
                report["aspect"] = aspect_ratio
                time.sleep(0.3)
            if self._pick_option(rf"^x{max(1, int(outputs))}$"):
                report["outputs"] = outputs
                time.sleep(0.3)

            # Confirm the image model dropdown exists; log the options seen.
            if self._real_click(r"nano banana|imagen"):
                time.sleep(1.0)
                report["model_options_seen"] = self._eval(_JS_OPTION_TEXTS) or []
                self.page.keyboard.press("Escape")
                time.sleep(0.5)

            if self._real_click(r"^save$|save settings"):
                report["saved"] = True
                time.sleep(1.0)
        except Exception as exc:
            report["error"] = str(exc)
        finally:
            report["composer_ready"] = self.close_settings_panel()
        return report

    def settings_diagnostics(self) -> list[str]:
        """Visible button/setting texts — used by dry_run and failure reports."""
        try:
            return self._eval(_js_settings_context()) or []
        except Exception:
            return []

    # -- per-prompt loop ----------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        return self._eval(_js_media_snapshot()) or {}

    def fill_prompt(self, prompt: str) -> None:
        """Type into the composer: legacy textarea or the agent contenteditable.

        Every fallback must be visibility-checked — the page embeds hidden
        fields (e.g. g-recaptcha-response textarea) that otherwise hijack the
        first-match lookup.
        """
        deadline = time.time() + 10.0
        box = None
        while time.time() < deadline and box is None:
            pin = self.page.locator("#PINHOLE_TEXT_AREA_ELEMENT_ID")
            if pin.count() and pin.first.is_visible():
                box = pin.first
                break
            for editable in self.page.locator('[contenteditable="true"]').all():
                try:
                    if not editable.is_visible():
                        continue
                    bb = editable.bounding_box()
                except Exception:
                    continue
                # real inputs only — excludes zero-size/ghost editables; the
                # hidden g-recaptcha trap is a textarea, handled below
                if bb and bb["width"] >= 40 and bb["height"] >= 10:
                    box = editable
                    break
            if box is not None:
                break
            for ta in self.page.locator("textarea").all():
                try:
                    if ta.is_visible() and not ta.is_disabled():
                        box = ta
                        break
                except Exception:
                    continue
            if box is not None:
                break
            time.sleep(1.0)
        if box is None:
            raise GenerationTimeout(
                "Prompt composer not found (no visible contenteditable/textarea). "
                "The composer may still be remounting after the settings panel."
            )
        box.click()
        self.page.keyboard.press("ControlOrMeta+a")  # replace any prior text
        self.page.keyboard.insert_text(prompt)

    def submit(self, verify_s: float = 10.0) -> bool:
        """Submit the prompt and verify the send actually started.

        The Create arrow is React-controlled: a synthetic JS .click() hits it
        but never fires the send (the prompt just sits there), so a real
        pointer click is required. Submission signs: the composer text clears,
        a busy state appears, the Create button goes away, or the agent's
        confirmation dialog opens. Enter (composer still focused) is the
        fallback — tried only when the click shows no signs, never after.
        """
        try:
            before_text = self._eval(_JS_COMPOSER_TEXT)
        except Exception:
            before_text = None
        for action in ("click", "enter"):
            if action == "click":
                clicked = self._real_click(r"arrow_forwardCreate")
                if not clicked:
                    continue
            else:
                try:
                    self.page.keyboard.press("Enter")
                except Exception:
                    continue
            deadline = time.time() + verify_s
            while time.time() < deadline:
                time.sleep(1.0)
                try:
                    snap = self.snapshot()
                    text_now = self._eval(_JS_COMPOSER_TEXT)
                except Exception:
                    continue
                if (text_now != before_text
                        or snap.get("busy")
                        or not snap.get("createReady")
                        or snap.get("dialogTexts")):
                    return True
        return False

    def submit_and_wait(
        self,
        prompt: str,
        before_imgs: set[str],
        timeout_s: float = 240.0,
        poll_s: float = 1.5,
        auto_confirm: bool = True,
    ) -> dict[str, Any]:
        """Fill the prompt, click Create, and wait for a new media item.

        Returns {'url': str} on success or raises RateLimitError /
        GenerationTimeout. A new image counts as done when it persists across
        two polls (stable render) and the Create button is ready again.

        When the agent's spend-confirmation dialog is configured to 'Always ask
        before generating', auto_confirm clicks its confirm button — the run
        itself (N approved prompts) is the user's spend authorization.
        """
        try:
            self.fill_prompt(prompt)
        except GenerationTimeout:
            raise
        except Exception as exc:
            raise GenerationTimeout(f"Could not fill the prompt composer: {exc}")
        if not self.submit():
            raise GenerationTimeout(
                "Could not submit the prompt (Create arrow unresponsive and "
                "Enter fallback showed no submission signs)."
            )
        time.sleep(2.0)

        net_mark = len(self.network_media)
        deadline = time.time() + timeout_s
        stable_seen = 0
        last_alerts: list[str] = []
        while time.time() < deadline:
            try:
                snap = self.snapshot()
            except Exception:
                time.sleep(poll_s)
                continue  # transient navigation; keep polling until the deadline
            alerts = snap.get("alerts", [])
            last_alerts = alerts
            for text in alerts:
                kind = classify_alert_text(text)
                if kind == "rate_limit":
                    raise RateLimitError(text)
            new_urls = [u for u in snap.get("imgs", []) if u not in before_imgs]
            if not new_urls:
                outcome = self._confirm_agent_dialog(
                    snap.get("dialogTexts", []), auto_confirm
                )
                if outcome == "blocked":
                    raise GenerationTimeout(
                        "Agent asked for confirmation before generating media and "
                        "auto-confirm is disabled. Re-run with auto-confirm enabled, "
                        "or set Flow's agent autonomy to 'Never'."
                    )
                if outcome == "confirmed":
                    time.sleep(1.5)
            # Primary signal: an image response captured from the network log.
            found: Optional[str] = None
            new_net = [m["url"] for m in self.network_media[net_mark:]
                       if m["url"] not in before_imgs]
            if new_net:
                found = new_net[0]
            elif new_urls and (snap.get("createReady") or not snap.get("busy")):
                found = new_urls[0]  # fallback: DOM diff
            if found:
                stable_seen += 1
                if stable_seen >= 2:
                    return {"url": found, "alerts": last_alerts}
            else:
                stable_seen = 0
            time.sleep(poll_s)
        raise GenerationTimeout(
            f"Generation did not complete in {timeout_s:.0f}s. Last alerts: {last_alerts!r}"
        )

    def _confirm_agent_dialog(
        self, dialog_texts: list[str], auto_confirm: bool
    ) -> Optional[str]:
        """Handle the agent's 'generate media?' confirmation dialog if present."""
        for text in dialog_texts:
            if re.search(r"generat|spend|credit|confirm", text, re.I):
                if not auto_confirm:
                    return "blocked"
                if self._real_click(r"generate|create|confirm|continue|yes",
                                    scope='[role="dialog"] button'):
                    return "confirmed"
                return "blocked"
        return None

    def fetch_media_bytes(self, url: str) -> tuple[bytes, str]:
        """Download media bytes; request-context first, then in-page fetch.

        Flow media URLs are same-origin tRPC redirect endpoints; a plain in-page
        fetch is CORS-blocked, but the browser context's own request client
        shares cookies, follows redirects, and has no CORS restriction. The
        redirected file is the media's native (pre-upscale) size.
        """
        try:
            resp = self._context.request.get(url, timeout=60_000)
            if resp.ok:
                body = resp.body()
                if body:
                    return body, url
        except Exception:
            pass
        candidates: list[str] = []
        up = upsize_media_url(url)
        if up:
            candidates.append(up)
        candidates.append(url)
        errors: list[str] = []
        for candidate in candidates:
            try:
                result = self._eval(_js_fetch_media_b64(candidate)) or {}
            except Exception as exc:
                errors.append(f"{candidate[:80]}…: {exc}")
                continue
            if result.get("ok"):
                return base64.b64decode(result["b64"]), candidate
            errors.append(f"{candidate[:80]}…: HTTP {result.get('status')}")
        raise RuntimeError("In-page fetch failed for all URL variants: " + "; ".join(errors))

    def _find_img_locator(self, url_base: str):
        """Locate the generated media <img> element by its URL file base.

        googleusercontent/usercontent URLs differ only in the trailing size
        directive, so everything after the last '=' is stripped for matching.
        """
        imgs = self.page.locator("img")
        for i in range(imgs.count()):
            el = imgs.nth(i)
            try:
                src = el.evaluate("e => e.currentSrc || e.src") or ""
            except Exception:
                continue
            if src.split("=")[0] == url_base:
                return el
        return None

    def _click_tile_more(self, img_loc) -> bool:
        """Hover the media tile to reveal its toolbar, then click its 3-dot button.

        The download affordance only exists behind the tile's hover-revealed
        more_vert button (top-right of the tile), so hover first, then pick the
        visible more_vert button geometrically closest to the image — the app
        bar's own more_vert is far away and loses that comparison.
        """
        try:
            img_loc.scroll_into_view_if_needed(timeout=5000)
            img_loc.hover(timeout=5000)
        except Exception:
            pass
        time.sleep(0.8)
        try:
            bb = img_loc.bounding_box()
        except Exception:
            return False
        if not bb:
            return False
        cx = bb["x"] + bb["width"] / 2
        cy = bb["y"] + bb["height"] / 2
        best = None
        best_dist = None
        for btn in self.page.locator("button").all():
            try:
                text = (btn.text_content() or "").strip()
                if "more_vert" not in text:
                    continue
                if not btn.is_visible():
                    continue
                b2 = btn.bounding_box()
                if not b2:
                    continue
                dist = ((b2["x"] + b2["width"] / 2 - cx) ** 2
                        + (b2["y"] + b2["height"] / 2 - cy) ** 2) ** 0.5
            except Exception:
                continue
            if best_dist is None or dist < best_dist:
                best, best_dist = btn, dist
        if best is None or best_dist > 400:
            return False
        try:
            best.hover(timeout=2000)  # keep the hover-toolbar alive
            best.click(timeout=4000)
        except Exception:
            return False
        return True

    def _wait_for_native_download(
        self, dest: Path, before_files: set[str], min_width: int,
        timeout_s: float = 180.0,
    ) -> dict[str, Any]:
        """Pick up the finished download from the watch folder.

        Chrome streams into `<name>.crdownload` and renames when done — but a
        Chrome crash leaves COMPLETE downloads stuck as `.crdownload` forever
        (bytes fully on disk, rename never fires). So in-flight files are
        skipped, yet `.crdownload` files whose size is stable across two polls
        are accepted as complete; the bytes verify themselves through PIL.
        """
        stable: dict[str, int] = {}
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            time.sleep(2.0)
            candidates = [
                p for p in self._download_dir.iterdir()
                if p.is_file() and p.name not in before_files
            ]
            if not candidates:
                continue
            newest = max(candidates, key=lambda p: p.stat().st_mtime)
            size = newest.stat().st_size
            if size == 0:
                continue
            if stable.get(newest.name) == size and size >= 100_000:
                res_str = _save_image_bytes(newest.read_bytes(), dest)
                newest.unlink(missing_ok=True)
                width = int(res_str.split("x")[0])
                result: dict[str, Any] = {"path": "download-native", "resolution": res_str}
                if width < min_width:
                    result["note"] = (f"downloaded file is {width}px wide, below the "
                                      f"{min_width}px target")
                return result
            stable[newest.name] = size
        raise RuntimeError(
            f"no native download appeared in {self._download_dir} "
            f"within {timeout_s:.0f}s"
        )

    def capture_master_fast(self, media_url: str, dest: Path,
                            resolution: str = "2K",
                            min_width: int = 1900) -> dict[str, Any]:
        """Bulk capture via the LIVE session's request context.

        Nesting a second sync Playwright inside the running loop is forbidden,
        so the fast path must reuse this session's context. Fetches the native
        master (plain HTTP GET — no download manager) and upscales locally.
        """
        resp = self._context.request.get(media_url, timeout=60_000)
        if not resp.ok:
            raise RuntimeError(f"master fetch HTTP {resp.status}")
        raw = resp.body()
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        path_label = "native-master"
        if resolution and resolution.upper().startswith("2") and im.width < min_width:
            im = local_upscale_2x(im)
            path_label = "local-2x-upscale"
        res_str = f"{im.width}x{im.height}"
        im.save(dest, format="PNG")
        result: dict[str, Any] = {"path": path_label, "resolution": res_str}
        if im.width < min_width:
            result["note"] = f"master is {res_str}, below the {min_width}px target"
        return result

    def _install_blob_hook(self) -> bool:
        """Install the createObjectURL/anchor-click hook. MUST run before the
        2K click — the Blob is created the moment the upscale finishes, and a
        hook installed afterwards misses it entirely."""
        try:
            return bool(self._eval(_JS_INSTALL_BLOB_HOOK))
        except Exception:
            return False

    def _collect_generated_blob(self, min_size: int = 100_000,
                                timeout_s: float = 180.0) -> Optional[bytes]:
        """Poll the in-page blob hook for Flow's generated download blob.

        Flow builds the (client-side upscaled) file as an in-memory Blob and
        hands it to an anchor download; Chrome's download manager crashes on
        exactly that under automation, so the hook captures the Blob directly
        and swallows the anchor click. Returns the file bytes, or None when no
        qualifying blob appeared within the window.
        """
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            time.sleep(2.0)
            try:
                result = self._eval(
                    _JS_READ_CAPTURED_BLOB.replace("(minSize)", f"({int(min_size)})")
                ) or {}
            except Exception:
                continue  # transient navigation
            if result.get("ok"):
                return base64.b64decode(result["b64"])
        return None

    def _release_blobs(self) -> None:
        try:
            self._eval(_JS_RELEASE_BLOBS)
        except Exception:
            pass

    def download_media_2k(
        self,
        img_url: str,
        dest: Path,
        resolution: str = "2K",
        min_width: int = 1900,
        debug: bool = False,
    ) -> dict[str, Any]:
        """Capture the generated media at the requested resolution.

        Flow's download path (verified live): hover the tile → its 3-dot menu
        → Download → a picker of plain buttons appears ('1KOriginal size',
        '2KUpscaled', '4KUpscaledUpgrade') → clicking the resolution starts
        the browser download directly (no confirm step). The upscale is
        produced server-side at that moment, which is why this cannot be
        replaced by scraping a URL. Fallbacks: cookie-authed request-context
        fetch of the media URL (native size, no CORS limits), then in-page
        fetch. The returned dict records which path was used and the actual
        pixel size so shortfalls are visible.
        """
        failure: Optional[str] = None
        try:
            img_url_base = img_url.split("=")[0]
            # The tile toolbar is hover-revealed, so the 3-dot → menu dance can
            # flake; retry with a fresh hover until the Download item appears.
            opened = False
            for attempt in range(3):
                img_loc = self._find_img_locator(img_url_base)
                if img_loc is None:
                    raise RuntimeError("generated media img not found on page")
                if self._click_tile_more(img_loc):
                    time.sleep(1.0)
                    if self._real_click(r"download|save to device", scope=MENU_SCOPE):
                        opened = True
                        break
                time.sleep(1.5)  # toolbar re-hides; try again from a fresh hover
            if not opened:
                raise RuntimeError(
                    "could not open the tile 3-dot menu / find its Download item"
                    + (f" after {3} attempts" if attempt else "")
                )
            time.sleep(1.5)

            # The 1K/2K/4K choices are a flyout submenu anchored to the Download
            # item — hovering Download keeps it mounted ("move right slightly").
            # Option text is '2KUpscaled' etc., so the match anchors at start
            # but cannot require a trailing word boundary.
            pick_re = rf"^{re.escape(resolution)}"
            before_files = {
                p.name for p in self._download_dir.iterdir() if p.is_file()
            }
            # The hook MUST be live before the 2K click: Flow upscales
            # client-side and creates the Blob the instant the click lands.
            self._install_blob_hook()
            self._real_hover(r"download|save to device", scope=MENU_SCOPE)
            time.sleep(0.6)
            if not self._pick_option(pick_re):
                self._real_hover(r"download|save to device", scope=MENU_SCOPE)
                time.sleep(0.8)
                if not self._pick_option(pick_re):
                    raise RuntimeError(
                        f"resolution option '{resolution}' not clickable"
                    )
            # Capture path 1 (primary): read the in-memory Blob Flow builds for
            # the download. Chrome 152's download manager crashes on blob
            # downloads under automation, so the hook also swallows the anchor
            # click — no download-manager involvement at all.
            raw = self._collect_generated_blob()
            if raw is not None:
                res_str = _save_image_bytes(raw, dest)
                width = int(res_str.split("x")[0])
                result: dict[str, Any] = {"path": "blob-hook", "resolution": res_str}
                if width < min_width:
                    result["note"] = (f"downloaded file is {width}px wide, below "
                                      f"the {min_width}px target")
                self._release_blobs()
                try:
                    self.page.keyboard.press("Escape")
                except Exception:
                    pass
                time.sleep(0.3)
                return result
            # Capture path 2: native download into the CDP watch folder.
            result = self._wait_for_native_download(
                dest, before_files, min_width=min_width
            )
            try:
                self.page.keyboard.press("Escape")  # dismiss any open menu
            except Exception:
                pass
            time.sleep(0.3)
            return result
        except Exception as exc:
            failure = str(exc)
            if debug:
                print(f"  [debug] download-dialog path failed: {failure}", flush=True)
                print(f"  [debug] visible UI: {self.settings_diagnostics()}", flush=True)
        try:
            self.page.keyboard.press("Escape")
        except Exception:
            pass
        raw, used = self.fetch_media_bytes(img_url)
        res_str = _save_image_bytes(raw, dest)
        return {"path": "request-fetch", "resolution": res_str,
                "note": f"download-dialog path failed: {failure}"}

    def new_project_if_needed(self) -> bool:
        """Open a new Flow project when no composer is present.

        The signed-in landing shows 'New project' / 'Start Creating' buttons;
        after clicking, the agent composer (a contenteditable div) can take a
        few seconds to appear.
        """
        if self.snapshot().get("hasPromptBox"):
            return True
        clicked = self._real_click(r"new project|start creating|^new$",
                                   scope="button, a")
        if not clicked:
            return False
        deadline = time.time() + 20.0
        while time.time() < deadline:
            time.sleep(2.0)
            if self.snapshot().get("hasPromptBox"):
                return True
        return False


# =============================================================================
# DRIVER ORCHESTRATION
# =============================================================================


def extract_media_id(url: str) -> Optional[str]:
    """Pull the media uuid out of a getMediaUrlRedirect URL."""
    m = re.search(r"name=([\w-]+)", url or "")
    return m.group(1) if m else None


def local_upscale_2x(im: Image.Image) -> Image.Image:
    """2x Lanczos resample — the bulk stand-in for Flow's in-browser SR.

    Flow's 'Upscaled' output measures ~7/255 mean-channel difference from this
    (verified against a salvaged true-2K download): close, slightly softer on
    fine texture, and it never touches the crash-prone download manager.
    """
    return im.resize((im.width * 2, im.height * 2), Image.LANCZOS)


def _fetch_master_bytes(profile_dir: Path, media_url: str,
                        timeout_s: float = 60.0) -> bytes:
    """Fetch a media's current master via a cookie-authed request context.

    Deliberately uses NO page automation and NO download manager — a plain
    HTTP GET of the tRPC redirect is the bulk-safe capture path. Runs fine
    headless and cannot trigger the Chrome 152 blob-download crash.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir), headless=True, channel="chrome",
            no_viewport=True,
        )
        try:
            resp = browser.request.get(media_url, timeout=int(timeout_s * 1000))
            if not resp.ok:
                raise RuntimeError(f"master fetch HTTP {resp.status}")
            return resp.body()
        finally:
            browser.close()


def capture_master_fast(profile_dir: Path, media_url: str, dest: Path,
                        resolution: str = "2K",
                        min_width: int = 1900) -> dict[str, Any]:
    """Bulk capture: HTTP-fetch the native master, upscale locally for 2K."""
    raw = _fetch_master_bytes(profile_dir, media_url)
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    path_label = "native-master"
    if resolution and resolution.upper().startswith("2") and im.width < min_width:
        im = local_upscale_2x(im)
        path_label = "local-2x-upscale"
    res_str = f"{im.width}x{im.height}"
    im.save(dest, format="PNG")
    result: dict[str, Any] = {"path": path_label, "resolution": res_str}
    if im.width < min_width:
        result["note"] = f"master is {res_str}, below the {min_width}px target"
    return result


def _save_image_bytes(raw: bytes, dest: Path) -> str:
    """Persist bytes as PNG at dest; returns the 'WxH' resolution string."""
    im = Image.open(io.BytesIO(raw))
    width, height = im.size
    if im.format == "PNG":
        dest.write_bytes(raw)
    else:
        im.convert("RGB").save(dest, format="PNG")
    return f"{width}x{height}"


def _load_queue(project_dir: Path) -> list[dict[str, Any]]:
    queue_path = project_dir / "exports" / "google_flow" / "queue.json"
    if not queue_path.is_file():
        raise FileNotFoundError(
            f"queue.json not found at {queue_path}. Run `google_flow_bridge export` first."
        )
    return json.loads(queue_path.read_text(encoding="utf-8"))


def capture_only(
    project_id: str,
    projects_root: Optional[Path] = None,
    resolution: str = "2K",
    profile_dir: Optional[Path] = None,
    force: bool = False,
    only_scene_ids: Optional[list[str]] = None,
    logger: Optional[Callable[[str], None]] = None,
) -> ToolResult:
    """Phase-2 only: (re)fetch masters for items that already have a media id.

    Runs with zero page automation and zero downloads — one cookie-authed GET
    per image plus a local 2x upscale when requested. Use after a run whose
    generation succeeded but whose capture crashed, or to re-derive variants.
    """
    log = logger or (lambda msg: print(msg, flush=True))
    projects_root = projects_root or _PROJECT_ROOT / "projects"
    project_dir = projects_root / project_id
    if not project_dir.is_dir():
        return ToolResult(success=False, error=f"Project directory not found: {project_dir}")
    try:
        queue = _load_queue(project_dir)
    except FileNotFoundError as exc:
        return ToolResult(success=False, error=str(exc))

    drop_dir = project_dir / "drop_images"
    drop_dir.mkdir(parents=True, exist_ok=True)
    state = DriverState(project_dir / "exports" / "google_flow" / _STATE_FILENAME, project_id)
    eff_profile = profile_dir or _DEFAULT_PROFILE_DIR

    if only_scene_ids:
        wanted = set(only_scene_ids)
        queue = [q for q in queue if q.get("scene_id") in wanted]

    succeeded = skipped = failed = 0
    for item in queue:
        target = item["target_filename"]
        entry = state.items.get(target, {})
        media_id = entry.get("media_id") or extract_media_id(entry.get("source_url", ""))
        if not media_id:
            skipped += 1
            continue
        if not force and st_status(entry) == "succeeded" and (drop_dir / target).is_file():
            skipped += 1
            log(f"  [=] {target} already captured, skipping (use --force to redo)")
            continue
        media_url = f"https://labs.google/fx/api/trpc/media.getMediaUrlRedirect?name={media_id}"
        try:
            result = capture_master_fast(
                eff_profile, media_url, drop_dir / target, resolution=resolution
            )
        except Exception as exc:
            state.mark(target, "failed", reason=f"capture failed: {exc}")
            failed += 1
            log(f"  [!] {target}: {exc}")
            continue
        state.mark(target, "succeeded", resolution=result.get("resolution"),
                   capture=result.get("path"), media_id=media_id)
        succeeded += 1
        note = f" — {result['note']}" if result.get("note") else ""
        log(f"  [✓] {target} ({result.get('resolution')}, via {result.get('path')}){note}")

    return ToolResult(
        success=failed == 0,
        data={
            "message": (f"capture finished: {succeeded} captured, {failed} failed, "
                        f"{skipped} skipped (no media id / already done)"),
            "succeeded": succeeded, "failed": failed, "skipped": skipped,
        },
    )


def st_status(entry: dict[str, Any]) -> Optional[str]:
    return entry.get("status")


def run_driver(
    project_id: str,
    projects_root: Optional[Path] = None,
    model_hint: str = "Nano Banana",
    resolution: str = "2K",
    aspect_ratio: str = "16:9",
    outputs: int = 1,
    auto_confirm: bool = True,
    min_delay_s: float = 20.0,
    max_delay_s: float = 55.0,
    timeout_s: float = 240.0,
    only_scene_ids: Optional[list[str]] = None,
    force: bool = False,
    dry_run: bool = False,
    upscale_mode: str = "fast",
    profile_dir: Optional[Path] = None,
    cdp_url: Optional[str] = None,
    headless: bool = False,
    keep_open: bool = False,
    login_timeout_s: float = 600.0,
    debug: bool = False,
    logger: Optional[Callable[[str], None]] = None,
) -> ToolResult:
    """Full loop: queue.json -> Flow UI -> drop_images/<target_filename>.png."""
    log = logger or (lambda msg: print(msg, flush=True))
    projects_root = projects_root or _PROJECT_ROOT / "projects"
    project_dir = projects_root / project_id
    if not project_dir.is_dir():
        return ToolResult(success=False, error=f"Project directory not found: {project_dir}")

    try:
        queue = _load_queue(project_dir)
    except FileNotFoundError as exc:
        return ToolResult(success=False, error=str(exc))

    if only_scene_ids:
        wanted = set(only_scene_ids)
        queue = [q for q in queue if q.get("scene_id") in wanted]
        if not queue:
            return ToolResult(success=False, error="No queue items match --only scene ids.")

    drop_dir = project_dir / "drop_images"
    drop_dir.mkdir(parents=True, exist_ok=True)
    state = DriverState(project_dir / "exports" / "google_flow" / _STATE_FILENAME, project_id)

    pending: list[dict[str, Any]] = []
    for item in queue:
        target = item["target_filename"]
        st = state.status_of(target)
        if not force and st == "succeeded" and (drop_dir / target).is_file():
            log(f"  [=] {target} already done, skipping (use --force to redo)")
            continue
        pending.append(item)
    if not pending:
        return ToolResult(success=True, data={
            "message": "All queue items already generated. Nothing to do.",
            "succeeded": len(queue), "pending": 0,
        })

    limiter = RateLimiter(
        min_delay_s=min_delay_s, max_delay_s=max_delay_s
    )
    session = FlowSession(
        profile_dir=profile_dir or _DEFAULT_PROFILE_DIR,
        headless=headless,
        cdp_url=cdp_url,
        logger=log,
    )
    succeeded = failed = 0

    try:
        session.start()
        session.open_flow()
        if not session.wait_for_login(login_timeout_s):
            return ToolResult(success=False, error=(
                "Google login was not completed in time. Log in once via "
                f"`python -m tools.graphics.google_flow_driver login`, then re-run."
            ))
        if not session.new_project_if_needed():
            return ToolResult(success=False, error=(
                "Flow UI did not show a prompt surface. Run with --debug to dump the "
                "visible UI texts and share them for selector updates."
            ))

        # Session-level setup: model, aspect ratio, outputs per generation.
        # (2K is NOT set here — Flow's upscale happens at download time and is
        # captured per-image by download_media_2k below.)
        setup = session.setup_generation_settings(
            model_hint=model_hint, aspect_ratio=aspect_ratio, outputs=outputs
        )
        if not setup.get("panel_opened"):
            return ToolResult(success=False, error=(
                f"Could not open Flow's settings panel: {setup}. "
                f"Visible UI: {session.settings_diagnostics()}"
            ))
        log(f"  [+] Settings: {setup}")
        if not setup.get("composer_ready"):
            log("  [!] Composer missing after the settings panel — reopening a project.")
            if not session.new_project_if_needed():
                return ToolResult(success=False, error=(
                    "Prompt composer did not re-appear after the settings panel. "
                    f"Visible UI: {session.settings_diagnostics()}"
                ))

        if dry_run:
            return ToolResult(success=True, data={
                "message": ("Dry run passed: composer, settings panel, and submit "
                            "controls verified. No prompts were submitted."),
                "settings": setup,
                "pending_count": len(pending),
            })

        for i, item in enumerate(pending, start=1):
            target = item["target_filename"]
            scene_id = item["scene_id"]
            log(f"[{i}/{len(pending)}] Generating {scene_id} → {target}")
            before = set(session.snapshot().get("imgs", []))
            state.mark(target, "in_progress")

            try:
                gen = session.submit_and_wait(
                    item["prompt"], before, timeout_s=timeout_s,
                    auto_confirm=auto_confirm,
                )
            except RateLimitError as exc:
                try:
                    wait = limiter.backoff_delay()
                except RateLimitError as fatal:
                    state.mark(target, "blocked", reason=str(fatal))
                    log(f"  [!] {fatal}")
                    break
                state.mark(target, "pending_backoff", reason=str(exc))
                log(f"  [!] Rate limit hit ({exc}). Backing off {wait/60:.1f} min…")
                time.sleep(wait)
                # Retry the same item once per loop iteration via queue re-append
                pending.append(item)
                continue
            except GenerationTimeout as exc:
                state.mark(target, "failed", reason=str(exc))
                failed += 1
                log(f"  [!] {exc}")
                continue

            try:
                if upscale_mode == "fast":
                    # Bulk-safe path: plain HTTP fetch of the master + local 2x.
                    # No download manager, no CDP page interaction, no crash.
                    # Uses the live session's context (nested sync Playwright
                    # inside this loop is not allowed).
                    result = session.capture_master_fast(
                        gen["url"], drop_dir / target, resolution=resolution,
                    )
                else:
                    # Flow-true SR path: the UI menu dance with blob hook,
                    # native watch-folder, and crash salvage.
                    result = session.download_media_2k(
                        gen["url"], drop_dir / target,
                        resolution=resolution, debug=debug,
                    )
            except Exception as exc:
                # the media exists server-side even though capture failed —
                # record its id so `capture` can recover without new credits
                state.mark(target, "failed", reason=f"capture failed: {exc}",
                           media_id=extract_media_id(gen["url"]))
                failed += 1
                log(f"  [!] Capture failed: {exc}")
                continue

            res_str = result.get("resolution", "unknown")
            width = int(res_str.split("x")[0]) if "x" in res_str else 0
            note = result.get("note", "")
            media_id = extract_media_id(gen["url"])
            state.mark(target, "succeeded", resolution=res_str,
                       capture=result.get("path"), media_id=media_id,
                       source_url=gen["url"][:200])
            succeeded += 1
            log(f"  [✓] Saved {target} ({res_str}, via {result.get('path')})")
            if note:
                log(f"  [!] {note}")
            if width and width < 1900 and resolution.lower() == "2k":
                log(f"  [!] Warning: {target} is only {res_str} — below the "
                    f"requested {resolution}. Check the capture note above.")

            if i < len(pending):
                pause = limiter.success_delay()
                log(f"  … next prompt in {pause:.0f}s")
                time.sleep(pause)

    finally:
        session.close(keep_open=keep_open)
        state.save()

    return ToolResult(
        success=failed == 0,
        data={
            "message": (
                f"Google Flow driver finished: {succeeded} succeeded, {failed} failed, "
                f"{len(pending) - succeeded - failed} not attempted. Images saved to "
                f"{drop_dir}. Run `google_flow_bridge ingest {project_id}` to build the manifest."
            ),
            "succeeded": succeeded,
            "failed": failed,
            "pending": max(0, len(pending) - succeeded - failed),
            "state_file": str(state.path),
        },
    )


# =============================================================================
# BASETOOL WRAPPER
# =============================================================================


class GoogleFlowDriver(BaseTool):
    name = "google_flow_driver"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "google_flow_driver"
    provider = "google_flow"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.LOCAL

    dependencies = ["playwright"]
    install_instructions = (
        "Uses the project venv's Playwright with the machine's Google Chrome. "
        "No API key required — drives the user's own flow.google session in a "
        "dedicated browser profile (~/.openmontage/flow-driver-profile)."
    )
    agent_skills = ["visual-style"]

    capabilities = ["drive_google_flow_generation"]
    supports = {
        "automated_prompt_submission": True,
        "download_time_2k_capture": True,
        "rate_limit_backoff": True,
        "resumable_runs": True,
        "no_third_party_code": True,
    }
    best_for = [
        "closing the manual loop between google_flow_bridge export and ingest",
        "batch generation of 99+ prompts with jitter and exponential backoff",
        "capturing Flow's download-time 2K upscale into the project drop folder",
        "auditable first-party browser automation without closed-source extensions",
    ]
    not_good_for = [
        "headless generation on machines where nobody can complete Google login",
        "bypassing Flow's terms of service or account limits",
    ]

    input_schema = {
        "type": "object",
        "required": ["project_id", "operation"],
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["run", "capture", "dry_run", "status", "reset"],
            },
            "project_id": {"type": "string"},
            "model": {"type": "string", "default": "Nano Banana"},
            "resolution": {
                "type": "string", "default": "2K",
                "description": "Resolution picked in Flow's download-time dialog",
            },
            "aspect_ratio": {"type": "string", "default": "16:9"},
            "outputs": {"type": "integer", "default": 1},
            "auto_confirm": {
                "type": "boolean", "default": True,
                "description": "Click the agent's spend-confirmation dialog when it appears",
            },
            "upscale_mode": {
                "type": "string", "enum": ["fast", "flow"], "default": "fast",
                "description": "fast = HTTP fetch + local 2x (bulk-safe); "
                               "flow = UI dance for Flow's true SR",
            },
            "only_scene_ids": {"type": "array", "items": {"type": "string"}},
            "force": {"type": "boolean", "default": False},
            "projects_root": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=200, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=0, retryable_errors=[])
    idempotency_key_fields = ["project_id", "operation"]
    side_effects = [
        "drives the user's Chrome against flow.google using their account credits",
        "writes generated images into projects/<id>/drop_images/",
        "writes exports/google_flow/driver_state.json",
    ]
    user_visible_verification = [
        "Generated images land in projects/<id>/drop_images/ with correct names",
        "Backlot filmstrip after running google_flow_bridge ingest",
    ]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        operation = inputs.get("operation", "run")
        project_id = inputs.get("project_id")
        if not project_id:
            return ToolResult(success=False, error="project_id is required")
        projects_root = (
            Path(inputs["projects_root"]) if inputs.get("projects_root") else None
        )
        project_dir = (projects_root or _PROJECT_ROOT / "projects") / project_id

        if operation == "status":
            state = DriverState(
                project_dir / "exports" / "google_flow" / _STATE_FILENAME, project_id
            )
            counts: dict[str, int] = {}
            for entry in state.items.values():
                counts[entry.get("status", "?")] = counts.get(entry.get("status", "?"), 0) + 1
            return ToolResult(success=True, data={"state_file": str(state.path), "counts": counts})
        if operation == "reset":
            state = DriverState(
                project_dir / "exports" / "google_flow" / _STATE_FILENAME, project_id
            )
            state.reset()
            return ToolResult(success=True, data={"message": "Driver state cleared."})

        if operation == "capture":
            return capture_only(
                project_id=project_id,
                projects_root=projects_root,
                resolution=inputs.get("resolution", "2K"),
                force=bool(inputs.get("force", False)),
                only_scene_ids=inputs.get("only_scene_ids"),
            )

        return run_driver(
            project_id=project_id,
            projects_root=projects_root,
            model_hint=inputs.get("model", "Nano Banana"),
            resolution=inputs.get("resolution", "2K"),
            aspect_ratio=inputs.get("aspect_ratio", "16:9"),
            outputs=int(inputs.get("outputs", 1)),
            auto_confirm=bool(inputs.get("auto_confirm", True)),
            upscale_mode=inputs.get("upscale_mode", "fast"),
            only_scene_ids=inputs.get("only_scene_ids"),
            force=bool(inputs.get("force", False)),
            dry_run=operation == "dry_run",
        )


# =============================================================================
# CLI
# =============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Google Flow Driver: automated prompt submission and 2K image capture."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser, with_project: bool = True) -> None:
        if with_project:
            p.add_argument("project_id", help="Project ID (e.g. 'hidden-math-of-nature')")
            p.add_argument("--projects-root", default=None)
        p.add_argument("--model", default="Nano Banana",
                       help="Image model substring to select (default: Nano Banana)")
        p.add_argument("--resolution", default="2K",
                       help="Resolution to pick in Flow's download dialog (default: 2K)")
        p.add_argument("--aspect", default="16:9", help="Aspect ratio setting (default: 16:9)")
        p.add_argument("--outputs", type=int, default=1, choices=[1, 2, 3, 4],
                       help="Images per generation (default: 1)")
        p.add_argument("--no-auto-confirm", action="store_true",
                       help="Do not click the agent's spend-confirmation dialog "
                            "(run will stop if the agent asks for confirmation)")
        p.add_argument("--min-delay", type=float, default=20.0,
                       help="Minimum jitter delay between prompts (s)")
        p.add_argument("--max-delay", type=float, default=55.0,
                       help="Maximum jitter delay between prompts (s)")
        p.add_argument("--timeout", type=float, default=240.0,
                       help="Per-prompt generation timeout (s)")
        p.add_argument("--profile-dir", default=None,
                       help="Chrome profile dir (default: ~/.openmontage/flow-driver-profile)")
        p.add_argument("--cdp", default=None,
                       help="Attach to an existing Chrome debugging endpoint instead of launching")
        p.add_argument("--headless", action="store_true",
                       help="Run headless (not recommended; login needs a visible window)")
        p.add_argument("--keep-open", action="store_true",
                       help="Leave the browser open after the run")
        p.add_argument("--debug", action="store_true",
                       help="Dump visible UI texts on failures")

    run_p = sub.add_parser("run", help="Generate all pending prompts and save images")
    common(run_p)
    run_p.add_argument("--upscale", choices=["fast", "flow"], default="fast",
                       help="fast = fetch native master + local 2x (bulk-safe, default); "
                            "flow = UI dance for Flow's true in-browser SR")
    run_p.add_argument("--only", action="append", default=[],
                       help="Restrict to specific scene ids (repeatable)")
    run_p.add_argument("--force", action="store_true",
                       help="Regenerate even items marked succeeded")

    cap_p = sub.add_parser("capture",
                           help="Re-fetch masters for items with a known media id (no generation)")
    common(cap_p)
    cap_p.add_argument("--only", action="append", default=[],
                       help="Restrict to specific scene ids (repeatable)")
    cap_p.add_argument("--force", action="store_true",
                       help="Re-capture even items marked succeeded")

    dry_p = sub.add_parser("dry_run", help="Verify mode/model/prompt selectors without generating")
    common(dry_p)

    status_p = sub.add_parser("status", help="Show driver state counts")
    common(status_p)

    reset_p = sub.add_parser("reset", help="Clear driver state for the project")
    common(reset_p)

    login_p = sub.add_parser("login", help="Open the profile browser for one-time Google login")
    login_p.add_argument("--profile-dir", default=None)

    args = parser.parse_args()
    tool = GoogleFlowDriver()
    projects_root = getattr(args, "projects_root", None)

    if args.command == "login":
        session = FlowSession(
            profile_dir=Path(args.profile_dir or _DEFAULT_PROFILE_DIR),
            logger=lambda msg: print(msg, flush=True),
        )
        session.start()
        session.open_flow()
        signed_in = session.wait_for_login(timeout_s=3600.0)
        session.close(keep_open=False)
        if signed_in:
            print(f"Login saved to the dedicated profile ({_DEFAULT_PROFILE_DIR}).")
        else:
            print("Timed out waiting for sign-in; nothing saved. Re-run `login` and "
                  "complete sign-in in the opened window.")
            sys.exit(1)
        return

    if args.command == "status":
        res = tool.execute({
            "operation": "status", "project_id": args.project_id,
            "projects_root": projects_root,
        })
        print(json.dumps(res.data, indent=2))
        return

    if args.command == "reset":
        res = tool.execute({
            "operation": "reset", "project_id": args.project_id,
            "projects_root": projects_root,
        })
        print(res.data.get("message", ""))
        return

    if args.command == "capture":
        res = capture_only(
            project_id=args.project_id,
            projects_root=Path(projects_root) if projects_root else None,
            resolution=args.resolution,
            force=args.force,
            only_scene_ids=list(args.only),
        )
        if res.success:
            print(f"SUCCESS: {res.data.get('message')}")
        else:
            print(f"ERROR: {res.error}", file=sys.stderr)
            sys.exit(1)
        return

    res = run_driver(
        project_id=args.project_id,
        projects_root=Path(projects_root) if projects_root else None,
        model_hint=args.model,
        resolution=args.resolution,
        aspect_ratio=args.aspect,
        outputs=args.outputs,
        auto_confirm=not args.no_auto_confirm,
        min_delay_s=args.min_delay,
        max_delay_s=args.max_delay,
        timeout_s=args.timeout,
        only_scene_ids=list(args.only) if args.command in ("run", "capture") else None,
        force=args.command in ("run", "capture") and args.force,
        dry_run=args.command == "dry_run",
        upscale_mode=args.upscale if args.command in ("run", "capture") else "fast",
        profile_dir=Path(args.profile_dir) if args.profile_dir else None,
        cdp_url=args.cdp,
        headless=args.headless,
        keep_open=args.keep_open,
        debug=args.debug,
    )
    if res.success:
        print(f"SUCCESS: {res.data.get('message')}")
    else:
        print(f"ERROR: {res.error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
