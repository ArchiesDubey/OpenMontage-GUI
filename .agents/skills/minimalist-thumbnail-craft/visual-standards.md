# Visual Standards & Safe Zones for Minimalist Thumbnails

This guide defines the exact mathematical dimensions, typography specifications, color tokens, and platform safe zones required to build pixel-perfect 2D minimalist vector thumbnails.

---

## 1. Canvas Dimensions & Resolutions

* **Design Canvas:** `1280 x 720 px` (Standard 16:9 YouTube Thumbnail)
* **Master High-Res Canvas:** `1920 x 1080 px` (Full HD Master)
* **Mobile Evaluation Scale:** `120 x 67.5 px` (The Squint Test scale)
* **Color Space:** sRGB
* **Export Formats:** PNG (lossless vector render) or JPEG (quality 92+ under 2MB)

---

## 2. Platform Safe Zones (The Timestamp Danger Zone)

YouTube permanently renders a black duration badge (`"11:12"`, `"21:47"`) over the **bottom-right corner** of every thumbnail across mobile and desktop. 

```
+-------------------------------------------------------------------+
| [SAFE: Headline Text Zone - Top 30%]                              |
|   "NO JOBS" / "FAKE SLEEP?" / "WHY?"                              |
|                                                                   |
| [SAFE: Primary Focal Point]            [SAFE: Secondary Prop]      |
|  - Left/Center Hero Character           - Environmental context   |
|                                                                   |
|                                        +--------------------------+
|                                        | [DANGER ZONE: TIMESTAMP] |
|                                        |  Bottom-Right (280x140px)|
|                                        |  NO FACES / NO TEXT HERE |
+----------------------------------------+--------------------------+
```

### Safe Zone Rules:
1. **Timestamp Exclusion Box (on 1280x720):**
   * `X: 1000px to 1280px`
   * `Y: 580px to 720px`
   * Never place the character's face, key props, or words inside this coordinate box.
2. **Text Placement:** Place text either:
   * **Top-Center** (e.g., `"WHY?"`)
   * **Top-Right** (e.g., `"NO JOBS"`)
   * **Top-Left** (if character is framed on the right)

---

## 3. Typography Specifications

The goal of minimalist explainer typography is **instantaneous decipherability under high visual noise**.

### Font Hierarchy
* **Primary Fonts:** `Outfit` (Weight 900), `Montserrat` (Weight 900 / Black), `Impact`, or `Anton`.
* **Casing:** Strictly **ALL CAPS** (e.g., `NO JOBS`, `FAKE SLEEP?`, `NOT IN CHARGE`).
* **Letter Spacing (Tracking):** `-1px` to `-3px` (compact and punchy).
* **Font Size (on 1280x720):**
  * 1 Word (`"WHY?"`): `160px – 190px`
  * 2 Words (`"NO JOBS"`): `130px – 150px`
  * 3 Words (`"NOT IN CHARGE"`): `110px – 130px`

### The Outer Stroke Formula (CSS / SVG)
To achieve the distinct cartoon outer border without distorting the letter interiors:

```css
.thumbnail-headline {
  font-family: 'Outfit', 'Montserrat', 'Impact', sans-serif;
  font-weight: 900;
  font-size: 140px;
  color: #FFEE00; /* Canary Yellow */
  text-transform: uppercase;
  letter-spacing: -2px;
  
  /* The Double Stroke + Drop Shadow Formula */
  -webkit-text-stroke: 18px #121212;
  paint-order: stroke fill;
  filter: drop-shadow(0 12px 0 #121212);
}
```

---

## 4. Color Palette & Token Matrix

```
/* Text Tokens */
--color-text-primary:      #FFEE00; /* High-Luminance Canary Yellow (Highest CTR) */
--color-text-secondary:    #FFDF00; /* Golden Warm Yellow */
--color-text-alert:        #FF3B30; /* Warning Red (For crisis/controversy) */
--color-text-stroke:       #121212; /* Deep Ink Black */

/* Character Tokens */
--color-character-head:    #FFFFFF; /* Pure Flat White */
--color-character-stroke:  #121212; /* Thick Ink Linework */
--color-character-skin-sh: #E8EDF2; /* Subtle Soft-Cell Shadow */

/* Atmosphere & Background Tokens */
--color-bg-day-sky:        #87CEEB; /* Ancient Prehistoric Sky */
--color-bg-day-grass:      #A2D075; /* Savannah Sage */
--color-bg-night-room:     #0D1B2A; /* Insomnia Midnight Navy */
--color-bg-night-accent:   #7B2CBF; /* Headboard Purple */
--color-bg-industrial:     #B8C1C8; /* Cold Factory Steel */
--color-bg-psychology-vign:#111A24; /* Mind-Cockpit Vignette */
```

---

## 5. Vector Stroke Hierarchy

| Element | Stroke Weight (on 1280x720) | Visual Role |
| :--- | :--- | :--- |
| **Headline Text Outer Stroke** | `16px – 22px` | Maximizes contrast over any background. |
| **Hero Character Outline** | `7px – 9px` | Separates foreground avatar from scene. |
| **Secondary Props / Machines** | `4px – 6px` | Communicates context without clutter. |
| **Background Landscape Lines** | `2px – 3px` | Atmospheric depth without competing for attention. |
