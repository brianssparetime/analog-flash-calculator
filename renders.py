"""Beauty shots, and the camera settings that produce them.

    python renders.py                # every shot and the animation
    python renders.py hero power     # only shots whose name contains these
    python renders.py assembly       # just the animation

This file is the record of how each image was framed. Every camera below
is OpenSCAD's own gimbal form -- the seven numbers it prints in its status
bar and accepts on `--camera` -- so a shot can be reproduced, nudged, and
re-run without hunting for the angle again.

    --camera = cx, cy, cz, rx, ry, rz, dist

`cx, cy, cz` is the point looked at, `rx, ry, rz` the camera rotation in
degrees, and `dist` how far back it sits. Rotation (0, 0, 0) looks
straight down -Z; (90, 0, 90) looks level along -X, which is the view the
instrument is built for. The posed variants stand on end with their
reading line facing +X, so that camera sees every window and the slot
stacked up the near face with their labels level.

Rebuild the .scad files first if the model has changed:

    scadwright build main.py --variant=display
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from scadwright import bbox

from dims import Dims as D
from main import AnalogFlashCalculator

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
IMG = HERE / "rendered_img"

OPENSCAD = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"

# One scheme for every shot, the same Metallic that SCADwright's own
# documentation images use: a lavender backdrop with the part in gold and
# every cut face in magenta. Preview fills the faces of a subtracted
# volume in that contrasting colour, which reads exactly like the paint
# fill the finished engraving is meant to get.
INKED = HONEST = "Metallic"

# Preview (OpenCSG), not a full CGAL render. Every engraving is a separate
# difference and there are several hundred of them, so CGAL takes minutes
# per frame while preview takes seconds and looks the same at these
# sizes. Pass --cgal if a shot ever needs the real mesh.
CGAL = "--cgal" in sys.argv

# The assembled variants stand along +Z. These are the heights worth
# aiming a camera at.
MID = D.overall_len / 2                       # middle of the whole tool
POWER_MID = D.power_z0 + D.power_band / 2     # middle of the aperture slot
WINDOWS_MID = D.power_z0 / 2                  # the three setting windows

# The exploded stage reaches well past both ends of the tool, and by how
# much depends on the explode step and the hardware travel. Measure it
# rather than carry a number that goes stale every time either changes.
_EXPLODED = bbox(AnalogFlashCalculator().exploded())
EXPLODED_MID = (_EXPLODED.min[2] + _EXPLODED.max[2]) / 2
EXPLODED_SPAN = _EXPLODED.max[2] - _EXPLODED.min[2]


def fit(span_mm, size, margin=1.1):
    """Camera distance that frames `span_mm` of height in an image of `size`.

    OpenSCAD's default field of view is 22.5 degrees, so the visible
    height at distance d is 0.4 * d and the visible width scales with the
    aspect ratio. Solving for d keeps the framing right when an image
    size changes, instead of leaving a hand-tuned number to go stale.
    """
    return span_mm * margin / 0.4


def fit_wide(span_mm, size, margin=1.1):
    """Camera distance that frames `span_mm` of width instead."""
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


# Sizes first, so the camera distances can be solved from them. The tool
# stands on end, so most shots are portrait.
TALL = (1100, 1700)
LANDSCAPE = (1800, 1050)
DETAIL = (1000, 1300)

SHOTS = [
    Shot(
        "hero", "display",
        camera=(0, 0, MID, 84, 0, 80, fit(102, TALL)),
        size=TALL,
        caption="Three-quarter view of the whole instrument.",
    ),
    Shot(
        "reading-line", "display",
        camera=(0, 0, MID, 90, 0, 90, fit(100, TALL)),
        size=TALL,
        colorscheme=INKED,
        caption="Straight down the reading line: every window and the "
                "whole aperture slot at once.",
    ),
    Shot(
        "power-slot", "display",
        camera=(0, 0, POWER_MID, 90, 0, 90, fit(46, DETAIL)),
        size=DETAIL,
        colorscheme=INKED,
        caption="The answer: the readout under each aperture heading.",
    ),
    Shot(
        "windows", "display",
        camera=(0, 0, WINDOWS_MID, 90, 0, 90, fit(44, DETAIL)),
        size=DETAIL,
        colorscheme=INKED,
        caption="The three setting windows, GN through the third ring.",
    ),
    Shot(
        "exploded", "exploded",
        camera=(0, 0, EXPLODED_MID, 82, 0, 80, fit(EXPLODED_SPAN, TALL)),
        size=TALL,
        caption="Five pieces, in the order they thread on.",
    ),
    Shot(
        "section", "section",
        camera=(0, 0, MID, 90, 0, 180, fit(100, TALL)),
        size=TALL,
        colorscheme=INKED,
        caption="Cut away: nesting, clearances, and the spring cavity.",
    ),
    Shot(
        "print-plate", "print",
        camera=(124, 22, 38, 72, 0, 18, fit_wide(270, LANDSCAPE)),
        size=LANDSCAPE,
        caption="All five pieces as they print, standing on their axes.",
    ),
]


# The assembly animation, in three steps rather than one.
#
# `scadwright morph` will write the APNG itself, but it gives every frame
# the same duration and aims OpenSCAD's default camera, so the loop
# restarts the instant the tool comes together and it does so with the
# reading face turned away. Taking the animated SCAD instead lets the
# same camera the stills use frame it, and lets the last frame be held.
ANIM = dict(name="assembly", frames=48, hold=24, fps=30, size=(700, 1000),
            camera=(0, 0, EXPLODED_MID, 82, 0, 80))


def animate(spec=ANIM):
    """Render the morph on the reading face, holding before it loops."""
    out = IMG / f"{spec['name']}.apng"
    tmp = Path(tempfile.mkdtemp(prefix="morph-"))
    try:
        scad = tmp / "morph.scad"
        subprocess.run(
            [".venv/bin/scadwright", "morph", "main.py", "assemble",
             str(scad), f"--frames={spec['frames']}"],
            check=True, capture_output=True, text=True,
        )
        w, h = spec["size"]
        subprocess.run(
            [OPENSCAD, "-o", str(tmp / "f.png"),
             f"--animate={spec['frames']}", f"--imgsize={w},{h}",
             "--camera=" + ",".join(
                 f"{v:g}" for v in (*spec["camera"],
                                    fit(EXPLODED_SPAN, spec["size"]))),
             f"--colorscheme={INKED}", str(scad)],
            check=True, capture_output=True, text=True,
        )
        frames = sorted(tmp.glob("f*.png"))
        if not frames:
            raise SystemExit("no frames rendered from the morph")
        for i in range(len(frames), len(frames) + spec["hold"]):
            shutil.copyfile(frames[-1], tmp / f"f{i:05d}.png")
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error",
             "-framerate", str(spec["fps"]), "-i", str(tmp / "f%05d.png"),
             "-plays", "0", str(out)],
            check=True, capture_output=True, text=True,
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out.stat().st_size


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
    want_anim = not wanted or any(w in ANIM["name"] for w in wanted)
    if not shots and not want_anim:
        raise SystemExit(f"no shot matches {wanted}")

    for shot in shots:
        size = render(shot)
        print(f"{shot.name:<20} {size / 1024:6.0f} kB  {shot.caption}")

    if want_anim:
        size = animate()
        print(f"{ANIM['name']:<20} {size / 1024:6.0f} kB  "
              f"The five pieces closing up, holding on the finished tool.")
