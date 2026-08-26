"""Reconcile script.json + scene_plan.json start/end timestamps to the REAL
generated audio durations (source of truth), per the mandatory timing
assertion. The original timestamps were estimates from a planning word-rate
(2.35 wps) that turned out to run ~26% slower than the actual ElevenLabs
output (2.96 wps) -- accepted by the user as a shorter ~8:00 runtime rather
than adding content or slowing pacing (decision d-009).
"""
import json
import subprocess

OUT = "projects/ink-testimony-e02/assets/e02"


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    return float(out.stdout.strip())


script = json.load(open("projects/ink-testimony-e02/artifacts/script.json"))
scene_plan = json.load(open("projects/ink-testimony-e02/artifacts/scene_plan.json"))

new_times = {}  # section id -> (start, end)
t = 0.7
for sec in sorted(script["sections"], key=lambda s: s["start_seconds"]):
    sid = sec["id"]
    dur = duration(f"{OUT}/{sid}_narration.mp3")
    start = round(t, 2)
    end = round(t + dur, 2)
    new_times[sid] = (start, end)
    sec["start_seconds"] = start
    sec["end_seconds"] = end
    gap = sec["delivery_cues"].get("pause_after_seconds", 0.55)
    t = end + gap

total_duration = round(t - script["sections"][-1]["delivery_cues"].get("pause_after_seconds", 0.55) + 0.0, 2)
# actually total = end of last section (no trailing gap needed after the very last beat)
total_duration = new_times[script["sections"][-1]["id"]][1]

script["total_duration_seconds"] = total_duration
script["metadata"]["duration_check"] = (
    f"RECONCILED to real audio durations post-generation: {total_duration}s (~{round(total_duration/60,1)} min). "
    f"Original estimate was 599.62s assuming 2.35 wps; actual ElevenLabs output measured 2.964 wps (178 wpm) for "
    f"this voice/content, ~26% faster than planned. User reviewed the real shortfall (decision d-009 in "
    f"decision_log.json) and explicitly chose to accept the shorter runtime rather than add content or slow pacing."
)

# Propagate to scene_plan: each scene's start/end follows its script_section_id's new timing.
for scene in scene_plan["scenes"]:
    sid = scene["script_section_id"]
    start, end = new_times[sid]
    scene["start_seconds"] = start
    scene["end_seconds"] = end
    # keep enhancement_cues-derived overlay timestamps out of scope here (scene_plan has none)

json.dump(script, open("projects/ink-testimony-e02/artifacts/script.json", "w"), indent=2)
json.dump(scene_plan, open("projects/ink-testimony-e02/artifacts/scene_plan.json", "w"), indent=2)

print("reconciled total_duration_seconds:", total_duration)
