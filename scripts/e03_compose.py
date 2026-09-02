"""E03-specific composer: 'Ink & Testimony E03 -- The Silly Season'.

Adapts scripts/e02_compose.py (which itself reuses explainer_compose.py's
validated primitives): every beat -- including the 5 act-break cards -- has its
own real narration clip, so the timeline is a uniform lead/clip/gap/tail chain
with no split-card branch.

E03 override (decision d-003): burn_subtitles = False. The merged SRT is still
built per-clip via subtitle_gen (max 8 words/cue, word-timings offset to the
timeline) and written as a SIDECAR beside the MP4 -- it is NOT burned into the
video and NOT muxed as a stream. Act-break cards, being composited drawtext,
are unaffected.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts.explainer_compose import dur, zoompan_segment, card_segment, transcribe_section  # noqa: E402

PROJ = REPO / "projects" / "ink-testimony-e03"
ASSETS = PROJ / "assets" / "e03"
OUT_MP4 = ASSETS / "ink-testimony-e03_episode.mp4"
SIDECAR_SRT = ASSETS / "subtitles.srt"
FPS = 25
LEAD, GAP, CARD_GAP, TAIL = 0.7, 0.5, 0.8, 5.0
MUSIC_VOLUME, MUSIC_FADE_IN, MUSIC_FADE_OUT = 0.14, 1.5, 3.0
FADE_IN_FIRST, FADE_OUT_LAST = 0.8, 2.5
BURN_SUBTITLES = False  # decision d-003: sidecar SRT only

# held beat -> anchor whose generated frame it reuses (E03 scene_plan holds)
REUSE = {
    "s2": "s1", "a1_5": "a1_4", "a1_12": "a1_11", "a2_14": "a2_13",
    "a3_5": "a3_4", "a3_9": "a3_8", "a3_26": "a3_25", "a5_16": "a5_1",
}
REUSE_MODE = "micro"

ANCHOR_MODE = {
    "s1": "in", "s3": "micro", "s4": "static",
    "a1_1": "in", "a1_2": "micro", "a1_4": "micro", "a1_6": "in", "a1_7": "micro",
    "a1_8": "out", "a1_10": "micro", "a1_11": "micro", "a1_14": "in",
    "a2_1": "in", "a2_2": "micro", "a2_4": "micro", "a2_6": "in", "a2_7": "micro",
    "a2_8": "out", "a2_9": "in", "a2_10": "micro", "a2_12": "in", "a2_13": "micro",
    "a2_15": "out", "a2_17": "in",
    "a3_1": "in", "a3_2": "out", "a3_4": "in", "a3_7": "micro", "a3_8": "micro",
    "a3_10": "in", "a3_11": "static", "a3_12": "static", "a3_13": "micro",
    "a3_15": "out", "a3_16": "micro", "a3_17": "in", "a3_18": "micro",
    "a3_20": "out", "a3_22": "micro", "a3_23": "micro", "a3_25": "in",
    "a4_1": "in", "a4_2": "in", "a4_3": "micro", "a4_4": "micro", "a4_5": "in",
    "a4_6": "micro", "a4_7": "out", "a4_8": "micro", "a4_9": "in", "a4_11": "micro",
    "a4_12": "out", "a4_13": "micro", "a4_14": "static", "a4_15": "static",
    "a4_17": "static", "a4_18": "micro", "a4_19": "static", "a4_20": "micro",
    "a4_22": "in", "a4_23": "micro", "a4_24": "out", "a4_25": "micro",
    "a5_1": "in", "a5_2": "micro", "a5_5": "micro", "a5_6": "in", "a5_7": "micro",
    "a5_8": "micro", "a5_10": "out", "a5_11": "micro", "a5_12": "micro",
    "a5_14": "static", "a5_15": "micro",
}

script = json.load(open(PROJ / "artifacts" / "script.json"))
plan = json.load(open(PROJ / "artifacts" / "scene_plan.json"))
sections = {s["id"]: s for s in script["sections"]}
TEXT_CARD_IDS = {sc["script_section_id"] for sc in plan["scenes"] if sc["type"] == "text_card"}
ORDER = [s["id"] for s in sorted(script["sections"], key=lambda s: s["start_seconds"])]

# cards render as dimmed drawtext over the most recent non-card frame
CARD_BACKDROP, _last = {}, None
for _sid in ORDER:
    if _sid in TEXT_CARD_IDS:
        CARD_BACKDROP[_sid] = _last
    else:
        _last = REUSE.get(_sid, _sid)


def resolve_image(sid):
    anchor = CARD_BACKDROP[sid] if sid in TEXT_CARD_IDS else REUSE.get(sid, sid)
    return str(ASSETS / f"e03_{anchor}.png")


def resolve_mode(sid):
    if sid in TEXT_CARD_IDS:
        return "card"
    if sid in REUSE:
        return REUSE_MODE
    return ANCHOR_MODE[sid]


def card_text_for(sid):
    return sections[sid]["text"]  # "ACT ONE\nTHE SLOW MONTHS" -> drawtext renders 2 lines


# --- decode every clip to WAV once (sample-accurate; MP3 container duration
#     over-reads by ~35ms of LAME padding -> ~3s desync across ~90 clips) ---
mp3_clips = {sid: ASSETS / f"{sid}_narration.mp3" for sid in ORDER}
missing = [s for s, c in mp3_clips.items() if not c.exists()]
assert not missing, f"missing narration clips: {missing}"
WAV_DIR = ASSETS / "_wav_cache"
WAV_DIR.mkdir(exist_ok=True)
clips = {}
for sid in ORDER:
    wav = WAV_DIR / f"{sid}_narration.wav"
    if not wav.exists():
        subprocess.run(["ffmpeg", "-y", "-i", str(mp3_clips[sid]), str(wav)],
                       check=True, capture_output=True)
    clips[sid] = wav
ndurs = {sid: dur(c) for sid, c in clips.items()}

starts, t = {}, LEAD
for i, sid in enumerate(ORDER):
    starts[sid] = t
    gap = CARD_GAP if sid in TEXT_CARD_IDS else GAP
    t += ndurs[sid] + (TAIL if i == len(ORDER) - 1 else gap)
total = t
print(f"total timeline: {total:.2f}s ({total/60:.2f} min)")

segdur = {sid: ndurs[sid]
          + (TAIL if i == len(ORDER) - 1 else (CARD_GAP if sid in TEXT_CARD_IDS else GAP))
          + (LEAD if i == 0 else 0)
          for i, sid in enumerate(ORDER)}
assert abs(sum(segdur.values()) - total) < 0.05, \
    f"timeline mismatch: segments={sum(segdur.values()):.3f} audio={total:.3f}"
print(f"timing assert OK: {sum(segdur.values()):.2f}s == {total:.2f}s")

# --- transcription (cached) + timeline offsets, for the sidecar SRT ---
all_segments = []
for sid in ORDER:
    for seg in transcribe_section(sid, clips[sid], ASSETS, {"transcribe_model": "large-v3"}):
        seg["beat"] = sid
        seg["start"] = round(seg["start"] + starts[sid], 3)
        seg["end"] = round(seg["end"] + starts[sid], 3)
        seg["words"] = [{**w, "start": round(w["start"] + starts[sid], 3),
                         "end": round(w["end"] + starts[sid], 3)}
                        for w in seg.get("words", [])]
        all_segments.append(seg)
print(f"transcript segments: {len(all_segments)} across {len(ORDER)} clips")

# --- render video segments ---
n = len(ORDER)
segs = []
for i, sid in enumerate(ORDER):
    seg = ASSETS / f"seg_{i:03d}.mp4"
    sd = segdur[sid]
    img, mode = resolve_image(sid), resolve_mode(sid)
    if mode == "card":
        card_segment(img, card_text_for(sid), sd, ASSETS, seg, FPS)
    else:
        zoompan_segment(img, sd, seg, mode, FPS,
                        fade_in=FADE_IN_FIRST if i == 0 else 0.0,
                        fade_out=FADE_OUT_LAST if i == n - 1 else 0.0)
    segs.append(str(seg))
    print("seg", sid, mode, f"{sd:.2f}s")

# --- narration chain + music bed ---
def e03_audio_filter():
    nb = len(ORDER)
    fc = f"aevalsrc=0:d={LEAD}[a0];[a0][0:a]concat=n=2:v=0:a=1[p1];"
    for i in range(1, nb):
        gap = CARD_GAP if ORDER[i] in TEXT_CARD_IDS else GAP
        fc += (f"aevalsrc=0:d={gap}[g{i}];"
               f"[p{i}][g{i}][{i}:a]concat=n=3:v=0:a=1[p{i + 1}];")
    fc += (f"[p{nb}]apad=pad_dur={TAIL}[narpsrc];[narpsrc]asplit=2[narp][narsub];"
           f"[{nb}:a]atrim=0:{total},afade=t=in:d={MUSIC_FADE_IN},"
           f"afade=t=out:st={max(0.0, total - MUSIC_FADE_OUT)}:d={MUSIC_FADE_OUT},"
           f"volume={MUSIC_VOLUME}[bed];"
           f"[narp][bed]amix=inputs=2:duration=first:normalize=0[a]")
    return fc


subprocess.run(
    ["ffmpeg", "-y"] + sum([["-i", str(clips[s])] for s in ORDER], []) +
    ["-i", str(ASSETS / "music_bed.mp3"),
     "-filter_complex", e03_audio_filter(),
     "-map", "[a]", "-ar", "44100", str(ASSETS / "audio_mix.m4a"),
     "-map", "[narsub]", "-ar", "44100", str(ASSETS / "narration_only.wav")],
    check=True, capture_output=True)
print("audio mixed")

subprocess.run(
    ["ffmpeg", "-y"] + sum([["-i", s] for s in segs], []) +
    ["-filter_complex",
     "".join(f"[{i}:v]" for i in range(len(segs))) +
     f"concat=n={len(segs)}:v=1:a=0[v]",
     "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(ASSETS / "video.mp4")],
    check=True, capture_output=True)
print("video concatenated")

# --- sidecar SRT: per-clip subtitle_gen, merged, offset to the timeline ---
from tools.subtitle.subtitle_gen import SubtitleGen  # noqa: E402
sg = SubtitleGen()
blocks, idx = [], 0
for sid in ORDER:
    beat = [x for x in all_segments if x["beat"] == sid]
    if not beat:
        continue
    res = sg.execute({"segments": beat, "format": "srt", "max_words_per_cue": 8,
                      "max_chars_per_line": 42, "corrections": {"shape": "shaped"},
                      "output_path": str(ASSETS / f"subs_{sid}.srt")})
    if not res.success:
        raise RuntimeError(f"subtitle_gen failed on {sid}: {res.error}")
    cues_text = Path(res.artifacts[0]).read_text().strip()
    if not cues_text:
        continue
    for cue in cues_text.split("\n\n"):
        lines = cue.strip().splitlines()
        if len(lines) < 2:
            continue
        idx += 1
        blocks.append(f"{idx}\n" + "\n".join(lines[1:]))
srt_text = "\n\n".join(blocks) + "\n"
(ASSETS / "subs.srt").write_text(srt_text)
SIDECAR_SRT.write_text(srt_text)
print(f"sidecar SRT: {idx} cues -> {SIDECAR_SRT}")

# --- final mux (NO subtitle burn; NO subtitle stream) ---
mux = ["ffmpeg", "-y", "-i", str(ASSETS / "video.mp4"), "-i", str(ASSETS / "audio_mix.m4a"),
       "-c:v", "libx264", "-crf", "18", "-c:a", "copy", "-shortest", str(OUT_MP4)]
subprocess.run(mux, check=True, capture_output=True)
print("muxed (burn_subtitles=False):", OUT_MP4)

# --- verify ---
fdur, vdur, adur = dur(OUT_MP4), dur(ASSETS / "video.mp4"), dur(ASSETS / "audio_mix.m4a")
print(f"final={fdur:.2f}s video={vdur:.2f}s audio={adur:.2f}s formula_total={total:.2f}s")
assert abs(fdur - min(vdur, adur)) < 0.3, f"mux drift: final={fdur:.2f} video={vdur:.2f} audio={adur:.2f}"

probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=index,codec_type", "-of", "csv=p=0", str(OUT_MP4)],
                       capture_output=True, text=True).stdout.strip()
print("streams:\n" + probe)
assert "subtitle" not in probe, "a subtitle stream was muxed in -- must be sidecar only"
assert probe.count("video") == 1 and probe.count("audio") == 1, f"unexpected streams: {probe}"

spot_dir = ASSETS / "_spotcheck"
spot_dir.mkdir(exist_ok=True)
times, acc = [0.5], 0.0
for sid in ORDER:
    sd = segdur[sid]
    if sid in TEXT_CARD_IDS:
        times.append(acc + sd * 0.55)
    acc += sd
# one representative frame inside each act + the closing fade
for sid in ("s1", "a1_7", "a2_9", "a3_17", "a4_18", "a5_7"):
    times.append(starts[sid] + 1.0)
times.append(fdur - 1.5)
times = sorted(set(round(x, 1) for x in times if 0 <= x < fdur))
for tt in times:
    subprocess.run(["ffmpeg", "-y", "-ss", f"{tt:.2f}", "-i", str(OUT_MP4),
                    "-frames:v", "1", str(spot_dir / f"f_{tt:05.1f}.jpg")],
                   check=True, capture_output=True)
print("spot frames:", ", ".join(f"{x:.1f}s" for x in times))

meta = {"scenes": {s: round(segdur[s], 2) for s in ORDER},
        "modes": {s: resolve_mode(s) for s in ORDER},
        "images": {s: resolve_image(s) for s in ORDER},
        "narr_starts": {k: round(v, 2) for k, v in starts.items()},
        "total_s": round(total, 2), "video_duration_s": round(vdur, 2),
        "audio_duration_s": round(adur, 2), "final_duration_s": round(fdur, 2),
        "fps": FPS, "burn_subtitles": BURN_SUBTITLES,
        "sidecar_srt": str(SIDECAR_SRT), "srt_cues": idx, "output": str(OUT_MP4)}
json.dump(meta, open(OUT_MP4.with_name(OUT_MP4.stem + "_meta.json"), "w"), indent=2)
print(f"COMPOSED: {OUT_MP4} ({fdur:.2f}s, {fdur/60:.2f} min) | SRT sidecar {idx} cues")
