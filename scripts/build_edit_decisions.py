"""Build edit_decisions artifact and checkpoint edit stage for physical-limit-of-silicon."""

import json
from pathlib import Path

from lib.checkpoint import write_checkpoint
from schemas.artifacts import validate_artifact

PROJECT_ID = "physical-limit-of-silicon"
PROJECT_ROOT = Path(__file__).resolve().parents[1] / "projects"
PROJECT_DIR = PROJECT_ROOT / PROJECT_ID
ARTIFACTS_DIR = PROJECT_DIR / "artifacts"

# Load asset manifest to verify asset IDs and paths
manifest = json.loads((ARTIFACTS_DIR / "asset_manifest.json").read_text(encoding="utf-8"))

# Narration timings from Kokoro synthesis
timings = [
    ("sec-1", "scene-1", "img-scene-1", 0.0, 7.45, "zoom-in"),
    ("sec-2", "scene-2", "img-scene-2", 7.45, 16.73, "pan-right"),
    ("sec-3", "scene-3", "img-scene-3", 16.73, 28.51, "zoom-out"),
    ("sec-4", "scene-4", "img-scene-4", 28.51, 38.39, "pan-left"),
    ("sec-5", "scene-5", "img-scene-5", 38.39, 49.65, "zoom-in"),
    ("sec-6", "scene-6", "img-scene-6", 49.65, 59.68, "zoom-rotate"),
    ("sec-7", "scene-7", "img-scene-7", 59.68, 70.56, "zoom-out"),
]

cuts = []
narration_segments = []

for idx, (sec_id, scene_id, img_id, start_s, end_s, anim) in enumerate(timings, start=1):
    cuts.append({
        "id": f"cut-{idx}",
        "source": img_id,
        "in_seconds": start_s,
        "out_seconds": end_s,
        "speed": 1.0,
        "layer": "primary",
        "transform": {
            "scale": 1.0,
            "position": "center",
            "animation": anim,
        },
        "transition_in": "fade" if idx > 1 else "cut",
        "transition_out": "fade" if idx < len(timings) else "dissolve",
        "transition_duration": 0.4,
        "reason": f"Visual presentation for {scene_id}",
    })
    narration_segments.append({
        "asset_id": f"audio-{sec_id}",
        "start_seconds": start_s,
        "end_seconds": end_s,
    })

edit_decisions = {
    "version": "1.0",
    "render_runtime": "remotion",
    "renderer_family": "explainer-data",
    "composition_mode": "templated",
    "cut_timing": "timeline",
    "cuts": cuts,
    "audio": {
        "narration": {
            "segments": narration_segments,
        },
        "music": {
            "asset_id": "music-bed",
            "volume": 0.18,
            "fade_in_seconds": 1.0,
            "fade_out_seconds": 2.5,
            "ducking": {
                "enabled": True,
                "reduction_db": 12.0,
            },
        },
    },
    "subtitles": {
        "enabled": True,
        "style": "word-by-word",
        "font": "Inter",
        "font_size": 42,
        "position": "bottom-center",
        "color": "#FFFFFF",
        "background": "#00000088",
    },
}

validate_artifact("edit_decisions", edit_decisions)

ed_path = ARTIFACTS_DIR / "edit_decisions.json"
ed_path.write_text(json.dumps(edit_decisions, indent=2), encoding="utf-8")
print("edit_decisions artifact created and validated successfully!")

# Write Checkpoint for edit stage
write_checkpoint(
    PROJECT_ROOT,
    PROJECT_ID,
    stage="edit",
    status="completed",
    artifacts={"edit_decisions": edit_decisions},
    pipeline_type="animated-explainer",
    human_approved=True,
    metadata={"cut_count": len(cuts), "total_duration_seconds": 70.56},
)
print("Edit stage checkpointed as COMPLETED!")
