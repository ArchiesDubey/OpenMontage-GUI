---
name: minimalist-thumbnail-craft
description: Engineer high-CTR YouTube thumbnails for 2D minimalist vector explainers (Ink Explainer, Robert Like's History, OverSimplified styles) using HTML/SVG templates, viral psychology frameworks, and headless rendering.
---

# Minimalist Thumbnail Craft

A dedicated production skill for engineering high-CTR YouTube thumbnails in the **2D Minimalist Vector / Egghead Stickman** style (emulating *Ink Explainer*, *Robert Like's History*, and top educational essayists).

---

## The 4 Golden Rules of High-CTR Minimalist Thumbnails

Mainstream clickbait thumbnails with over-saturated 3D faces and red arrows fatigue modern viewers. Minimalist vector explainers achieve massive CTR (often >10–14%) because they rely on **High Cognitive Dissonance & Radical Visual Simplicity**:

1. **Title-Thumbnail Synergy (Never Duplicate):**
   * The thumbnail text must **never** repeat the video title.
   * If the title asks a question (*"Why Do Humans Have to Pretend to Sleep..."*), the thumbnail validates the private weirdness (*"FAKE SLEEP?"*).
   * If the title is an exploration (*"What Did Ancient Humans Actually Do All Day?"*), the thumbnail drops the shocking conclusion (*"NO JOBS"*).
2. **The 3-Element Rule:**
   * Maximum 3 visual anchors on screen: (1) One emotive white Egghead character, (2) One stark contextual prop/paradox, (3) One 1–3 word high-luminance headline.
3. **Canary Yellow + Heavy Ink Outline:**
   * Text is always high-luminance Canary Yellow (`#FFEE00` / `#FFDF00`) with a heavy dark ink stroke (`#121212`, 16–22px) or bold drop-shadow.
4. **Pass the 120px Mobile Squint Test:**
   * 75%+ of YouTube views originate on mobile devices where thumbnails are viewed at ~120–150px wide. If the character's emotion and the punchline aren't instantly decipherable at that scale, the thumbnail fails.

---

## The 4 Proven Design Archetypes

| Archetype | Reference Video | Formula | Emotional Trigger |
| :--- | :--- | :--- | :--- |
| **1. The Counter-Intuitive Truth** | *What Did Ancient Humans Do All Day?* (`49_Ph2q6uIM`) | `[Relaxed Egghead] + [Prehistoric Savannah] + "NO JOBS"` | Irony / Workplace escape fantasy |
| **2. The Private Behavior Mirror** | *Why Do Humans Pretend to Sleep?* (`ZhIeknerhrQ`) | `[Restless Egghead in Bed] + [Midnight Moon] + "FAKE SLEEP?"` | Validation of private habit |
| **3. The Moral Tragedy / Paradox** | *Why We Kill Every Male Chick* (`YtDaH7GkhOc`) | `[Distressed Vulnerable Subject] + [Cold Industrial Factory] + "WHY?"` | Deep empathy / Injustice outcry |
| **4. The Inside-Out Mind Cockpit** | *Human Psychology Redesign* (`uoj1qA47KN4`) | `[Panicked Egghead with Open Head] + [Mini-Stickman Cockpit] + "NOT IN CHARGE"` | Loss of cognitive control / Matrix reveal |

---

## Reference Playbooks

* **[CTR Psychology & Archetype Breakdown](ctr-psychology-and-archetypes.md):** Side-by-side deconstruction of all 4 reference videos, including the exact flaws of Video 4 and how to fix them.
* **[Visual Standards & Safe Zones](visual-standards.md):** Typography specs, YouTube mobile duration badge exclusion zones, color hex tokens, and stroke math.
* **[Ready-to-Render HTML Templates](templates/):**
  * `templates/counter-intuitive-truth.html` — The "NO JOBS" archetype.
  * `templates/private-behavior-mirror.html` — The "FAKE SLEEP?" archetype.
  * `templates/moral-tragedy.html` — The "WHY?" archetype.
  * `templates/mind-cockpit.html` — The optimized "NOT IN CHARGE" psychology archetype.
* **[Headless Render Script](scripts/render_thumbnail.py):** CLI tool to render pixel-perfect 1280x720 thumbnails and auto-generate 120px mobile-squint test previews.

---

## Quick Generation Workflow

```bash
# 1. Render a thumbnail from any HTML template
python .agents/skills/minimalist-thumbnail-craft/scripts/render_thumbnail.py \
  --template .agents/skills/minimalist-thumbnail-craft/templates/counter-intuitive-truth.html \
  --output scratch/thumbnail_no_jobs.png

# 2. Check the automatically generated mobile preview
# Output: scratch/thumbnail_no_jobs_mobile_squint.png (120px wide)
```
