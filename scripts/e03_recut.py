"""E03 re-cut: faster edit. The narration audio (audio_mix.m4a, 643.19s) is
NOT touched. Only the VIDEO track is rebuilt: each beat's on-screen time is
sliced into sub-segments of 2.5-6s, and each sub-segment shows a genuinely
different picture -- a new detail frame, or a hard crop into a different region
of the beat's own still (which reads as a fresh shot), never the same image
zoomed differently.

Reads meta (beat -> segdur), the primary frame per beat (from e03_compose
resolve), and a NEWFRAME map. Concats video, muxes against the existing
audio_mix.m4a. subtitles.srt is unchanged (timeline unchanged).
"""
import json, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from scripts.explainer_compose import dur  # noqa: E402

PROJ = REPO / "projects" / "ink-testimony-e03"
ASSETS = PROJ / "assets" / "e03"
OUT_MP4 = ASSETS / "ink-testimony-e03_episode.mp4"
FPS = 25
FADE_IN_FIRST, FADE_OUT_LAST = 0.8, 2.5
MINSEG, MAXSEG = 2.5, 5.8

meta = json.load(open(ASSETS / "ink-testimony-e03_episode_meta.json"))
SEGDUR = meta["scenes"]          # beat id -> seconds on screen (from the verified render)
PRIMARY = meta["images"]         # beat id -> primary png path
MODES = meta["modes"]
ORDER = list(SEGDUR.keys())
CARDS = {"c1", "c2", "c3", "c4", "c5"}
CARD_TEXT = {c: json.load(open(PROJ / "artifacts" / "script.json"))["sections"]
             and next(s["text"] for s in json.load(open(PROJ / "artifacts" / "script.json"))["sections"] if s["id"] == c)
             for c in CARDS}

# beat -> [extra frame ids] used as distinct sub-shots (in addition to crops of the primary)
NEWFRAME = {
    "s2":   ["n_s2c"],   # a turned page carrying a devil woodcut (headline cropped out)
    "a2_4": ["n_a2_4"],
    "a3_2": ["n_a3_2"],
    "a3_18": ["n_a3_18"],
    "a3_23": ["n_a3_23"],
    "a3_25": ["n_a3_25"],
    "a4_2": ["n_a4_2"],
    "a4_9": ["n_a4_9"],
    "a4_15": ["n_a4_15"],
    "a4_18": ["n_a4_18"],
    "a4_20": ["n_a4_20"],
    "a5_2": ["n_a5_2a", "n_a5_2b"],
    "a5_12": ["n_a5_12"],
}
DARK = set(json.load(open(PROJ / "artifacts" / "script.json"))["metadata"]["dark_register_beats"])

# beats that were HOLDS in the first render (showed the anchor's frame again).
# They must NOT re-show the anchor full-frame. s2 gets its own new frame; the
# rest open on a tight crop of the anchor so it reads as a distinct detail shot.
HELD_ANCHOR = {"s2": "s1", "a1_5": "a1_4", "a1_12": "a1_11", "a2_14": "a2_13",
               "a3_5": "a3_4", "a3_9": "a3_8", "a3_26": "a3_25", "a5_16": "a5_1"}

# beat -> composited editorial DATE CARD text (Georgia, over the dimmed anchor
# frame; drawtext, NOT a generated image -- a generated calendar would put the
# month/year in the frame as text, which the guard forbids). Display text keeps
# proper numerals per the brief. s2 line: "The month is January, the year
# nineteen oh nine." -> verified January 1909 (the Jersey Devil week / the
# witness-object volume).
DATECARD = {"s2": "JANUARY 1909"}

# 3 crop windows (x0,y0,w,h as fractions) -> each reads as a different shot
CROPS = [
    (0.06, 0.05, 0.60, 0.60),   # upper-left detail
    (0.22, 0.20, 0.56, 0.56),   # centre push
    (0.36, 0.34, 0.60, 0.60),   # lower-right detail
]


def n_sub(d):
    if d <= MAXSEG:
        return 1
    return max(2, min(6, round(d / 4.0)))


def render_zoom(img, secs, out, mode):
    frames = max(1, round(secs * FPS))
    z = {"in": "min(1.001+0.055*on/%d,1.06)" % frames,
         "out": "max(1.06-0.055*on/%d,1.001)" % frames,
         "micro": "min(1.001+0.02*on/%d,1.02)" % frames}.get(mode, "1.0")
    fi = fo = ""
    vf = (f"scale=1920:1080,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
          f"d={frames}:s=1280x720:fps={FPS},setpts=PTS-STARTPTS")
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(img), "-vf", vf,
                    "-frames:v", str(frames + 1), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)],
                   check=True, capture_output=True)


def render_crop(img, secs, out, box, drift):
    frames = max(1, round(secs * FPS))
    x0, y0, w, h = box
    # gentle drift on the crop so it isn't dead-static
    z = "min(1.0+0.03*on/%d,1.03)" % frames if drift else "1.0"
    vf = (f"crop=iw*{w}:ih*{h}:iw*{x0}:ih*{y0},scale=1920:1080,"
          f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
          f"d={frames}:s=1280x720:fps={FPS},setpts=PTS-STARTPTS")
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(img), "-vf", vf,
                    "-frames:v", str(frames + 1), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)],
                   check=True, capture_output=True)


def render_card(img, text, secs, out):
    tf = ASSETS / "_cardtext.txt"
    tf.write_text(text)
    frames = max(1, round(secs * FPS))
    vf = (f"scale=1920:1080,zoompan=z='1.0':d={frames}:s=1280x720:fps={FPS},setpts=PTS-STARTPTS,"
          f"eq=brightness=-0.22,"
          f"drawtext=fontfile=/System/Library/Fonts/Supplemental/Georgia.ttf:textfile={tf}:"
          f"fontsize=30:fontcolor=0xF2EDE4:box=1:boxcolor=black@0.62:boxborderw=18:"
          f"x=(w-text_w)/2:y=(h-text_h)/2,"
          f"fade=t=in:st=0:d=0.35,fade=t=out:st={secs - 0.35:.3f}:d=0.35")
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(img), "-vf", vf,
                    "-frames:v", str(frames + 1), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)],
                   check=True, capture_output=True)


segs = []
idx = 0
plan = []
n = len(ORDER)
for bi, beat in enumerate(ORDER):
    total = SEGDUR[beat]
    primary = PRIMARY[beat]
    if beat.startswith("e03_"):
        primary = str(ASSETS / Path(primary).name)
    primary = str(ASSETS / Path(primary).name)
    is_card = beat in CARDS

    if is_card:
        seg = ASSETS / f"rc_{idx:03d}.mp4"
        render_card(primary, CARD_TEXT[beat], total, seg)
        segs.append(str(seg)); plan.append((beat, "card", round(total, 1), Path(primary).name)); idx += 1
        continue

    k = n_sub(total)
    parts = [total / k] * k
    if beat in DATECARD and k >= 2:
        # keep the date card tight (~2.8s), give the rest to the following shots
        card_s = min(2.8, total * 0.4)
        parts = [card_s] + [(total - card_s) / (k - 1)] * (k - 1)
    extras = NEWFRAME.get(beat, [])
    dark = beat in DARK
    held = beat in HELD_ANCHOR
    # held beats: first shot is a NEW frame (s2) or a tight crop of the anchor,
    # never the anchor full-frame again
    first_shot = None
    if beat in DATECARD:
        # date card over the dimmed anchor frame; shot 1+ uses this beat's
        # NEWFRAME extra(s) first (a distinct picture), then crops of the anchor
        anchor_img = str(ASSETS / f"e03_{HELD_ANCHOR.get(beat, beat)}.png")
        first_shot = ("datecard", anchor_img, DATECARD[beat])
        primary = anchor_img
    elif held:
        if extras:
            first_shot = ("zoom", str(ASSETS / f"e03_{extras[0]}.png"), "in")
            extras = extras[1:]
        else:
            anchor_img = str(ASSETS / f"e03_{HELD_ANCHOR[beat]}.png")
            first_shot = ("crop", anchor_img, CROPS[2])
            primary = anchor_img  # later crops pull from the anchor too
    shots = []
    ei = ci = 0
    for si in range(k):
        if si == 0:
            shots.append(first_shot if first_shot else
                         ("zoom", primary, "in" if bi % 2 == 0 else "out"))
        elif ei < len(extras):
            shots.append(("zoom", str(ASSETS / f"e03_{extras[ei]}.png"), "in"))
            ei += 1
        else:
            # crop of primary (dark frames: gentler, centre-biased crop only)
            box = CROPS[1] if dark else CROPS[ci % 3]
            shots.append(("crop", primary, box))
            ci += 1
    for si, (kind, img, arg) in enumerate(shots):
        seg = ASSETS / f"rc_{idx:03d}.mp4"
        secs = parts[si]
        if seg.exists() and dur(seg) and abs(dur(seg) - secs) < 0.08 and kind != "datecard":
            segs.append(str(seg)); plan.append((beat, f"{kind}", round(secs, 1), Path(img).name)); idx += 1
            continue
        if kind == "zoom":
            render_zoom(img, secs, seg, arg)
        elif kind == "datecard":
            render_card(img, arg, secs, seg)
        else:
            render_crop(img, secs, seg, arg, drift=True)
        segs.append(str(seg))
        plan.append((beat, f"{kind}:{arg if kind=='crop' else arg}", round(secs, 1), Path(img).name))
        idx += 1

# fade in on the very first segment, fade out on the very last -- re-encode those two
def refade(path, fade_in=0.0, fade_out=0.0, out=None):
    d = dur(path)
    vf = []
    if fade_in:
        vf.append(f"fade=t=in:st=0:d={fade_in}")
    if fade_out:
        vf.append(f"fade=t=out:st={max(0.0, d - fade_out):.3f}:d={fade_out}")
    out = out or path
    tmp = Path(str(path) + ".f.mp4")
    subprocess.run(["ffmpeg", "-y", "-i", str(path), "-vf", ",".join(vf),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(tmp)], check=True, capture_output=True)
    tmp.replace(out)

refade(segs[0], fade_in=FADE_IN_FIRST)
refade(segs[-1], fade_out=FADE_OUT_LAST)

print(f"{len(segs)} video sub-segments (was 87). rendering concat...", flush=True)
concat = ASSETS / "video_recut.mp4"
subprocess.run(["ffmpeg", "-y"] + sum([["-i", s] for s in segs], []) +
               ["-filter_complex", "".join(f"[{i}:v]" for i in range(len(segs))) +
                f"concat=n={len(segs)}:v=1:a=0[v]", "-map", "[v]",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(concat)],
               check=True, capture_output=True)

subprocess.run(["ffmpeg", "-y", "-i", str(concat), "-i", str(ASSETS / "audio_mix.m4a"),
                "-c:v", "libx264", "-crf", "18", "-c:a", "copy", "-shortest", str(OUT_MP4)],
               check=True, capture_output=True)

fdur, vdur, adur = dur(OUT_MP4), dur(concat), dur(ASSETS / "audio_mix.m4a")
probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
                        "-of", "csv=p=0", str(OUT_MP4)], capture_output=True, text=True).stdout.strip()
print(f"final={fdur:.2f}s video={vdur:.2f}s audio={adur:.2f}s  streams={probe.split()}", flush=True)
assert "subtitle" not in probe and probe.count("video") == 1 and probe.count("audio") == 1
assert abs(fdur - min(vdur, adur)) < 0.35, f"drift {fdur} {vdur} {adur}"

# per-shot hold report
holds = [p[2] for p in plan]
over = [(p[0], p[2]) for p in plan if p[2] > 6.0]
print(f"sub-segments: {len(plan)} | mean {sum(holds)/len(holds):.1f}s | max {max(holds):.1f}s | over 6s: {len(over)} {over}", flush=True)
json.dump({"plan": plan, "final_s": round(fdur, 2), "segments": len(segs)},
          open(ASSETS / "recut_plan.json", "w"), indent=2)

# refresh spot frames + contact sheet inputs
spot = ASSETS / "_spotcheck_recut"
spot.mkdir(exist_ok=True)
for tt in [0.6, 16.0, 40.0, 95.0, 150.0, 300.0, 360.0, 470.0, 540.0, 600.0, fdur - 1.5]:
    if 0 <= tt < fdur:
        subprocess.run(["ffmpeg", "-y", "-ss", f"{tt:.2f}", "-i", str(OUT_MP4), "-frames:v", "1",
                        str(spot / f"f_{tt:06.1f}.jpg")], check=True, capture_output=True)
print("COMPOSED (recut):", OUT_MP4, f"{fdur/60:.2f} min", flush=True)
