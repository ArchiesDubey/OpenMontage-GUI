"""Compose Ink & Testimony E01 — full episode (16 scenes, 14 narration beats).

Extends the validated compose_ink_sample_v2.py grammar:
- per-beat zoompan (push-in / pull-back / micro drift), hard cuts, concat
- lead/gap/tail narration chain via aevalsrc+concat, music bed at volume 0.13
- per-beat transcription -> subtitle_gen cues (never crossing hard cuts)
- BorderStyle=3 backplane subtitle burn (Georgia, cream)
E01 additions per scene_plan.json:
- text_card scenes 11/13: dimmed frame + ffmpeg drawtext date/stat cards
- fade from black (scene-01) and fade to black (scene-16)
- s10/s11 narration split across frame+card scenes at word-timestamp boundaries
"""
import json
import subprocess
from pathlib import Path

E01 = "projects/ink-testimony-e01/assets/e01"
SMP = "projects/ink-testimony-e01/assets/sample"
FPS = 25
LEAD, GAP, TAIL = 0.7, 0.55, 1.6

# (scene_id, image_path, mode, narr)  mode: in|out|micro|static|card
# card = text_card scene over dimmed prior frame; narr None = continues prior clip
SCENES = [
    ("scene-01", f"{SMP}/sc01_hook.png",         "in",    "s1"),
    ("scene-02", f"{SMP}/b2_glow.png",           "in",    "s2"),
    ("scene-03", f"{E01}/e01_undark_jars.png",   "out",   "s3"),
    ("scene-04", f"{SMP}/b4_floor.png",          "in",    "s4"),
    ("scene-05", f"{SMP}/sc02_lippoint.png",     "micro", "s5"),
    ("scene-06", f"{E01}/e01_foreman.png",       "in",    "s6"),
    ("scene-07", f"{E01}/e01_lead_screen.png",   "in",    "s7"),
    ("scene-08", f"{E01}/e01_dentist_chair.png", "micro", "s8"),
    ("scene-09", f"{SMP}/b3_bones.png",          "in",    "s9"),
    ("scene-10", f"{E01}/e01_courtroom.png",     "in",    "s10"),
    ("scene-11", f"{E01}/e01_courtroom.png",     "card",  None),
    ("scene-12", f"{E01}/e01_settlement_desk.png", "static", "s11"),
    ("scene-13", f"{E01}/e01_settlement_desk.png", "card",  None),
    ("scene-14", f"{E01}/e01_lab_ledgers.png",   "out",   "s12"),
    ("scene-15", f"{E01}/e01_brush_sill.png",    "micro", "s13"),
    ("scene-16", f"{SMP}/sc01_hook.png",         "out",   "s14"),
]

CARDS = {
    "scene-11": "May 25, 1927 \u2014 the Radium Girls sue U.S. Radium",
    "scene-13": "$10,000 each \u2014 January 1928",
}
# card appears after these words in the owning clip's transcript (fallback: fraction)
CARD_SPLIT_WORD = {"s10": ("sued", 0.40), "s11": ("each", 0.68)}

ZOOM = {"in": 0.06, "out": 0.06, "micro": 0.02, "static": 0.0}


def dur(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip())


def ts(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)):03d}"


# --- timing from actual narration clips ---
NARRS = [s for _, _, _, s in SCENES if s]
ndurs = {s: dur(f"{E01}/{s}_narration.mp3") for s in NARRS}
starts, t = {}, LEAD
for s in NARRS:
    starts[s] = t
    t += ndurs[s] + GAP
total = t - GAP + TAIL
print("narr durations:", {k: round(v, 2) for k, v in ndurs.items()})
print("total:", f"{total:.2f}s")

# --- transcription (per clip, offsets cues + card split points) ---
import sys
from pathlib import Path as _P

sys.path.insert(0, str(_P(__file__).resolve().parents[1]))
from tools.analysis.transcriber import Transcriber
from tools.subtitle.subtitle_gen import SubtitleGen

tr = Transcriber()
segments = []
words_by_clip = {}
for s in NARRS:
    res = tr.execute({
        "input_path": f"{E01}/{s}_narration.mp3",
        "model_size": "large-v3",
        "language": "en",
        "output_dir": E01,
    })
    if not res.success:
        raise RuntimeError(f"transcriber failed on {s}: {res.error}")
    words_by_clip[s] = res.data["segments"] and [
        w for seg in res.data["segments"] for w in seg.get("words", [])] or []
    off = starts[s]
    for seg in res.data["segments"]:
        seg["beat"] = s
        seg["start"] = round(seg["start"] + off, 3)
        seg["end"] = round(seg["end"] + off, 3)
        seg["words"] = [
            {**w, "start": round(w["start"] + off, 3),
             "end": round(w["end"] + off, 3)} for w in seg.get("words", [])]
        segments.append(seg)
print(f"transcribed {len(segments)} segments across {len(NARRS)} clips")

# --- card split times (clip-local seconds) ---
split = {}
for s, (word, frac) in CARD_SPLIT_WORD.items():
    cut = None
    for w in words_by_clip[s]:
        if word in w.get("word", "").lower().strip(".,—-"):
            cut = w["end"]  # raw transcript words are clip-local already
            break
    split[s] = round(cut if cut is not None else ndurs[s] * frac, 3)
    print(f"card split {s}: at {split[s]:.2f}s of {ndurs[s]:.2f}s (word='{word}')")

# --- per-scene segment durations ---
segdur, i = {}, 0
for idx, (sid, _, mode, narr) in enumerate(SCENES):
    first, last = idx == 0, idx == len(SCENES) - 1
    next_mode = SCENES[idx + 1][2] if not last else None
    if mode == "card":
        owner = SCENES[idx - 1][3]          # narration clip being held over
        segdur[sid] = ndurs[owner] - split[owner] + GAP
    elif next_mode == "card":
        segdur[sid] = split[narr]           # frame only up to the card split
    else:
        segdur[sid] = ndurs[narr] + (TAIL if last else GAP) + (LEAD if first else 0)
assert abs(sum(segdur.values()) - total) < 0.05, (sum(segdur.values()), total)

# --- render video segments ---
def zoompan(img, secs, out, mode, fade_in=0.0, fade_out=0.0):
    frames = int(secs * FPS) + 1
    amt = ZOOM[mode]
    if mode == "out":
        z = f"1.06-0.06*on/{frames}"
    elif amt > 0:
        z = f"1.0+{amt}*on/{frames}"
    else:
        z = "1.0"
    vf = (f"scale=1920:1080,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':"
          f"y='ih/2-(ih/zoom/2)':d={frames}:s=1280x720:fps={FPS},"
          f"trim=duration={secs},setpts=PTS-STARTPTS")
    if fade_in:
        vf += f",fade=t=in:st=0:d={fade_in}"
    if fade_out:
        vf += f",fade=t=out:st={secs - fade_out:.3f}:d={fade_out}"
    subprocess.run(
        ["ffmpeg", "-y", "-loop", "1", "-i", img, "-vf", vf,
         "-c:v", "libx264", "-pix_fmt", "yuv420p", out],
        check=True, capture_output=True)


def card_segment(img, text, secs, out):
    tf = f"{E01}/_cardtext.txt"
    Path(tf).write_text(text)
    frames = int(secs * FPS) + 1
    vf = (f"scale=1920:1080,zoompan=z='1.0':d={frames}:s=1280x720:fps={FPS},"
          f"trim=duration={secs},setpts=PTS-STARTPTS,"
          f"eq=brightness=-0.22,"
          f"drawtext=fontfile=/System/Library/Fonts/Supplemental/Georgia.ttf"
          f":textfile={tf}:fontsize=30:fontcolor=0xF2EDE4:"
          f"box=1:boxcolor=black@0.62:boxborderw=18:"
          f"x=(w-text_w)/2:y=(h-text_h)/2,"
          f"fade=t=in:st=0:d=0.35,fade=t=out:st={secs - 0.35:.3f}:d=0.35")
    subprocess.run(
        ["ffmpeg", "-y", "-loop", "1", "-i", img, "-vf", vf,
         "-c:v", "libx264", "-pix_fmt", "yuv420p", out],
        check=True, capture_output=True)


segs = []
for i, (sid, img, mode, _) in enumerate(SCENES):
    seg = f"{E01}/seg_{i:02d}.mp4"
    sd = segdur[sid]
    if mode == "card":
        card_segment(img, CARDS[sid], sd, seg)
    else:
        zoompan(img, sd, seg, mode,
                fade_in=0.7 if i == 0 else 0.0,
                fade_out=1.2 if i == len(SCENES) - 1 else 0.0)
    segs.append(seg)
    print("seg", sid, f"{sd:.2f}s")

subprocess.run(
    ["ffmpeg", "-y"] + sum([["-i", s] for s in segs], []) +
    ["-filter_complex", "".join(f"[{i}:v]" for i in range(len(segs))) +
     f"concat=n={len(segs)}:v=1:a=0[v]",
     "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", f"{E01}/video.mp4"],
    check=True, capture_output=True)

# --- audio: lead + 14 clips with gaps + tail, music bed underneath ---
inputs, chains = [], []
for s in NARRS:
    inputs += ["-i", f"{E01}/{s}_narration.mp3"]
inputs += ["-i", f"{E01}/music_bed.mp3"]
nb = len(NARRS)
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
     "-map", "[a]", "-ar", "44100", f"{E01}/audio_mix.m4a",
     "-map", "[narsub]", "-ar", "44100", f"{E01}/narration_only.wav"],
    check=True, capture_output=True)

# --- subtitles: one subtitle_gen call per clip, then merge ---
sg = SubtitleGen()
srt_blocks, idx = [], 0
for s in NARRS:
    beat_segs = [x for x in segments if x["beat"] == s]
    sg_res = sg.execute({
        "segments": beat_segs,
        "format": "srt",
        "max_words_per_cue": 8,
        "max_chars_per_line": 42,
        "corrections": {"shape": "shaped"},
        "output_path": f"{E01}/subs_{s}.srt",
    })
    if not sg_res.success:
        raise RuntimeError(f"subtitle_gen failed on {s}: {sg_res.error}")
    body = Path(sg_res.artifacts[0]).read_text().strip()
    for cue in body.split("\n\n"):
        lines = cue.strip().splitlines()
        idx += 1
        srt_blocks.append(f"{idx}\n" + "\n".join(lines[1:]))
    print(f"{s}: {sg_res.data['cue_count']} cues")
Path(f"{E01}/subs.srt").write_text("\n\n".join(srt_blocks) + "\n")
print(f"subs: {idx} cues -> {E01}/subs.srt")

# --- final mux with burned subtitles ---
sub_escaped = f"{E01}/subs.srt".replace(":", "\\:")
subprocess.run([
    "ffmpeg", "-y", "-i", f"{E01}/video.mp4", "-i", f"{E01}/audio_mix.m4a",
    "-vf", (f"subtitles={sub_escaped}:force_style='FontName=Georgia,FontSize=18,"
            "Bold=1,PrimaryColour=&H00F2EDE4,BorderStyle=3,"
            "BackColour=&H80000000,Outline=10,Shadow=0,MarginV=42'"),
    "-c:v", "libx264", "-crf", "18", "-c:a", "copy", "-shortest",
    f"{E01}/e01_episode.mp4",
], check=True, capture_output=True)

meta = {"scenes": {sid: round(d, 2) for sid, d in segdur.items()},
        "narr_starts": {k: round(v, 2) for k, v in starts.items()},
        "card_splits": split, "total_s": round(total, 2), "fps": FPS}
json.dump(meta, open(f"{E01}/e01_meta.json", "w"), indent=2)
print("COMPOSED:", json.dumps(meta["total_s"]))

