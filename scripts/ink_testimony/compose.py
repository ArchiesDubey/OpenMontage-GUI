"""Ink & Testimony compose -- artifact-driven FFmpeg render with 2-6s sub-shot
pacing built in (no separate re-cut pass).

    python -m scripts.ink_testimony.compose --project projects/ink-testimony-eNN

Reads artifacts/scene_plan.json (order, movement, holds), artifacts/script.json
(narration, card text, dark_register_beats), ink_config.json (timing, subtitle
mode), and optional cut_plan.json (detail_frames per beat, date_cards).

Grammar (E02/E03): every beat -- including act cards -- has its own narration
clip; uniform lead/clip/gap/tail chain; hard cut on the next narration start;
fade in from black on shot one, long fade to black on the last shot. Each beat's
on-screen time is sliced into 2.5-6s sub-shots, each showing a different picture
(a detail frame, or a hard crop into a different region of the beat's still --
which reads as a fresh shot only INSIDE its own beat).

Reuses explainer_compose.py's primitives: zoompan_segment, card_segment, dur,
transcribe_section.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from scripts.explainer_compose import dur, zoompan_segment, card_segment, transcribe_section, FORCE_STYLE  # noqa: E402
from scripts.ink_testimony import common as C  # noqa: E402

CROPS = [(0.06, 0.05, 0.60, 0.60), (0.22, 0.20, 0.56, 0.56), (0.36, 0.34, 0.60, 0.60)]


def parse_mode(scene: dict) -> str:
    if scene.get("type") == "text_card":
        return "card"
    mov = (scene.get("movement") or "").lower()
    cam = (scene.get("shot_language") or {}).get("camera_movement", "").lower()
    if "micro" in mov:
        return "micro"
    if "pull-back" in mov or "pull back" in mov or cam == "dolly_out":
        return "out"
    if "push-in" in mov or "push in" in mov or cam == "dolly_in":
        return "in"
    if "static" in mov or cam == "static":
        return "static"
    return "micro"


def render_crop(img, secs, out, box, fps, drift=True):
    frames = max(1, round(secs * fps))
    x0, y0, w, h = box
    z = f"min(1.0+0.03*on/{frames},1.03)" if drift else "1.0"
    vf = (f"crop=iw*{w}:ih*{h}:iw*{x0}:ih*{y0},scale=1920:1080,"
          f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
          f"d={frames}:s=1280x720:fps={fps},setpts=PTS-STARTPTS")
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(img), "-vf", vf,
                    "-frames:v", str(frames + 1), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)],
                   check=True, capture_output=True)


def refade(path, fps, fade_in=0.0, fade_out=0.0):
    d = dur(path)
    parts = []
    if fade_in:
        parts.append(f"fade=t=in:st=0:d={fade_in}")
    if fade_out:
        parts.append(f"fade=t=out:st={max(0.0, d - fade_out):.3f}:d={fade_out}")
    if not parts:
        return
    tmp = Path(str(path) + ".f.mp4")
    subprocess.run(["ffmpeg", "-y", "-i", str(path), "-vf", ",".join(parts),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(tmp)], check=True, capture_output=True)
    tmp.replace(path)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    proj, AD, cfg, script, plan, cut_plan = C.load_project(a.project)
    ep = cfg["episode"]
    fps = cfg["fps"]
    T = cfg["timing"]
    LEAD, GAP, CARD_GAP, TAIL = T["lead"], T["gap"], T["card_gap"], T["tail"]
    MV, MFI, MFO = cfg["music"]["volume"], cfg["music"]["fade_in"], cfg["music"]["fade_out"]
    FI, FO = cfg["fade"]["in_first"], cfg["fade"]["out_last"]
    MINS, MAXS, TGT = cfg["pacing"]["min_shot"], cfg["pacing"]["max_shot"], cfg["pacing"]["target_shot"]
    burn = bool(cfg["burn_subtitles"])
    out_mp4 = Path(a.out) if a.out else AD / f"ink-testimony-{ep}_episode.mp4"

    sections = {s["id"]: s for s in script["sections"]}
    ORDER = [s["id"] for s in sorted(script["sections"], key=lambda s: s["start_seconds"])]
    CARD_IDS = {s["script_section_id"] for s in plan["scenes"] if s["type"] == "text_card"}
    DARK = set(script.get("metadata", {}).get("dark_register_beats", []))
    scenes_by_sec = {s["script_section_id"]: s for s in plan["scenes"]}
    gen_log_p = AD / "generation_log.json"
    gen_log = json.loads(gen_log_p.read_text()) if gen_log_p.exists() else {"images": {}}

    detail_frames = cut_plan.get("detail_frames", {})   # beat -> [frame_id, ...]
    date_cards = cut_plan.get("date_cards", {})          # beat -> "MONTH YEAR"

    # --- held beats: source=="provided" + "REUSE <anchor>" in the description ---
    HELD = {}
    for s in plan["scenes"]:
        ra = (s.get("required_assets") or [{}])[0]
        if s["type"] != "text_card" and ra.get("source") == "provided":
            d = ra.get("description", "")
            anchor = d.split("REUSE ", 1)[1].split("'")[0].split()[0] if "REUSE " in d else None
            HELD[s["script_section_id"]] = anchor

    def img_for(sid):
        e = gen_log.get("images", {}).get(sid)
        if e and e.get("success") and (AD / e["file"]).exists():
            return str(AD / e["file"])
        p = AD / f"{ep}_{sid}.png"
        if p.exists():
            return str(p)
        if sid in HELD and HELD[sid]:
            return img_for(HELD[sid])
        raise FileNotFoundError(f"{sid}: no image")

    def card_text_for(sid):
        return sections[sid]["text"]

    # --- decode narration to WAV (MP3 LAME padding over-reads ~35ms/clip) ---
    WAV = AD / "_wav_cache"
    WAV.mkdir(exist_ok=True)
    clips = {}
    for sid in ORDER:
        mp3 = AD / f"{sid}_narration.mp3"
        assert mp3.exists(), f"missing narration clip: {sid}"
        wav = WAV / f"{sid}_narration.wav"
        if not wav.exists():
            subprocess.run(["ffmpeg", "-y", "-i", str(mp3), str(wav)], check=True, capture_output=True)
        clips[sid] = wav
    ndurs = {sid: dur(c) for sid, c in clips.items()}

    starts, t = {}, LEAD
    for i, sid in enumerate(ORDER):
        starts[sid] = t
        gap = CARD_GAP if sid in CARD_IDS else GAP
        t += ndurs[sid] + (TAIL if i == len(ORDER) - 1 else gap)
    total = t
    segdur = {sid: ndurs[sid]
              + (TAIL if i == len(ORDER) - 1 else (CARD_GAP if sid in CARD_IDS else GAP))
              + (LEAD if i == 0 else 0)
              for i, sid in enumerate(ORDER)}
    assert abs(sum(segdur.values()) - total) < 0.05, \
        f"timeline mismatch: {sum(segdur.values()):.3f} vs {total:.3f}"
    print(f"timeline {total:.1f}s ({total/60:.2f} min); timing assert OK", flush=True)

    # --- transcription (cached) + timeline offsets ---
    all_segments = []
    for sid in ORDER:
        for seg in transcribe_section(sid, clips[sid], AD, {"transcribe_model": cfg["transcribe_model"]}):
            seg["beat"] = sid
            seg["start"] = round(seg["start"] + starts[sid], 3)
            seg["end"] = round(seg["end"] + starts[sid], 3)
            seg["words"] = [{**w, "start": round(w["start"] + starts[sid], 3),
                             "end": round(w["end"] + starts[sid], 3)} for w in seg.get("words", [])]
            all_segments.append(seg)

    # --- build sub-shot list ---
    def n_sub(d):
        return 1 if d <= MAXS else max(2, min(6, round(d / TGT)))

    segs, plan_rows = [], []
    idx = 0
    n = len(ORDER)
    last_non_card_img = None
    for bi, beat in enumerate(ORDER):
        d = segdur[beat]
        sc = scenes_by_sec.get(beat, {})
        if beat in CARD_IDS:
            # act card = drawtext over the dimmed most-recent non-card frame
            backdrop = last_non_card_img
            if backdrop is None:  # card as the very first beat (unusual): use the next frame
                nxt = next((b for b in ORDER[bi + 1:] if b not in CARD_IDS), None)
                backdrop = img_for(nxt) if nxt else None
            seg = AD / f"seg_{idx:03d}.mp4"
            card_segment(backdrop, card_text_for(beat), d, AD, seg, fps)
            segs.append(str(seg)); plan_rows.append((beat, "card", round(d, 1))); idx += 1
            continue
        last_non_card_img = img_for(beat)

        k = n_sub(d)
        parts = [d / k] * k
        primary = img_for(beat)
        held = beat in HELD
        dark = beat in DARK
        extras = list(detail_frames.get(beat, []))

        shots = []  # (kind, img, arg)
        if beat in date_cards and k >= 1:
            anchor = img_for(HELD.get(beat, beat))
            card_s = min(2.8, d * 0.4)
            parts = [card_s] + ([(d - card_s) / (k - 1)] * (k - 1) if k > 1 else [])
            if k == 1:
                parts = [d]
            shots.append(("datecard", anchor, date_cards[beat]))
            primary = anchor
        elif held:
            anchor = img_for(HELD[beat])
            if extras:
                shots.append(("zoom", str(AD / f"{ep}_{extras.pop(0)}.png"), "in"))
            else:
                shots.append(("crop", anchor, CROPS[2]))
            primary = anchor
        else:
            shots.append(("zoom", primary, "in" if bi % 2 == 0 else "out"))

        ci = 0
        while len(shots) < k:
            if extras:
                shots.append(("zoom", str(AD / f"{ep}_{extras.pop(0)}.png"), "in"))
            else:
                box = CROPS[1] if dark else CROPS[ci % 3]
                shots.append(("crop", primary, box)); ci += 1

        for si, (kind, img, arg) in enumerate(shots):
            seg = AD / f"seg_{idx:03d}.mp4"
            secs = parts[si]
            if kind == "zoom":
                zoompan_segment(img, secs, seg, arg if arg in ("in", "out", "micro", "static") else "micro", fps)
            elif kind == "datecard":
                card_segment(img, arg, secs, AD, seg, fps)
            else:
                render_crop(img, secs, seg, arg, fps)
            segs.append(str(seg))
            plan_rows.append((beat, kind, round(secs, 1))); idx += 1

    refade(segs[0], fps, fade_in=FI)
    refade(segs[-1], fps, fade_out=FO)
    print(f"{len(segs)} sub-shots (from {n} beats). rendering...", flush=True)

    # --- audio chain: lead / clip / gap(card_gap) / tail, split for subs ---
    fc = f"aevalsrc=0:d={LEAD}[a0];[a0][0:a]concat=n=2:v=0:a=1[p1];"
    for i in range(1, n):
        g = CARD_GAP if ORDER[i] in CARD_IDS else GAP
        fc += f"aevalsrc=0:d={g}[g{i}];[p{i}][g{i}][{i}:a]concat=n=3:v=0:a=1[p{i+1}];"
    fc += (f"[p{n}]apad=pad_dur={TAIL}[nps];[nps]asplit=2[narp][narsub];"
           f"[{n}:a]atrim=0:{total},afade=t=in:d={MFI},"
           f"afade=t=out:st={max(0.0, total - MFO)}:d={MFO},volume={MV}[bed];"
           f"[narp][bed]amix=inputs=2:duration=first:normalize=0[a]")
    subprocess.run(["ffmpeg", "-y"] + sum([["-i", str(clips[s])] for s in ORDER], []) +
                   ["-i", str(AD / "music_bed.mp3"), "-filter_complex", fc,
                    "-map", "[a]", "-ar", "44100", str(AD / "audio_mix.m4a"),
                    "-map", "[narsub]", "-ar", "44100", str(AD / "narration_only.wav")],
                   check=True, capture_output=True)

    concat = AD / "video.mp4"
    subprocess.run(["ffmpeg", "-y"] + sum([["-i", s] for s in segs], []) +
                   ["-filter_complex", "".join(f"[{i}:v]" for i in range(len(segs))) +
                    f"concat=n={len(segs)}:v=1:a=0[v]", "-map", "[v]",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(concat)],
                   check=True, capture_output=True)

    # --- subtitles: per-clip subtitle_gen, merged, offset to timeline ---
    from tools.subtitle.subtitle_gen import SubtitleGen  # noqa: E402
    sg = SubtitleGen()
    blocks, cue = [], 0
    for sid in ORDER:
        beat = [x for x in all_segments if x["beat"] == sid]
        if not beat:
            continue
        res = sg.execute({"segments": beat, "format": "srt", "max_words_per_cue": 8,
                          "max_chars_per_line": 42, "corrections": {"shape": "shaped"},
                          "output_path": str(AD / f"subs_{sid}.srt")})
        if not res.success:
            raise RuntimeError(f"subtitle_gen failed on {sid}: {res.error}")
        txt = Path(res.artifacts[0]).read_text().strip()
        for c in (txt.split("\n\n") if txt else []):
            lines = c.strip().splitlines()
            if len(lines) < 2:
                continue
            cue += 1
            blocks.append(f"{cue}\n" + "\n".join(lines[1:]))
    srt = "\n\n".join(blocks) + "\n"
    (AD / "subs.srt").write_text(srt)
    (out_mp4.with_name("subtitles.srt")).write_text(srt)
    print(f"subtitles.srt: {cue} cues (sidecar{' + burned' if burn else ''})", flush=True)

    # --- mux ---
    mux = ["ffmpeg", "-y", "-i", str(concat), "-i", str(AD / "audio_mix.m4a")]
    if burn:
        esc = str(AD / "subs.srt").replace(":", "\\:")
        mux += ["-vf", f"subtitles={esc}:force_style='{FORCE_STYLE}'"]
    mux += ["-c:v", "libx264", "-crf", "18", "-c:a", "copy", "-shortest", str(out_mp4)]
    subprocess.run(mux, check=True, capture_output=True)

    # --- verify ---
    fd, vd, ad = dur(out_mp4), dur(concat), dur(AD / "audio_mix.m4a")
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
                            "-of", "csv=p=0", str(out_mp4)], capture_output=True, text=True).stdout.split()
    assert abs(fd - min(vd, ad)) < 0.35, f"mux drift {fd} {vd} {ad}"
    assert probe.count("video") == 1 and probe.count("audio") == 1, probe
    if not burn:
        assert "subtitle" not in probe, "subtitle stream muxed in -- sidecar only"
    holds = [r[2] for r in plan_rows]
    over = [(r[0], r[2]) for r in plan_rows if r[2] > 6.0]
    print(f"final {fd:.2f}s | video {vd:.2f}s | audio {ad:.2f}s | streams {probe}", flush=True)
    print(f"sub-shots {len(plan_rows)} | mean {sum(holds)/len(holds):.1f}s | max {max(holds):.1f}s | "
          f"over 6s: {len(over)} {over}", flush=True)

    spot = AD / "_spotcheck"
    spot.mkdir(exist_ok=True)
    times, acc = [0.5], 0.0
    for r in plan_rows:
        if r[1] == "card":
            times.append(acc + r[2] * 0.55)
        acc += r[2]
    times.append(fd - 1.5)
    for tt in sorted(set(round(x, 1) for x in times if 0 <= x < fd)):
        subprocess.run(["ffmpeg", "-y", "-ss", f"{tt:.2f}", "-i", str(out_mp4), "-frames:v", "1",
                        str(spot / f"f_{tt:06.1f}.jpg")], check=True, capture_output=True)

    meta = {"episode": ep, "total_s": round(total, 2), "final_s": round(fd, 2),
            "video_s": round(vd, 2), "audio_s": round(ad, 2), "fps": fps,
            "sub_shots": len(plan_rows), "beats": n, "burn_subtitles": burn,
            "srt_cues": cue, "shot_hold_mean": round(sum(holds) / len(holds), 2),
            "shot_hold_max": round(max(holds), 2), "shots_over_6s": len(over),
            "output": str(out_mp4), "sidecar_srt": str(out_mp4.with_name("subtitles.srt")),
            "plan": plan_rows}
    (out_mp4.with_name(out_mp4.stem + "_meta.json")).write_text(json.dumps(meta, indent=2))
    C.contact_sheet(sorted(spot.glob("f_*.jpg")), spot / "CONTACT_SHEET", cols=5)
    print(f"COMPOSED: {out_mp4} ({fd/60:.2f} min)", flush=True)


if __name__ == "__main__":
    main()
