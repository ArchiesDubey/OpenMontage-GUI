"""Shot prompt builder — converts structured shot language into provider-optimized prompts.

Uses a 5-layer framework based on professional cinematography prompting research:
  Layer 1: Camera (lens, depth of field)
  Layer 2: Movement (shot size, camera movement)
  Layer 3: Subject (description + texture keywords)
  Layer 4: Lighting (lighting key, color temperature)
  Layer 5: Style (adapted from playbook, not verbatim)

This replaces the old approach of prepending a fixed playbook image_prompt_prefix
to every scene description, which made all scenes look the same.
"""

from __future__ import annotations

from typing import Any


# Mapping from shot_language enums to natural language for prompting
_SHOT_SIZE_PHRASES = {
    "extreme_wide": "extreme wide shot showing vast environment",
    "wide": "wide shot capturing full scene",
    "medium_wide": "medium-wide shot framing subject with surroundings",
    "medium": "medium shot from waist up",
    "medium_close": "medium close-up from chest up",
    "close_up": "close-up focusing on face or detail",
    "extreme_close_up": "extreme close-up on fine detail",
    "over_shoulder": "over-the-shoulder perspective",
    "insert": "insert shot of specific detail",
    "establishing": "establishing shot setting the location",
}

_MOVEMENT_PHRASES = {
    "static": "locked-off static camera",
    "pan_left": "smooth pan to the left",
    "pan_right": "smooth pan to the right",
    "tilt_up": "gentle tilt upward",
    "tilt_down": "gentle tilt downward",
    "dolly_in": "slow dolly in toward subject",
    "dolly_out": "slow dolly out from subject",
    "tracking_left": "tracking shot moving left alongside subject",
    "tracking_right": "tracking shot moving right alongside subject",
    "crane_up": "crane shot rising upward",
    "crane_down": "crane shot descending",
    "handheld": "handheld camera with natural movement",
    "steadicam": "smooth steadicam following movement",
    "whip_pan": "fast whip pan",
    "orbital": "orbital camera circling subject",
    "zoom_in": "slow zoom in",
    "zoom_out": "slow zoom out",
    "rack_focus": "rack focus shift between foreground and background",
}

_LIGHTING_PHRASES = {
    "high_key": "bright high-key lighting, minimal shadows",
    "low_key": "dramatic low-key lighting with deep shadows",
    "natural": "natural ambient lighting",
    "golden_hour": "warm golden hour sunlight",
    "blue_hour": "cool blue hour twilight",
    "tungsten_warm": "warm tungsten interior lighting",
    "neon": "neon-lit with vibrant color spill",
    "silhouette": "backlit silhouette",
    "rim_lit": "rim lighting highlighting edges",
    "volumetric": "volumetric light with visible rays",
    "overcast_soft": "soft overcast diffused light",
}

_DOF_PHRASES = {
    "shallow": "shallow depth of field with bokeh",
    "medium": "medium depth of field",
    "deep": "deep focus with everything sharp",
}

_COLOR_TEMP_PHRASES = {
    "cool": "cool blue-toned color palette",
    "neutral": "neutral balanced colors",
    "warm": "warm amber-toned color palette",
    "mixed": "mixed color temperatures for contrast",
}


def build_shot_prompt(
    scene: dict[str, Any],
    style_context: dict[str, Any] | None = None,
    target_engine: str = "standard",
) -> str:
    """Convert a scene with structured shot language into a generation prompt.

    Args:
        scene: Scene dict from scene_plan (with shot_language, description,
               texture_keywords, etc.)
        style_context: Optional playbook-derived style info with keys like
                       'generation_prefix', 'visual_language', 'mood'.
        target_engine: Target prompt syntax ('standard' or 'google_flow').

    Returns:
        A natural-language prompt optimized for image/video generation.
    """
    if target_engine == "google_flow":
        return build_google_flow_prompt(scene, style_context)

    sl = scene.get("shot_language", {})
    layers: list[str] = []

    # Layer 1: Camera — lens and depth of field
    camera_parts = []
    if sl.get("lens_mm"):
        camera_parts.append(f"{sl['lens_mm']}mm lens")
    if sl.get("depth_of_field"):
        camera_parts.append(_DOF_PHRASES.get(sl["depth_of_field"], ""))
    if camera_parts:
        layers.append(", ".join(filter(None, camera_parts)))

    # Layer 2: Movement — shot size and camera movement
    movement_parts = []
    if sl.get("shot_size"):
        movement_parts.append(_SHOT_SIZE_PHRASES.get(sl["shot_size"], sl["shot_size"]))
    if sl.get("camera_movement") and sl["camera_movement"] != "static":
        movement_parts.append(_MOVEMENT_PHRASES.get(sl["camera_movement"], sl["camera_movement"]))
    if movement_parts:
        layers.append(", ".join(movement_parts))

    # Layer 3: Subject — the scene description + texture keywords
    description = scene.get("description", "")
    texture = scene.get("texture_keywords", [])
    subject_parts = [description]
    if texture:
        subject_parts.append(", ".join(texture))
    layers.append(". ".join(filter(None, subject_parts)))

    # Layer 4: Lighting — lighting key and color temperature
    lighting_parts = []
    if sl.get("lighting_key"):
        lighting_parts.append(_LIGHTING_PHRASES.get(sl["lighting_key"], sl["lighting_key"]))
    if sl.get("color_temperature"):
        lighting_parts.append(_COLOR_TEMP_PHRASES.get(sl["color_temperature"], ""))
    if lighting_parts:
        layers.append(", ".join(filter(None, lighting_parts)))

    # Layer 5: Style — adapted from playbook (NOT verbatim prefix)
    if style_context:
        mood = style_context.get("mood", "")
        visual_lang = style_context.get("visual_language", {})
        style_hint = visual_lang.get("aesthetic", "") or mood
        if style_hint:
            layers.append(f"Style: {style_hint}")

    return ". ".join(filter(None, layers))


# Mapping from shot language to Google Flow slash commands
_FLOW_LIGHTING_COMMANDS = {
    "golden_hour": "/golden_hour",
    "blue_hour": "/blue_hour",
    "volumetric": "/volumetric_lighting",
    "low_key": "/dramatic_lighting",
    "high_key": "/bright",
    "neon": "/neon",
    "silhouette": "/silhouette",
    "rim_lit": "/rim_lighting",
    "tungsten_warm": "/warm_light",
}

_FLOW_CAMERA_COMMANDS = {
    "shallow": "/bokeh",
    "close_up": "/close_up",
    "extreme_close_up": "/macro",
    "wide": "/wide_angle",
    "extreme_wide": "/panoramic",
}


def build_google_flow_prompt(
    scene: dict[str, Any],
    style_context: dict[str, Any] | None = None,
    aspect_ratio: str = "16:9",
    character_anchors: dict[str, str] | None = None,
) -> str:
    """Build an image prompt tailored for Google Flow (flow.google).

    Google Flow incorporates slash commands (e.g. /bokeh, /volumetric_lighting),
    character/ingredient anchors (@CharacterName), and aspect ratio flags (--ar 16:9).

    Args:
        scene: Scene dictionary from scene_plan.
        style_context: Optional playbook-derived style context.
        aspect_ratio: Target aspect ratio ('16:9', '9:16', '1:1', etc.).
        character_anchors: Optional mapping from character identifier to @Anchor tag.

    Returns:
        A Google Flow formatted prompt string.
    """
    sl = scene.get("shot_language", {})
    description = scene.get("description", "").strip()

    # Apply character anchors if specified
    if character_anchors:
        for char_key, anchor_tag in character_anchors.items():
            if char_key in description and not anchor_tag.startswith("@"):
                anchor_tag = f"@{anchor_tag}"
            description = description.replace(char_key, anchor_tag)

    parts: list[str] = [description]

    # Visual texture and details
    texture = scene.get("texture_keywords", [])
    if texture:
        parts.append(", ".join(texture))

    # Cinematography notes
    camera_details = []
    if sl.get("shot_size"):
        camera_details.append(_SHOT_SIZE_PHRASES.get(sl["shot_size"], sl["shot_size"]))
    if sl.get("lens_mm"):
        camera_details.append(f"{sl['lens_mm']}mm lens")
    if camera_details:
        parts.append(", ".join(camera_details))

    # Style direction
    if style_context:
        mood = style_context.get("mood", "")
        visual_lang = style_context.get("visual_language", {})
        style_hint = visual_lang.get("aesthetic", "") or mood
        if style_hint:
            parts.append(f"aesthetic: {style_hint}")

    base_prompt = ". ".join(filter(None, parts))

    # Collect Google Flow slash commands
    slash_commands: list[str] = []
    dof = sl.get("depth_of_field", "")
    if dof in _FLOW_CAMERA_COMMANDS:
        slash_commands.append(_FLOW_CAMERA_COMMANDS[dof])

    shot_size = sl.get("shot_size", "")
    if shot_size in _FLOW_CAMERA_COMMANDS and _FLOW_CAMERA_COMMANDS[shot_size] not in slash_commands:
        slash_commands.append(_FLOW_CAMERA_COMMANDS[shot_size])

    lighting = sl.get("lighting_key", "")
    if lighting in _FLOW_LIGHTING_COMMANDS:
        slash_commands.append(_FLOW_LIGHTING_COMMANDS[lighting])

    # Add general cinematic command if none added
    if not slash_commands:
        slash_commands.append("/cinematic")

    # Add aspect ratio flag
    ar_tag = f"--ar {aspect_ratio}" if aspect_ratio else "--ar 16:9"

    commands_str = " ".join(slash_commands)
    return f"{base_prompt} {commands_str} {ar_tag}".strip()


def build_batch_prompts(
    scenes: list[dict[str, Any]],
    style_context: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Build prompts for all visual scenes in a scene plan.

    Returns list of {scene_id, prompt} dicts.
    """
    results = []
    for scene in scenes:
        # Skip non-visual scene types
        scene_type = scene.get("type", "")
        if scene_type in ("transition",):
            continue
        prompt = build_shot_prompt(scene, style_context)
        results.append({
            "scene_id": scene.get("id", "unknown"),
            "prompt": prompt,
            "hero_moment": scene.get("hero_moment", False),
        })
    return results


def build_batch_google_flow_prompts(
    scenes: list[dict[str, Any]],
    style_context: dict[str, Any] | None = None,
    aspect_ratio: str = "16:9",
    character_anchors: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Build Google Flow prompts for all visual scenes in a scene plan.

    Returns list of dictionaries containing sequence indexing, target filename,
    and formatted prompt.
    """
    results = []
    seq_index = 1
    for scene in scenes:
        scene_type = scene.get("type", "")
        if scene_type in ("transition",):
            continue

        scene_id = scene.get("id", f"scene-{seq_index}")
        flow_prompt = build_google_flow_prompt(
            scene=scene,
            style_context=style_context,
            aspect_ratio=aspect_ratio,
            character_anchors=character_anchors,
        )

        target_filename = f"{seq_index:02d}_{scene_id}.png"
        results.append({
            "index": seq_index,
            "scene_id": scene_id,
            "target_filename": target_filename,
            "prompt": flow_prompt,
            "description": scene.get("description", ""),
            "start_seconds": scene.get("start_seconds", 0.0),
            "end_seconds": scene.get("end_seconds", 0.0),
            "hero_moment": scene.get("hero_moment", False),
        })
        seq_index += 1

    return results

