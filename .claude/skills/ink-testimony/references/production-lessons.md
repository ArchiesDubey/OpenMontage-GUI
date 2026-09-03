# Ink & Testimony — Production Lessons (apply without being asked)

Lessons learned the hard way on E01, E02 and E03. Each caught a real failure. Apply
them by default on every episode; do not wait to be told.

Several of these are not channel-specific — they bite any stills + TTS + FFmpeg
production. The shared copies live in `skills/pipelines/explainer/asset-director.md`,
`skills/pipelines/explainer/compose-director.md` and `skills/core/subtitle-sync.md`.
This file is the ink-testimony-tuned version with the exact values.

## 1. TTS — spell out every numeral

`eleven_multilingual_v2` misnormalizes comma-grouped numerals. In E01, `"1,600"` was
read aloud as **"section"**. Dates and bare figures also drift.

- In `script.delivery_cues.provider_text`, write every number, date and figure as
  words: `"nineteen thirty"`, `"four hundred and thirty-six"`, `"ten thousand
  dollars"`, `"eighteen ninety-six"`, `"the fifteenth of December, nineteen
  sixty-seven"`.
- Keep proper numerals in `display_text` / card text — those are composited, not
  spoken.
- The **sidecar SRT gets proper numerals for free**: you feed TTS spelled-out words,
  whisper `large-v3` then re-normalizes them back to digits in the transcript
  (`"nineteen oh nine"` → `"1909"`). No manual step — the spell-out-for-TTS /
  transcribe-for-subtitles loop produces both correct forms.
- **No audio tags** in the narration text.
- Voice, fixed: `voice_id "S9GPGBaMND8XWwwzxQXp"`, `model_id
  "eleven_multilingual_v2"`, `stability 0.75`, `similarity_boost 0.9`, `style 0.1`,
  `speed 1.0`.
- Run the `humanizer` pass on the script **before** TTS. E03 also: no em/en dashes in
  spoken text, plain verbs, varied sentence length, no "the real question is…" /
  "let's look at…".

## 2. FLUX batch → preview → guard review, every time

After every image batch:

1. Write **480px JPEG** previews to `<assets>/_preview/` — full-size PNGs exceed the
   inline image limit and can't be reviewed. Build **contact-sheet montages** (PIL, ~15
   frames/sheet) so the whole batch is reviewable in a few images.
2. Look at **every** frame against the guard: `Full-bleed image, no border, no plate
   frame, no label. No text or numbers anywhere.` Plus: is it pen-and-ink (not
   photographic)? Is the dark register legible (not a black rectangle)?
3. **Subject-accuracy pass on the hero frames (E03).** The guard checklist does NOT
   catch "this is the wrong thing." On E03 the single most important frame — the Silver
   Bridge collapse — rendered as a **sinking ocean liner** and shipped in v1. Give the
   3–5 highest-stakes frames a dedicated "is this actually what the narration
   describes?" look, separate from the guard.
4. Regenerate each failure **medium-first** (see `style-lock.md`) with a **fresh
   seed** and appended positive reinforcement clauses. Log `{scene, old_result,
   new_seed, reason}` in the run's `regen_log.json` and roll it into
   `decision_log.json`.

E02 filter bug: a scene-plan iteration that selected on `scene["type"]` instead of
`required_assets[0].source == "generate"` sent the literal string `"REUSE sN's
generated frame…"` to FLUX as a prompt and produced 36 garbage images. Filter on the
asset **source**, and make the batch script idempotent (skip any output file that
already exists).

Budget reality (E01–E03): `flux-pro/v1.1` ≈ **$0.05/frame**, and **regens inflate the
call count ~1.3×** (E03: 99 FLUX calls for 74 final frames). TTS is **~$0.60/1k
characters** on `eleven_multilingual_v2`, not the ~$0.30 a naive estimate gives —
size the budget off characters, not word count.

## 3. FLUX writes legible text on anything paper-shaped (E03)

`flux-pro/v1.1` renders a **legible faux headline / masthead / signage / calendar
grid** on any depicted newspaper, storefront, museum wall, book cover or calendar, no
matter how many "no lettering / no text" clauses you stack. On E03 ~10 of 74 frames
failed this on the first pass; several needed 2–3 re-rolls.

Reliable fixes, in order of preference:

1. **Keep the text-bearing object out of frame** — describe presses, paper, folds,
   brittleness, hands; not "a front page".
2. **Show it edge-on / turned away / cropped** — "the printed face turned away, at a
   steep raking angle, so no text surface is legible".
3. **Crop the headline out post-hoc** and bake the crop as a new PNG (E03 `n_s2c`).
4. **Composite the real text in the render layer** (see lesson 9).

"Print texture" — hatching that *suggests* columns of type but spells nothing, no
numerals — is the **accepted compromise** (book spines, pinned wall clippings, brittle
volume pages). It matches E01/E02. Chasing it to zero makes frames worse.

Append this to every Act 1 / Act 5 and any press/paper/book/type prompt:

> Every sheet of paper, every newspaper page, every book cover, spine and label in
> the frame is completely blank: no printing, no headlines, no words, no numerals, no
> masthead, only plain uniform paper tone and the texture of the ink drawing itself.
> Absolutely no artist signature, no monogram, no lettering, no drawn border.

## 4. Pacing — 2–6 s per SHOT, not "~7 s per beat" (E03)

The channel grammar is **one still per shot, hard cut on the next narration start**.
That means the **narration clip length is the cut rhythm**. E03's first cut followed
the old "~7 s/beat, 75–90 beats" scale model and merged sentences to hit the count —
the result was **59 of 87 shots over 6 s and a 16-second opening hold**. The user's
real target:

- **2–4 s per shot typical, 5–6 s hard maximum.**
- A 10-minute episode is **~130–170 shots**, not ~85.
- **Beats are short single sentences** (~2–5 s of speech). Never merge sentences into
  one clip — an 8–18 s clip on one still is the failure mode.
- Multiple shots inside one narration clip are fine and expected: cut to a genuinely
  different picture (a new frame, or a hard crop into a *different region* of the
  same still, which reads as a separate shot). A crop only works **inside its own
  beat** — a crop of frame X used in a later beat still reads as "frame X" if beat X
  already showed it.
- Reserve 5–6 s only for the deliberate holds — a cold-open establishing frame, the
  final fade beat.

**Recovery move if a cut ships too slow:** rebuild the **video track only**. Slice
each beat's screen time into 2.5–6 s sub-shots from detail crops of the beat's own
still plus ~15–20 new detail/second-angle frames; leave `audio_mix.m4a` and the SRT
untouched (no re-transcribe, no desync risk). E03 did this for ~$1 and ~15 min;
`scripts/ink_testimony/compose.py` (video-track-only rebuild) is the standardized template.

## 5. Compose data-driven, with the timing assertion — but the generic runner is not generic

Drive the render from `scene_plan.json` — image list, movement, cards, fades,
narration mapping. Assert the timeline before rendering:

```python
assert abs(sum(segdur.values()) - total_audio) < 0.05, \
    f"timeline mismatch: segments={sum(segdur.values()):.3f} audio={total_audio:.3f}"
```

This caught a real off-by-one-beat bug in E01. Also assert final render duration ==
`min(video_dur, audio_dur)` within ~0.3 s, and `ffprobe` the stream list.

**Use the standardised runner `scripts/ink_testimony/` (E04+).** Two artifact-driven
modules — `assets.py` (`--mode sample|batch|regen`) and `compose.py` — replace the
per-episode `eNN_*.py` scripts. `compose.py` reads `scene_plan.json` + `script.json` +
`ink_config.json` (+ optional `cut_plan.json` for `detail_frames` / `date_cards`),
builds the timeline, **slices every beat to 2–6 s sub-shots by default**, handles the
act-card structure, and burns or sidecars subtitles per config. It reuses
`explainer_compose.py`'s primitives (`zoompan_segment`, `card_segment`, `dur`,
`transcribe_section`) but not its `main()`. Validated by reproducing E03 (643.19 s,
165 shots, mean 3.9 s, 0 over 6 s, 287 SRT cues) from artifacts alone.

**Why not `scripts/explainer_compose.py` directly** — two traps it has (E01–E03 each
worked around them with a bespoke `eNN_compose.py`):

- Act-break cards whose "owner" beat has no `card_split` configured → `KeyError` on
  `split[owner]`. The channel's cards each have their **own** narration clip
  ("Act one. The slow months.") and don't borrow time from a neighbour, so use a
  uniform lead/clip/gap/tail chain with **no split-card branch** (see
  `scripts/ink_testimony/compose.py`, which handles this in its timing chain).
- The final mux **hardcodes burned subtitles**. E03 added a `burn_subtitles` flag
  (default `True`) to the shared runner; renders opt out via
  `ink_config.json` → `"burn_subtitles": false`.

**MP3 timing (E02, E03):** ElevenLabs MP3s carry ~35 ms of LAME encoder
delay/padding, so `ffprobe`'s container duration reads **longer** than what decodes.
Across ~90 clips that alone caused ~3 s of audio/video desync. **Decode every clip to
WAV once (cached) and derive all timing from the WAV.**

**Long renders:** redirect to a logfile — `python3 -u <script> > <log> 2>&1` — as a
harness background job. Do **not** pipe the script's stdout into `tee`/`head`; a
`| head` closing early sends SIGPIPE and kills the render mid-run (lost two E03
renders this way). `screen -dmS bash -c 'cd … && …'` was also flaky here — sessions
died silently. Always use absolute paths or `cd <repo-root> &&` at the head of every
compound shell command; `cd` state leaked across Bash calls in this environment.

## 6. Subtitles

- Per-clip transcription with `transcriber` (faster-whisper `large-v3`, `en`), each
  clip's word timings offset to its position on the timeline.
- `subtitle_gen` with **max 8 words per cue**.
- **Default: burn** with the E01/E02 `force_style`:

  ```
  FontName=Georgia,FontSize=18,Bold=1,PrimaryColour=&H00F2EDE4,
  BorderStyle=3,BackColour=&H80000000,Outline=10,Shadow=0,MarginV=42
  ```

  `BorderStyle=3` draws the semi-transparent black backplane that keeps text legible
  over both warm-white and black-register frames.
- **Sidecar-only override** (E03): set `burn_subtitles=False`. Still build the merged
  `subs.srt` per-clip (max 8 words/cue, word timings offset to the timeline), write it
  as `subtitles.srt` **beside** the MP4, and mux with **no subtitles filter and no
  subtitle stream**. Verify: `ffprobe` shows exactly one video + one audio stream, no
  spot-check frame carries burned caption text, first cue ≈ 0.7 s, no cue > 8 words.
  The last cue legitimately ends a few seconds before the file end when there's a
  music-only closing fade.

## 7. On-screen dates / places = composited cards, planned into the scene plan (E03)

"The month is January, the year nineteen oh nine" wants a **date marker** on screen.
Do **not** generate a calendar — FLUX puts the month and year in the frame as legible
text (guard violation; see lesson 3). Use E02's **date-card device**: `drawtext`
Georgia small-caps (`#F2EDE4`) on a semi-transparent dark box over the dimmed prior
frame, ~2.5–3 s, exactly like an act-break card but smaller. Display text keeps proper
numerals (`JANUARY 1909`). **Plan these into the scene plan** at the scene-director
stage for every cold date-and-place line, rather than bolting one on later.

## 8. Verify before delivery

1. `ffprobe` the final MP4 — expected duration; one video + one audio stream; 720p;
   expected codec; **no subtitle stream** when sidecar-only.
2. Extract spot-check frames: the opening, one per act, each act-break card, the
   closing fade, and each **hero frame** (dark-register beats especially). **Look at
   them** — for burned caption text, for wrong subjects (lesson 2 §3), for legible
   faux text (lesson 3).
3. Skim the narration audio (via its transcript) for any numeral read as letters or
   "section" (lesson 1).
4. Check the **per-shot hold report**: mean 3–4 s, max ≤ 6 s, zero over 6 s
   (lesson 4). No image repeated across beat boundaries.
5. Build the contact sheet from the spot-check frames — it's part of the deliverable.
