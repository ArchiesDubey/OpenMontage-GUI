# Visual Standards & Color Tokens

## Canvas Architecture

* **Dimensions**: `1280 × 720` (Standard) or `1920 × 1080` (High-DPI, 16:9).
* **Safe Outer Margin**: `60px` padding on all four edges.
* **YouTube Timestamp Safe Zone**: Keep the bottom-right corner (`240px` wide by `100px` tall) completely clear of essential logos, text, or focal icons.

```
┌──────────────────────────────────────────────────────────┐
│  60px Margin                                             │
│  ┌────────────────────────────────────────────────────┐  │
│  │  HEADLINE ZONE (Top 25% of Canvas, 110px–140px)    │  │
│  │                                                    │  │
│  │  VISUAL ACTION CENTER                              │  │
│  │  [Entity A]    ───► [Entity B + Sticker]           │  │
│  │                                                    │  │
│  │                                    ┌────────────┐  │  │
│  │                                    │ TIMESTAMP  │  │  │
│  │                                    │ DEAD ZONE  │  │  │
│  └────────────────────────────────────┴────────────┘──┘  │
└──────────────────────────────────────────────────────────┘
```

---

## Color Tokens

### 1. The Canvas Bases
| Token | Hex | Role | Usage |
| :--- | :--- | :--- | :--- |
| `bg-pitch` | `#0A0A0A` | Primary Canvas | Infinite deep space, zero light leakage |
| `bg-card` | `#121217` | Entity Cards | Surface container for ICs and logos |
| `bg-card-subtle` | `#16161F` | Secondary Panels | Outer framing and pill containers |
| `border-subtle` | `#262632` | Structural Lines | Grid borders and hardware pin lines |

### 2. High-Voltage Accent Accents
| Token | Hex | Role | Reference Precedent |
| :--- | :--- | :--- | :--- |
| `accent-yellow` | `#FFD600` | Foundry Gold / Attention | Kai's GPU shroud, Devsplainers shadow, Wafer gold |
| `accent-cyan` | `#38BDF8` | Cyber Compute / Interface | RepoChad GPU badge, Devsplainers circle, Memory pools |
| `accent-red` | `#EF4444` | Warning / Crisis / Nerf | Kai's `"LOL"`, Devsplainers `"NERFED"`, Sacrificed DDR5 |
| `accent-green` | `#22C55E` | Hardware Health / Profit | RepoChad `"EVERY GPU"`, Margin badges, 32GB safe tier |
| `text-white` | `#FFFFFF` | Headline Primary | Pure crisp sans-serif block typography |

---

## The Zero-Blur Offset Shadow Law

A signature visual element of both **Kai** and **Devsplainers** is the complete absence of soft gaussian blurred drop-shadows. Soft blur looks like generic web UI; **sharp zero-blur comic offset shadows** look like bespoke technical illustration.

### Correct CSS Implementation:
```css
/* Card with Canary Yellow Offset Shadow */
.technical-card-yellow {
  background: #121217;
  border: 2px solid #ffffff;
  /* 8px X-offset, 8px Y-offset, 0px BLUR, solid color */
  box-shadow: 8px 8px 0px #FFD600;
}

/* Sticker with Cyber Blue Offset Shadow */
.sticker-blue {
  background: #ffffff;
  color: #EF4444;
  /* Crisp 6px offset */
  box-shadow: 6px 6px 0px #38BDF8;
  transform: rotate(-3deg);
}

/* SVG Graphic with Hard Drop Shadow */
.vector-node {
  filter: drop-shadow(8px 8px 0px #FFD600);
}
```

---

## Typography Standards

### 1. Main Headline
* **Font**: `Inter` (Font-Weight: `900` Black), `Impact`, or `Bebas Neue`.
* **Size**: `110px – 140px` on 1920x1080 (`76px – 96px` on 1280x720).
* **Letter-Spacing**: `-0.03em` to `-0.04em` (compact, massive visual weight).
* **Word Count**: **2 to 4 words strictly**. If you need 5 words, cut 2.
* **Color Rule**: 1 or 2 words in `#FFFFFF`, remaining word in `#EF4444` or `#FFD600`.

### 2. Monospace Receipt Badges
* **Font**: `JetBrains Mono` (Font-Weight: `700` Bold) or `Roboto Mono`.
* **Size**: `26px – 34px`.
* **Letter-Spacing**: `0.1em` uppercase.
* **Padding**: `6px 14px` inside solid pill container.
