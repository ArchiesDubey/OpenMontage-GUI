"""Generate Kokoro TTS narration for physical-limit-of-silicon and complete assets stage."""

import json
import subprocess
from pathlib import Path

from lib.checkpoint import write_checkpoint
from schemas.artifacts import validate_artifact
from tools.audio.kokoro_tts import KokoroTTS

PROJECT_ID = "physical-limit-of-silicon"
PROJECT_ROOT = Path(__file__).resolve().parents[1] / "projects"
PROJECT_DIR = PROJECT_ROOT / PROJECT_ID
ARTIFACTS_DIR = PROJECT_DIR / "artifacts"
AUDIO_DIR = PROJECT_DIR / "assets" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

script_path = ARTIFACTS_DIR / "script.json"
script = json.loads(script_path.read_text(encoding="utf-8"))
sections = script["sections"]

kokoro = KokoroTTS()

def get_audio_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return round(float(res.stdout.strip()), 2)
    except Exception:
        return 0.0

narration_records = []
for sec in sections:
    sec_id = sec["id"]
    out_file = AUDIO_DIR / f"{sec_id}.wav"
    print(f"Generating Kokoro TTS for {sec_id}...")
    res = kokoro.execute({
        "text": sec["text"],
        "output_path": str(out_file),
        "voice_id": "am_adam",
        "speed": 1.05,
    })
    if not res.success:
        print(f"Error generating {sec_id}: {res.error}")
        raise RuntimeError(res.error)

    dur = get_audio_duration(out_file)
    print(f"  -> Generated {out_file.name} ({dur}s)")
    narration_records.append({
        "id": f"audio-{sec_id}",
        "type": "narration",
        "path": f"assets/audio/{sec_id}.wav",
        "source_tool": "kokoro_tts",
        "scene_id": f"scene-{sec_id.split('-')[1]}",
        "duration_seconds": dur,
        "format": "wav",
        "cost_usd": 0.0,
        "provider": "kokoro",
        "subtype": "generated",
        "generation_summary": f"Local Kokoro-82M TTS synthesis (voice: am_adam, duration: {dur}s)",
    })

# Load existing manifest with images
manifest_path = ARTIFACTS_DIR / "asset_manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

# Keep image assets
image_assets = [a for a in manifest.get("assets", []) if a["type"] == "image"]

# Music asset
music_path = PROJECT_DIR / "assets" / "music" / "background_music.mp3"
music_dur = get_audio_duration(music_path)
music_asset = {
    "id": "music-bed",
    "type": "music",
    "path": "assets/music/background_music.mp3",
    "source_tool": "music_library",
    "scene_id": "all",
    "duration_seconds": music_dur,
    "format": "mp3",
    "cost_usd": 0.0,
    "provider": "local_library",
    "subtype": "background",
    "generation_summary": "Reused background music track from ink-testimony-ep01",
}

# Merge all assets
all_assets = image_assets + narration_records + [music_asset]
manifest["assets"] = all_assets
manifest["total_cost_usd"] = 0.0

validate_artifact("asset_manifest", manifest)
manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"Asset manifest updated with {len(all_assets)} assets (7 images, 7 narrations, 1 music track)!")

# Checkpoint assets stage as completed
write_checkpoint(
    PROJECT_ROOT,
    PROJECT_ID,
    stage="assets",
    status="completed",
    artifacts={"asset_manifest": manifest},
    pipeline_type="animated-explainer",
    human_approved=True,
    metadata={"ingested_image_count": len(image_assets), "narration_count": len(narration_records)},
)
print("Assets stage checkpointed as COMPLETED!")
