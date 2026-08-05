"""Analog flash calculator: an exposure dial folded into a cylinder.

    scadwright build main.py                        # print plate (default)
    scadwright build main.py --variant=display      # assembled, one setting
    scadwright build main.py --readout=aperture     # f/stop per distance
    scadwright build main.py --variant=exploded     # pulled apart along the axis
    scadwright build main.py --variant=section      # cut away, to check fits
    scadwright morph  main.py assemble out.apng     # the stack coming together

    python renders.py                               # beauty shots into rendered_img/

Turn three rings, read every aperture at once:

    1. GN ring    -> the flash's guide number
    2. ISO ring   -> the film speed
    3. DIST ring  -> the flash-to-subject distance
    then read the power needed under each aperture in the long slot.

Orientation of the posed variants
---------------------------------
Assembled views lie the instrument along +X with its reading line facing
+Z, so a camera looking down sees the whole line at once and the engraved
text reads left to right. `_posed` also rotates the whole assembly so that
line always lands on the same meridian whatever setting is on show, which
keeps the camera positions in `renders.py` valid across settings.

Print orientation
-----------------
Every segment prints standing on its axis. Bores stay round without
support, the windows become vertical slots that need only a short bridge
at the top, and engraved text on a vertical wall comes out crisp.

Which end goes down is decided by the detents. A spherical dimple opening
downward loses about 0.13 mm of radius per 0.2 mm layer -- a 57 degree
overhang, which prints clean. A dome pointing downward does not. So every
segment is oriented bumps-up, which all four are as modelled.
"""

from scadwright import morph
from scadwright.boolops import union
from scadwright.composition_helpers import arrange_on_bed
from scadwright.design import Design, run, variant
from scadwright.primitives import cylinder
from scadwright.shapes import Spring, Tube

import scales
from dims import LAYOUT, Dims as D
from parts import DistRing, EndCap, GnRing, InnerTube, IsoRing

# The setting the posed variants are shown at: a Mecablitz-sized flash on
# slow film at one metre.
#
# Chosen because it is the setting that photographs best, and it is worth
# saying why. Two things fall out of it at once. Every aperture column is
# populated, so the slot reads 1/128 through 1/1 across the full f/2 to
# f/22 span. And all four windows land on the same meridian, so the whole
# instrument can be read down one line -- which only happens when the ISO
# and distance rings are both at their first mark.
POSE = dict(
    gn=scales.GUIDE_NUMBERS.index("45"),
    iso=scales.ISOS.index("25"),
    third=0,        # first mark of whichever setting the layout puts third
)

# How far apart the exploded view pulls the segments, along the axis. The
# morph animates this closing up, which is the order they assemble in.
EXPLODE_STEP = 55.0


def lay_down(node):
    """Lay a Z-axis assembly along +X with its reading line facing +Z."""
    return node.rotate([0, 90, 0]).rotate([180, 0, 0])


class AnalogFlashCalculator(Design):
    name = "analog-flash-calculator"

    inner = InnerTube()
    gn_ring = GnRing()
    iso_ring = IsoRing()
    dist_ring = DistRing()
    end_cap = EndCap()

    # Stand-in hardware. These have to be class attributes rather than
    # built inside a helper: `morph` matches the two stages leaf by leaf
    # and requires each leaf to be the same Component instance, so a
    # helper that constructs a fresh Tube per call stops it dead.
    # Both washers are wider than the stack, so each caps its end instead
    # of dropping into it. That is what makes the spring load the whole
    # chain and what bounds the total axial travel.
    washer = Tube(h=1.6, od=D.washer_od, id=7)
    fender = Tube(h=1.6, od=D.washer_od, id=7)
    spring = Spring(r=8.0, wire_r=0.8, pitch=2.6, turns=5)

    def _posed(self):
        """The four segments rotated to POSE, innermost first.

        The whole assembly is then counter-rotated so the dist ring's
        reading line sits on +X regardless of the setting. Turning every
        segment by the same amount changes no reading, and it means a
        camera aimed at +X frames the answer whatever POSE says.
        """
        inner_a, gn_a, iso_a, dist_a = LAYOUT.rotations(**POSE)
        # The reading line is on the end cap now, so trim against that.
        # The cap is keyed to the inner tube and turns with it.
        trim = -inner_a
        return (
            self.inner.rotate([0, 0, inner_a + trim]),
            self.gn_ring.rotate([0, 0, gn_a + trim]),
            self.iso_ring.rotate([0, 0, iso_a + trim]),
            self.dist_ring.rotate([0, 0, dist_a + trim]),
            self.end_cap.rotate([0, 0, inner_a + trim]),
        )

    def _hardware(self, spread):
        """Stand-in 1/4 inch bolt, washers and spring.

        The spring loads into the cavity in the inner segment's end face,
        under the bolt head, which puts it in series with the whole
        stack. The end washer is a fender washer: it bears on the dist
        ring's tail face, and an ordinary one would drop into the bore.

        `spread` draws the two ends apart for the exploded stage. What is
        yielded, and in what order, never varies with it.
        """
        lead = -spread * 55                       # head end, off to the left
        tail = spread * (3 * EXPLODE_STEP + 45)   # nut end, off to the right
        head_z = -12.0 + lead

        yield cylinder(h=D.overall_len + 20, d=6.35).up(head_z).color("silver")
        yield cylinder(h=5, d=13).up(head_z - 5).color("silver")
        yield self.washer.up(head_z).color("silver")
        # Seated in the cap's recess and standing `spring_proud` out of
        # it, so the washer meets the spring before the cap's rim.
        yield self.spring.up(D.inner_end_z + tail).color("gold")
        yield self.fender.up(
            D.overall_len + D.spring_proud + tail
        ).color("silver")
        yield cylinder(h=5.5, d=11.5, fn=6).up(
            D.overall_len + D.spring_proud + 1.6 + tail
        ).color("silver")

    def _scene(self, spread):
        """The whole assembly, drawn apart by `spread` (0 together, 1 apart).

        Both morph stages come from here so their CSG skeletons cannot
        drift: `morph` matches stage to stage by position in the tree, and
        a variant that quietly gains or loses a part stops it dead.
        """
        inner, gn, iso, dist, cap = self._posed()
        step = spread * EXPLODE_STEP
        return lay_down(union(
            inner,
            gn.up(step),
            iso.up(2 * step),
            dist.up(3 * step),
            cap.up(4 * step),
            *self._hardware(spread),
        ))

    @variant(fn=96, out="out/analog-flash-calculator-print.scad", default=True)
    def print(self):
        # Bumps up on all four: every segment prints as modelled.
        return arrange_on_bed(
            self.inner, self.gn_ring, self.iso_ring, self.dist_ring,
            self.end_cap, plate=(250, 250), gap=10,
        )

    @variant(fn=96, out="out/analog-flash-calculator-display.scad")
    def display(self):
        return self._scene(0.0)

    @variant(fn=96, out="out/analog-flash-calculator-exploded.scad")
    def exploded(self):
        # Along the axis, in assembly order, so the morph plays as the
        # rings actually go on: each slides down over the one before it.
        return self._scene(1.0)

    @variant(fn=96, out="out/analog-flash-calculator-settings.scad")
    def settings(self):
        # The same assembly rolled half a turn, so the three setting
        # windows face the camera instead of the readout. With a full
        # slot the settings always land opposite the readout, so no one
        # view can hold both.
        return self._scene(0.0).rotate([180, 0, 0])

    @variant(fn=96, out="out/analog-flash-calculator-section.scad")
    def section(self):
        # Half the assembly away, to eyeball wall thicknesses, the
        # concentric clearances, and where the spring actually seats.
        return self._scene(0.0).halve([0, 0, -1])

    # The stack coming together, for a posting-friendly animation.
    assemble = morph(stages=["exploded", "display"])


if __name__ == "__main__":
    run()
