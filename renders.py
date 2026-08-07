"""Beauty shots, and the camera settings that produce them.

    python renders.py                # every shot into rendered_img/
    python renders.py hero power     # only shots whose name contains these

This file is the record of how each image was framed. Every camera below
is OpenSCAD's own gimbal form -- the seven numbers it prints in its status
bar and accepts on `--camera` -- so a shot can be reproduced, nudged, and
re-run without hunting for the angle again.

    --camera = cx, cy, cz, rx, ry, rz, dist

`cx, cy, cz` is the point looked at, `rx, ry, rz` the camera rotation in
degrees, and `dist` how far back it sits. Rotation (0, 0, 0) looks
straight down -Z with +X to the right, which is why the assembled
variants lie along +X with their reading line facing +Z: at rz = 0 the
text reads left to right and the whole line is in frame.

Rebuild the .scad files first if the model has changed:

    scadwright build main.py --variant=display
"""

import subprocess
import sys
from pathlib import Path

from dims import Dims as D

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
IMG = HERE / "rendered_img"

OPENSCAD = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"

# Two schemes, chosen per shot by which of OpenSCAD's preview artifacts
# tells the truth at that angle.
#
# Preview fills the faces of a subtracted volume in a contrasting colour.
# Looking straight down at an engraving, that reads exactly like the paint
# fill the finished part is meant to get, and it makes the scales legible.
# At a three-quarter angle it instead floods the inside walls of a window,
# so an opening you should be able to see through looks solid. Monotone
# gives every face the same colour, which kills the artifact and costs
# only some engraving contrast.
INKED = "Metallic"      # straight-on: engraving reads as paint fill
HONEST = "Monotone"     # angled: windows read as openings

# Preview (OpenCSG), not a full CGAL render. Every engraving is a separate
# difference and there are several hundred of them, so CGAL takes minutes
# per frame while preview takes seconds and looks the same at these
# sizes. Pass --cgal if a shot ever needs the real mesh.
CGAL = "--cgal" in sys.argv

# The assembled variants lie along +X. These are the landmarks worth
# aiming a camera at, in that laid-down frame.
MID = D.overall_len / 2                       # middle of the whole tool
POWER_MID = D.power_z0 + D.power_band / 2     # middle of the aperture slot
WINDOWS_MID = D.dist_z0 / 2                   # the three setting windows


def fit(span_mm, size, margin=1.15):
    """Camera distance that frames `span_mm` of width in an image of `size`.

    OpenSCAD's default field of view is 22.5 degrees, so the visible
    height at distance d is 0.4 * d and the visible width scales with the
    aspect ratio. Solving for d keeps the framing right when an image
    size changes, instead of leaving a hand-tuned number to go stale.
    """
    w, h = size
    return span_mm * margin / (0.4 * w / h)


class Shot:
    """One framed image: which variant, seen from where."""

    def __init__(self, name, variant, camera, size=(1600, 1000),
                 projection="p", colorscheme=HONEST, caption=""):
        self.name = name
        self.variant = variant
        self.camera = camera
        self.size = size
        self.projection = projection
        self.colorscheme = colorscheme
        self.caption = caption

    @property
    def source(self):
        return OUT / f"analog-flash-calculator-{self.variant}.scad"

    @property
    def target(self):
        return IMG / f"{self.name}.png"


# Sizes first, so the camera distances can be solved from them.
WIDE = (2000, 700)
LANDSCAPE = (1800, 1050)
DETAIL = (1800, 900)

SHOTS = [
    Shot(
        "hero", "display",
        camera=(MID, 0, 0, 63, 0, 24, fit(210, LANDSCAPE)),
        size=LANDSCAPE,
        caption="Three-quarter view of the whole instrument.",
    ),
    Shot(
        "reading-line", "display",
        camera=(MID, 0, 0, 0, 0, 0, fit(195, WIDE)),
        size=WIDE,
        colorscheme=INKED,
        caption="Straight down the reading line: every window and the "
                "whole aperture slot at once.",
    ),
    Shot(
        "power-slot", "display",
        camera=(POWER_MID, 0, 0, 20, 0, 0, fit(100, DETAIL)),
        size=DETAIL,
        colorscheme=INKED,
        caption="The answer: the readout under each aperture heading.",
    ),
    Shot(
        "settings-line", "settings",
        camera=(MID, 0, 0, 0, 0, 0, fit(195, WIDE)),
        size=WIDE,
        colorscheme=INKED,
        caption="The other side: the three setting windows in a row.",
    ),
    Shot(
        "windows", "settings",
        camera=(WINDOWS_MID, 0, 0, 24, 0, 0, fit(85, DETAIL)),
        size=DETAIL,
        colorscheme=INKED,
        caption="The three setting windows, GN through the third ring.",
    ),
    Shot(
        "three-quarter-rear", "settings",
        camera=(MID, 0, 0, 66, 0, 24, fit(210, LANDSCAPE)),
        size=LANDSCAPE,
        caption="Three-quarter view from the settings side.",
    ),
    Shot(
        "exploded", "exploded",
        camera=(160, 0, 0, 66, 0, 24, fit(350, LANDSCAPE)),
        size=LANDSCAPE,
        caption="Five pieces, in the order they thread on.",
    ),
    Shot(
        "section", "section",
        camera=(MID, 0, 0, 90, 0, 0, fit(195, WIDE)),
        size=WIDE,
        colorscheme=INKED,
        caption="Cut away: nesting, clearances, and the spring cavity.",
    ),
    Shot(
        "print-plate", "print",
        camera=(95, 22, 76, 66, 0, 18, fit(280, LANDSCAPE)),
        size=LANDSCAPE,
        caption="All five pieces as they print, standing on their axes.",
    ),
]


def render(shot):
    if not shot.source.exists():
        raise SystemExit(
            f"{shot.source.name} is missing. Build it first:\n"
            f"    scadwright build main.py --variant={shot.variant}"
        )
    IMG.mkdir(exist_ok=True)
    cmd = [
        OPENSCAD,
        "-o", str(shot.target),
        *(["--render"] if CGAL else []),
        f"--imgsize={shot.size[0]},{shot.size[1]}",
        "--camera=" + ",".join(f"{v:g}" for v in shot.camera),
        f"--projection={shot.projection}",
        f"--colorscheme={shot.colorscheme}",
        str(shot.source),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not shot.target.exists():
        raise SystemExit(
            f"{shot.name} failed:\n{result.stderr.strip()[-2000:]}"
        )
    return shot.target.stat().st_size


if __name__ == "__main__":
    wanted = [a for a in sys.argv[1:] if not a.startswith("-")]
    shots = [s for s in SHOTS
             if not wanted or any(w in s.name for w in wanted)]
    if not shots:
        raise SystemExit(f"no shot matches {wanted}")

    for shot in shots:
        size = render(shot)
        print(f"{shot.name:<20} {size / 1024:6.0f} kB  {shot.caption}")
