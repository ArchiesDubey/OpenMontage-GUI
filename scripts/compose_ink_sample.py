"""Compose the Ink & Testimony E01 sample (pre-pipeline, Step 5)."""
import json
import subprocess

OUT = "projects/ink-testimony-e01/assets/sample"
FPS = 25
LEAD, GAP, TAIL = 0.7, 1.1, 1.4

def dur(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip())

d1 = dur(f"{OUT}/sc01_hook_narration.mp3")
d2 = dur(f"{OUT}/sc02_lippoint_narration.mp3")
s1 = LEAD + d1 + GAP          # scene 1 total
s2 = d2 + TAIL                # scene 2 total
total = s1 + s2
print(f"narr {d1:.2f}/{d2:.2f}s  scenes {s1:.2f}/{s2:.2f}s  total {total:.2f}s")

def zoompan(img, secs, out):
    frames = int(secs * FPS) + 1
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", img, "-vf",
        f"scale=1920:1080,zoompan=z='1.0+0.06*on/{frames}':x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':d={frames}:s=1280x720:fps={FPS},"
        f"trim=duration={secs},setpts=PTS-STARTPTS",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", out,
    ], check=True, capture_output=True)

zoompan(f"{OUT}/sc01_hook.png", s1, f"{OUT}/v1.mp4")
zoompan(f"{OUT}/sc02_lippoint.png", s2, f"{OUT}/v2.mp4")

# Crossfade the two scenes
xf = 0.6
subprocess.run([
    "ffmpeg", "-y", "-i", f"{OUT}/v1.mp4", "-i", f"{OUT}/v2.mp4", "-filter_complex",
    f"[0:v][1:v]xfade=transition=fade:duration={xf}:offset={s1 - xf}[v]",
    "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", f"{OUT}/video.mp4",
], check=True, capture_output=True)

# Subtitles (burned)
def ts(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)):03d}"

subs = f"""1
{ts(LEAD + 1.0)} --> {ts(LEAD + 5.2)}
It hasn't glowed in a century. It is still radioactive.

2
{ts(s1 + 0.4)} --> {ts(s1 + 4.6)}
To keep the brush sharp, they shaped the bristles with their lips.
"""
open(f"{OUT}/subs.srt", "w").write(subs)

# Audio: lead silence + n1 + gap + n2 + tail, music bed underneath
subprocess.run([
    "ffmpeg", "-y",
    "-i", f"{OUT}/sc01_hook_narration.mp3",
    "-i", f"{OUT}/sc02_lippoint_narration.mp3",
    "-i", f"{OUT}/music_bed.mp3", "-filter_complex",
    (f"aevalsrc=0:d={LEAD}[a0];[a0][0:a]concat=n=2:v=0:a=1[p1];"
     f"aevalsrc=0:d={GAP}[g];[p1][g][1:a]concat=n=3:v=0:a=1[nar];"
     f"[nar]apad=pad_dur={TAIL}[narp];"
     f"[2:a]atrim=0:{total},afade=t=in:d=1.5,afade=t=out:st={total - 2}:d=2,"
     f"volume=0.13[bed];[narp][bed]amix=inputs=2:duration=first:normalize=0[a]"),
    "-map", "[a]", "-ar", "44100", f"{OUT}/audio_mix.m4a",
], check=True, capture_output=True)

subprocess.run([
    "ffmpeg", "-y", "-i", f"{OUT}/video.mp4", "-i", f"{OUT}/audio_mix.m4a",
    "-vf", (f"subtitles={OUT}/subs.srt:force_style='FontName=Georgia,FontSize=18,"
            "PrimaryColour=&H00F2EDE4,OutlineColour=&H00101010,BorderStyle=1,"
            "Outline=2.5,Shadow=1,ShadowColour=&HA0000000,MarginV=42'"),
    "-c:v", "libx264", "-crf", "18", "-c:a", "copy", "-shortest",
    f"{OUT}/sample_v1.mp4",
], check=True, capture_output=True)

meta = {"scene1_s": round(s1, 2), "scene2_s": round(s2, 2),
        "total_s": round(total, 2), "fps": FPS}
json.dump(meta, open(f"{OUT}/sample_meta.json", "w"), indent=2)
print("COMPOSED:", meta)
