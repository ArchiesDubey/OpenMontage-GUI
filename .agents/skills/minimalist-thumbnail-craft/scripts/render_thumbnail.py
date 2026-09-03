#!/usr/bin/env python3
"""
Render pixel-perfect 16:9 YouTube thumbnails from HTML/SVG templates using headless Chrome.
Automatically generates a 120px-wide mobile preview to verify the mobile squint test.
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


def generate_mobile_squint_test(image_path: Path, output_squint_path: Path, target_width: int = 120) -> None:
    """Generate a 120px wide thumbnail preview for testing mobile readability."""
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            aspect = img.height / img.width
            target_height = int(target_width * aspect)
            resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            resized.save(output_squint_path)
            print(f"[MobileSquintTest] Generated {output_squint_path.name} ({target_width}x{target_height})")
            return
    except ImportError:
        pass

    # Fallback using macOS sips if PIL is not installed
    try:
        subprocess.run(
            ["sips", "-z", str(int(target_width * 720 / 1280)), str(target_width), str(image_path), "--out", str(output_squint_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"[MobileSquintTest] Generated {output_squint_path.name} via sips ({target_width}px wide)")
    except Exception as e:
        print(f"[Warning] Could not generate mobile squint test: {e}")


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

    print(f"[ThumbnailCraft] Success! Master thumbnail saved to {output_path}")

    # Generate 120px mobile preview
    squint_path = output_path.parent / f"{output_path.stem}_mobile_squint{output_path.suffix}"
    generate_mobile_squint_test(output_path, squint_path, target_width=120)


def main():
    parser = argparse.ArgumentParser(description="Render minimalist YouTube thumbnails via headless Chrome.")
    parser.add_argument("--template", "-t", required=True, type=Path, help="Path to HTML thumbnail template")
    parser.add_argument("--output", "-o", required=True, type=Path, help="Path to output PNG/JPEG image")
    parser.add_argument("--width", type=int, default=1280, help="Output width (default: 1280)")
    parser.add_argument("--height", type=int, default=720, help="Output height (default: 720)")

    args = parser.parse_args()

    if not args.template.exists():
        print(f"Error: Template file not found: {args.template}", file=sys.stderr)
        sys.exit(1)

    try:
        render_thumbnail(args.template, args.output, args.width, args.height)
    except Exception as err:
        print(f"Error during thumbnail render: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
