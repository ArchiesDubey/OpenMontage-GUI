"""Google Flow Bridge — prompt export and sequence-safe image ingestion tool.

Bridges OpenMontage with Google Flow (flow.google), Google's creative studio workspace
powered by Nano Banana and Veo 3.1.

Capabilities:
1. Export: Converts scene_plan visual scenes into Google Flow formatted prompts
   (including slash commands like /bokeh, /volumetric_lighting, aspect ratio tags,
   and character anchors), generating:
     - exports/google_flow/prompts.md (human checklist and copyable cards)
     - exports/google_flow/queue.csv (prompt queue for extensions like Image Flow / Autoflow)
     - exports/google_flow/queue.json (structured prompt data)
2. Ingest: Discovers downloaded images from a drop folder or downloads directory,
   maps them in exact sequence order to the scenes, validates aspect ratios and resolution,
   copies them to assets/images/scene_<id>.png, generates 480px previews for the Backlot
   filmstrip, and emits a schema-valid asset_manifest.json.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Optional

from PIL import Image

from lib.shot_prompt_builder import (
    build_batch_google_flow_prompts,
    build_google_flow_prompt,
)
from schemas.artifacts import validate_artifact
from styles.playbook_loader import load_playbook
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


class GoogleFlowBridge(BaseTool):
    name = "google_flow_bridge"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "google_flow_bridge"
    provider = "google_flow"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.LOCAL

    dependencies = []
    install_instructions = (
        "No API key required. Generates export packages for Google Flow (flow.google) "
        "and ingests downloaded assets safely into OpenMontage projects."
    )
    agent_skills = ["visual-style"]

    capabilities = [
        "export_google_flow_prompts",
        "ingest_google_flow_images",
    ]
    supports = {
        "export_markdown": True,
        "export_csv_queue": True,
        "sequence_matching_by_name": True,
        "sequence_matching_by_timestamp": True,
        "backlot_preview_generation": True,
        "free": True,
        "offline_local": True,
    }
    best_for = [
        "exporting prompts formatted for Google Flow (flow.google / Nano Banana / Veo)",
        "generating prompt queues for Google Flow browser extensions (Image Flow, Autoflow)",
        "sequence-safe ingestion of downloaded images without naming errors",
        "zero-cost human-in-the-loop image generation",
    ]
    not_good_for = [
        "fully headless generation without user or browser involvement",
        "real-time instant single-frame generation (use flux_image or google_imagen)",
    ]

    input_schema = {
        "type": "object",
        "required": ["project_id"],
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["export", "ingest"],
                "default": "export",
                "description": "'export' to generate prompt files, 'ingest' to process downloaded images",
            },
            "project_id": {
                "type": "string",
                "description": "The target project identifier (e.g. 'hidden-math-of-nature')",
            },
            "projects_root": {
                "type": "string",
                "description": "Optional override for projects root directory",
            },
            "source_dir": {
                "type": "string",
                "description": "Directory containing downloaded images for ingestion. Defaults to projects/<project_id>/drop_images",
            },
            "aspect_ratio": {
                "type": "string",
                "default": "16:9",
                "description": "Target aspect ratio for prompts and validation ('16:9', '9:16', '1:1', etc.)",
            },
            "auto_sort_strategy": {
                "type": "string",
                "enum": ["auto", "name", "timestamp"],
                "default": "auto",
                "description": "Strategy to order downloaded images: 'name' (index prefixes), 'timestamp' (download time), or 'auto'",
            },
            "scene_plan": {
                "type": "object",
                "description": "Optional scene_plan artifact. If omitted, loaded from artifacts/scene_plan.json",
            },
            "style_context": {
                "type": "object",
                "description": (
                    "Optional style context. Keys honored: 'image_prompt_prefix' "
                    "(playbook style block appended verbatim after each scene; switches "
                    "export to playbook mode with no cinematic slash commands), "
                    "'image_prompt_suffix', 'prompt_guard', 'visual_language', 'mood'"
                ),
            },
            "style_playbook": {
                "type": "string",
                "description": (
                    "Optional playbook name (e.g. 'ink-testimony'). Loads "
                    "styles/<name>.yaml and derives the style context from its "
                    "asset_generation.image_prompt_prefix. Defaults to the scene_plan's "
                    "'style_playbook' field. Explicit style_context wins."
                ),
            },
            "character_anchors": {
                "type": "object",
                "description": "Optional mapping of character names to Google Flow @Anchor tags",
            },
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=256, vram_mb=0, disk_mb=50, network_required=False
    )
    retry_policy = RetryPolicy(max_retries=1, retryable_errors=[])
    idempotency_key_fields = ["project_id", "operation"]
    side_effects = [
        "writes prompt files to exports/google_flow/",
        "copies normalized images to assets/images/",
        "writes preview images to assets/_preview/",
        "writes artifacts/asset_manifest.json",
    ]
    user_visible_verification = [
        "Inspect exported prompts in exports/google_flow/prompts.md",
        "Inspect filmstrip preview thumbnails in Backlot board",
    ]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        project_id = inputs.get("project_id")
        if not project_id:
            return ToolResult(success=False, error="project_id is required")

        operation = inputs.get("operation", "export")
        projects_root = Path(inputs["projects_root"]) if inputs.get("projects_root") else _PROJECT_ROOT / "projects"
        project_dir = projects_root / project_id

        if not project_dir.is_dir():
            return ToolResult(
                success=False,
                error=f"Project directory not found at: {project_dir}",
            )

        if operation == "export":
            return self._export_prompts(project_dir, project_id, inputs)
        elif operation == "ingest":
            return self._ingest_images(project_dir, project_id, inputs)
        else:
            return ToolResult(
                success=False,
                error=f"Unsupported operation '{operation}'. Must be 'export' or 'ingest'.",
            )

    # -------------------------------------------------------------------------
    # EXPORT LOGIC
    # -------------------------------------------------------------------------

    def _export_prompts(
        self, project_dir: Path, project_id: str, inputs: dict[str, Any]
    ) -> ToolResult:
        scene_plan = inputs.get("scene_plan")
        if not scene_plan:
            sp_path = project_dir / "artifacts" / "scene_plan.json"
            if not sp_path.is_file():
                return ToolResult(
                    success=False,
                    error=f"scene_plan artifact not found at {sp_path}. Complete scene_plan stage first.",
                )
            try:
                with open(sp_path, encoding="utf-8") as f:
                    scene_plan = json.load(f)
            except Exception as e:
                return ToolResult(success=False, error=f"Failed to read scene_plan.json: {e}")

        scenes = scene_plan.get("scenes", [])
        if not scenes:
            return ToolResult(success=False, error="scene_plan contains no scenes")

        aspect_ratio = inputs.get("aspect_ratio", "16:9")
        style_context = inputs.get("style_context")
        character_anchors = inputs.get("character_anchors")

        # Resolve the style contract for this project. Priority:
        #   explicit style_context (agent-provided) > style_playbook input >
        #   scene_plan['style_playbook'] > cinematic mode (no style context).
        style_playbook_name = inputs.get("style_playbook")
        if not style_playbook_name:
            sp_playbook = scene_plan.get("style_playbook")
            if isinstance(sp_playbook, str) and sp_playbook:
                style_playbook_name = sp_playbook
        if style_playbook_name and not (style_context or {}).get("image_prompt_prefix"):
            try:
                playbook = load_playbook(style_playbook_name)
            except FileNotFoundError as e:
                return ToolResult(
                    success=False,
                    error=(
                        f"style_playbook {style_playbook_name!r} could not be loaded: {e}. "
                        "Fix the name, or pass an explicit style_context."
                    ),
                )
            prefix = (playbook.get("asset_generation") or {}).get("image_prompt_prefix")
            if prefix:
                style_context = {"image_prompt_prefix": prefix, "playbook": style_playbook_name,
                                 **(style_context or {})}

        # Compile Google Flow prompt records
        batch_records = build_batch_google_flow_prompts(
            scenes=scenes,
            style_context=style_context,
            aspect_ratio=aspect_ratio,
            character_anchors=character_anchors,
        )

        if not batch_records:
            return ToolResult(
                success=False,
                error="No visual scenes requiring image generation found in scene_plan",
            )

        # Setup export directory
        export_dir = project_dir / "exports" / "google_flow"
        export_dir.mkdir(parents=True, exist_ok=True)

        # Ensure drop folder exists with instructions
        drop_dir = project_dir / "drop_images"
        drop_dir.mkdir(parents=True, exist_ok=True)
        readme_drop = drop_dir / "README.md"
        if not readme_drop.exists():
            readme_drop.write_text(
                "# Google Flow Download Drop Zone\n\n"
                "Images land here automatically when you run the Google Flow Driver:\n\n"
                f"`python -m tools.graphics.google_flow_driver run {project_id}`\n\n"
                "(It drives flow.google in your own Chrome: submits each queued prompt, "
                "waits for the render, saves the 2K image under the correct filename, "
                "and handles rate limits with jitter + backoff. Re-running resumes where "
                "it left off.)\n\n"
                "If you prefer generating by hand, drop the downloaded images here instead.\n"
                "Files can be named:\n"
                "- With sequence prefix: e.g. `01_scene-1.png`, `02_scene-2.png`, or `01.png`\n"
                "- Or left as downloaded in batch order (the ingestion tool will sequence them by download timestamp)\n\n"
                "Once images are here, run:\n"
                f"`python -m tools.graphics.google_flow_bridge ingest {project_id}`\n",
                encoding="utf-8",
            )

        # 1. Write prompts.md
        md_path = export_dir / "prompts.md"
        md_content = self._render_prompts_markdown(project_id, batch_records, aspect_ratio)
        md_path.write_text(md_content, encoding="utf-8")

        # 2. Write queue.csv (for browser extension prompt queues)
        csv_path = export_dir / "queue.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["index", "scene_id", "target_filename", "prompt", "prompt_mode",
                            "aspect_ratio", "description"],
            )
            writer.writeheader()
            for rec in batch_records:
                writer.writerow({
                    "index": rec["index"],
                    "scene_id": rec["scene_id"],
                    "target_filename": rec["target_filename"],
                    "prompt": rec["prompt"],
                    "prompt_mode": rec.get("prompt_mode", "cinematic"),
                    "aspect_ratio": aspect_ratio,
                    "description": rec.get("description", ""),
                })

        # 3. Write queue.json
        json_path = export_dir / "queue.json"
        json_path.write_text(json.dumps(batch_records, indent=2), encoding="utf-8")

        return ToolResult(
            success=True,
            data={
                "project_id": project_id,
                "scene_count": len(batch_records),
                "style_playbook": style_playbook_name,
                "prompt_modes": sorted({r.get("prompt_mode", "cinematic") for r in batch_records}),
                "export_dir": str(export_dir.relative_to(project_dir)),
                "markdown_file": str(md_path.relative_to(project_dir)),
                "csv_queue_file": str(csv_path.relative_to(project_dir)),
                "json_queue_file": str(json_path.relative_to(project_dir)),
                "drop_dir": str(drop_dir.relative_to(project_dir)),
                "instructions": (
                    f"Generated {len(batch_records)} Google Flow prompts. "
                    f"Review prompts in '{md_path.relative_to(project_dir)}' or load '{csv_path.relative_to(project_dir)}' "
                    f"in flow.google. Run `python -m tools.graphics.google_flow_driver run {project_id}` "
                    f"to generate and auto-download the images (or generate by hand and drop them into "
                    f"'{drop_dir.relative_to(project_dir)}'), then call ingest."
                ),
            },
        )

    def _render_prompts_markdown(
        self, project_id: str, records: list[dict[str, Any]], aspect_ratio: str
    ) -> str:
        modes = sorted({rec.get("prompt_mode", "cinematic") for rec in records})
        if modes == ["cinematic"]:
            style_note = (
                "> **Style mode: cinematic** — prompts carry Flow slash commands and an "
                f"`--ar {aspect_ratio}` tag."
            )
        else:
            style_note = (
                f"> **Style mode: {'/'.join(modes)}** — prompts follow the project's playbook "
                "style contract verbatim (medium-first ordering, full-bleed guard). Do NOT "
                "append cinematic slash commands or --ar tags; the driver sets the aspect "
                "ratio in Flow's settings panel."
            )
        lines = [
            f"# Google Flow Image Generation Prompts — `{project_id}`",
            "",
            "> **Instructions:**",
            "> 1. Open [flow.google](https://flow.google).",
            f"> 2. Ensure project aspect ratio is set to **{aspect_ratio}**.",
            "> 3. Paste each prompt below into Google Flow (or load `queue.csv` with a batch queue extension).",
            "> 4. Download the generated images.",
            f"> 5. Save/move the downloaded images into `projects/{project_id}/drop_images/`.",
            f"> 6. Run ingestion: `python -m tools.graphics.google_flow_bridge ingest {project_id}`.",
            "",
            style_note,
            "> Prefer the automated driver: `python -m tools.graphics.google_flow_driver run "
            f"{project_id}` (see `skills/core/google-flow.md`).",
            "",
            "---",
            "",
            "## Scene Prompts Checklist",
            "",
        ]

        for rec in records:
            idx = rec["index"]
            scene_id = rec["scene_id"]
            filename = rec["target_filename"]
            desc = rec.get("description", "")
            prompt = rec["prompt"]
            t_in = rec.get("start_seconds", 0.0)
            t_out = rec.get("end_seconds", 0.0)

            lines.append(f"### Scene [{idx:02d}] `{scene_id}` ({t_in:.1f}s – {t_out:.1f}s)")
            if desc:
                lines.append(f"**Description:** {desc}")
            lines.append(f"**Target Filename:** `{filename}`")
            lines.append("")
            lines.append("```text")
            lines.append(prompt)
            lines.append("```")
            lines.append(f"- [ ] Downloaded as `{filename}`")
            lines.append("")

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # INGESTION LOGIC
    # -------------------------------------------------------------------------

    def _ingest_images(
        self, project_dir: Path, project_id: str, inputs: dict[str, Any]
    ) -> ToolResult:
        # 1. Locate scene_plan
        scene_plan = inputs.get("scene_plan")
        if not scene_plan:
            sp_path = project_dir / "artifacts" / "scene_plan.json"
            if not sp_path.is_file():
                return ToolResult(
                    success=False,
                    error=f"scene_plan artifact not found at {sp_path}",
                )
            try:
                with open(sp_path, encoding="utf-8") as f:
                    scene_plan = json.load(f)
            except Exception as e:
                return ToolResult(success=False, error=f"Failed to read scene_plan.json: {e}")

        # Filter visual scenes that need images
        scenes = [
            s for s in scene_plan.get("scenes", [])
            if s.get("type") != "transition"
        ]
        if not scenes:
            return ToolResult(success=False, error="No visual scenes found in scene_plan")

        # 2. Determine source directory
        source_dir_arg = inputs.get("source_dir")
        if source_dir_arg:
            source_dir = Path(source_dir_arg).expanduser().resolve()
        else:
            source_dir = project_dir / "drop_images"
            if not source_dir.is_dir() or not any(self._is_image_file(f) for f in source_dir.iterdir()):
                alt_dir = project_dir / "assets" / "incoming"
                if alt_dir.is_dir() and any(self._is_image_file(f) for f in alt_dir.iterdir()):
                    source_dir = alt_dir

        if not source_dir.is_dir():
            return ToolResult(
                success=False,
                error=f"Image source directory not found: {source_dir}. Create it and place images there.",
            )

        # 3. Discover image files
        raw_files = [f for f in source_dir.iterdir() if f.is_file() and self._is_image_file(f)]
        if not raw_files:
            return ToolResult(
                success=False,
                error=f"No image files (.png, .jpg, .jpeg, .webp) found in {source_dir}",
            )

        # 4. Load existing prompt mappings if queue.json exists
        queue_json_path = project_dir / "exports" / "google_flow" / "queue.json"
        prompt_lookup: dict[str, str] = {}
        if queue_json_path.is_file():
            try:
                qdata = json.loads(queue_json_path.read_text(encoding="utf-8"))
                for qitem in qdata:
                    prompt_lookup[qitem["scene_id"]] = qitem.get("prompt", "")
            except Exception:
                pass

        # 5. Sort and sequence image files
        strategy = inputs.get("auto_sort_strategy", "auto")
        ordered_files = self._order_image_files(
            raw_files, len(scenes), strategy, scenes=scenes, prompt_lookup=prompt_lookup
        )

        if len(ordered_files) < len(scenes):
            return ToolResult(
                success=False,
                error=(
                    f"Found {len(ordered_files)} images in '{source_dir}', but scene_plan requires "
                    f"{len(scenes)} visual scenes. Provide all {len(scenes)} images before ingesting."
                ),
            )

        # 6. Prepare destination folders
        images_dir = project_dir / "assets" / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        preview_dir = project_dir / "assets" / "_preview"
        preview_dir.mkdir(parents=True, exist_ok=True)

        # 7. Process each image, copy & create thumbnails
        manifest_assets = []
        ingested_summary = []

        for idx, (scene, img_file) in enumerate(zip(scenes, ordered_files), start=1):
            scene_id = scene.get("id", f"scene-{idx}")
            dest_filename = f"{scene_id}.png"
            dest_path = images_dir / dest_filename
            rel_asset_path = f"assets/images/{dest_filename}"

            try:
                with Image.open(img_file) as im:
                    width, height = im.size
                    # Convert to RGB if needed (e.g. RGBA or palette) and save as standard PNG
                    if im.format != "PNG" or im.mode not in ("RGB", "RGBA"):
                        im_converted = im.convert("RGB")
                        im_converted.save(dest_path, format="PNG")
                    else:
                        shutil.copy2(img_file, dest_path)

                    # Generate 480px preview thumbnail for Backlot
                    preview_thumb_path = preview_dir / f"{scene_id}.jpg"
                    im_thumb = im.convert("RGB")
                    # Calculate thumbnail height maintaining aspect ratio
                    thumb_w = 480
                    thumb_h = max(1, int(thumb_w * height / width))
                    im_thumb = im_thumb.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                    im_thumb.save(preview_thumb_path, format="JPEG", quality=85)

            except Exception as e:
                return ToolResult(
                    success=False,
                    error=f"Error reading/processing image {img_file.name}: {e}",
                )

            prompt_text = prompt_lookup.get(scene_id) or scene.get("description", "")
            asset_entry = {
                "id": f"img-{scene_id}",
                "type": "image",
                "path": rel_asset_path,
                "source_tool": "google_flow",
                "provider": "google_flow",
                "scene_id": scene_id,
                "prompt": prompt_text,
                "cost_usd": 0.0,
                "resolution": f"{width}x{height}",
                "format": "png",
                "quality_score": 1.0,
                "subtype": "generated",
                "generation_summary": f"Generated via Google Flow and ingested from {img_file.name}",
            }
            manifest_assets.append(asset_entry)
            ingested_summary.append({
                "index": idx,
                "scene_id": scene_id,
                "source_file": img_file.name,
                "dest_file": dest_filename,
                "resolution": f"{width}x{height}",
            })

        # 7. Merge or write canonical asset_manifest.json
        artifacts_dir = project_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = artifacts_dir / "asset_manifest.json"

        # Check if existing manifest exists (preserve non-image assets like narration/music)
        merged_assets = []
        if manifest_path.is_file():
            try:
                existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                for a in existing_manifest.get("assets", []):
                    # Keep non-image assets or assets from other scenes
                    if a.get("type") not in ("image", "diagram", "animation"):
                        merged_assets.append(a)
            except Exception:
                pass

        merged_assets.extend(manifest_assets)

        manifest_data = {
            "version": "1.0",
            "assets": merged_assets,
            "total_cost_usd": sum(a.get("cost_usd", 0.0) for a in merged_assets),
            "metadata": {
                "project_id": project_id,
                "ingest_timestamp": time.time(),
                "provider": "google_flow",
                "ingested_count": len(manifest_assets),
            },
        }

        # Validate against official artifact schema
        try:
            validate_artifact("asset_manifest", manifest_data)
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Constructed asset_manifest failed schema validation: {e}",
            )

        # Write canonical artifact
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        return ToolResult(
            success=True,
            data={
                "project_id": project_id,
                "ingested_count": len(manifest_assets),
                "total_manifest_assets": len(merged_assets),
                "asset_manifest_path": str(manifest_path.relative_to(project_dir)),
                "summary": ingested_summary,
                "message": (
                    f"Successfully ingested {len(manifest_assets)} images in sequence from {source_dir}. "
                    f"Asset manifest validated and written to {manifest_path.relative_to(project_dir)}."
                ),
            },
        )

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    @staticmethod
    def _is_image_file(path: Path) -> bool:
        return path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}

    @classmethod
    def _order_image_files(
        cls,
        files: list[Path],
        expected_count: int,
        strategy: str = "auto",
        scenes: Optional[list[dict[str, Any]]] = None,
        prompt_lookup: Optional[dict[str, str]] = None,
    ) -> list[Path]:
        """Order image files by index in filename, prompt keyword match, or download timestamp."""
        if strategy == "name":
            return cls._sort_by_name_index(files)
        elif strategy == "timestamp":
            return sorted(files, key=lambda f: f.stat().st_mtime)

        # 'auto' strategy:
        # 1. Check if files have index prefixes ("01_...", "scene_1", etc.)
        has_indices = sum(1 for f in files if cls._extract_leading_number(f.name) is not None)
        if has_indices >= max(1, len(files) // 2):
            return cls._sort_by_name_index(files)

        # 2. Check if filenames match scene descriptions / prompt keywords
        if scenes:
            matched = cls._match_by_keywords(files, scenes, prompt_lookup or {})
            if matched is not None:
                return matched

        # 3. Fall back to creation / modification timestamp order
        return sorted(files, key=lambda f: f.stat().st_mtime)

    @staticmethod
    def _match_by_keywords(
        files: list[Path],
        scenes: list[dict[str, Any]],
        prompt_lookup: dict[str, str],
    ) -> Optional[list[Path]]:
        """Match files to scenes based on keyword overlap between filename and prompt/description."""
        if len(files) < len(scenes):
            return None

        stopwords = {
            "the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "for",
            "with", "by", "from", "up", "about", "into", "over", "after", "shot",
            "image", "frame", "view", "2k", "4k", "hd"
        }

        scene_candidates: list[list[tuple[int, Path]]] = []
        for scene in scenes:
            sid = scene.get("id", "")
            desc = scene.get("description", "")
            prompt = prompt_lookup.get(sid, "")
            text = f"{sid} {desc} {prompt}".lower()
            scene_words = {w for w in re.findall(r"[a-z0-9]+", text) if len(w) >= 3 and w not in stopwords}

            file_scores = []
            for f in files:
                f_words = {w for w in re.findall(r"[a-z0-9]+", f.stem.lower()) if len(w) >= 3 and w not in stopwords}
                overlap = len(scene_words & f_words)
                file_scores.append((overlap, f))
            file_scores.sort(key=lambda x: x[0], reverse=True)
            scene_candidates.append(file_scores)

        all_matches = []
        for s_idx, scores in enumerate(scene_candidates):
            for score, f in scores:
                if score >= 2:
                    all_matches.append((score, s_idx, f))

        all_matches.sort(key=lambda x: x[0], reverse=True)

        assigned_files: dict[int, Path] = {}
        used_files: set[Path] = set()

        for score, s_idx, f in all_matches:
            if s_idx not in assigned_files and f not in used_files:
                assigned_files[s_idx] = f
                used_files.add(f)

        if len(assigned_files) == len(scenes):
            return [assigned_files[i] for i in range(len(scenes))]

        return None

    @classmethod
    def _sort_by_name_index(cls, files: list[Path]) -> list[Path]:
        def sort_key(f: Path) -> tuple[int, str]:
            num = cls._extract_leading_number(f.name)
            if num is not None:
                return (num, f.name)
            return (999999, f.name)

        return sorted(files, key=sort_key)

    @staticmethod
    def _extract_leading_number(filename: str) -> Optional[int]:
        # Match "01_...", "1_...", etc. at start of filename (1-3 digits)
        m = re.match(r"^(\d{1,3})[_\-\s]", filename)
        if m:
            return int(m.group(1))
        # Match "scene_1", "scene-01", etc.
        m2 = re.search(r"scene[_\-\s]?(\d{1,3})", filename, re.IGNORECASE)
        if m2:
            return int(m2.group(1))
        # Match trailing index like "shot_1.png", "img - 02.jpg" (max 3 digits, avoids timestamps)
        m3 = re.search(r"[_\-\s](\d{1,3})\.[^.]+$", filename)
        if m3:
            return int(m3.group(1))
        return None


# -----------------------------------------------------------------------------
# CLI ENTRY POINT
# -----------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Google Flow Bridge: export prompts and ingest downloaded images in sequence."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # export command
    exp_parser = subparsers.add_parser("export", help="Export scene prompts for Google Flow")
    exp_parser.add_argument("project_id", help="Project ID (e.g. 'hidden-math-of-nature')")
    exp_parser.add_argument("--aspect-ratio", default="16:9", help="Aspect ratio (default: 16:9)")
    exp_parser.add_argument(
        "--style-playbook", default=None,
        help="Playbook name for the style contract (e.g. 'ink-testimony'); defaults to the scene_plan's style_playbook",
    )
    exp_parser.add_argument("--projects-root", default=None, help="Override projects root")

    # ingest command
    ing_parser = subparsers.add_parser("ingest", help="Ingest downloaded images in correct sequence")
    ing_parser.add_argument("project_id", help="Project ID")
    ing_parser.add_argument("--source", default=None, help="Source folder of downloaded images")
    ing_parser.add_argument(
        "--sort", choices=["auto", "name", "timestamp"], default="auto", help="Ordering strategy"
    )
    ing_parser.add_argument("--projects-root", default=None, help="Override projects root")

    args = parser.parse_args()
    tool = GoogleFlowBridge()

    if args.command == "export":
        res = tool.execute({
            "operation": "export",
            "project_id": args.project_id,
            "aspect_ratio": args.aspect_ratio,
            "projects_root": args.projects_root,
        })
        if res.success:
            print(f"SUCCESS: {res.data.get('instructions')}")
            print(f"Prompts markdown: {res.data.get('markdown_file')}")
            print(f"CSV queue file:   {res.data.get('csv_queue_file')}")
        else:
            print(f"ERROR: {res.error}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "ingest":
        res = tool.execute({
            "operation": "ingest",
            "project_id": args.project_id,
            "source_dir": args.source,
            "auto_sort_strategy": args.sort,
            "projects_root": args.projects_root,
        })
        if res.success:
            print(f"SUCCESS: {res.data.get('message')}")
            for item in res.data.get("summary", []):
                print(f"  [{item['index']:02d}] {item['source_file']} -> {item['dest_file']} ({item['resolution']})")
        else:
            print(f"ERROR: {res.error}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
