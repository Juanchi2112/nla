"""Generate project-logo.png at 1000x1000.

v3: mark-only Golgi-stained neuron. Several dendrites converge into a
single soma from one side; one axon trails out the other. Anatomically
this matches the actual signal flow in a real neuron (dendrites are
inputs, axon is the output), and symbolically it matches what Verbalize
does: many internal activation patterns converge and we read the
single emergent computation.

No wordmark on the mark itself — sans-serif fallback rendering inside
resvg clashed with the delicate ink-illustration register. The brand
name is set in proper typography wherever the mark is used.

Drawn entirely in flat strokes (no gradients, no filters) so it
rasterizes cleanly with resvg-py. Stroke widths step down on each
subdivision to suggest tapering: ~6px primary, ~2.5px secondary,
~1.5px terminal.
"""

from __future__ import annotations

from pathlib import Path

import resvg_py

ROOT = Path(__file__).resolve().parent.parent

# Brand tokens lifted from nla-frontend/src/app/tokens.css
BG = "#0E0E10"
FG = "#F5F4EE"
ACCENT = "#cc785c"

# Soma center, in viewBox coords. Dendrites converge into the soma from
# the left and above; the axon trails out to the lower-right.
SOMA_X, SOMA_Y = 500, 510

SVG = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000" viewBox="0 0 1000 1000">
  <rect width="1000" height="1000" fill="{BG}"/>

  <g fill="none" stroke="{ACCENT}" stroke-linecap="round" stroke-linejoin="round">

    <!-- ── Dendrite 1 ── long, far up-left, branches at tip ────────────── -->
    <path d="M 488 498 C 440 450, 380 388, 290 296" stroke-width="6.5"/>
    <path d="M 314 320 C 290 296, 264 284, 232 274" stroke-width="2.5"/>
    <path d="M 290 296 C 280 268, 274 244, 268 212" stroke-width="2.5"/>

    <!-- ── Dendrite 2 ── medium, almost vertical, two terminal tips ───── -->
    <path d="M 496 492 C 488 420, 480 350, 470 282" stroke-width="5.6"/>
    <path d="M 470 282 C 460 260, 450 240, 442 220" stroke-width="1.8"/>
    <path d="M 470 282 C 478 260, 484 244, 488 226" stroke-width="1.8"/>

    <!-- ── Dendrite 3 ── medium, up-right, branches splay out ─────────── -->
    <path d="M 510 494 C 540 438, 568 380, 600 318" stroke-width="5.0"/>
    <path d="M 600 318 C 614 298, 622 282, 632 266" stroke-width="1.7"/>
    <path d="M 600 318 C 608 296, 612 278, 612 258" stroke-width="1.7"/>

    <!-- ── Dendrite 4 ── horizontal, mid-left, short with two tips ────── -->
    <path d="M 484 510 C 432 514, 380 514, 326 510" stroke-width="4.0"/>
    <path d="M 326 510 C 312 502, 302 494, 292 484" stroke-width="1.6"/>
    <path d="M 326 510 C 312 516, 302 524, 292 532" stroke-width="1.6"/>

    <!-- ── Dendrite 5 ── short, down-left, slightly stubby for asymmetry  -->
    <path d="M 490 522 C 458 548, 422 568, 384 580" stroke-width="3.6"/>
    <path d="M 384 580 C 372 588, 364 594, 356 598" stroke-width="1.5"/>
    <path d="M 384 580 C 378 594, 374 604, 374 618" stroke-width="1.5"/>

    <!-- ── Axon ── single long fiber, trailing lower-right with one bend  -->
    <path d="M 514 522 C 580 552, 660 600, 720 660 S 770 720, 800 740" stroke-width="3.2"/>
    <path d="M 800 740 C 816 754, 824 762, 830 770" stroke-width="1.5"/>
    <path d="M 800 740 C 808 760, 810 770, 808 782" stroke-width="1.5"/>

  </g>

  <!-- ── Soma ── slightly elongated, organic, drawn last so dendrite stems
       sit cleanly underneath it ─────────────────────────────────────── -->
  <ellipse cx="{SOMA_X}" cy="{SOMA_Y}" rx="17" ry="14" fill="{ACCENT}"/>
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
