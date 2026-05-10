"""Generate project-logo.png at 1000x1000 from the inline Navbar SVG.

Pulls the same neuron mark used in nla-frontend/src/components/Navbar.tsx,
re-lays it on a square canvas with the wordmark beneath, and rasterizes
to PNG with resvg.
"""

from __future__ import annotations

from pathlib import Path

import resvg_py

ROOT = Path(__file__).resolve().parent.parent

# Brand tokens lifted from nla-frontend/src/app/tokens.css
BG = "#0E0E10"
FG = "#F5F4EE"
ACCENT = "#cc785c"
ACCENT_LIGHT = "#e8a987"

# Neuron paths from Navbar.tsx (group is at translate(60, 80) in 500x160).
# We re-anchor to the centre of the 1000x1000 canvas at scale ~6.5x.
SVG = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000" viewBox="0 0 1000 1000">
  <rect width="1000" height="1000" fill="{BG}"/>

  <!-- Neuron mark: original at translate(60,80) scale 1, here we centre and scale ~6.0x -->
  <g transform="translate(500,420) scale(6.0)" stroke-linecap="round" fill="none">
    <!-- top-left dendrite + branches -->
    <path d="M -5 -4 C -16 -14, -22 -22, -26 -32" stroke="{ACCENT}" stroke-width="4.5"/>
    <path d="M -26 -32 C -30 -36, -32 -36, -34 -32" stroke="{ACCENT}" stroke-width="3"/>
    <path d="M -26 -32 C -22 -36, -22 -40, -20 -42" stroke="{ACCENT}" stroke-width="3"/>
    <!-- left dendrite + branches -->
    <path d="M -7 0 C -22 -2, -32 -2, -38 0" stroke="{ACCENT}" stroke-width="4.5"/>
    <path d="M -38 0 C -42 -3, -44 -3, -46 0" stroke="{ACCENT}" stroke-width="3"/>
    <path d="M -38 0 C -42 3, -44 3, -46 4" stroke="{ACCENT}" stroke-width="3"/>
    <!-- bottom-left dendrite + branches -->
    <path d="M -5 4 C -16 14, -22 22, -26 32" stroke="{ACCENT}" stroke-width="4.5"/>
    <path d="M -26 32 C -30 36, -32 36, -34 32" stroke="{ACCENT}" stroke-width="3"/>
    <path d="M -26 32 C -22 36, -22 40, -20 42" stroke="{ACCENT}" stroke-width="3"/>
    <!-- soma -->
    <circle cx="0" cy="0" r="11" fill="{ACCENT}"/>
    <!-- right axon + terminal branches -->
    <path d="M 9 1 C 28 1, 48 0, 64 4" stroke="{ACCENT}" stroke-width="4.5"/>
    <path d="M 64 4 C 70 0, 74 -2, 76 -4" stroke="{ACCENT}" stroke-width="3"/>
    <path d="M 64 4 C 70 8, 72 12, 72 16" stroke="{ACCENT}" stroke-width="3"/>
    <circle cx="77" cy="-5" r="3" fill="{ACCENT_LIGHT}"/>
    <circle cx="73" cy="17" r="3" fill="{ACCENT_LIGHT}"/>
  </g>

  <!-- Wordmark -->
  <text x="500" y="850" text-anchor="middle"
        font-family="-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', system-ui, sans-serif"
        font-weight="600" font-size="120" letter-spacing="-2" fill="{FG}">verbalize</text>
</svg>
"""


def main() -> int:
    out_path = ROOT / "project-logo.png"
    svg_path = ROOT / "scripts" / "project-logo.svg"
    svg_path.write_text(SVG)

    # resvg_py expects bytes/str of svg, returns list[int] of PNG bytes
    png_data = resvg_py.svg_to_bytes(svg_string=SVG, width=1000, height=1000)
    out_path.write_bytes(bytes(png_data))

    size_kb = out_path.stat().st_size / 1024
    print(f"wrote {out_path} ({size_kb:.1f} KB, target <500)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
