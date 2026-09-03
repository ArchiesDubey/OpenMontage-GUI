---
name: technical-thumbnail-craft
description: Design and generate high-CTR technical thumbnails in the minimalist vector, cyber-chalk, and hardware-schematic styles of Kai, RepoChad, and Devsplainers.
---

# Technical Thumbnail Craft

A production skill for engineering high-CTR YouTube thumbnails for dark technical explainers, hardware essays, and developer benchmarks. Emulates the distinct visual strategies of **Kai** (`fXWFSTSvnVM`), **RepoChad** (`0xUxO_9zqTU`), and **Devsplainers** (`7usmtO_bJx8`).

## Core Philosophy: The Zero-Slop Anti-MrBeast Standard

Mainstream YouTube thumbnails rely on over-saturated facial expressions, 3D gradient renders, and visual clutter. Technical audiences (software engineers, hardware enthusiasts, system architects) actively avoid these cues, associating them with low-substance clickbait.

This genre succeeds because it uses **The Whistleblower / Blueprint Aesthetic**:
1. **Pitch-Black / Deep Charcoal Canvas**: `#000000` to `#0A0A0A` base background.
2. **2 to 4 Word Headline Punch**: Massive sans-serif type (>110pt) stating a provocative assertion or reaction.
3. **The 3-Element Rule**: Maximum 3 visual elements on screen. Never crowd the canvas.
4. **100% Vector / Diagrammatic Precision**: Flat vector hardware silhouettes, stylized IC chips, mathematical arrows, and offset comic/chalk drop-shadows. Zero photorealistic human faces or generative AI artifacts.
5. **Monospace Technical Receipts**: Spec tags (`16GB`, `61.44TB`, `DDR5`, `BOM 38%`) pinned like physical evidence.

---

## The 3 Design Archetypes

| Archetype | Pioneer | Composition Formula | Emotional Hook |
| :--- | :--- | :--- | :--- |
| **1. The Asymmetry Reaction** | **Kai** | `[Entity A] -> [Arrow] -> [Mutated Entity B + Absurd Spec Sticker]` | Provocative disbelief ("HERE WE GO. LOL", "MINIMUM 1 TB") |
| **2. The Categorical Hardware Lineup** | **RepoChad** | `[Ranked Tier Progression of 4–5 Hardware Chips/GPUs]` | Definitive optimization / Benchmark authority ("BEST METHOD / EVERY GPU") |
| **3. The Whistleblower Degradation** | **Devsplainers** | `[Pure Ideal Primitive] -> [Arrow] -> [Fragmented / Nerfed Primitive]` | Secret exposed / Hardware scandal ("QUIETLY NERFED") |

---

## Detailed Playbooks & References

- **[Archetypes & Psychology](archetypes-and-psychology.md)**: Deep dive into the 3 archetypes, title-thumbnail pairing formulas, and mobile CTR psychology.
- **[Visual Standards & Color Tokens](visual-standards.md)**: Exact hex codes, typography rules, offset shadow math, and YouTube timestamp safe zones.
- **[Ready-to-Render HTML Templates](templates/)**:
  - `templates/asymmetry-reaction.html`: The Kai template.
  - `templates/hardware-lineup.html`: The RepoChad template.
  - `templates/whistleblower-degradation.html`: The Devsplainers template.
- **[Render Script](scripts/render_thumbnail.py)**: Headless CLI script to render pixel-perfect 1280x720 / 1920x1080 JPEG thumbnails.

---

## Quick Generation Workflow

```bash
# Render a thumbnail from any HTML template
python .agents/skills/technical-thumbnail-craft/scripts/render_thumbnail.py \
  --template .agents/skills/technical-thumbnail-craft/templates/asymmetry-reaction.html \
  --output projects/my-project/renders/thumbnail.jpg \
  --width 1280 \
  --height 720
```
