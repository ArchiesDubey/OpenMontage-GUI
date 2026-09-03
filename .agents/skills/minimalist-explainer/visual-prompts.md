# Visual Prompts & Art Direction Guide

This guide provides the exact generative prompt templates, art tokens, color palettes, and composition blueprints required to generate visuals matching the **Ink Explainer** aesthetic using image and video generation models (FLUX, Midjourney, Gemini Omni, Recraft, ComfyUI).

---

## 1. Aesthetic DNA & Core Style Tokens

To reliably replicate this distinct 2D vector cartoon look across any model:

### Key Positive Style Tokens
* `minimalist 2D vector cartoon illustration`
* `clean bold black ink outlines, thick uniform linework`
* `pure white round head stickman character with expressive minimalist face`
* `solid flat color fills with subtle soft-cell shading`
* `OverSimplified and Kurzgesagt minimalist aesthetic`
* `clean digital comic art, modern educational explainer style`
* `decluttered composition, high visual hierarchy, clean framing`

### Universal Negative Tokens
* `photorealistic, 3D render, CGI, realism, hyperdetailed`
* `complex gradients, heavy drop shadows, realistic textures, noise`
* `realistic human face, detailed skin, pupils, nostrils, realistic anatomy`
* `messy sketch, pencil drawing, watercolor, blurred lines, chromatic aberration`
* `muddy colors, cluttered background, visual noise`

---

## 2. Color Palette & Lighting Hierarchy

The style relies on high contrast between the pure white character, muted atmospheric backgrounds, and vibrant focal points:

```
[Character Head]   #FFFFFF (Pure Flat White) + #121212 (Bold Ink Outline)
[Thumbnail Accent] #FFEE00 / #FFD700 (High-Impact Canary Yellow)
[Day Sky / Nature] #87CEEB (Sky Blue), #A2D075 (Muted Sage Green), #E2B276 (Warm Earth)
[Night / Bedroom]  #0D1B2A (Midnight Navy), #1B4965 (Deep Blue), #7B2CBF (Moody Violet)
[Industrial/Work]  #D3D3D3 (Cool Gray), #B08968 (Cardboard Kraft), #E9ECEF (Clean Steel)
```

---

## 3. The 3-Element Thumbnail Formula

Thumbnails in this niche achieve 10M+ views by adhering strictly to the **Rule of Three**:

```
+-------------------------------------------------------------------+
|                                                                   |
|              [ ELEMENT 3: POWER TEXT (1-2 WORDS) ]                |
|                    "NO JOBS" / "FAKE SLEEP?"                      |
|                 (Bold Yellow Sans + Black Outline)                |
|                                                                   |
|   [ ELEMENT 1: EMOTIVE CHARACTER ]     [ ELEMENT 2: STRIKING PROP ]|
|   - Big white egghead                  - Absurd, surprising,      |
|   - Extreme expression                 - or stark visual counter   |
|   - High-contrast gesture              - (alarm clock, chick,      |
|                                           conveyor belt, campfire)|
+-------------------------------------------------------------------+
```

### Thumbnail Rules:
1. **Zero Title Duplication:** Never duplicate words from the video title.
2. **Never use more than 3 words** in the thumbnail text.
3. **Text Font:** Heavy sans-serif (Outfit 900, Impact, Montserrat Black) in bright yellow (`#FFEE00`) with a thick black outer stroke (16–22px) and drop shadow.
4. **Readability at Mobile Scale:** Must pass the 120px mobile squint test.
5. **Dedicated Skill & HTML Templates:** For ready-to-render templates and automated mobile squint test generation, use [**`minimalist-thumbnail-craft`**](file:///Users/archiesdubey/Desktop/Code.nosync/OpenMontage/.agents/skills/minimalist-thumbnail-craft/SKILL.md).

---

## 4. Model-Specific Prompt Templates

### A. Midjourney / FLUX (Text-to-Image)

#### Template: Character in Context
```text
A minimalist 2D vector illustration of an expressive cartoon stickman with a smooth pure white circular head and simple black stroke facial features, [EXPRESSION: e.g. looking skeptical with one raised eyebrow], wearing [OUTFIT: e.g. a simple light blue t-shirt and dark pants]. The character is [ACTION: e.g. lying in bed staring at a glowing alarm clock]. Minimalist clean background of [ENVIRONMENT: e.g. a dark blue bedroom with a window showing a crescent moon]. Bold clean black outlines, flat solid color fills, subtle soft shading, clean lines, educational webcomic style, 16:9 widescreen composition --ar 16:9 --style raw --v 6.1
```

#### Template: High-Clickrate Thumbnail
```text
YouTube thumbnail art, minimalist 2D vector cartoon style. In the center-left, a cartoon stickman with a pure white round head and bold black outlines [EXPRESSION: e.g. wide eyes in existential shock], looking at [PROP: e.g. an assembly line carrying thousands of tiny yellow chicks]. High-contrast bold composition, bright vibrant colors, clean vector line-art, zero clutter, large open negative space at the top for title text, 16:9 aspect ratio --ar 16:9 --v 6.1
```

### B. Gemini Omni / Runway / Kling (Image-to-Video Animation)

When animating static vector scenes into video:
* **Camera Movement:** Subtle slow push-in (zoom 1.05x over 4 seconds) or gentle lateral pan.
* **Character Motion:** Micro-animations only—blinking, eyebrow twitching, slow breath expansion in the chest, head tilting 5 degrees.
* **Prompt Structure:**
```text
Static 2D vector art animation. Keep the 2D illustration style completely flat and consistent with the reference image. The white-headed character slowly blinks and raises one eyebrow in skeptical disbelief while the digital alarm clock digits pulse quietly. Maintain crisp black outlines and zero 3D deformation.
```

### C. SVG Vector Character Generation (Code-Driven Rigs)

When generating code for direct rendering in web browsers or Remotion:
```html
<svg viewBox="0 0 400 600" xmlns="http://www.w3.org/2000/svg">
  <!-- Character Head -->
  <circle cx="200" cy="180" r="80" fill="#FFFFFF" stroke="#121212" stroke-width="7" />
  
  <!-- Eyebrows (Skeptical State) -->
  <path d="M 150 145 Q 165 135 180 145" stroke="#121212" stroke-width="5" stroke-linecap="round" fill="none" />
  <path d="M 220 150 Q 235 155 250 150" stroke="#121212" stroke-width="5" stroke-linecap="round" fill="none" />
  
  <!-- Eyes -->
  <circle cx="165" cy="170" r="6" fill="#121212" />
  <ellipse cx="235" cy="172" rx="7" ry="5" fill="#121212" />
  
  <!-- Mouth (Smirk) -->
  <path d="M 185 220 Q 200 220 215 212" stroke="#121212" stroke-width="5" stroke-linecap="round" fill="none" />
  
  <!-- Modular Torso -->
  <path d="M 160 260 L 240 260 L 255 380 L 145 380 Z" fill="#4EA8DE" stroke="#121212" stroke-width="6" />
</svg>
```
