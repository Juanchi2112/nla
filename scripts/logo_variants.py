"""Render 4 logo concept variants for Verbalize, all 1000x1000.

Outputs to docs/logo-variants/{variant-a,variant-b,variant-c,variant-d}.png
plus a side-by-side compare grid at docs/logo-variants/compare.png.

Concepts:
  A — Magnifying glass over a neuron (direct inspection metaphor)
  B — Speech bubble containing a neuron (say-vs-compute tension)
  C — Brackets [ ] framing a neuron (code register: "we read this")
  D — Transformer layer stack with a neuron tapping one layer (architectural)

All variants share the same palette and rasterizer, so we can pick one
and drop it into make_logo.py without further work.
"""

from __future__ import annotations

from pathlib import Path

import resvg_py

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "logo-variants"

BG = "#0E0E10"
FG = "#F5F4EE"
ACCENT = "#cc785c"
ACCENT_DIM = "#7a4836"  # darker terracotta for de-emphasized strokes


# ─── Reusable: a small Golgi-style neuron centred at (cx, cy), scaled ────
# Returns the <g> contents (paths + soma). Caller wraps in own group.
def neuron_paths(cx: float, cy: float, scale: float = 1.0, color: str = ACCENT) -> str:
    s = scale
    # Pre-computed asymmetric branches anchored at (0,0). Multiply by s, offset by (cx, cy).
    # Each tuple: (d, stroke_width)
    paths = [
        # Dendrite 1 — long up-left
        (
            f"M {-12 * s} {-2 * s} C {-60 * s} {-50 * s} {-120 * s} {-112 * s} {-210 * s} {-204 * s}",
            6.5 * s,
        ),
        (
            f"M {-186 * s} {-180 * s} C {-210 * s} {-204 * s} {-236 * s} {-216 * s} {-268 * s} {-226 * s}",
            2.5 * s,
        ),
        (
            f"M {-210 * s} {-204 * s} C {-220 * s} {-232 * s} {-226 * s} {-256 * s} {-232 * s} {-288 * s}",
            2.5 * s,
        ),
        # Dendrite 2 — vertical
        (
            f"M {-4 * s} {-8 * s} C {-12 * s} {-80 * s} {-20 * s} {-150 * s} {-30 * s} {-218 * s}",
            5.6 * s,
        ),
        (
            f"M {-30 * s} {-218 * s} C {-40 * s} {-240 * s} {-50 * s} {-260 * s} {-58 * s} {-280 * s}",
            1.8 * s,
        ),
        (
            f"M {-30 * s} {-218 * s} C {-22 * s} {-240 * s} {-16 * s} {-256 * s} {-12 * s} {-274 * s}",
            1.8 * s,
        ),
        # Dendrite 3 — up-right
        (
            f"M {10 * s} {-6 * s} C {40 * s} {-62 * s} {68 * s} {-120 * s} {100 * s} {-182 * s}",
            5.0 * s,
        ),
        (
            f"M {100 * s} {-182 * s} C {114 * s} {-202 * s} {122 * s} {-218 * s} {132 * s} {-234 * s}",
            1.7 * s,
        ),
        (
            f"M {100 * s} {-182 * s} C {108 * s} {-204 * s} {112 * s} {-222 * s} {112 * s} {-242 * s}",
            1.7 * s,
        ),
        # Dendrite 4 — left horizontal
        (
            f"M {-16 * s} {10 * s} C {-68 * s} {14 * s} {-120 * s} {14 * s} {-174 * s} {10 * s}",
            4.0 * s,
        ),
        (
            f"M {-174 * s} {10 * s} C {-188 * s} {2 * s} {-198 * s} {-6 * s} {-208 * s} {-16 * s}",
            1.6 * s,
        ),
        (
            f"M {-174 * s} {10 * s} C {-188 * s} {16 * s} {-198 * s} {24 * s} {-208 * s} {32 * s}",
            1.6 * s,
        ),
        # Dendrite 5 — short down-left
        (
            f"M {-10 * s} {22 * s} C {-42 * s} {48 * s} {-78 * s} {68 * s} {-116 * s} {80 * s}",
            3.6 * s,
        ),
        (
            f"M {-116 * s} {80 * s} C {-128 * s} {88 * s} {-136 * s} {94 * s} {-144 * s} {98 * s}",
            1.5 * s,
        ),
        (
            f"M {-116 * s} {80 * s} C {-122 * s} {94 * s} {-126 * s} {104 * s} {-126 * s} {118 * s}",
            1.5 * s,
        ),
        # Axon — long, down-right with a bend
        (
            f"M {14 * s} {22 * s} C {80 * s} {52 * s} {160 * s} {100 * s} {220 * s} {160 * s} S {270 * s} {220 * s} {300 * s} {240 * s}",
            3.2 * s,
        ),
        (
            f"M {300 * s} {240 * s} C {316 * s} {254 * s} {324 * s} {262 * s} {330 * s} {270 * s}",
            1.5 * s,
        ),
        (
            f"M {300 * s} {240 * s} C {308 * s} {260 * s} {310 * s} {270 * s} {308 * s} {282 * s}",
            1.5 * s,
        ),
    ]

    soma_rx, soma_ry = 17 * s, 14 * s
    return f"""
  <g transform="translate({cx},{cy})" fill="none" stroke="{color}" stroke-linecap="round" stroke-linejoin="round">
    {chr(10).join(f'<path d="{d}" stroke-width="{w:.2f}"/>' for d, w in paths)}
  </g>
  <ellipse cx="{cx}" cy="{cy}" rx="{soma_rx:.1f}" ry="{soma_ry:.1f}" fill="{color}"/>
"""


# ─── Variant A — magnifying glass over a neuron ─────────────────────────
def variant_a() -> str:
    # Lens centred upper-left, handle going lower-right
    lens_cx, lens_cy, lens_r = 410, 410, 230
    handle_x1, handle_y1 = 575, 575
    handle_x2, handle_y2 = 800, 800
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000" viewBox="0 0 1000 1000">
  <rect width="1000" height="1000" fill="{BG}"/>

  <!-- Neuron, contained within the lens (drawn first, behind lens ring) -->
  {neuron_paths(lens_cx, lens_cy, scale=0.7, color=ACCENT)}

  <!-- Lens ring -->
  <circle cx="{lens_cx}" cy="{lens_cy}" r="{lens_r}" fill="none" stroke="{ACCENT}" stroke-width="14"/>

  <!-- Handle -->
  <line x1="{handle_x1}" y1="{handle_y1}" x2="{handle_x2}" y2="{handle_y2}"
        stroke="{ACCENT}" stroke-width="26" stroke-linecap="round"/>
</svg>
"""


# ─── Variant B — speech bubble containing a neuron ──────────────────────
def variant_b() -> str:
    # Rounded-rect speech bubble with a tail at the bottom-left
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000" viewBox="0 0 1000 1000">
  <rect width="1000" height="1000" fill="{BG}"/>

  <!-- Speech bubble outline -->
  <path d="M 200 220
           Q 200 160, 260 160
           L 740 160
           Q 800 160, 800 220
           L 800 600
           Q 800 660, 740 660
           L 410 660
           L 350 760
           L 360 660
           L 260 660
           Q 200 660, 200 600
           Z"
        fill="none" stroke="{ACCENT}" stroke-width="14" stroke-linejoin="round"/>

  <!-- Neuron inside the bubble -->
  {neuron_paths(500, 410, scale=0.62, color=ACCENT)}
</svg>
"""


# ─── Variant C — brackets framing a neuron ──────────────────────────────
def variant_c() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000" viewBox="0 0 1000 1000">
  <rect width="1000" height="1000" fill="{BG}"/>

  <!-- Left bracket -->
  <path d="M 270 240 L 170 240 L 170 760 L 270 760"
        fill="none" stroke="{ACCENT}" stroke-width="18" stroke-linecap="round" stroke-linejoin="miter"/>

  <!-- Right bracket -->
  <path d="M 730 240 L 830 240 L 830 760 L 730 760"
        fill="none" stroke="{ACCENT}" stroke-width="18" stroke-linecap="round" stroke-linejoin="miter"/>

  <!-- Neuron centred between brackets -->
  {neuron_paths(500, 500, scale=0.78, color=ACCENT)}
</svg>
"""


# ─── Variant D — transformer layers + tap point + neuron ────────────────
def variant_d() -> str:
    """Five horizontal layer-bars stacked. The middle bar is highlighted
    and a small neuron 'grows' out of it (dendrites up, axon down) — the
    visual claim 'we tap layer N and read what's there'."""
    layers_y = [240, 320, 400, 480, 560, 640, 720]  # 7 layers
    tap_y = 480  # the layer we tap (~middle, like Qwen layer 20 of 28)

    layer_lines = []
    for y in layers_y:
        emphasized = y == tap_y
        sw = 14 if emphasized else 6
        col = ACCENT if emphasized else ACCENT_DIM
        layer_lines.append(
            f'<line x1="200" y1="{y}" x2="800" y2="{y}" stroke="{col}" stroke-width="{sw}" stroke-linecap="round"/>'
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000" viewBox="0 0 1000 1000">
  <rect width="1000" height="1000" fill="{BG}"/>

  <!-- Layer stack -->
  <g>
    {chr(10).join("    " + ln for ln in layer_lines)}
  </g>

  <!-- Neuron tapping the middle layer, scaled down so it doesn't overpower -->
  {neuron_paths(500, tap_y, scale=0.55, color=ACCENT)}
</svg>
"""


# ─── Driver ─────────────────────────────────────────────────────────────
VARIANTS = {
    "a-magnifier": variant_a,
    "b-speech-bubble": variant_b,
    "c-brackets": variant_c,
    "d-layers": variant_d,
}


def render_one(name: str, svg: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    svg_path = OUT_DIR / f"variant-{name}.svg"
    png_path = OUT_DIR / f"variant-{name}.png"
    svg_path.write_text(svg)
    png_data = resvg_py.svg_to_bytes(svg_string=svg, width=1000, height=1000)
    png_path.write_bytes(bytes(png_data))
    return png_path


def render_compare_grid() -> Path:
    """Render a 2x2 grid 2000x2000 showing all 4 variants side by side."""
    quadrants = []
    coords = [
        ("a-magnifier", 0, 0),
        ("b-speech-bubble", 1000, 0),
        ("c-brackets", 0, 1000),
        ("d-layers", 1000, 1000),
    ]
    for name, x, y in coords:
        # Strip the outer <svg> wrapper so we can nest into the grid
        svg = VARIANTS[name]()
        # Crude: replace top svg open with a translated <g>, drop </svg>
        inner = svg.split(">", 1)[1].split("<rect")[1].split("/>", 1)[1]
        quadrants.append(
            f'<g transform="translate({x},{y})">'
            f'  <rect width="1000" height="1000" fill="{BG}"/>'
            f"{inner}"
            f"</g>"
            f'<text x="{x + 500}" y="{y + 980}" text-anchor="middle" font-size="36" fill="{FG}" font-family="-apple-system,sans-serif" font-weight="500">variant {name.split("-")[0].upper()}</text>'
        )
    grid = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="2000" viewBox="0 0 2000 2000">
  <rect width="2000" height="2000" fill="{BG}"/>
  {chr(10).join(quadrants)}
  <line x1="1000" y1="0" x2="1000" y2="2000" stroke="{ACCENT_DIM}" stroke-width="2"/>
  <line x1="0" y1="1000" x2="2000" y2="1000" stroke="{ACCENT_DIM}" stroke-width="2"/>
</svg>
"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "compare.png"
    png_data = resvg_py.svg_to_bytes(svg_string=grid, width=2000, height=2000)
    out.write_bytes(bytes(png_data))
    return out


def main() -> int:
    for name, fn in VARIANTS.items():
        path = render_one(name, fn())
        size_kb = path.stat().st_size / 1024
        print(f"  variant {name:<18}  {size_kb:>6.1f} KB  {path}")
    grid = render_compare_grid()
    print(f"  compare grid       {grid.stat().st_size / 1024:>6.1f} KB  {grid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
