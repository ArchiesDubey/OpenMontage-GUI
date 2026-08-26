#!/usr/bin/env python3
"""One-command, cross-platform install for OpenMontage.

Equivalent to `make setup`, but works anywhere Python runs — no `make`
required (useful on stock Windows, and for an AI coding agent that just
cloned the repo and needs a single command to run).

    python scripts/setup.py            # standard install
    python scripts/setup.py --dev      # + dev/test dependencies
    python scripts/setup.py --gpu      # + local GPU generation stack
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MIN_PYTHON = (3, 10)


def log(msg: str) -> None:
    print(f"==> {msg}")


def warn(msg: str) -> None:
    print(f"  [skip] {msg}")


def venv_python_path(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def resolve_python(venv_dir: Path) -> Path:
    """Reuse an already-active venv/conda env; otherwise create .venv."""
    active = os.environ.get("VIRTUAL_ENV") or os.environ.get("CONDA_PREFIX")
    if active:
        candidate = venv_python_path(Path(active))
        if candidate.is_file():
            log(f"Using active environment: {active}")
            return candidate

    py = venv_python_path(venv_dir)
    if py.is_file():
        log(f"Using existing virtual environment: {venv_dir}")
        return py

    if sys.version_info[:2] < MIN_PYTHON:
        sys.exit(
            f"ERROR: OpenMontage requires Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+, "
            f"found {sys.version_info.major}.{sys.version_info.minor}. "
            "Install a newer Python and re-run this script."
        )

    log(f"Creating virtual environment: {venv_dir}")
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    return venv_python_path(venv_dir)


def pip_install(python: Path, *args: str, required: bool = True) -> bool:
    result = subprocess.run([str(python), "-m", "pip", "install", *args])
    if result.returncode == 0:
        return True
    if required:
        sys.exit(f"ERROR: pip install failed (exit {result.returncode}): {' '.join(args)}")
    return False


def which(binary: str) -> str | None:
    return shutil.which(binary)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev", action="store_true", help="also install requirements-dev.txt")
    parser.add_argument("--gpu", action="store_true", help="also install the local GPU stack")
    parser.add_argument("--venv-dir", default=".venv", help="virtual environment directory (default: .venv)")
    args = parser.parse_args()

    os.chdir(REPO_ROOT)
    venv_dir = REPO_ROOT / args.venv_dir
    python = resolve_python(venv_dir)

    log("Installing Python dependencies...")
    pip_install(python, "-r", "requirements.txt")

    if args.dev:
        log("Installing dev/test dependencies...")
        pip_install(python, "-r", "requirements-dev.txt")

    if args.gpu:
        log("Installing local GPU generation stack...")
        pip_install(python, "-r", "requirements-gpu.txt")
        pip_install(python, "diffusers", "transformers", "accelerate")

    print()
    log("Installing Remotion composer...")
    if which("npm") is None:
        sys.exit(
            "ERROR: npm not found. Install Node.js 18+ (https://nodejs.org/) "
            "then re-run this script — Remotion composition needs it."
        )
    result = subprocess.run(["npm", "install"], cwd=REPO_ROOT / "remotion-composer")
    if result.returncode != 0:
        sys.exit(f"ERROR: 'npm install' in remotion-composer/ failed (exit {result.returncode}).")

    print()
    log("Installing free offline TTS (Piper)...")
    if not pip_install(python, "piper-tts", required=False):
        warn("piper-tts install failed — TTS will use cloud providers instead")

    print()
    log("Warming the HyperFrames runtime (npx cache)...")
    if which("npx") is None:
        warn("npx not found — HyperFrames will fetch on first render instead")
    else:
        warm = subprocess.run(
            ["npx", "--yes", "hyperframes", "--version"],
            capture_output=True, text=True,
        )
        if warm.returncode == 0:
            log("HyperFrames CLI cached (npx)")
        else:
            warn("HyperFrames cache-warm failed — offline or npm unavailable; first render will fetch on demand")

    print()
    env_path = REPO_ROOT / ".env"
    env_example = REPO_ROOT / ".env.example"
    if env_path.exists():
        log(".env already exists — skipping.")
    else:
        shutil.copy(env_example, env_path)
        log("Created .env from .env.example — add your API keys there.")

    print()
    print("Done! Open this project in your AI coding assistant and start creating.")
    print("  Optional: add API keys to .env to unlock cloud providers.")
    print("  Optional: run 'python scripts/setup.py --gpu' if you have an NVIDIA GPU.")
    print("  Optional: run 'make hyperframes-doctor' (or the equivalent Python check in README) to fully validate the HyperFrames runtime.")
    if not (os.environ.get("VIRTUAL_ENV") or os.environ.get("CONDA_PREFIX")):
        activate = (
            f"{args.venv_dir}\\Scripts\\Activate.ps1" if os.name == "nt"
            else f"source {args.venv_dir}/bin/activate"
        )
        print(f"  Activate the environment in new shells with: {activate}")


if __name__ == "__main__":
    main()
