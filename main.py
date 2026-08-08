"""Analog flash calculator: an exposure dial folded into a cylinder.

    scadwright build main.py                        # print plate (default)
    scadwright build main.py --variant=display      # assembled, one setting
    scadwright build main.py --readout power        # power per f/stop
    scadwright build main.py --units feet           # slot labelled in feet
    scadwright build main.py --variant=exploded     # pulled apart along the axis
    scadwright build main.py --variant=section      # cut away, to check fits
    scadwright morph  main.py assemble out.apng     # the stack coming together

    python renders.py                               # beauty shots into rendered_img/

Turn three rings, read every aperture at once:

    1. GN ring    -> the flash's guide number
    2. ISO ring   -> the film speed
    3. POWER ring -> the flash's power setting
    then read the distance reached under each aperture in the long slot.

With `--readout=power` the third ring sets the distance instead, and the
slot reads the power each aperture needs.

Orientation of the posed variants
---------------------------------
Assembled views stand the instrument on end with its reading line facing
+X, which is how it is held: labels run around the barrel, so they read
level only with the axis upright. `_posed` turns the whole assembly so
that line lands on the same meridian whatever setting is on show, which
keeps the camera positions in `renders.py` valid across settings.

Print orientation
-----------------
Every segment prints standing on its axis. Bores stay round without
support, the windows become vertical slots that need only a short bridge
at the top, and engraved text on a vertical wall comes out crisp.

Which end goes down is decided by the detents. A spherical dimple opening
downward loses about 0.13 mm of radius per 0.2 mm layer -- a 57 degree
overhang, which prints clean. A dome pointing downward does not. So every
segment is oriented bumps-up, which all five are as modelled.
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

# The setting the posed variants are shown at. It is the setting the
# scales are aligned on, so the three setting windows and the readout slot
# all sit on one meridian and a single view shows the tool being read.
# Retune it in `scales.ALIGN`, and the renders follow.
POSE = dict(scales.ALIGN)

# How far apart the exploded view pulls the segments, along the axis. The
# morph animates this closing up, which is the order they assemble in.
EXPLODE_STEP = 30.0


def stand_up(node):
    """Stand the assembly guide-number-end up, reading line facing +X.

    The bands are built from the GN end at z = 0, but that end is the one
    held uppermost: a thumb and finger reach the top of the tool, not the
    bottom, so the settings have to run downward from there. Turning the
    whole assembly over puts band A on top and leaves the reading line
    facing +X, where `_posed` put it.
    """
    return node.rotate([180, 0, 0]).up(D.overall_len)


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
    # One instance per spring, for the same reason the two washers are
    # separate instances of an identical tube: `morph` pairs leaves
    # between stages by instance, so drawing one spring three times leaves
    # it unable to tell the three apart. It animates whichever it pairs
    # first and abandons the rest in place.
    springs = tuple(
        Spring(r=1.5, wire_r=0.25, pitch=D.pocket_depth / 8, turns=8)
        for _ in range(int(D.spring_count))
    )

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

        Three springs seat in pockets around the cap's hub at the nut end,
        which puts them in series with the whole stack. The washer above
        them is a fender washer: it spans the whole pocket circle and
        bears on all three where a smaller one would miss them.

        Drawn tightened: the nut washer sits on the cap's end face, which
        is the hard stop that bounds travel, and the springs are shut into
        their pockets. `spread` draws the two ends apart for the exploded
        stage. What is yielded, and in what order, never varies with it.
        """
        # The cap is the last segment off, so everything at the nut end has
        # to clear the height the cap itself reaches, not one step short of
        # it. Short, and the springs draw apart below the pockets they are
        # supposed to fall into, and the washer inside the cap.
        lead = -spread * 30                       # head end, below
        cap_lift = spread * 4 * EXPLODE_STEP      # the cap's own travel
        tail = cap_lift + spread * 25             # nut end, clear above it
        spring_z = D.pocket_z0 + cap_lift + spread * 12
        washer_t, head_t, nut_t = 1.6, 5.0, 5.5
        head_z = -washer_t + lead                 # its face bears on z = 0
        # Cut off flush with the nut, as it would be in the hand: a bolt
        # bought long enough to assemble with leaves a stub otherwise. The
        # length is fixed rather than solved per stage, because `morph`
        # pairs inline primitives by their parameters and will not accept
        # a cylinder that changes height between stages. In the exploded
        # stage the nut therefore floats off the end, which is what an
        # exploded view is for.
        shank = D.overall_len + 2 * washer_t + nut_t + head_t

        yield cylinder(h=shank, d=6.35).up(head_z - head_t).color("silver")
        yield cylinder(h=head_t, d=13).up(head_z - head_t).color("silver")
        yield self.washer.up(head_z).color("silver")
        n = len(self.springs)
        for i, spring in enumerate(self.springs):
            yield (spring
                   .translate([D.pocket_r, 0, spring_z])
                   .rotate([0, 0, i * 360.0 / n])
                   .color("gold"))
        yield self.fender.up(D.overall_len + tail).color("silver")
        yield cylinder(h=nut_t, d=11.5, fn=6).up(
            D.overall_len + washer_t + tail
        ).color("silver")

    def _scene(self, spread):
        """The whole assembly, drawn apart by `spread` (0 together, 1 apart).

        Both morph stages come from here so their CSG skeletons cannot
        drift: `morph` matches stage to stage by position in the tree, and
        a variant that quietly gains or loses a part stops it dead.
        """
        inner, gn, iso, dist, cap = self._posed()
        step = spread * EXPLODE_STEP
        return stand_up(union(
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

    @variant(fn=96, out="out/analog-flash-calculator-section.scad")
    def section(self):
        # Half the assembly away, on a plane through the axis, so the
        # nesting, the clearances and the spring pockets all show. Cut
        # across the axis instead and there is nothing to see.
        return self._scene(0.0).halve([0, -1, 0])

    # The stack coming together, for a posting-friendly animation.
    assemble = morph(stages=["exploded", "display"])


if __name__ == "__main__":
    run()
