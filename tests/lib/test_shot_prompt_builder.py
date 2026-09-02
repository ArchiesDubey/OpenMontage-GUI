"""Tests for the style-aware Google Flow prompt modes in lib/shot_prompt_builder."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.shot_prompt_builder import (  # noqa: E402
    build_google_flow_prompt,
    flow_prompt_mode,
    scene_verbatim_prompt,
)


def _scene(**overrides):
    scene = {
        "id": "scene-1",
        "type": "broll",
        "description": "A radium dial glows on a factory bench",
        "shot_language": {
            "shot_size": "close_up",
            "depth_of_field": "shallow",
            "lighting_key": "golden_hour",
            "lens_mm": 50,
        },
        "texture_keywords": ["fine cross-hatching", "matte paper grain"],
    }
    scene.update(overrides)
    return scene


class TestVerbatimMode:
    def test_generate_prefixed_required_asset_is_forwarded_untouched(self):
        prompt = (
            "Pen-and-ink illustration with soft gray brush washes on warm white paper: "
            "A radium dial glows. INK_STYLE block. No text or numbers anywhere."
        )
        scene = _scene(required_assets=[{"type": "image", "description": f"GENERATE: {prompt}"}])
        assert scene_verbatim_prompt(scene) == prompt
        assert flow_prompt_mode(scene) == "verbatim"
        assert build_google_flow_prompt(scene, style_context={"image_prompt_prefix": "X"}) == prompt

    def test_no_slash_commands_or_ar_even_with_cinematic_shot_language(self):
        prompt = "GENERATE: full authored prompt /bokeh-free"
        scene = _scene(required_assets=[{"type": "image", "description": prompt}],
                       shot_language={"depth_of_field": "shallow", "lighting_key": "golden_hour"})
        out = build_google_flow_prompt(scene)
        assert out == "full authored prompt /bokeh-free"
        assert "--ar" not in out

    def test_non_generate_required_asset_is_ignored(self):
        scene = _scene(required_assets=[{"type": "image", "description": "reuse frame 03"}])
        assert scene_verbatim_prompt(scene) is None
        assert flow_prompt_mode(scene) == "cinematic"

    def test_missing_or_malformed_required_assets(self):
        assert scene_verbatim_prompt(_scene()) is None
        assert scene_verbatim_prompt(_scene(required_assets=[])) is None
        assert scene_verbatim_prompt(_scene(required_assets=["not-a-dict"])) is None


class TestPlaybookMode:
    def test_style_block_appended_after_scene(self):
        ctx = {"image_prompt_prefix": "Historical narrative illustration in pen-and-ink. No text or numbers anywhere."}
        scene = _scene()
        assert flow_prompt_mode(scene, ctx) == "playbook"
        out = build_google_flow_prompt(scene, style_context=ctx)
        assert out.startswith("A radium dial glows on a factory bench")
        assert "fine cross-hatching, matte paper grain" in out
        assert out.endswith("Historical narrative illustration in pen-and-ink. No text or numbers anywhere.")

    def test_no_slash_commands_or_ar(self):
        ctx = {"image_prompt_prefix": "flat illustration style"}
        out = build_google_flow_prompt(_scene(), style_context=ctx, aspect_ratio="16:9")
        assert "/bokeh" not in out
        assert "/golden_hour" not in out
        assert "--ar" not in out

    def test_suffix_and_guard_appended_in_order(self):
        ctx = {
            "image_prompt_prefix": "STYLE BLOCK",
            "image_prompt_suffix": "POSITIVE REINFORCEMENT",
            "prompt_guard": "GUARD",
        }
        out = build_google_flow_prompt(_scene(texture_keywords=[]), style_context=ctx)
        assert out == "A radium dial glows on a factory bench. STYLE BLOCK. POSITIVE REINFORCEMENT. GUARD"

    def test_playbook_mode_loses_to_verbatim(self):
        ctx = {"image_prompt_prefix": "STYLE"}
        scene = _scene(required_assets=[{"type": "image", "description": "GENERATE: authored"}])
        assert flow_prompt_mode(scene, ctx) == "verbatim"


class TestCinematicMode:
    def test_slash_commands_and_ar(self):
        scene = _scene()
        assert flow_prompt_mode(scene) == "cinematic"
        out = build_google_flow_prompt(scene, aspect_ratio="16:9")
        assert "/bokeh" in out
        assert "/golden_hour" in out
        assert "--ar 16:9" in out

    def test_defaults_to_cinematic_command_when_nothing_maps(self):
        scene = _scene(shot_language={}, texture_keywords=[])
        out = build_google_flow_prompt(scene, aspect_ratio="9:16")
        assert "/cinematic" in out
        assert "--ar 9:16" in out

    def test_character_anchors_still_apply_in_cinematic_mode(self):
        scene = _scene(description="Explorer named Mara stands on a ridge")
        out = build_google_flow_prompt(scene, character_anchors={"Mara": "@Mara"})
        assert "@Mara" in out
