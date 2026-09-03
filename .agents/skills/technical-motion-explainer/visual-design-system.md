# Technical Motion Explainer: Visual Design System

Complete specification of design tokens, layout geometry, vector SVG assets, and ready-to-render Remotion & HyperFrames components for dark technical motion explainers.

---

## 1. Design Tokens & Color Palettes

### Dialect A: Cyber-Minimalist Architecture (Kai & Devsplainers)
```css
:root {
  /* Backgrounds */
  --bg-primary: #0A0A0A;
  --bg-card: #121214;
  --bg-card-hover: #18181C;
  --bg-code: #0D0D10;

  /* Accent Colors */
  --accent-yellow: #FFD600;      /* Primary emphasis & stat counters */
  --accent-cyan: #38BDF8;        /* System nodes & active headroom */
  --accent-blue: #2563EB;        /* Cold models & router elements */
  --accent-red: #EF4444;         /* Errors, alerts, high load, cheap models */
  --accent-green: #22C55E;       /* Safe memory zones & verified badges */

  /* Borders & Glows */
  --border-subtle: rgba(255, 255, 255, 0.08);
  --border-cyan-glow: 0 0 16px rgba(56, 189, 248, 0.25);
  --border-yellow-glow: 0 0 16px rgba(255, 214, 0, 0.25);
  --border-red-glow: 0 0 16px rgba(239, 68, 68, 0.25);

  /* Typography */
  --font-headline: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-mono: "JetBrains Mono", "SF Mono", "Fira Code", monospace;
  --text-primary: #FFFFFF;
  --text-muted: #888888;
  --text-dim: #4B5563;
}
```

### Dialect B: Dark Blueprint / Chalk-Vector (RepoChad)
```css
:root {
  /* Backgrounds */
  --bg-blueprint: #0B0E14;
  --bg-card-blueprint: #131722;

  /* Chalk / Marker Accents */
  --marker-green: #84CC16;       /* GPU fans & resident weight */
  --marker-orange: #F97316;      /* Entry-level cards & PCIe bottlenecks */
  --marker-yellow: #FACC15;      /* 12GB VRAM cards & control titles */
  --marker-lavender: #A855F7;    /* VRAM specifications */
  --marker-teal: #14B8A6;        /* Quantization & step counters */
  --marker-crimson: #F43F5E;     /* Decode collapse & OOM threshold */

  /* Typography */
  --font-chalk: "Architects Daughter", "Caveat", "Comic Neue", cursive;
  --font-mono: "JetBrains Mono", monospace;
}
```

---

## 2. Typography Hierarchy

| Role | Font Family | Size | Weight | Tracking / Case | Color |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Eyebrow / Category** | Monospace | 14px – 18px | 500 | `letter-spacing: 0.18em; uppercase;` | `--text-muted` (`#888888`) |
| **Main Headline** | Sans-Serif | 48px – 64px | 800 | `letter-spacing: -0.02em;` | Pure White (`#FFFFFF`) |
| **Stat Counter** | Sans-Serif | 72px – 120px | 900 | Compact numerals | `--accent-yellow` or `--accent-cyan` |
| **Card Header** | Sans or Chalk | 20px – 28px | 700 | Title Case or All-Caps | Accent or White |
| **Code / Diagnostics** | Monospace | 16px – 22px | 400 | Standard monospace | `#CCCCCC` (alert: `#EF4444`) |
| **Watermark Tag** | Monospace | 13px – 15px | 400 | `letter-spacing: 0.1em;` | `#4B5563` (`<kaiexplains>`) |

---

## 3. Core Vector Component Catalogue

### Component 1: `StatCounter` (Massive Number Reveal)
Used for shocking data points (`6,971`, `896`, `$2.3M`).

```tsx
// Remotion (React) Implementation
import React from "react";
import { interpolate, useCurrentFrame, spring, useVideoConfig } from "remotion";

export const StatCounter: React.FC<{
  eyebrow: string;
  value: number;
  prefix?: string;
  suffix?: string;
  label: string;
  calloutBoxText?: string;
}> = ({ eyebrow, value, prefix = "", suffix = "", label, calloutBoxText }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Snappy counter spring
  const progress = spring({ frame, fps, config: { damping: 14, stiffness: 100 } });
  const displayVal = Math.round(interpolate(progress, [0, 1], [0, value]));

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", background: "#0A0A0A" }}>
      <div style={{ fontFamily: "monospace", color: "#888888", letterSpacing: "0.2em", fontSize: 18, marginBottom: 24 }}>
        {eyebrow.toUpperCase()}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 48 }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontFamily: "Inter, sans-serif", fontWeight: 900, fontSize: 110, color: "#FFD600", lineHeight: 1 }}>
            {prefix}{displayVal.toLocaleString()}{suffix}
          </div>
          <div style={{ fontFamily: "monospace", color: "#AAAAAA", letterSpacing: "0.15em", fontSize: 16, marginTop: 12 }}>
            {label.toUpperCase()}
          </div>
        </div>
        {calloutBoxText && (
          <div style={{ border: "3px solid #EF4444", padding: "16px 28px", borderRadius: 4, fontFamily: "Inter, sans-serif", fontWeight: 800, fontSize: 24, color: "#FFFFFF" }}>
            {calloutBoxText.toUpperCase()}
          </div>
        )}
      </div>
      <div style={{ position: "absolute", bottom: 32, right: 48, fontFamily: "monospace", color: "#444444", fontSize: 14 }}>
        &lt;channelname&gt;
      </div>
    </div>
  );
};
```

---

### Component 2: `CapacityBar` (VRAM & Headroom Threshold)
Used for memory limits, context budgets, and useful headroom calculations.

```html
<!-- HyperFrames / CSS Blueprint -->
<div class="capacity-container" style="background:#0A0A0A; padding:60px; color:#FFF; font-family:'Inter',sans-serif;">
  <div class="eyebrow" style="font-family:monospace; color:#888; letter-spacing:0.15em; font-size:16px;">
    DGX B300 — 8×B300 GPUS
  </div>
  <div class="headline" style="font-size:48px; font-weight:800; margin:16px 0 36px 0;">
    2.3 TB — USEFUL HEADROOM
  </div>
  
  <!-- Outer Bar Track -->
  <div class="bar-track" style="position:relative; width:100%; height:32px; background:#1C1C20; border-radius:4px; overflow:hidden;">
    <!-- Filled Portion -->
    <div class="bar-fill" style="width:72%; height:100%; background:#FFD600;"></div>
    <!-- Red Threshold Marker -->
    <div class="threshold-line" style="position:absolute; left:68%; top:0; bottom:0; width:3px; background:#EF4444;"></div>
  </div>

  <!-- Stat Highlight -->
  <div class="stat-highlight" style="margin-top:28px; text-align:center;">
    <span style="font-size:72px; font-weight:900; color:#38BDF8;">900</span>
    <span style="font-family:monospace; font-size:22px; color:#AAA; margin-left:12px;">GB CLEAR</span>
  </div>

  <!-- Tag Pill -->
  <div style="display:flex; justify-content:center; margin-top:24px;">
    <div style="padding:10px 32px; border:1px solid #2563EB; box-shadow:0 0 12px rgba(37,99,235,0.4); border-radius:8px; font-family:monospace; font-size:16px; color:#93C5FD;">
      DGX B300
    </div>
  </div>
</div>
```

---

### Component 3: `HardwareCard` (Vector Dual-Fan GPU)
Used for graphics card specifications, local hardware comparisons, and VRAM sizing.

```svg
<!-- Vector SVG Graphics Card with Dual Fans -->
<svg width="340" height="200" viewBox="0 0 340 200" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Card Shroud Outer -->
  <rect x="6" y="6" width="328" height="150" rx="14" fill="#11161F" stroke="#84CC16" stroke-width="3"/>
  <!-- PCIe Finger Connector at Bottom -->
  <g fill="#84CC16">
    <rect x="100" y="160" width="8" height="14"/>
    <rect x="114" y="160" width="8" height="14"/>
    <rect x="128" y="160" width="8" height="14"/>
    <rect x="142" y="160" width="8" height="14"/>
    <rect x="156" y="160" width="8" height="14"/>
    <rect x="170" y="160" width="8" height="14"/>
    <rect x="184" y="160" width="8" height="14"/>
    <rect x="198" y="160" width="8" height="14"/>
    <rect x="212" y="160" width="8" height="14"/>
  </g>
  <!-- Mini Logo Tag -->
  <rect x="280" y="16" width="38" height="20" rx="3" fill="#84CC16"/>
  <!-- Fan 1 (Left) -->
  <circle cx="95" cy="81" r="42" stroke="#84CC16" stroke-width="2"/>
  <g transform="rotate(45 95 81)">
    <path d="M95 81 C90 55 105 50 115 50 C110 65 105 75 95 81 Z" fill="#84CC16"/>
    <path d="M95 81 C121 76 126 91 126 101 C111 96 101 91 95 81 Z" fill="#84CC16"/>
    <path d="M95 81 C100 107 85 112 75 112 C80 97 85 87 95 81 Z" fill="#84CC16"/>
    <path d="M95 81 C69 86 64 71 64 61 C79 66 89 71 95 81 Z" fill="#84CC16"/>
  </g>
  <!-- Fan 2 (Right) -->
  <circle cx="215" cy="81" r="42" stroke="#84CC16" stroke-width="2"/>
  <g transform="rotate(45 215 81)">
    <path d="M215 81 C210 55 225 50 235 50 C230 65 225 75 215 81 Z" fill="#84CC16"/>
    <path d="M215 81 C241 76 246 91 246 101 C231 96 221 91 215 81 Z" fill="#84CC16"/>
    <path d="M215 81 C220 107 205 112 195 112 C200 97 205 87 215 81 Z" fill="#84CC16"/>
    <path d="M215 81 C189 86 184 71 184 61 C199 66 209 71 215 81 Z" fill="#84CC16"/>
  </g>
</svg>
```

---

### Component 4: `ArchitectureRouter` (Flowchart & Percentage Split)
Used for model routing, dynamic dispatch, and load-splitting explainers.

```tsx
// Remotion Flowchart Node
export const ArchitectureRouter: React.FC<{
  inputPromptText: string;
  routerName: string;
  leftTarget: { name: string; pct: number; color: string };
  rightTarget: { name: string; pct: number; color: string };
}> = ({ inputPromptText, routerName, leftTarget, rightTarget }) => {
  return (
    <div style={{ position: "relative", width: 500, height: 420 }}>
      {/* Input Prompt Box */}
      <div style={{ border: "3px solid #FFF", padding: "12px 24px", color: "#FFF", fontFamily: "Inter, sans-serif", fontWeight: 800, textAlign: "center" }}>
        {inputPromptText.toUpperCase()}
      </div>

      {/* Pulsing Diamond Router */}
      <div style={{ width: 90, height: 90, background: "#2563EB", transform: "rotate(45deg)", margin: "36px auto 0 auto", boxShadow: "0 0 24px rgba(37,99,235,0.6)", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ transform: "rotate(-45deg)", color: "#FFF", fontSize: 13, fontFamily: "monospace", fontWeight: 700 }}>
          {routerName}
        </span>
      </div>

      {/* Target Nodes */}
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 48 }}>
        {/* Left Destination */}
        <div style={{ textAlign: "center" }}>
          <div style={{ width: 110, height: 110, borderRadius: "50%", border: `3px solid ${leftTarget.color}`, display: "flex", alignItems: "center", justifyContent: "center", color: leftTarget.color, fontFamily: "monospace", fontSize: 13, padding: 8 }}>
            {leftTarget.name}
          </div>
          <div style={{ fontSize: 32, fontWeight: 900, color: leftTarget.color, marginTop: 12 }}>
            {leftTarget.pct}%
          </div>
        </div>

        {/* Right Destination */}
        <div style={{ textAlign: "center" }}>
          <div style={{ width: 110, height: 110, borderRadius: "50%", border: `3px solid ${rightTarget.color}`, display: "flex", alignItems: "center", justifyContent: "center", color: rightTarget.color, fontFamily: "monospace", fontSize: 13, padding: 8 }}>
            {rightTarget.name}
          </div>
          <div style={{ fontSize: 32, fontWeight: 900, color: rightTarget.color, marginTop: 12 }}>
            {rightTarget.pct}%
          </div>
        </div>
      </div>
    </div>
  );
};
```

---

### Component 5: `GlitchTerminal` (Corrupted Monospace Window)
Used for bug disclosures, degraded code outputs, and silent infrastructure failures.

```css
.glitch-terminal {
  background: #0E0E10;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 24px 32px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 18px;
  line-height: 1.8;
  color: #CCCCCC;
}

.glitch-terminal .line-alert {
  color: #EF4444;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}

.glitch-terminal .cursor {
  display: inline-block;
  width: 10px;
  height: 20px;
  background: #EF4444;
  animation: blink 0.8s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
```

---

## 4. Motion Physics & GSAP Easing Rules

1. **Spring Transitions (Remotion)**:
   * **Cards & Panels**: `damping: 18, stiffness: 140` (settles in 0.35s without rubber-banding).
   * **Stat Rollups**: Linear interpolation driven by a smooth cubic-bezier (`[0.16, 1, 0.3, 1]`).
2. **GSAP Timeline (HyperFrames)**:
   * **Element Entrance**: `gsap.from(target, { y: 24, opacity: 0, duration: 0.45, ease: "power3.out" })`.
   * **Threshold Split**: `gsap.to(".threshold-line", { left: "68%", duration: 0.6, ease: "back.out(1.4)" })`.
3. **Pacing Rule**: Never allow a static frame to remain unchanged for more than **3.2 seconds**. Introduce subtle pan, number count-up, or progressive highlight.
