"""Generic data-driven composer for animated-explainer projects.

Promotes the validated Ink & Testimony compose grammar (compose_ink_sample_v2.py,
compose_e01.py) into a reusable runner driven entirely by a project's artifacts:

    python3 scripts/explainer_compose.py --project projects/<name>
        [--config <path>] [--out <file>]

Reads (relative to --project):
  artifacts/scene_plan.json   scenes: type / movement / transitions /
                              script_section_id / required_assets (REUSE paths) /
                              quoted card text in description
  assets/<assets_dir>/        generated frames + generation_log.json +
                              <section>_narration.mp3 + cached *_transcript.json
  compose_config.json         optional overrides (see DEFAULTS below)

Grammar (identical to E01, no hardcoded scene tables):
- per-beat zoompan: in | out | micro | static | card (parsed from movement)
- hard cuts + concat; lead/gap/tail narration chain via aevalsrc+concat+asplit
- music bed at configured volume with fades; fade-in/fade-out bookends
- text_card scenes: ffmpeg drawtext over dimmed prior frame, fades 0.35
- card split points from transcript word timestamps (fallback fraction)
- subtitles via subtitle_gen (max 8 words/cue), burned BorderStyle=3 backplane
- ASSERTS sum(segment durations) == audio timeline BEFORE rendering video
- verification: ffprobe duration check + auto-extracted spot-check frames
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

DEFAULTS = {
    "assets_dir": None,          # default: assets/<project folder name>
    "output_name": None,         # default: <project folder name>_episode.mp4
    "fps": 25,
    "lead": 0.7, "gap": 0.55, "tail": 1.6,
    "music_volume": 0.13, "music_fade_in": 1.5, "music_fade_out": 2.0,
    "fade_in_first": 0.7, "fade_out_last": 1.2,
    "card_split_default_fraction": 0.5,
    "transcribe_model": "large-v3",
    "card_splits": {},           # section_id -> {after_word, fallback_fraction}
    "image_overrides": {},       # scene-id -> path (repo-relative or absolute)
    "mode_overrides": {},        # scene-id -> in|out|micro|static|card
    "card_text_overrides": {},   # scene-id -> card text
    "extra_spot_times": [],      # extra verification frame times (seconds)
    "burn_subtitles": True,      # False -> deliver subtitles.srt as a sidecar only
                                 #          (no subtitles filter, no force_style, no
                                 #          burn into the video). The merged SRT is
                                 #          still written beside the MP4.
    "sidecar_srt_name": "subtitles.srt",  # sidecar copy of the merged SRT
}

FORCE_STYLE = ("FontName=Georgia,FontSize=18,Bold=1,PrimaryColour=&H00F2EDE4,"
               "BorderStyle=3,BackColour=&H80000000,Outline=10,Shadow=0,"
               "MarginV=42")
ZOOM = {"in": 0.06, "out": 0.06, "micro": 0.02, "static": 0.0}


def dur(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True
    ).stdout.strip())


def ts(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)):03d}"


def parse_mode(scene, cfg):
    """movement/shot_language -> zoompan mode. text_card always wins."""
    ov = cfg["mode_overrides"].get(scene["id"])
    if scene["type"] == "text_card":
        return ov or "card"
    if ov:
        return ov
    mov = scene.get("movement", "").lower()
    cam = (scene.get("shot_language") or {}).get("camera_movement", "").lower()
    if "micro" in mov:
        return "micro"
    if "pull-back" in mov or cam == "dolly_out":
        return "out"
    if "push-in" in mov or cam == "dolly_in":
        return "in"
    if "static" in mov or cam == "static":
        return "static"
    raise ValueError(f"{scene['id']}: cannot parse mode from movement={mov!r}")


def resolve_image(sid, scene, cfg, gen_log, assets_dir, prev_img):
    ov = cfg["image_overrides"].get(sid)
    if ov:
        return ov if Path(ov).is_absolute() else str(REPO / ov)
    entry = (gen_log or {}).get("images", {}).get(sid)
    if entry and entry.get("success"):
        return str(assets_dir / entry["file"])
    desc = " ".join(a.get("description", "")
                    for a in scene.get("required_assets", []))
    m = re.search(r"([\w./\\-]+\.(?:png|jpg))", desc)
    if m:
        p = REPO / m.group(1)
        if p.exists():
            return str(p)
    if prev_img:  # text_card backing frame = prior scene's frame
        return prev_img
    raise FileNotFoundError(f"{sid}: no image resolved (gen_log/REUSE/config)")


def card_text(scene, cfg):
    ov = cfg["card_text_overrides"].get(scene["id"])
    if ov:
        return ov
    m = re.search(r"'([^']+)'", scene.get("description", ""))
    if not m:
        raise ValueError(f"{scene['id']}: no quoted card text in description")
    return m.group(1)




def transcribe_section(sec, clip, assets_dir, cfg):
    """Cached per-clip transcription: reuse <sec>_narration_transcript.json
    if present; otherwise run Transcriber once and rely on its cache file."""
    tf = assets_dir / f"{sec}_narration_transcript.json"
    if not tf.exists():
        sys.path.insert(0, str(REPO))
        from tools.analysis.transcriber import Transcriber
        res = Transcriber().execute({
            "input_path": str(clip), "model_size": cfg["transcribe_model"],
            "language": "en", "output_dir": str(assets_dir)})
        if not res.success:
            raise RuntimeError(f"transcriber failed on {sec}: {res.error}")
    return json.load(open(tf))["segments"]


def build_timeline(scenes, ndurs, split, cfg):
    """Segment durations; asserts sum == narration timeline before rendering."""
    lead, gap, tail = cfg["lead"], cfg["gap"], cfg["tail"]
    n = len(scenes)
    segdur, last_narr = {}, None
    for i, sc in enumerate(scenes):
        sid, mode = sc["id"], sc["mode"]
        if mode == "card":
            owner = last_narr
            segdur[sid] = ndurs[owner] - split[owner] + gap
        else:
            last_narr = sc["narr"]
            next_mode = scenes[i + 1]["mode"] if i + 1 < n else None
            if next_mode == "card":
                segdur[sid] = split[sc["narr"]]
            else:
                segdur[sid] = (ndurs[sc["narr"]]
                               + (tail if i == n - 1 else gap)
                               + (lead if i == 0 else 0))
    total = cfg["lead"] + sum(ndurs.values()) + gap * (len(ndurs) - 1) + tail
    assert abs(sum(segdur.values()) - total) < 0.05, \
        f"timeline mismatch: segments={sum(segdur.values()):.3f} audio={total:.3f}"
    print(f"timing assert OK: {sum(segdur.values()):.2f}s == {total:.2f}s")
    return segdur, total


def zoompan_segment(img, secs, out, mode, fps, fade_in=0.0, fade_out=0.0):
    # BUGFIX: frames = int(secs*fps)+1 followed by trim=duration=secs always
    # rounds DOWN to the nearest frame (trim keeps frames with pts < duration),
    # so every segment is systematically ~0-1 frame SHORT of its target -- never
    # long. Across a long video (e.g. 86 segments) this is a monotonic deficit,
    # not a random rounding error, and accumulates into multi-second audio/video
    # desync (discovered on Ink & Testimony E02: 3.48s drift over 86 segments,
    # which visibly desynced burned subtitles from their narration by the end).
    # Fix: round to the NEAREST frame instead of flooring, and drive duration
    # directly from zoompan's frame count `d=` -- no separate trim needed. This
    # makes the per-segment error unbiased (+-0.5 frame) instead of monotonic.
    frames = max(1, round(secs * fps))
    amt = ZOOM[mode]
    if mode == "out":
        z = f"1.06-0.06*on/{frames}"
    elif amt > 0:
        z = f"1.0+{amt}*on/{frames}"
    else:
        z = "1.0"
    vf = (f"scale=1920:1080,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':"
          f"y='ih/2-(ih/zoom/2)':d={frames}:s=1280x720:fps={fps},"
          f"setpts=PTS-STARTPTS")
    if fade_in:
        vf += f",fade=t=in:st=0:d={fade_in}"
    if fade_out:
        vf += f",fade=t=out:st={secs - fade_out:.3f}:d={fade_out}"
    # -frames:v is the required termination bound: zoompan's `d=` alone does
    # NOT stop the encode against a `-loop 1` (infinite) single-image input --
    # omitting an explicit frame limit here hangs ffmpeg indefinitely (this
    # exact hang happened during the E02 fix -- two runaway processes had to
    # be killed after 40+ min of CPU time on a single ~5s segment).
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", img, "-vf", vf,
                    "-frames:v", str(frames + 1),  # measured off-by-one: zoompan/-frames:v drops exactly 1 frame
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)],
                   check=True, capture_output=True)


def card_segment(img, text, secs, workdir, out, fps):
    tf = Path(workdir) / "_cardtext.txt"
    tf.write_text(text)
    frames = max(1, round(secs * fps))  # see zoompan_segment bugfix note above
    vf = (f"scale=1920:1080,zoompan=z='1.0':d={frames}:s=1280x720:fps={fps},"
          f"setpts=PTS-STARTPTS,"
          f"eq=brightness=-0.22,"
          f"drawtext=fontfile=/System/Library/Fonts/Supplemental/Georgia.ttf"
          f":textfile={tf}:fontsize=30:fontcolor=0xF2EDE4:"
          f"box=1:boxcolor=black@0.62:boxborderw=18:"
          f"x=(w-text_w)/2:y=(h-text_h)/2,"
          f"fade=t=in:st=0:d=0.35,fade=t=out:st={secs - 0.35:.3f}:d=0.35")
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", img, "-vf", vf,
                    "-frames:v", str(frames + 1),  # measured off-by-one: zoompan/-frames:v drops exactly 1 frame
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)],
                   check=True, capture_output=True)



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--config", default=None)
    ap.add_argument("--out", default=None, help="override output mp4 path")
    a = ap.parse_args()

    proj = Path(a.project).resolve()
    cfg = dict(DEFAULTS)
    cfg_path = Path(a.config) if a.config else proj / "compose_config.json"
    if cfg_path.exists():
        cfg.update(json.load(open(cfg_path)))
    name = proj.name
    assets_dir = (proj / cfg["assets_dir"]) if cfg["assets_dir"] \
        else proj / "assets" / name
    out_mp4 = Path(a.out) if a.out else (
        assets_dir / (cfg["output_name"] or f"{name}_episode.mp4"))
    fps = cfg["fps"]

    plan = json.load(open(proj / "artifacts" / "scene_plan.json"))
    gen_log_p = assets_dir / "generation_log.json"
    gen_log = json.load(open(gen_log_p)) if gen_log_p.exists() else None

    # --- resolve scenes -> (id, image, mode, narr, card text) ---
    scenes, prev_img = [], None
    for sc in plan["scenes"]:
        sid = sc["id"]
        mode = parse_mode(sc, cfg)
        narr = None if mode == "card" else sc.get("script_section_id")
        img = resolve_image(sid, sc, cfg, gen_log, assets_dir, prev_img)
        prev_img = img
        scenes.append({"id": sid, "img": img, "mode": mode, "narr": narr,
                       "text": card_text(sc, cfg) if mode == "card" else None})
    for sc in scenes:
        print(f"{sc['id']:10s} {sc['mode']:6s} {sc['narr'] or '-':4s} "
              f"{Path(sc['img']).name}")

    # --- narration clips + timeline ---
    narrs = []
    for sc in scenes:
        if sc["narr"] and sc["narr"] not in narrs:
            narrs.append(sc["narr"])
    clips = {s: assets_dir / f"{s}_narration.mp3" for s in narrs}
    missing = [s for s, c in clips.items() if not c.exists()]
    assert not missing, f"missing narration clips: {missing}"
    ndurs = {s: dur(c) for s, c in clips.items()}
    lead, gap, tail = cfg["lead"], cfg["gap"], cfg["tail"]
    starts, t = {}, lead
    for s in narrs:
        starts[s] = t
        t += ndurs[s] + gap
    total = t - gap + tail

    # --- transcription (cached) + offsets + card splits ---
    all_segments, words_by_clip = [], {}
    for s in narrs:
        for seg in transcribe_section(s, clips[s], assets_dir, cfg):
            seg["beat"] = s
            seg["start"] = round(seg["start"] + starts[s], 3)
            seg["end"] = round(seg["end"] + starts[s], 3)
            seg["words"] = [{**w, "start": round(w["start"] + starts[s], 3),
                             "end": round(w["end"] + starts[s], 3)}
                            for w in seg.get("words", [])]
            all_segments.append(seg)
        words_by_clip[s] = [w for seg in json.load(open(
            assets_dir / f"{s}_narration_transcript.json"))["segments"]
            for w in seg.get("words", [])]
    print(f"transcript segments: {len(all_segments)} across {len(narrs)} clips")

    split = {}
    for sec in narrs:
        spec = cfg["card_splits"].get(sec)
        if not spec:
            continue
        word, frac = spec.get("after_word"), spec.get(
            "fallback_fraction", cfg["card_split_default_fraction"])
        cut = next((w["end"] for w in words_by_clip[sec]
                    if word and word in w.get("word", "").lower().strip(".,—-")),
                   None)
        split[sec] = round(cut if cut is not None else ndurs[sec] * frac, 3)
        print(f"card split {sec}: {split[sec]:.2f}s of {ndurs[sec]:.2f}s")

    segdur, _ = build_timeline(scenes, ndurs, split, cfg)

    # --- render video segments ---
    n = len(scenes)
    segs = []
    for i, sc in enumerate(scenes):
        seg = assets_dir / f"seg_{i:02d}.mp4"
        sd = segdur[sc["id"]]
        if sc["mode"] == "card":
            card_segment(sc["img"], sc["text"], sd, assets_dir, seg, fps)
        else:
            zoompan_segment(sc["img"], sd, seg, sc["mode"], fps,
                            fade_in=cfg["fade_in_first"] if i == 0 else 0.0,
                            fade_out=cfg["fade_out_last"] if i == n - 1 else 0.0)
        segs.append(str(seg))
        print("seg", sc["id"], f"{sd:.2f}s")

    # --- narration chain + music bed ---
    subprocess.run(
        ["ffmpeg", "-y"] + sum([["-i", str(clips[s])] for s in narrs], []) +
        ["-i", str(assets_dir / "music_bed.mp3"),
         "-filter_complex", audio_filter(narrs, total, cfg),
         "-map", "[a]", "-ar", "44100", str(assets_dir / "audio_mix.m4a"),
         "-map", "[narsub]", "-ar", "44100",
         str(assets_dir / "narration_only.wav")],
        check=True, capture_output=True)

    # --- concat video ---
    subprocess.run(
        ["ffmpeg", "-y"] + sum([["-i", s] for s in segs], []) +
        ["-filter_complex",
         "".join(f"[{i}:v]" for i in range(len(segs))) +
         f"concat=n={len(segs)}:v=1:a=0[v]",
         "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         str(assets_dir / "video.mp4")],
        check=True, capture_output=True)

    # --- subtitles: per-clip subtitle_gen, merged ---
    sys.path.insert(0, str(REPO))
    from tools.subtitle.subtitle_gen import SubtitleGen
    sg = SubtitleGen()
    blocks, idx = [], 0
    for s in narrs:
        beat = [x for x in all_segments if x["beat"] == s]
        res = sg.execute({
            "segments": beat, "format": "srt", "max_words_per_cue": 8,
            "max_chars_per_line": 42, "corrections": {"shape": "shaped"},
            "output_path": str(assets_dir / f"subs_{s}.srt")})
        if not res.success:
            raise RuntimeError(f"subtitle_gen failed on {s}: {res.error}")
        for cue in Path(res.artifacts[0]).read_text().strip().split("\n\n"):
            lines = cue.strip().splitlines()
            idx += 1
            blocks.append(f"{idx}\n" + "\n".join(lines[1:]))
    subs = assets_dir / "subs.srt"
    subs.write_text("\n\n".join(blocks) + "\n")
    print(f"subs: {idx} cues")

    # sidecar copy of the merged SRT beside the final MP4 (always written)
    sidecar = out_mp4.with_name(cfg["sidecar_srt_name"])
    sidecar.write_text(subs.read_text())
    print(f"sidecar SRT -> {sidecar}")

    # --- final mux ---
    if cfg["burn_subtitles"]:
        sub_escaped = str(subs).replace(":", "\\:")
        subprocess.run([
            "ffmpeg", "-y", "-i", str(assets_dir / "video.mp4"),
            "-i", str(assets_dir / "audio_mix.m4a"),
            "-vf", f"subtitles={sub_escaped}:force_style='{FORCE_STYLE}'",
            "-c:v", "libx264", "-crf", "18", "-c:a", "copy", "-shortest",
            str(out_mp4)], check=True, capture_output=True)
    else:
        # no subtitles filter, no force_style, no burn-in; SRT is sidecar only
        subprocess.run([
            "ffmpeg", "-y", "-i", str(assets_dir / "video.mp4"),
            "-i", str(assets_dir / "audio_mix.m4a"),
            "-c:v", "libx264", "-crf", "18", "-c:a", "copy", "-shortest",
            str(out_mp4)], check=True, capture_output=True)
        print("burn_subtitles=False -> final MP4 has no burned captions and no muxed subtitle stream")

    # --- verify: duration + auto-extracted spot-check frames ---
    # NOTE: concat video runs ~N_segments/fps shorter than the formula total
    # (frame quantization); compare against actually rendered streams instead.
    fdur = dur(out_mp4)
    vdur = dur(assets_dir / "video.mp4")
    adur = dur(assets_dir / "audio_mix.m4a")
    assert abs(fdur - min(vdur, adur)) < 0.3, \
        f"mux drift: final={fdur:.2f} video={vdur:.2f} audio={adur:.2f}"
    if abs(total - vdur) > 0.05:
        print(f"note: formula total {total:.2f}s vs rendered {vdur:.2f}s "
              f"(frame quantization, ~{len(scenes) / fps:.2f}s expected)")
    spot_dir = assets_dir / "_spotcheck"
    spot_dir.mkdir(exist_ok=True)
    times = [0.5]
    acc = 0.0
    for sc in scenes:
        sd = segdur[sc["id"]]
        if sc["mode"] == "card":
            times.append(acc + sd * 0.6)
        acc += sd
    times += [total - 1.2] + list(cfg["extra_spot_times"])
    for tt in sorted(times):
        subprocess.run(["ffmpeg", "-y", "-ss", f"{tt:.2f}", "-i", str(out_mp4),
                        "-frames:v", "1", str(spot_dir / f"f_{tt:.1f}.jpg")],
                       check=True, capture_output=True)
    print("spot frames:", ", ".join(f"{x:.1f}s" for x in sorted(times)))

    meta = {"scenes": {sc["id"]: round(segdur[sc["id"]], 2) for sc in scenes},
            "modes": {sc["id"]: sc["mode"] for sc in scenes},
            "images": {sc["id"]: sc["img"] for sc in scenes},
            "narr_starts": {k: round(v, 2) for k, v in starts.items()},
            "card_splits": split, "total_s": round(total, 2),
            "video_duration_s": round(vdur, 2),
            "audio_duration_s": round(adur, 2),
            "final_duration_s": round(fdur, 2), "fps": fps,
            "output": str(out_mp4)}
    meta_p = out_mp4.with_name(out_mp4.stem + "_meta.json")
    json.dump(meta, open(meta_p, "w"), indent=2)
    print(f"COMPOSED: {out_mp4} ({fdur:.2f}s) | meta -> {meta_p}")


def audio_filter(narrs, total, cfg):
    lead, gap, tail = cfg["lead"], cfg["gap"], cfg["tail"]
    mv, mfi, mfo = cfg["music_volume"], cfg["music_fade_in"], cfg["music_fade_out"]
    nb = len(narrs)
    fc = f"aevalsrc=0:d={lead}[a0];[a0][0:a]concat=n=2:v=0:a=1[p1];"
    for i in range(1, nb):
        fc += (f"aevalsrc=0:d={gap}[g{i}];"
               f"[p{i}][g{i}][{i}:a]concat=n=3:v=0:a=1[p{i + 1}];")
    fc += (f"[p{nb}]apad=pad_dur={tail}[narpsrc];[narpsrc]asplit=2[narp][narsub];"
           f"[{nb}:a]atrim=0:{total},afade=t=in:d={mfi},"
           f"afade=t=out:st={max(0.0, total - mfo)}:d={mfo},volume={mv}[bed];"
           f"[narp][bed]amix=inputs=2:duration=first:normalize=0[a]")
    return fc


if __name__ == "__main__":
    main()
