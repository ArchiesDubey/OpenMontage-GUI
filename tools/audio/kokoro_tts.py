"""Kokoro-82M local text-to-speech provider tool.

Runs the Kokoro-82M model offline via the HyperFrames CLI (`npx hyperframes tts`),
which bundles it as its local speech engine. No API key, no network after the
first run — the ~310MB ONNX model is cached under ~/.cache/hyperframes/tts/models/.

Kokoro's context is ~510 phoneme tokens (~30s of speech). Longer text is silently
truncated by the model, so text is split into conservative pieces here and the
rendered pieces are stitched with ffmpeg.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

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

# Well under Kokoro's ~510-token context. Phoneme count per character varies, so
# stay conservative — most single sentences fit in one piece.
PIECE_MAX_CHARS = 300

# Minimum Node major version required by the HyperFrames CLI.
MIN_NODE_MAJOR = 22


def split_for_kokoro(text: str, max_len: int = PIECE_MAX_CHARS) -> list[str]:
    """Split text into pieces Kokoro can synthesize without truncation.

    Strips bracketed performance tags (Kokoro would try to pronounce them),
    normalizes whitespace, then packs whole sentences into pieces. A single
    sentence longer than ``max_len`` is split on word boundaries.
    """
    clean = re.sub(r"\[[^\]\n]{0,40}\]", " ", str(text))
    clean = re.sub(r"\s+", " ", clean).strip()
    if not clean:
        return []

    sentences = re.findall(r"[^.!?]+[.!?]+[\"')\]]*|\S[^.!?]*$", clean) or [clean]

    pieces: list[str] = []
    cur = ""
    for raw in sentences:
        s = raw.strip()
        if not s:
            continue
        if len(s) <= max_len:
            if cur and len(cur) + 1 + len(s) > max_len:
                pieces.append(cur)
                cur = ""
            cur = f"{cur} {s}".strip() if cur else s
        else:
            if cur:
                pieces.append(cur)
                cur = ""
            word_buf = ""
            for word in s.split():
                if word_buf and len(word_buf) + 1 + len(word) > max_len:
                    pieces.append(word_buf)
                    word_buf = word
                else:
                    word_buf = f"{word_buf} {word}".strip() if word_buf else word
            if word_buf:
                pieces.append(word_buf)
    if cur:
        pieces.append(cur)
    return pieces


class KokoroTTS(BaseTool):
    name = "kokoro_tts"
    version = "0.1.0"
    tier = ToolTier.VOICE
    capability = "tts"
    provider = "kokoro"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.LOCAL

    dependencies = ["cmd:npx", "cmd:ffmpeg", f"node>={MIN_NODE_MAJOR}"]
    install_instructions = (
        "Kokoro-82M runs locally through the HyperFrames CLI — no API key needed.\n"
        f"  1. Install Node.js >= {MIN_NODE_MAJOR} (provides npx)\n"
        "  2. Install ffmpeg (used to stitch multi-piece narration)\n"
        "The ~310MB Kokoro model downloads automatically on first use and is then\n"
        "cached at ~/.cache/hyperframes/tts/models/ for fully offline operation.\n"
        "List voices with: npx hyperframes tts --list"
    )
    # hyperframes-media documents this exact CLI, its 54 Kokoro voice IDs, and the
    # rule that a missing cloud credential is not licence to switch to the local
    # voice silently. NOT `text-to-speech` — that Layer 3 skill is HeyGen Starfish.
    agent_skills = ["hyperframes-media"]

    capabilities = [
        "text_to_speech",
        "offline_generation",
        "multilingual",
    ]
    supports = {
        "voice_cloning": False,
        "multilingual": True,
        "offline": True,
        "native_audio": True,
    }
    best_for = [
        "free offline narration with natural documentary delivery",
        "privacy-sensitive local-only workflows",
        "long-form narration at zero cost",
    ]
    not_good_for = [
        "voice clone matching",
        "fine-grained emotional direction via prompt tags",
    ]

    # First letter of a Kokoro voice ID selects the phonemizer language.
    input_schema = {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string"},
            "voice_id": {
                "type": "string",
                "default": "af_heart",
                "description": (
                    "Kokoro voice ID. en-US: af_heart, af_nova, af_sky, am_adam, "
                    "am_michael. en-GB: bf_emma, bf_isabella, bm_george. Also "
                    "ef_dora (es), ff_siwis (fr), jf_alpha (ja), zf_xiaobei (zh)."
                ),
            },
            "speed": {
                "type": "number",
                "minimum": 0.5,
                "maximum": 2.0,
                "default": 1.0,
                "description": "Speech speed multiplier.",
            },
            "lang": {
                "type": "string",
                "enum": ["en-us", "en-gb", "es", "fr-fr", "hi", "it", "pt-br", "ja", "zh"],
                "description": "Phonemizer override. Auto-detected from the voice prefix when omitted.",
            },
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=2, ram_mb=1024, vram_mb=0, disk_mb=400, network_required=False
    )
    retry_policy = RetryPolicy(max_retries=1, retryable_errors=[])
    idempotency_key_fields = ["text", "voice_id", "speed", "lang"]
    side_effects = ["writes audio file to output_path"]
    user_visible_verification = ["Listen to generated narration for pacing and intelligibility"]

    _status_cache: ToolStatus | None = None

    def get_status(self) -> ToolStatus:
        """Available only when npx, ffmpeg, and a new enough Node are all present.

        Checked properly rather than trusting a bare `which` — a tool that reports
        AVAILABLE but cannot actually speak fails deep inside the assets stage.
        """
        if KokoroTTS._status_cache is not None:
            return KokoroTTS._status_cache

        status = ToolStatus.UNAVAILABLE
        if shutil.which("npx") and shutil.which("ffmpeg") and shutil.which("node"):
            try:
                proc = subprocess.run(
                    ["node", "--version"], capture_output=True, text=True, timeout=15
                )
                major = int(proc.stdout.strip().lstrip("v").split(".")[0])
                if major >= MIN_NODE_MAJOR:
                    status = ToolStatus.AVAILABLE
            except (subprocess.SubprocessError, ValueError, IndexError):
                status = ToolStatus.UNAVAILABLE

        KokoroTTS._status_cache = status
        return status

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if self.get_status() != ToolStatus.AVAILABLE:
            return ToolResult(
                success=False,
                error="Kokoro TTS not available. " + self.install_instructions,
            )

        start = time.time()
        try:
            result = self._generate(inputs)
        except Exception as exc:
            return ToolResult(success=False, error=f"Kokoro TTS generation failed: {exc}")

        result.duration_seconds = round(time.time() - start, 2)
        return result

    def _generate(self, inputs: dict[str, Any]) -> ToolResult:
        voice = inputs.get("voice_id") or "af_heart"
        speed = inputs.get("speed", 1.0)
        lang = inputs.get("lang")

        output_path = Path(inputs.get("output_path", "tts_output.wav"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        pieces = split_for_kokoro(inputs["text"])
        if not pieces:
            return ToolResult(success=False, error="Kokoro: nothing to speak (empty text after cleaning)")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            rendered: list[Path] = []

            for idx, piece in enumerate(pieces):
                piece_wav = tmp / f"piece_{idx:04d}.wav"
                err = self._synthesize(piece, piece_wav, voice, speed, lang)
                if err:
                    return ToolResult(success=False, error=f"Kokoro piece {idx + 1}/{len(pieces)}: {err}")
                rendered.append(piece_wav)

            stitched = tmp / "stitched.wav"
            if len(rendered) == 1:
                shutil.copyfile(rendered[0], stitched)
            else:
                err = self._concat(rendered, stitched, tmp)
                if err:
                    return ToolResult(success=False, error=f"Kokoro stitch failed: {err}")

            err = self._finalize(stitched, output_path)
            if err:
                return ToolResult(success=False, error=f"Kokoro output conversion failed: {err}")

        if not output_path.exists():
            return ToolResult(success=False, error=f"Kokoro output file missing: {output_path}")

        return ToolResult(
            success=True,
            data={
                "provider": self.provider,
                "model": "kokoro-82m",
                "voice_id": voice,
                "speed": speed,
                "pieces": len(pieces),
                "text_length": len(inputs["text"]),
                "output": str(output_path),
                "format": output_path.suffix.lstrip(".") or "wav",
                "cost_usd": 0.0,
            },
            artifacts=[str(output_path)],
            model="kokoro-82m",
        )

    def _synthesize(
        self, text: str, dest: Path, voice: str, speed: float, lang: str | None
    ) -> str | None:
        """Render one piece. Returns an error string, or None on success.

        `hyperframes tts` is Kokoro-only and takes no --provider flag, so this
        cannot silently route to a paid cloud voice. If a future CLI version adds
        provider auto-detection (the vendored skill's table lists HeyGen and
        ElevenLabs ahead of Kokoro), pin it here — this tool reports
        provider="kokoro", runtime=LOCAL and cost 0.0, and must stay true to that.
        """
        cmd = [
            "npx", "hyperframes", "tts",
            "--voice", voice,
            "--speed", str(speed),
            "-o", str(dest),
        ]
        if lang:
            cmd += ["--lang", lang]
        cmd.append(text)

        import os
        import sys
        env = dict(os.environ)
        if "HYPERFRAMES_PYTHON" not in env:
            env["HYPERFRAMES_PYTHON"] = sys.executable

        # Generous timeout: the first ever call downloads the ~310MB model.
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, env=env)
        if proc.returncode != 0:
            return f"hyperframes tts exit {proc.returncode}: {proc.stderr.strip()[-500:]}"
        if not dest.exists():
            return f"expected output {dest.name} was not written"
        return None

    @staticmethod
    def _concat(pieces: list[Path], dest: Path, tmp: Path) -> str | None:
        """Stitch pieces with the ffmpeg concat demuxer.

        Safe here because every Kokoro piece shares one format (24kHz mono wav).
        """
        listing = tmp / "pieces.txt"
        listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in pieces))

        proc = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(listing), "-c", "copy", str(dest)],
            capture_output=True, text=True, timeout=600,
        )
        if proc.returncode != 0:
            return proc.stderr.strip()[-500:]
        return None

    @staticmethod
    def _finalize(stitched: Path, output_path: Path) -> str | None:
        """Move to the requested path, transcoding when a non-wav extension is asked for."""
        if output_path.suffix.lower() == ".wav":
            shutil.copyfile(stitched, output_path)
            return None

        proc = subprocess.run(
            ["ffmpeg", "-y", "-i", str(stitched), str(output_path)],
            capture_output=True, text=True, timeout=600,
        )
        if proc.returncode != 0:
            return proc.stderr.strip()[-500:]
        return None
