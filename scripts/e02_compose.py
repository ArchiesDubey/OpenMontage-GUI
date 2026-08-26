"""E02-specific composer: 'Ink & Testimony E02 -- The Examination Table'.

Reuses explainer_compose.py's validated primitives (zoompan_segment,
card_segment, dur, ts, transcribe_section, audio_filter) but implements its
own timeline logic because E02's structure differs from the generic runner's
assumption: EVERY scene here (including all 15 text_card beats) has its own
real, independently-generated narration clip -- none of them "borrow" time by
splitting an adjacent clip. This makes the timeline math simpler (uniform
lead/clip/gap chain, no split-card branch needed) rather than harder.

Image resolution for REUSE/held/bookend scenes is done via an explicit map
(not path-sniffing in description text), since those scenes intentionally
don't carry a literal generate-path in their required_assets description.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts.explainer_compose import dur, zoompan_segment, card_segment, transcribe_section, FORCE_STYLE, audio_filter  # noqa: E402

PROJ = REPO / "projects" / "ink-testimony-e02"
ASSETS = PROJ / "assets" / "e02"
OUT_MP4 = ASSETS / "ink-testimony-e02_episode.mp4"
FPS = 25
LEAD, GAP, CARD_GAP, TAIL = 0.7, 0.55, 0.8, 6.0  # tail extended for a deliberate closing hold
MUSIC_VOLUME, MUSIC_FADE_IN, MUSIC_FADE_OUT = 0.13, 1.5, 3.0
FADE_IN_FIRST, FADE_OUT_LAST = 0.8, 1.5

# script_section_id -> the anchor script_section_id whose generated frame it reuses.
REUSE = {
    "s2": "s1", "s3": "s1",
    "s5": "s4", "s7": "s4", "s8": "s4",
    "s12": "s11",
    "s14": "s13", "s16": "s13", "s17": "s13", "s18": "s13",
    "s20": "s19",
    "s22": "s21",
    "s26": "s25",
    "s29": "s27",
    "s32": "s31", "s33": "s31", "s34": "s31",
    "s36": "s35",
    "s38": "s37",
    "s40": "s39", "s41": "s39",
    "s44": "s42",
    "s46": "s45",
    "s49": "s48", "s50": "s48",
    "s52": "s51", "s54": "s51", "s55": "s51",
    "s57": "s56",
    "s60": "s59",
    "s62": "s61", "s63": "s61",
    "s65": "s64",
    "s69": "s67", "s70": "s67",
    "s73": "s71",
    "s75": "s74", "s77": "s74",
    "s78": "s1", "s79": "s1", "s80": "s1", "s81": "s1",
}
ANCHOR_MODE = {  # script_section_id -> zoompan mode, for the 29 anchors + bookends
    "s1": "in", "s4": "in", "s9": "static", "s11": "out", "s13": "in",
    "s19": "in", "s21": "out", "s24": "static", "s25": "in", "s27": "in",
    "s30": "micro", "s31": "in", "s35": "static", "s37": "static", "s39": "in",
    "s42": "micro", "s45": "static", "s47": "out", "s48": "in", "s51": "micro",
    "s56": "in", "s58": "static", "s59": "static", "s61": "static", "s64": "micro",
    "s66": "out", "s67": "out", "s71": "in", "s74": "in",
}
REUSE_MODE = "micro"  # held beats: subtler continued motion, distinct from fresh anchor cuts

script = json.load(open(PROJ / "artifacts" / "script.json"))
plan = json.load(open(PROJ / "artifacts" / "scene_plan.json"))
sections = {s["id"]: s for s in script["sections"]}
scenes_by_sec = {sc["script_section_id"]: sc for sc in plan["scenes"]}

TEXT_CARD_IDS = {sc["script_section_id"] for sc in plan["scenes"] if sc["type"] == "text_card"}
ORDER = [s["id"] for s in sorted(script["sections"], key=lambda s: s["start_seconds"])]


# Card scenes (both the 5 act-break cards and the 10 stat/date cards) have no
# generated frame of their own -- they render as a dimmed overlay on the most
# recently shown non-card frame, exactly like E01's scene-11/13 pattern.
CARD_BACKDROP = {}
_last_img_sid = None
for _sid in ORDER:
    if _sid in TEXT_CARD_IDS:
        CARD_BACKDROP[_sid] = _last_img_sid
    else:
        _last_img_sid = REUSE.get(_sid, _sid)


def resolve_image(sid):
    if sid in TEXT_CARD_IDS:
        anchor = CARD_BACKDROP[sid]
    else:
        anchor = REUSE.get(sid, sid)
    return str(ASSETS / f"e02_{anchor}.png")


def resolve_mode(sid):
    if sid in TEXT_CARD_IDS:
        return "card"
    if sid in REUSE:
        return REUSE_MODE
    return ANCHOR_MODE[sid]


def card_text_for(sid):
    return sections[sid]["text"]


# --- timeline: every beat has its own clip; uniform lead/clip/gap/tail chain ---
# BUGFIX: ElevenLabs MP3s carry ~35ms of LAME encoder-delay/padding that makes
# ffprobe's container duration read LONGER than what actually decodes and
# plays -- across 86 clips this alone caused a ~3s audio/video desync (found
# on this project). Fix: decode every clip to WAV once (sample-accurate,
# cached) and derive ALL timing (ndurs, starts, segdur, video render length)
# from the WAV, so video and audio are built from the same true numbers.
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

segdur = {sid: ndurs[sid] + (TAIL if i == len(ORDER) - 1 else (CARD_GAP if sid in TEXT_CARD_IDS else GAP))
          + (LEAD if i == 0 else 0)
          for i, sid in enumerate(ORDER)}
assert abs(sum(segdur.values()) - total) < 0.05, \
    f"timeline mismatch: segments={sum(segdur.values()):.3f} audio={total:.3f}"
print(f"timing assert OK: {sum(segdur.values()):.2f}s == {total:.2f}s")

# --- transcription (cached) + offsets, for subtitle burning on narration beats ---
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
    img = resolve_image(sid)
    mode = resolve_mode(sid)
    if mode == "card":
        card_segment(img, card_text_for(sid), sd, ASSETS, seg, FPS)
    else:
        zoompan_segment(img, sd, seg, mode, FPS,
                        fade_in=FADE_IN_FIRST if i == 0 else 0.0,
                        fade_out=FADE_OUT_LAST if i == n - 1 else 0.0)
    segs.append(str(seg))
    print("seg", sid, mode, f"{sd:.2f}s")

# --- narration chain + music bed ---
cfg = {"lead": LEAD, "gap": GAP, "tail": TAIL, "music_volume": MUSIC_VOLUME,
       "music_fade_in": MUSIC_FADE_IN, "music_fade_out": MUSIC_FADE_OUT}


def e02_audio_filter():
    """Like explainer_compose.audio_filter, but with per-clip gaps (cards use
    CARD_GAP instead of the uniform GAP) matching this project's segdur math."""
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
     "-filter_complex", e02_audio_filter(),
     "-map", "[a]", "-ar", "44100", str(ASSETS / "audio_mix.m4a"),
     "-map", "[narsub]", "-ar", "44100", str(ASSETS / "narration_only.wav")],
    check=True, capture_output=True)
print("audio mixed")

# --- concat video ---
subprocess.run(
    ["ffmpeg", "-y"] + sum([["-i", s] for s in segs], []) +
    ["-filter_complex",
     "".join(f"[{i}:v]" for i in range(len(segs))) +
     f"concat=n={len(segs)}:v=1:a=0[v]",
     "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
     str(ASSETS / "video.mp4")],
    check=True, capture_output=True)
print("video concatenated")

# --- subtitles: per-clip subtitle_gen, merged ---
from tools.subtitle.subtitle_gen import SubtitleGen  # noqa: E402
sg = SubtitleGen()
blocks, idx = [], 0
for sid in ORDER:
    beat = [x for x in all_segments if x["beat"] == sid]
    if not beat:
        continue
    res = sg.execute({
        "segments": beat, "format": "srt", "max_words_per_cue": 8,
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
subs = ASSETS / "subs.srt"
subs.write_text("\n\n".join(blocks) + "\n")
print(f"subs: {idx} cues")

# --- final mux with burned subtitles ---
sub_escaped = str(subs).replace(":", "\\:")
subprocess.run([
    "ffmpeg", "-y", "-i", str(ASSETS / "video.mp4"),
    "-i", str(ASSETS / "audio_mix.m4a"),
    "-vf", f"subtitles={sub_escaped}:force_style='{FORCE_STYLE}'",
    "-c:v", "libx264", "-crf", "18", "-c:a", "copy", "-shortest",
    str(OUT_MP4)], check=True, capture_output=True)
print("muxed:", OUT_MP4)

# --- verify ---
fdur = dur(OUT_MP4)
vdur = dur(ASSETS / "video.mp4")
adur = dur(ASSETS / "audio_mix.m4a")
print(f"final={fdur:.2f}s video={vdur:.2f}s audio={adur:.2f}s formula_total={total:.2f}s")
assert abs(fdur - min(vdur, adur)) < 0.3, \
    f"mux drift: final={fdur:.2f} video={vdur:.2f} audio={adur:.2f}"

spot_dir = ASSETS / "_spotcheck"
spot_dir.mkdir(exist_ok=True)
times = [0.5]
acc = 0.0
for sid in ORDER:
    sd = segdur[sid]
    if sid in TEXT_CARD_IDS:
        times.append(acc + sd * 0.6)
    acc += sd
times += [vdur - 2.0]
for tt in sorted(set(round(x, 1) for x in times if 0 <= x < vdur)):
    subprocess.run(["ffmpeg", "-y", "-ss", f"{tt:.2f}", "-i", str(OUT_MP4),
                    "-frames:v", "1", str(spot_dir / f"f_{tt:.1f}.jpg")],
                   check=True, capture_output=True)
print("spot frames:", ", ".join(f"{x:.1f}s" for x in sorted(set(round(x,1) for x in times if 0<=x<vdur))))

meta = {
    "scenes": {sid: round(segdur[sid], 2) for sid in ORDER},
    "modes": {sid: resolve_mode(sid) for sid in ORDER},
    "images": {sid: resolve_image(sid) for sid in ORDER},
    "narr_starts": {k: round(v, 2) for k, v in starts.items()},
    "total_s": round(total, 2),
    "video_duration_s": round(vdur, 2),
    "audio_duration_s": round(adur, 2),
    "final_duration_s": round(fdur, 2),
    "fps": FPS,
    "output": str(OUT_MP4),
}
meta_p = OUT_MP4.with_name(OUT_MP4.stem + "_meta.json")
json.dump(meta, open(meta_p, "w"), indent=2)
print(f"COMPOSED: {OUT_MP4} ({fdur:.2f}s) | meta -> {meta_p}")
