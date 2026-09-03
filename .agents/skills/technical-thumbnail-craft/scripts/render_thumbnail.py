#!/usr/bin/env python3
"""
Render pixel-perfect 16:9 YouTube thumbnails from HTML templates using headless Chrome.
Includes automatic 120px mobile scale generation to verify the mobile squint test.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def find_chrome() -> Path:
    """Find local headless Chrome binary."""
    # Check HyperFrames cached chrome first
    cache_base = Path.home() / ".cache" / "hyperframes" / "chrome" / "chrome-headless-shell"
    if cache_base.exists():
        for path in cache_base.glob("**/chrome-headless-shell"):
            if os.access(path, os.X_OK):
                return path

    # Fallback to system chrome
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
    ]
    for c in candidates:
        p = Path(c)
        if p.exists() and os.access(p, os.X_OK):
            return p

    raise FileNotFoundError("Could not find chrome-headless-shell or Google Chrome executable.")


def render_thumbnail(template_path: Path, output_path: Path, width: int = 1280, height: int = 720) -> None:
    chrome = find_chrome()
    template_uri = f"file://{template_path.resolve()}"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[ThumbnailCraft] Rendering {template_path.name} -> {output_path.name} ({width}x{height})...")
    
    cmd = [
        str(chrome),
        "--headless",
        "--no-sandbox",
        "--hide-scrollbars",
        "--force-color-profile=srgb",
        f"--window-size={width},{height}",
        f"--screenshot={output_path.resolve()}",
        template_uri,
    ]

    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(f"Failed to generate thumbnail image at {output_path}")

    print(f"[ThumbnailCraft] Rendered thumbnail successfully ({output_path.stat().st_size // 1024} KB)")

    # Generate 120px mobile preview for the mobile squint test
    mobile_out = output_path.parent / f"{output_path.stem}_mobile_120px.jpg"
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", str(output_path),
        "-vf", "scale=-1:120",
        str(mobile_out)
    ]
    try:
        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"[ThumbnailCraft] Generated 120px mobile preview at {mobile_out.name}")
    except Exception as e:
        print(f"[ThumbnailCraft] Note: Could not generate mobile preview: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render technical YouTube thumbnails from HTML templates.")
    parser.add_argument("--template", required=True, help="Path to HTML thumbnail template")
    parser.add_argument("--output", required=True, help="Path to output image (e.g. thumbnail.jpg)")
    parser.add_argument("--width", type=int, default=1280, help="Width in pixels (default: 1280)")
    parser.add_argument("--height", type=int, default=720, help="Height in pixels (default: 720)")

    args = parser.parse_args()
    template_path = Path(args.template)
    output_path = Path(args.output)

    if not template_path.exists():
        print(f"Error: Template not found at {template_path}", file=sys.stderr)
        sys.exit(1)

    try:
        render_thumbnail(template_path, output_path, args.width, args.height)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
