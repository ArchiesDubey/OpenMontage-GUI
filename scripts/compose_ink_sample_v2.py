"""Compose Ink & Testimony sample v2 — one image per narration beat, hard cuts.

Each beat: image segment = narration duration + GAP. Hard cut on every beat
(user feedback: stills held too long). Alternating push-in / pull-back motion.
Voice clips are placeholders until the user's voice_id is swapped in —
re-run sample_v2_beats.py TTS step, then this script, to re-voice.
"""
import json
import subprocess

OUT = "projects/ink-testimony-e01/assets/sample"
FPS = 25
LEAD, GAP, TAIL = 0.7, 0.55, 1.6

# (image, narration clip, subtitle) — image cut lands exactly on sentence start
BEATS = [
    ("sc01_hook.png",    "b1_dial_narration.mp3",
     "In Orange, New Jersey, there is a watch dial painted in 1918."),
    ("b2_glow.png",      "b2_glow_narration.mp3",
     "It hasn't glowed in a century."),
    ("b3_bones.png",     "b3_bones_narration.mp3",
     "It is still radioactive. And so are the bones of the women who painted it."),
    ("b4_floor.png",     "b4_floor_narration.mp3",
     "The paint was radium. The girls were told it was perfectly harmless."),
    ("sc02_lippoint.png", "b5_lip_narration.mp3",
     "To keep the brush sharp, they shaped the bristles with their lips."),
]


def dur(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip())


def ts(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)):03d}"


def zoompan(img, secs, out, mode):
    """mode 'in': slow push-in; mode 'out': slow pull-back."""
    frames = int(secs * FPS) + 1
    if mode == "in":
        z = f"1.0+0.06*on/{frames}"
    else:
        z = f"1.06-0.06*on/{frames}"
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", f"{OUT}/{img}", "-vf",
        f"scale=1920:1080,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':d={frames}:s=1280x720:fps={FPS},"
        f"trim=duration={secs},setpts=PTS-STARTPTS",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", out,
    ], check=True, capture_output=True)


# --- timing ---
ndurs = [dur(f"{OUT}/{n}") for _, n, _ in BEATS]
starts, t = [], LEAD
for d in ndurs:
    starts.append(t)
    t += d + GAP
total = t - GAP + TAIL
print("beat narr:", [f"{d:.2f}" for d in ndurs], "total:", f"{total:.2f}s")

# --- per-beat video segments, hard-cut concat ---
segs = []
for i, (img, _, _) in enumerate(BEATS):
    seg_dur = ndurs[i] + (GAP if i < len(BEATS) - 1 else TAIL) + (LEAD if i == 0 else 0)
    seg = f"{OUT}/seg_{i}.mp4"
    zoompan(img, seg_dur, seg, "in" if i % 2 == 0 else "out")
    segs.append(seg)

subprocess.run(
    ["ffmpeg", "-y"] + sum([["-i", s] for s in segs], []) +
    ["-filter_complex", "".join(f"[{i}:v]" for i in range(len(segs))) +
     f"concat=n={len(segs)}:v=1:a=0[v]",
     "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", f"{OUT}/video.mp4"],
    check=True, capture_output=True)

# --- audio: lead + beats with gaps + tail pad, music bed underneath ---
inputs, chains = [], []
for _, n, _ in BEATS:
    inputs += ["-i", f"{OUT}/{n}"]
inputs += ["-i", f"{OUT}/music_bed.mp3"]
nb = len(BEATS)
# lead silence + n0, then chain (gap + ni) onto the running concat
fc = f"aevalsrc=0:d={LEAD}[a0];[a0][0:a]concat=n=2:v=0:a=1[p1];"
for i in range(1, nb):
    fc += f"aevalsrc=0:d={GAP}[g{i}];[p{i}][g{i}][{i}:a]concat=n=3:v=0:a=1[p{i + 1}];"
fc += (f"[p{nb}]apad=pad_dur={TAIL}[narpsrc];[narpsrc]asplit=2[narp][narsub];"
       f"[{nb}:a]atrim=0:{total},afade=t=in:d=1.5,"
       f"afade=t=out:st={total - 2}:d=2,volume=0.13[bed];"
       f"[narp][bed]amix=inputs=2:duration=first:normalize=0[a]")

subprocess.run(
    ["ffmpeg", "-y"] + inputs +
    ["-filter_complex", fc,
     "-map", "[a]", "-ar", "44100", f"{OUT}/audio_mix.m4a",
     "-map", "[narsub]", "-ar", "44100", f"{OUT}/narration_only.wav"],
    check=True, capture_output=True)

# --- subtitles via the local toolchain: transcriber -> subtitle_gen ---
# Transcribe each beat clip separately, then offset its word timestamps to
# the beat's position in the final timeline. This keeps cues from crossing
# beat gaps (a whole-track transcription merges sentences across hard cuts).
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.analysis.transcriber import Transcriber
from tools.subtitle.subtitle_gen import SubtitleGen

tr = Transcriber()
segments = []
for i, (_, narr, _) in enumerate(BEATS):
    res = tr.execute({
        "input_path": f"{OUT}/{narr}",
        "model_size": "large-v3",  # same model as StickmanOS /transcribe; cached locally
        "language": "en",
        "output_dir": OUT,
    })
    if not res.success:
        raise RuntimeError(f"transcriber failed on {narr}: {res.error}")
    offset = starts[i]
    for seg in res.data["segments"]:
        seg["beat"] = i
        seg["start"] = round(seg["start"] + offset, 3)
        seg["end"] = round(seg["end"] + offset, 3)
        seg["words"] = [
            {**w, "start": round(w["start"] + offset, 3),
             "end": round(w["end"] + offset, 3)}
            for w in seg.get("words", [])
        ]
        segments.append(seg)
print(f"transcribed: {len(segments)} segments across {len(BEATS)} beats "
      f"(device={res.data['device']})")

sg = SubtitleGen()
# One subtitle_gen call per beat, then merge — the tool packs cues purely by
# word count, so a single call would let cues cross beat gaps / hard cuts.
srt_blocks, idx = [], 0
for i, (_, _, _) in enumerate(BEATS):
    beat_segs = [s for s in segments if s["beat"] == i]
    sg_res = sg.execute({
        "segments": beat_segs,
        "format": "srt",
        "max_words_per_cue": 8,
        "max_chars_per_line": 42,
        "corrections": {"shape": "shaped"},
        "output_path": f"{OUT}/subs_beat{i}.srt",
    })
    if not sg_res.success:
        raise RuntimeError(f"subtitle_gen failed on beat {i}: {sg_res.error}")
    body = Path(sg_res.artifacts[0]).read_text().strip()
    for cue in body.split("\n\n"):
        lines = cue.strip().splitlines()
        idx += 1
        srt_blocks.append(f"{idx}\n" + "\n".join(lines[1:]))
    print(f"beat {i}: {sg_res.data['cue_count']} cues")
Path(f"{OUT}/subs.srt").write_text("\n\n".join(srt_blocks) + "\n")
print(f"subs: {idx} cues -> {OUT}/subs.srt")

# --- final mux with burned subtitles ---
# Contrast: BorderStyle=3 draws a semi-transparent black backplane behind the
# text, so cues stay legible on bright frames (b4_floor) as well as dark ones.
sub_escaped = f"{OUT}/subs.srt".replace(":", "\\:")
subprocess.run([
    "ffmpeg", "-y", "-i", f"{OUT}/video.mp4", "-i", f"{OUT}/audio_mix.m4a",
    "-vf", (f"subtitles={sub_escaped}:force_style='FontName=Georgia,FontSize=18,"
            "Bold=1,PrimaryColour=&H00F2EDE4,BorderStyle=3,"
            "BackColour=&H80000000,Outline=10,Shadow=0,MarginV=42'"),
    "-c:v", "libx264", "-crf", "18", "-c:a", "copy", "-shortest",
    f"{OUT}/sample_v2.mp4",
], check=True, capture_output=True)

meta = {"beats": [round(d, 2) for d in ndurs], "starts": [round(s, 2) for s in starts],
        "total_s": round(total, 2), "fps": FPS}
json.dump(meta, open(f"{OUT}/sample_meta.json", "w"), indent=2)
print("COMPOSED:", meta)
