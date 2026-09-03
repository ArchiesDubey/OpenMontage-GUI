# Technical Motion Explainer: Audio & Sound Design

Mastering standards, music bed selection, frequency carving, and tactile micro-sound effects for dark technical explainer productions.

---

## 1. Mastering Standards & Loudness Profile

Technical motion explainers require clean, broadcast-grade dialogue intelligibility with an unobtrusive, driving electronic music bed.

| Audio Element | Target Integrated Loudness | True Peak Ceiling | Dynamic Range (LRA) | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Dialogue (Voiceover)** | **-15.0 LUFS** (±1.0) | **-1.0 dBFS** | 4 – 6 LU | Warm, articulate, close-mic proximity |
| **Music Bed (Under Voice)** | **-22.0 to -24.0 dBFS** | **-6.0 dBFS** | N/A | Subdued background pulse |
| **Music Bed (Stings / Pauses)** | **-16.0 dBFS** | **-2.0 dBFS** | N/A | Swells during 1.5s scene transition pauses |
| **Micro-SFX (UI / Clicks)** | **-18.0 to -20.0 dBFS** | **-3.0 dBFS** | N/A | Crisp tactile feedback |

---

## 2. Voiceover Frequency & EQ Carving

To prevent low-end mud and ensure speech clarity over electronic synth pulses:

### Voice EQ Profile
1. **High-Pass (Low-Cut)**: 80 Hz (18 dB/oct slope) to eliminate rumble and mic-handling sub-frequencies.
2. **Body & Warmth**: Gentle +1.5 dB wide boost at 180–220 Hz.
3. **Mud Notch**: -2.5 dB cut at 450–600 Hz (removes boxy room tone).
4. **Presence & Articulation**: +2.0 dB shelf at 3.5 kHz – 5.0 kHz (brings out consonant clarity).
5. **De-Esser**: Focused threshold at 6.8 kHz – 8.2 kHz to tame harsh sibilants.

### Music Bed EQ (Frequency Carving)
* **The Vocal Pocket Notch**: Cut **3.5 dB at 250 Hz – 1,500 Hz** on the music track. This carves out an acoustic "pocket" where vocal fundamentals sit, allowing the music to remain audible without masking speech.
* **Sub Control**: High-pass filter music at 35 Hz to prevent speaker distortion on mobile devices.

---

## 3. Sidechain Ducking Contract

Automated sidechain compression must duck the music bed whenever voiceover is active:
* **Threshold**: -24 dBFS.
* **Ratio**: 4:1.
* **Attack Time**: **15 ms** (rapid ducking as speech begins).
* **Release Time**: **250–350 ms** (smooth swell back up during sentence pauses).
* **Hold Time**: 120 ms (prevents annoying "pumping" between brief pauses).

---

## 4. Music Genre & Aesthetic Palette

The musical score must feel like a cross between *The Social Network* (Trent Reznor / Atticus Ross) and modern cyberpunk electronics:

1. **Core Elements**:
   * Low, pulsing 80–110 BPM synth bassline (analog saw or square wave with low-pass filter).
   * Muted electronic hi-hats or steady clock-like rim clicks.
   * Atmospheric ambient pads or dark drones that shift subtly between minor chords.
2. **Strict Anti-Patterns**:
   * ❌ No acoustic guitars or cheerful ukulele.
   * ❌ No vocal samples, choirs, or melodic hooks that distract from narration.
   * ❌ No chaotic high-tempo EDM or aggressive metal drops.

---

## 5. Tactile Micro-SFX Grammar

Sound effects in this style must be subtle, tactile, and surgical—reinforcing UI motion rather than dramatizing it.

| Visual Event | Audio Cue | Sound Characteristics |
| :--- | :--- | :--- |
| **Stat Counter Rolling Up** | `counter_tick.wav` | Rapid, low-volume mechanical clicks (like a rotary odometer or vintage keyboard switch). |
| **Capacity Bar Threshold Cross** | `sub_impact.wav` | Deep, low-end sine thump (40Hz–60Hz) with zero high-end hash. |
| **Card / Box Pop-in** | `ui_card_pop.wav` | Soft, subdued wood-block or damped glass tap. |
| **Glitch / Terminal Error** | `digital_glitch.wav` | Micro-second tape-stop or subtle bitcrush click (never a loud siren). |
| **Architecture Arrow Flow** | `data_whoosh.wav` | Smooth, high-frequency white noise sweep (filtered at 4kHz). |
| **Section Transition** | `riser_swell.wav` | 1.2-second reverse cymbal or synth riser cutting immediately to silence on beat 1. |
