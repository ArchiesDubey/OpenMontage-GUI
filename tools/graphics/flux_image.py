"""FLUX image generation via fal.ai API."""

from __future__ import annotations

import math
import os
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


class FluxImage(BaseTool):
    name = "flux_image"
    version = "0.3.0"
    tier = ToolTier.GENERATE
    capability = "image_generation"
    provider = "flux"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.SEEDED
    runtime = ToolRuntime.API

    dependencies = []  # checked dynamically via env var
    install_instructions = (
        "Set FAL_KEY to your fal.ai API key.\n"
        "  Get one at https://fal.ai/dashboard/keys"
    )
    agent_skills = ["flux-best-practices", "bfl-api"]

    capabilities = ["generate_image", "generate_illustration", "text_to_image"]
    supports = {
        "negative_prompt": True,
        "seed": True,
        "custom_size": True,
    }
    best_for = [
        "photorealistic images",
        "general-purpose image generation",
        "high quality at low cost (flux-2 ~$0.012/MP, flux/dev ~$0.025/MP)",
        "style-consistent batches / series work (flux-2, seed + richer prompt adherence)",
    ]
    not_good_for = ["text rendering in images", "offline generation"]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string"},
            "negative_prompt": {"type": "string", "default": ""},
            "width": {"type": "integer", "default": 1024},
            "height": {"type": "integer", "default": 1024},
            "model": {
                "type": "string",
                "enum": [
                    "flux-2",
                    "flux-pro/v1.1",
                    "flux/dev",
                    "flux/schnell",
                    "flux-pro",
                ],
                "default": "flux-pro/v1.1",
            },
            "seed": {"type": "integer"},
            "num_inference_steps": {"type": "integer"},
            "guidance_scale": {"type": "number"},
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=100, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["prompt", "width", "height", "seed", "model"]
    side_effects = ["writes image file to output_path", "calls fal.ai API"]
    user_visible_verification = ["Inspect generated image for relevance and quality"]

    def _get_api_key(self) -> str | None:
        return os.environ.get("FAL_KEY") or os.environ.get("FAL_AI_API_KEY")

    def get_status(self) -> ToolStatus:
        if self._get_api_key():
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    # fal.ai billing model (verified against fal.ai model pages, 2026-08):
    #   flux-2       — $0.012 per megapixel  (FLUX.2 [dev], endpoint fal-ai/flux-2)
    #   flux/dev     — $0.025 per megapixel
    #   flux/schnell — $0.003 per megapixel
    #   flux-pro/*   — flat $0.05 per image
    # fal's page advertises "billed by rounding up to the nearest megapixel",
    # but observed billing contradicts a strict ceil: dark-history-channel ep1
    # recorded 105 frames @ 1344x768 (~1.03 MP) totalling $2.70 (~$0.026 each),
    # i.e. exact-MP pricing. A strict ceil would also quote 1024x1024 (~1.05 MP)
    # at $0.05 — identical to pro — and poison selector cost scoring. We bill
    # exact megapixels at the per-MP rate, rounded UP to the nearest tenth of a
    # cent so estimates stay mildly conservative.
    _FAL_PRICE_PER_MP = {
        "flux-2": 0.012,
        "dev": 0.025,
        "schnell": 0.003,
    }

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        model = inputs.get("model", "flux-pro/v1.1")
        if "pro" in model:
            return 0.05

        width = int(inputs.get("width") or 1024)
        height = int(inputs.get("height") or 1024)
        megapixels = (width * height) / 1_000_000
        if model == "flux-2":
            rate = self._FAL_PRICE_PER_MP["flux-2"]
        elif "dev" in model:
            rate = self._FAL_PRICE_PER_MP["dev"]
        else:
            rate = self._FAL_PRICE_PER_MP["schnell"]
        # Round up to the nearest $0.001 — never under-quote.
        return math.ceil(megapixels * rate * 1000) / 1000

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        api_key = self._get_api_key()
        if not api_key:
            return ToolResult(
                success=False,
                error="No fal.ai API key found. " + self.install_instructions,
            )

        import requests

        start = time.time()
        model = inputs.get("model", "flux-pro/v1.1")
        prompt = inputs["prompt"]
        width = inputs.get("width", 1024)
        height = inputs.get("height", 1024)

        payload: dict[str, Any] = {
            "prompt": prompt,
            "image_size": {"width": width, "height": height},
        }
        if inputs.get("seed") is not None:
            payload["seed"] = inputs["seed"]
        if inputs.get("num_inference_steps"):
            payload["num_inference_steps"] = inputs["num_inference_steps"]
        if inputs.get("guidance_scale"):
            payload["guidance_scale"] = inputs["guidance_scale"]
        if inputs.get("negative_prompt"):
            payload["negative_prompt"] = inputs["negative_prompt"]

        try:
            response = requests.post(
                f"https://fal.run/fal-ai/{model}",
                headers={
                    "Authorization": f"Key {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()

            image_url = data["images"][0]["url"]
            image_response = requests.get(image_url, timeout=60)
            image_response.raise_for_status()

            output_path = Path(inputs.get("output_path", "generated_image.png"))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            raw = image_response.content

            # fal returns JPEG for several endpoints (flux/schnell, flux-pro). Writing those
            # bytes straight to a .png path produces a file whose extension lies about its
            # contents — downstream tools that sniff by extension (ffmpeg's image demuxer,
            # asset_manifest `format`) then fail or mis-report. Transcode to match the suffix.
            suffix = output_path.suffix.lower()
            is_jpeg = raw[:3] == b"\xff\xd8\xff"
            is_png = raw[:8] == b"\x89PNG\r\n\x1a\n"
            if (suffix == ".png" and not is_png) or (suffix in (".jpg", ".jpeg") and not is_jpeg):
                try:
                    import io

                    from PIL import Image as _PILImage

                    with _PILImage.open(io.BytesIO(raw)) as _im:
                        _im = _im.convert("RGB")
                        _im.save(output_path, "PNG" if suffix == ".png" else "JPEG")
                except Exception:
                    # Pillow unavailable or transcode failed — keep the original bytes rather
                    # than losing the generation, but the mismatch stands.
                    output_path.write_bytes(raw)
            else:
                output_path.write_bytes(raw)

        except Exception as e:
            return ToolResult(success=False, error=f"FLUX generation failed: {e}")

        return ToolResult(
            success=True,
            data={
                "provider": "flux",
                "model": model,
                "prompt": prompt,
                "output": str(output_path),
                "seed": data.get("seed"),
            },
            artifacts=[str(output_path)],
            cost_usd=self.estimate_cost(inputs),
            duration_seconds=round(time.time() - start, 2),
            seed=data.get("seed"),
            model=f"fal-ai/{model}",
        )
