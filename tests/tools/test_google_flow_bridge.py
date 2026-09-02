"""Tests for Google Flow Bridge (export & sequence-safe ingestion)."""

import csv
import json
import os
import time
from pathlib import Path
from PIL import Image
import pytest

from schemas.artifacts import validate_artifact
from tools.graphics.google_flow_bridge import GoogleFlowBridge
from tools.tool_registry import ToolRegistry


@pytest.fixture
def mock_project(tmp_path: Path):
    """Setup a mock project directory structure with scene_plan."""
    project_id = "test-flow-project"
    project_dir = tmp_path / project_id
    project_dir.mkdir(parents=True)
    artifacts_dir = project_dir / "artifacts"
    artifacts_dir.mkdir()

    scene_plan = {
        "version": "1.0",
        "style_playbook": "clean-professional",
        "scenes": [
            {
                "id": "scene-1",
                "type": "broll",
                "description": "Astronaut standing on a red planet looking at horizon",
                "start_seconds": 0.0,
                "end_seconds": 5.0,
                "shot_language": {
                    "shot_size": "extreme_wide",
                    "depth_of_field": "shallow",
                    "lighting_key": "golden_hour",
                    "lens_mm": 24,
                },
                "texture_keywords": ["cinematic dust", "sharp reflections"],
            },
            {
                "id": "scene-2",
                "type": "generated",
                "description": "Futuristic control center with holographic data charts",
                "start_seconds": 5.0,
                "end_seconds": 10.0,
                "shot_language": {
                    "shot_size": "close_up",
                    "lighting_key": "neon",
                    "lens_mm": 50,
                },
                "texture_keywords": ["clean glass", "glowing interfaces"],
            },
            {
                "id": "scene-trans",
                "type": "transition",
                "description": "Cross fade to black",
                "start_seconds": 10.0,
                "end_seconds": 10.5,
            },
        ],
    }
    (artifacts_dir / "scene_plan.json").write_text(json.dumps(scene_plan, indent=2), encoding="utf-8")
    return project_dir, project_id, tmp_path


def test_registry_discovery():
    reg = ToolRegistry()
    reg.discover()
    tool = reg.get("google_flow_bridge")
    assert tool is not None
    assert tool.name == "google_flow_bridge"
    assert tool.capability == "google_flow_bridge"
    assert tool.runtime == "local"


def test_export_prompts_playbook_mode(mock_project):
    """scene_plan declares style_playbook 'clean-professional' -> playbook mode:
    the playbook's image_prompt_prefix style block is appended verbatim and no
    cinematic slash commands / --ar tags are emitted."""
    project_dir, project_id, projects_root = mock_project
    bridge = GoogleFlowBridge()

    result = bridge.execute({
        "operation": "export",
        "project_id": project_id,
        "projects_root": str(projects_root),
        "aspect_ratio": "16:9",
    })

    assert result.success is True
    data = result.data
    assert data["scene_count"] == 2  # scene-trans skipped as transition
    assert data["style_playbook"] == "clean-professional"
    assert data["prompt_modes"] == ["playbook"]

    export_dir = project_dir / "exports" / "google_flow"
    assert export_dir.is_dir()

    # Verify prompts.md
    md_file = export_dir / "prompts.md"
    assert md_file.is_file()
    md_text = md_file.read_text(encoding="utf-8")
    assert "Scene [01] `scene-1`" in md_text
    assert "Scene [02] `scene-2`" in md_text
    assert "Style mode: playbook" in md_text
    assert "clean professional flat illustration" in md_text
    assert "/bokeh" not in md_text
    assert "--ar 16:9" not in md_text
    assert "01_scene-1.png" in md_text
    assert "02_scene-2.png" in md_text

    # Verify queue.csv
    csv_file = export_dir / "queue.csv"
    assert csv_file.is_file()
    with open(csv_file, encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 2
        assert reader[0]["index"] == "1"
        assert reader[0]["scene_id"] == "scene-1"
        assert reader[0]["target_filename"] == "01_scene-1.png"
        assert reader[0]["prompt_mode"] == "playbook"
        assert "clean professional flat illustration" in reader[0]["prompt"]
        assert "/bokeh" not in reader[0]["prompt"]
        assert reader[1]["index"] == "2"
        assert reader[1]["scene_id"] == "scene-2"

    # Verify queue.json
    json_file = export_dir / "queue.json"
    assert json_file.is_file()
    json_data = json.loads(json_file.read_text(encoding="utf-8"))
    assert len(json_data) == 2
    assert all(rec["prompt_mode"] == "playbook" for rec in json_data)

    # Verify drop_images README
    drop_readme = project_dir / "drop_images" / "README.md"
    assert drop_readme.is_file()


def test_export_prompts_cinematic_mode(mock_project):
    """No style playbook anywhere -> legacy cinematic slash-command prompts."""
    project_dir, project_id, projects_root = mock_project
    # Strip the declared playbook so nothing resolves to playbook mode
    sp_path = project_dir / "artifacts" / "scene_plan.json"
    scene_plan = json.loads(sp_path.read_text(encoding="utf-8"))
    del scene_plan["style_playbook"]
    sp_path.write_text(json.dumps(scene_plan, indent=2), encoding="utf-8")

    bridge = GoogleFlowBridge()
    result = bridge.execute({
        "operation": "export",
        "project_id": project_id,
        "projects_root": str(projects_root),
        "aspect_ratio": "16:9",
    })

    assert result.success is True
    assert result.data["prompt_modes"] == ["cinematic"]

    md_text = (project_dir / "exports" / "google_flow" / "prompts.md").read_text(encoding="utf-8")
    assert "Style mode: cinematic" in md_text
    assert "/bokeh" in md_text
    assert "/golden_hour" in md_text
    assert "/neon" in md_text
    assert "--ar 16:9" in md_text


def test_export_prompts_verbatim_generate_prompts(mock_project):
    """Scenes authored with 'GENERATE: ' full prompts are forwarded untouched."""
    project_dir, project_id, projects_root = mock_project
    sp_path = project_dir / "artifacts" / "scene_plan.json"
    scene_plan = json.loads(sp_path.read_text(encoding="utf-8"))
    ink_prompt = (
        "Pen-and-ink illustration with soft gray brush washes on warm white paper: "
        "A radium dial glows in a dark factory. Historical narrative illustration in "
        "black-and-white pen-and-ink with soft gray brush washes on warm white paper. "
        "No text or numbers anywhere. Full-bleed image, no border, no plate frame, no label."
    )
    scene_plan["scenes"][0]["required_assets"] = [
        {"type": "image", "description": f"GENERATE: {ink_prompt}", "source": "generate"}
    ]
    sp_path.write_text(json.dumps(scene_plan, indent=2), encoding="utf-8")

    bridge = GoogleFlowBridge()
    result = bridge.execute({
        "operation": "export",
        "project_id": project_id,
        "projects_root": str(projects_root),
        "aspect_ratio": "16:9",
    })

    assert result.success is True
    assert result.data["prompt_modes"] == ["playbook", "verbatim"]  # sorted; scene-1 verbatim, scene-2 playbook

    json_data = json.loads(
        (project_dir / "exports" / "google_flow" / "queue.json").read_text(encoding="utf-8")
    )
    assert json_data[0]["prompt_mode"] == "verbatim"
    assert json_data[0]["prompt"] == ink_prompt
    assert "/bokeh" not in json_data[0]["prompt"]
    assert "--ar" not in json_data[0]["prompt"]


def test_export_prompts_explicit_style_context_wins(mock_project):
    """An explicit style_context overrides the scene_plan's declared playbook."""
    project_dir, project_id, projects_root = mock_project
    bridge = GoogleFlowBridge()
    result = bridge.execute({
        "operation": "export",
        "project_id": project_id,
        "projects_root": str(projects_root),
        "aspect_ratio": "16:9",
        "style_context": {
            "image_prompt_prefix": "CUSTOM STYLE BLOCK",
            "prompt_guard": "GUARD SENTENCE.",
        },
    })

    assert result.success is True
    assert result.data["style_playbook"] == "clean-professional"  # reported, but not applied
    json_data = json.loads(
        (project_dir / "exports" / "google_flow" / "queue.json").read_text(encoding="utf-8")
    )
    assert "CUSTOM STYLE BLOCK" in json_data[0]["prompt"]
    assert "GUARD SENTENCE." in json_data[0]["prompt"]
    assert "clean professional flat illustration" not in json_data[0]["prompt"]


def test_export_prompts_unknown_playbook_fails_loudly(mock_project):
    project_dir, project_id, projects_root = mock_project
    bridge = GoogleFlowBridge()
    result = bridge.execute({
        "operation": "export",
        "project_id": project_id,
        "projects_root": str(projects_root),
        "style_playbook": "no-such-playbook-xyz",
    })
    assert result.success is False
    assert "no-such-playbook-xyz" in (result.error or "")


def test_ingest_images_by_name_prefix(mock_project):
    project_dir, project_id, projects_root = mock_project
    bridge = GoogleFlowBridge()

    # First export prompts
    bridge.execute({
        "operation": "export",
        "project_id": project_id,
        "projects_root": str(projects_root),
    })

    drop_dir = project_dir / "drop_images"

    # Create 2 mock downloaded images with index prefixes
    im1 = Image.new("RGB", (1920, 1080), color=(255, 0, 0))
    im1.save(drop_dir / "01_arbitrary_download_name.png")

    im2 = Image.new("RGB", (1920, 1080), color=(0, 255, 0))
    im2.save(drop_dir / "02_other_flow_take.jpg")

    # Ingest
    result = bridge.execute({
        "operation": "ingest",
        "project_id": project_id,
        "projects_root": str(projects_root),
    })

    assert result.success is True
    assert result.data["ingested_count"] == 2

    # Check images exist in assets/images/
    img1_dest = project_dir / "assets" / "images" / "scene-1.png"
    img2_dest = project_dir / "assets" / "images" / "scene-2.png"
    assert img1_dest.is_file()
    assert img2_dest.is_file()

    # Check previews exist in assets/_preview/
    prev1 = project_dir / "assets" / "_preview" / "scene-1.jpg"
    prev2 = project_dir / "assets" / "_preview" / "scene-2.jpg"
    assert prev1.is_file()
    assert prev2.is_file()

    # Verify preview image dimensions (width should be 480)
    with Image.open(prev1) as prev_im:
        assert prev_im.size[0] == 480

    # Check canonical asset_manifest.json
    manifest_path = project_dir / "artifacts" / "asset_manifest.json"
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Schema validation against official schema!
    validate_artifact("asset_manifest", manifest)

    assert len(manifest["assets"]) == 2
    assert manifest["assets"][0]["id"] == "img-scene-1"
    assert manifest["assets"][0]["path"] == "assets/images/scene-1.png"
    assert manifest["assets"][0]["source_tool"] == "google_flow"
    assert manifest["assets"][0]["provider"] == "google_flow"
    assert manifest["assets"][0]["scene_id"] == "scene-1"
    assert manifest["assets"][0]["cost_usd"] == 0.0

    assert manifest["assets"][1]["id"] == "img-scene-2"
    assert manifest["assets"][1]["path"] == "assets/images/scene-2.png"
    assert manifest["assets"][1]["scene_id"] == "scene-2"


def test_ingest_images_by_timestamp(mock_project):
    project_dir, project_id, projects_root = mock_project
    bridge = GoogleFlowBridge()

    drop_dir = project_dir / "drop_images"
    drop_dir.mkdir(parents=True, exist_ok=True)

    # Create images with arbitrary hash names and distinct timestamps
    file_a = drop_dir / "flow_hash_xyz.png"
    file_b = drop_dir / "flow_hash_abc.png"

    Image.new("RGB", (1280, 720), color=(10, 20, 30)).save(file_a)
    time.sleep(0.05)
    Image.new("RGB", (1280, 720), color=(40, 50, 60)).save(file_b)

    # Ingest using timestamp strategy
    result = bridge.execute({
        "operation": "ingest",
        "project_id": project_id,
        "projects_root": str(projects_root),
        "auto_sort_strategy": "timestamp",
    })

    assert result.success is True
    assert result.data["ingested_count"] == 2
    # First created file (file_a) should map to scene-1
    assert result.data["summary"][0]["source_file"] == "flow_hash_xyz.png"
    assert result.data["summary"][0]["scene_id"] == "scene-1"
    assert result.data["summary"][1]["source_file"] == "flow_hash_abc.png"
    assert result.data["summary"][1]["scene_id"] == "scene-2"


def test_ingest_insufficient_images(mock_project):
    project_dir, project_id, projects_root = mock_project
    bridge = GoogleFlowBridge()

    drop_dir = project_dir / "drop_images"
    drop_dir.mkdir(parents=True, exist_ok=True)

    # Only 1 image provided when 2 visual scenes are required
    Image.new("RGB", (100, 100)).save(drop_dir / "only_one.png")

    result = bridge.execute({
        "operation": "ingest",
        "project_id": project_id,
        "projects_root": str(projects_root),
    })

    assert result.success is False
    assert "requires 2 visual scenes" in result.error


def test_cli_export_and_ingest(mock_project):
    import subprocess
    import sys

    project_dir, project_id, projects_root = mock_project

    # Run CLI export
    cmd_export = [
        sys.executable,
        "-m",
        "tools.graphics.google_flow_bridge",
        "export",
        project_id,
        "--projects-root",
        str(projects_root),
        "--aspect-ratio",
        "16:9",
    ]
    res_exp = subprocess.run(cmd_export, capture_output=True, text=True)
    assert res_exp.returncode == 0
    assert "SUCCESS" in res_exp.stdout
    assert (project_dir / "exports" / "google_flow" / "prompts.md").is_file()

    # Drop 2 images
    drop_dir = project_dir / "drop_images"
    Image.new("RGB", (640, 360)).save(drop_dir / "01_scene-1.png")
    Image.new("RGB", (640, 360)).save(drop_dir / "02_scene-2.png")

    # Run CLI ingest
    cmd_ingest = [
        sys.executable,
        "-m",
        "tools.graphics.google_flow_bridge",
        "ingest",
        project_id,
        "--projects-root",
        str(projects_root),
    ]
    res_ing = subprocess.run(cmd_ingest, capture_output=True, text=True)
    assert res_ing.returncode == 0
    assert "SUCCESS" in res_ing.stdout
    assert (project_dir / "artifacts" / "asset_manifest.json").is_file()


def test_ingest_images_by_keyword_match(mock_project):
    project_dir, project_id, projects_root = mock_project
    bridge = GoogleFlowBridge()

    drop_dir = project_dir / "drop_images"
    drop_dir.mkdir(parents=True, exist_ok=True)

    # Image names generated by Google Flow based on prompt keywords without numeric index
    # Note: intentionally create them in reverse time order to verify keyword matching beats timestamp
    file_ctrl = drop_dir / "Futuristic_control_center_holographic_data_20260902.jpeg"
    Image.new("RGB", (640, 360), color=(1, 2, 3)).save(file_ctrl)
    time.sleep(0.05)
    file_astro = drop_dir / "Astronaut_standing_on_red_planet_horizon_20260902.jpeg"
    Image.new("RGB", (640, 360), color=(4, 5, 6)).save(file_astro)

    result = bridge.execute({
        "operation": "ingest",
        "project_id": project_id,
        "projects_root": str(projects_root),
        "auto_sort_strategy": "auto",
    })

    assert result.success is True
    assert result.data["ingested_count"] == 2
    # Astronaut should map to scene-1 despite being created later
    assert result.data["summary"][0]["scene_id"] == "scene-1"
    assert "Astronaut" in result.data["summary"][0]["source_file"]
    # Control center should map to scene-2
    assert result.data["summary"][1]["scene_id"] == "scene-2"
    assert "control_center" in result.data["summary"][1]["source_file"]


