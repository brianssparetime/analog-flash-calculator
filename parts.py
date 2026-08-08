"""The printed segments.

Reading chain, from the middle outwards. Each segment carries a window
onto the segment beneath it and a scale for the segment above it, so one
relative rotation per pair sets one variable:

    inner     <- gn ring     GN window over the GN scale
    gn ring   <- iso ring    ISO window over the ISO scale
    iso ring  <- dist ring   DIST window over the distance scale
    dist ring <- end cap     POWER window over the power table

The last pair is the readout rather than a setting: its rotation is
whatever the three settings add up to, which is exactly the answer. The
end cap is keyed to the inner tube, so those two are one body as far as
the arithmetic is concerned. They are two printed pieces only because
nothing could otherwise be threaded past a tube built up at both ends.

Each segment is a full-diameter sleeve over the band it reads and a
reduced-diameter spigot over the band it is read through, which keeps the
outside one constant cylinder. The two are `slip` apart radially and
share no length, so a floor joins them; that same annulus is the face the
segment below bears on, well inboard of the rim, and is where the detents
live. `BAND` has the radii, and each segment's `pieces()` the lengths.

Assembly runs right to left: gn ring, iso ring, dist ring, end cap, each
sliding over the inner tube's plain body and seating on the one before.
"""

from math import asin, degrees, radians

from scadwright import BBox, Component, bbox
from scadwright.boolops import difference, union
from scadwright.primitives import cube, cylinder, sphere
from scadwright.shapes import PieSlice, Tube

from dims import DETENT_BUMPS, DETENT_DIVOTS, LAYOUT, Dims
from scales import (
    DETENTS, DISTANCES_FT, DISTANCES_M, GUIDE_NUMBERS, ISOS, window_legend,
)

D = Dims
EPS = 0.01

# Named, never a path: OpenSCAD resolves fonts by fontconfig name, and
# scadwright reads its glyph metrics from whatever that same name matches.
# Asking for a face this machine does not have takes the metrics from the
# substitute while OpenSCAD renders something else, and the spacing drifts.
SCALE_FONT = "Arial:style=Bold"

# Reference cylinder the glyph placer measures against. Any label placed
# at its mid-wall has room to spread without tripping the overflow check,
# so band lengths never have to be threaded through the call.
_REF_H = 60.0

# Band boundaries. Every segment is described by the two bands it spans.
B0 = D.gn_z0
B1 = D.iso_z0
B2 = D.dist_z0
B3 = D.power_z0
B4 = D.power_z1

def window_rows(r0, r1):
    """The z of the metre and feet rows inside a band's window.

    Both the scale and the unit markers beside it read from here, so the
    markers cannot drift off the rows they label.
    """
    lo, hi = r0 + D.window_margin, r1 - D.window_margin
    mid, off = (lo + hi) / 2, (hi - lo) / 4
    return mid + off, mid - off        # metres above feet

# Held guide-number-end up, the barrel reads the other way round, so a
# label that comes first sits at a positive angle.
ABOVE = D.window_arc / 2 + 12


def label_arc(od, label, size):
    """How much of the circumference a label takes, in degrees."""
    bb = bbox(engrave_text(od=od, z=0, label=label, angle=0, size=size))
    return 2 * degrees(asin(max(abs(bb.min[1]), abs(bb.max[1])) / (od / 2)))


def offscale_marks(*, od, z, size, marks, angle_of):
    """Arrows in the detents a scale does not reach.

    Every scale is shorter than the twelve detents around the tool, so
    some settings show a blank window. Rather than leave the reader
    guessing whether the tool is broken, each empty detent carries an
    arrow toward the nearer end of the scale, and the odd one equidistant
    from both ends carries a pair.
    """
    last = len(marks) - 1
    for u in range(len(marks), DETENTS):
        to_last, to_first = u - last, DETENTS - u
        here = angle_of(u)
        if to_last == to_first:
            label = "<>"
        else:
            near = angle_of(last if to_last < to_first else 0)
            label = ">" if (near - here + 180) % 360 - 180 > 0 else "<"
        yield engrave_text(od=od, z=z, label=label, angle=here, size=size)


def beside_window(od, label, size, after=False, gap=2.5):
    """Angle that sets `label` just clear of a window, before or after it.

    Measured off the label's own geometry rather than guessed from its
    character count, so a longer unit or a bigger font moves itself out
    of the way instead of being swallowed by the window it names.
    """
    off = D.window_arc / 2 + label_arc(od, label, size) / 2 + gap
    return -off if after else off


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def engrave_text(*, od, z, label, angle, size, depth=None, font=SCALE_FONT):
    """An inset-text cutter centred at absolute height `z` on a wall of
    diameter `od`.

    Glyphs run around the circumference, so a label reads across the
    barrel with the tool stood on end. That is the posture the whole
    instrument is laid out for: every window and the slot stack up the
    side, and each label costs the band only its glyph height rather than
    its whole length. What it costs instead is arc, which is why the body
    is as wide as it is.

    `flip` turns each glyph in the tangent plane, which is what lets the
    tool be held guide-number-end up: band A sits at the top in the hand,
    so the text has to read the other way round from the order the bands
    are built in.
    """
    ref = Tube(h=_REF_H, od=od, thk=3)
    return ref.text_geometry(
        label=label,
        relief=-(D.engrave if depth is None else depth),
        on="outer_wall",
        font_size=size,
        font=font,
        angle=angle,
        at_z=0,                       # mid-wall
        text_dir="circumferential",
        rotate_glyphs=False,
        flip=True,
    ).up(z - _REF_H / 2)


def window(*, z0, length, arc=None):
    """A cutter that opens one angular slot through a sleeve wall.

    A wedge from the axis outward: the bore is already empty, so all it
    removes is the wall inside that angle.
    """
    half = (D.window_arc if arc is None else arc) / 2
    return PieSlice(
        r=D.outer_od / 2 + EPS, angles=(-half, half), h=length,
    ).up(z0)


def tick(*, z, angle, length=3.5, width=0.45, depth=0.3):
    """A fine circumferential index line cut into the outer surface.

    Lighter than an engraved label on purpose: it divides the readings
    without competing with them for the eye.
    """
    return (
        cube([2 * depth, length, width], center="xyz")
        .translate([D.outer_od / 2, 0, 0])
        .rotate([0, 0, angle])
        .up(z)
    )


def keyway(z0, z1):
    """The channel the inner tube's key passes through.

    The key stands proud of the tube by more than the rings' bores clear,
    so without this no ring could be threaded on at all. It is cut on the
    window meridian, which means the channels in all three rings line up
    only when the tool is set to the setting its scales are aligned on.
    Set it there and the stack drops together; set it anywhere else and
    the rings stop against the key.
    """
    return (
        cube([D.inner_od / 2 + D.key_h + D.key_slip / 2,
              D.key_w + D.key_slip,
              z1 - z0 + 2 * EPS], center="y")
        .up(z0 - EPS)
    )


def groove(*, z, od, width=0.45, depth=0.3):
    """The same index line, taken all the way around a scale surface.

    A scale turns under its window, so a mark at one angle would only
    line up with the cap's ticks at one setting. Cut right round, the
    divisions between readings meet the divisions between headings
    whatever the ring is set to.
    """
    return Tube(h=width, od=od + 2 * EPS, id=od - 2 * depth).up(z - width / 2)


def detents(*, z_face, count, sphere_r, reach):
    """Spheres for a detent ring on a spigot end or a sleeve floor.

    Used both ways: unioned onto a spigot's end they are bumps standing
    `reach` proud of it, subtracted from a sleeve floor they are divots
    `reach` deep. The placement is identical either way, because in both
    cases the sphere's upper pole sits `reach` above the face.
    """
    cz = z_face + reach - sphere_r
    one = sphere(r=sphere_r).translate([D.detent_r, 0, cz])
    return one.rotate_copy(angle=360.0 / count, n=count, axis=[0, 0, 1])


def bumps(z_face):
    return detents(z_face=z_face, count=DETENT_BUMPS,
                   sphere_r=D.bump_sphere_r, reach=D.bump_proud)


def divots(z_face):
    return detents(z_face=z_face, count=DETENT_DIVOTS,
                   sphere_r=D.divot_sphere_r, reach=D.divot_deep)


# How far in from the axis each kind of piece reaches, as (r_in, r_out).
# Only two diameters exist on the outside; what varies is the bore.
#
# `sleeve` rides the spigot beneath it, so it bores `slip` wider than one
# is round. A segment's own `spigot` is that same diameter less `slip`,
# and begins exactly where its sleeve ends -- radially disjoint from it,
# sharing no length, so the two do not touch and unioning them gives two
# loose shells rather than a part. `floor` is what joins them: it reaches
# from the outside all the way in to the spigot's bore, so it meets each
# over real area. The spigot being read stops `floor_t` short to leave it
# room, which is what puts the detent face on the floor's underside.
BAND = {
    "sleeve": (D.sleeve_bore / 2, D.outer_od / 2),
    "spigot": (D.spigot_bore / 2, D.spigot_od / 2),
    "floor": (D.spigot_bore / 2, D.outer_od / 2),
    "disc": (0.0, D.spigot_od / 2),     # the inner tube's scale surface
    "rod": (0.0, D.inner_od / 2),       # the tube that spans the length
    "tail": (0.0, D.outer_od / 2),      # the cap's solid end, bored later
}


def stack(pieces):
    """Build the annuli a segment describes itself as.

    Every segment is a handful of coaxial pieces, and its `pieces()` is
    where it says which and over what length. Building from that list
    rather than composing the shapes inline means the description
    `check_segments_hold_together` tests is the one the geometry actually
    comes from, so the two cannot drift apart.
    """
    def one(name, z0, z1):
        r_in, r_out = BAND[name]
        if r_in <= 0:
            return cylinder(h=z1 - z0, d=2 * r_out).up(z0)
        return Tube(h=z1 - z0, od=2 * r_out, id=2 * r_in).up(z0)

    return union(*(one(*p) for p in pieces))


def _extents(z0, z1, od=None):
    """Declare a segment's true extents.

    Every part here ends in a `difference()`, which the framework cannot
    tighten without evaluating the CSG. Each one is a cylinder of known
    diameter over a known z range, so the answer is worth stating
    outright: without it `arrange_on_bed` has no idea how big they are.
    """
    r = (D.outer_od if od is None else od) / 2
    return BBox(min=(-r, -r, z0), max=(r, r, z1))


def engrave(body, cutters):
    """Cut a segment's windows, detents and lettering out of its body.

    Deliberately a plain difference. Wrapping either side in
    `force_render` is the documented remedy for a difference this wide,
    and it was measured: a headless CGAL render failed to finish in four
    minutes either way, and the wrapping made preview twentyfold slower.
    """
    return difference(body, union(*cutters))


# ---------------------------------------------------------------------------
# Inner tube: the spine both ends are read against
# ---------------------------------------------------------------------------

class InnerTube(Component):
    """A solid disc carrying the GN scale, then a plain rod running the
    length of the tool.

    Its left end face is the head of the stack: the bolt's washer bears
    there, and the ring stack piles up against the far side of the same
    disc. The rod is deliberately plain and thinner than every spigot
    bore, so each ring threads straight over it. The far end carries a key
    rib that the end cap slides onto.

    The disc is solid rather than a spigot, alone among the segments,
    because nothing rides inside it: bored to the fit the rings use, it
    would stand `slip` clear of its own rod.
    """

    def tight_bbox(self):
        return _extents(B0, D.inner_end_z, D.spigot_od)   # body outruns the bumps

    def face(self):
        """Its detent face: the gn ring's floor lands here."""
        return B1 - D.floor_t

    def pieces(self):
        # `disc`, not `spigot`: a spigot bores to `spigot_bore`, which is
        # the fit that rides over this tube. Bored to it here, the disc
        # would clear its own rod by `slip` and the tube would print in
        # two. Only the bolt hole belongs down the middle, and that is cut.
        return (("disc", B0, self.face()),
                ("rod", self.face() - EPS, D.inner_end_z))

    def build(self):
        body = union(
            stack(self.pieces()),
            self._key(),
            bumps(self.face()),
        )
        cutters = [cylinder(h=D.inner_end_z + 2 * EPS, d=D.bolt_d).down(EPS)]
        cutters += self._gn_scale()
        return engrave(body, cutters)

    def _key(self):
        """A single rib, so the end cap can only seat one way round."""
        return (
            cube([D.inner_od / 2 + D.key_h, D.key_w, D.key_len], center="y")
            .up(D.inner_end_z - D.key_len)
        )

    def _gn_scale(self):
        for g, label in enumerate(GUIDE_NUMBERS):
            yield engrave_text(
                od=D.spigot_od, z=(B0 + B1) / 2, label=label,
                angle=LAYOUT.setting_angle("gn", g), size=D.scale_font,
            )
        yield from offscale_marks(
            od=D.spigot_od, z=(B0 + B1) / 2, size=D.scale_font,
            marks=GUIDE_NUMBERS,
            angle_of=lambda u: LAYOUT.setting_angle("gn", u),
        )


# ---------------------------------------------------------------------------
# The three setting rings, each a sleeve plus a spigot
# ---------------------------------------------------------------------------

class _SettingRing(Component):
    """Sleeve over the band it reads, spigot over the band it is read
    through.

    Subclasses fill in the two bands, the window legend, and the scale
    carried. The detents are the same on all three: divots all the way
    round the sleeve floor, bumps on the far end of the spigot.
    """

    READS = ()          # (z0, z1) of the band this ring's window looks at
    CARRIES = ()        # (z0, z1) of the band this ring's scale sits in
    LEGEND = ("", "")   # (before, after) the window, on its own line

    # How far short of its band this ring's spigot stops, to leave room for
    # the floor of the segment that reads it. The last ring is read by the
    # end cap, whose floor grows the other way, into the tail.
    TOP_INSET = D.floor_t

    def _top(self):
        return self.CARRIES[1] - self.TOP_INSET

    def tight_bbox(self):
        # The bumps stand proud of the spigot's end face.
        return _extents(self.READS[0] + D.seam_gap, self._top() + D.bump_proud)

    def pieces(self):
        r0, r1 = self.READS
        return (("sleeve", r0 + D.seam_gap, r1),
                ("floor", r1 - D.floor_t, r1),   # without it, two shells
                ("spigot", r1, self._top()))

    def build(self):
        r0, r1 = self.READS
        top = self._top()
        body = union(stack(self.pieces()), bumps(top))
        cutters = [
            window(z0=r0 + D.window_margin,
                   length=(r1 - r0) - 2 * D.window_margin),
            divots(r1 - D.floor_t),     # cut into the floor's underside
            keyway(r0 + D.seam_gap, top),
        ]
        # Name before the window and unit after it, on the window's own
        # line, so the three read across together: GN 32 m.
        before, after = self.LEGEND
        mid = (r0 + r1) / 2
        for label, is_after in ((before, False), (after, True)):
            if label:
                cutters.append(engrave_text(
                    od=D.outer_od, z=mid, label=label, size=D.legend_font,
                    angle=beside_window(D.outer_od, label, D.legend_font,
                                        after=is_after),
                ))
        cutters += list(self.window_legends())
        cutters += list(self.scale())
        return engrave(body, cutters)

    def scale(self):
        raise NotImplementedError

    def window_legends(self):
        """Extra marks above this ring's window. None by default."""
        return ()


class GnRing(_SettingRing):
    """Turn against the inner tube to dial in the flash's guide number."""

    READS = (B0, B1)
    CARRIES = (B1, B2)
    LEGEND = window_legend("gn")        # reads: GN 32 m

    def scale(self):
        for i, label in enumerate(ISOS):
            yield engrave_text(
                od=D.spigot_od, z=(B1 + B2) / 2, label=label,
                angle=LAYOUT.setting_angle("iso", i), size=D.scale_font,
            )
        yield from offscale_marks(
            od=D.spigot_od, z=(B1 + B2) / 2, size=D.scale_font,
            marks=ISOS, angle_of=lambda u: LAYOUT.setting_angle("iso", u),
        )


class IsoRing(_SettingRing):
    """Turn against the GN ring to make the third setting.

    Which setting that is depends on the layout: distance in the power
    layout, flash power in the aperture layout. When it is distance the
    scale is printed twice, metres and feet, marking the same detents --
    feet cannot land on round numbers when metres do, so the foot row is
    honestly rounded rather than prettied up.
    """

    READS = (B1, B2)
    CARRIES = (B2, B3)
    LEGEND = window_legend("iso")       # its window shows the film speed

    def scale(self):
        span = B3 - B2
        labels = LAYOUT.third_marks
        if LAYOUT.third != "distance":
            for t, label in enumerate(labels):
                yield engrave_text(
                    od=D.spigot_od, z=B2 + span / 2, label=label,
                    angle=LAYOUT.setting_angle("third", t), size=D.dist_font,
                )
            yield from offscale_marks(
                od=D.spigot_od, z=B2 + span / 2, size=D.dist_font,
                marks=labels,
                angle_of=lambda u: LAYOUT.setting_angle("third", u),
            )
            return
        metre_z, foot_z = window_rows(B2, B3)
        for t, (m_label, ft_label) in enumerate(zip(DISTANCES_M, DISTANCES_FT)):
            angle = LAYOUT.setting_angle("third", t)
            yield engrave_text(od=D.spigot_od, z=metre_z,
                               label=m_label, angle=angle, size=D.dist_font)
            yield engrave_text(od=D.spigot_od, z=foot_z,
                               label=ft_label, angle=angle, size=D.dist_font)
        for row_z in (metre_z, foot_z):
            yield from offscale_marks(
                od=D.spigot_od, z=row_z, size=D.dist_font, marks=DISTANCES_M,
                angle_of=lambda u: LAYOUT.setting_angle("third", u),
            )


class DistRing(_SettingRing):
    """Turn against the ISO ring to dial in the flash-to-subject distance.

    Its spigot carries the answer: one column of power settings per
    aperture, read through the end cap's long slot.
    """

    READS = (B2, B3)
    CARRIES = (B3, B4)
    # Read by the end cap, whose floor is the solid tail above band D
    # rather than an annulus taken out of it. So this spigot runs the band
    # out in full, and the detent face stays on the boundary.
    TOP_INSET = 0

    @property
    def LEGEND(self):
        # Its window shows the third setting, which the layout names. When
        # that is distance the two rows carry their own unit marks, so the
        # legend stays bare.
        if LAYOUT.third == "distance":
            return "DIST", ""       # the two rows carry their own units
        return window_legend(LAYOUT.third, LAYOUT.units)

    def window_legends(self):
        """Units above the window, in the order the rows appear.

        Only the distance scale has two rows. They are labelled in the
        order they run along the axis, so the marker over each row is the
        one that names it whichever way round the rows are placed.
        """
        if LAYOUT.third != "distance":
            return
        for z, unit in zip(window_rows(B2, B3), ("m", "ft")):
            yield engrave_text(
                od=D.outer_od, z=z, label=unit, size=D.legend_font,
                angle=beside_window(D.outer_od, unit, D.legend_font, after=True),
            )

    def scale(self):
        for c in range(len(LAYOUT.column_labels)):
            col_mid = B3 + D.power_margin + (c + 0.5) * D.power_col
            for v, label in enumerate(LAYOUT.value_marks):
                yield engrave_text(
                    od=D.spigot_od, z=col_mid, label=label,
                    angle=LAYOUT.table_angle(v, c), size=D.power_font,
                )
            yield from offscale_marks(
                od=D.spigot_od, z=col_mid, size=D.power_font,
                marks=LAYOUT.value_marks,
                angle_of=lambda u, c=c: LAYOUT.table_angle(u, c),
            )
        for a in range(len(LAYOUT.column_labels) + 1):
            yield groove(z=B3 + D.power_margin + a * D.power_col,
                         od=D.spigot_od)


# ---------------------------------------------------------------------------
# End cap: the readout window, the spring, and the nut
# ---------------------------------------------------------------------------

class EndCap(Component):
    """Keyed to the inner tube, so the two behave as one body.

    Carries the power slot and the aperture headings, closes the readout
    end, and houses the spring. It slides on its key rather than seating
    against a shoulder: if it could bottom out on the inner tube, that
    tube would take the bolt load in parallel with the ring stack and
    leave the rings loose.
    """

    def tight_bbox(self):
        return _extents(B3 + D.seam_gap, D.overall_len)

    def pieces(self):
        # Its floor is the whole solid tail rather than an annulus taken
        # out of the sleeve: past band D there is nothing to make room
        # for, so it grows upward and band D's face stays on the boundary.
        return (("sleeve", B3 + D.seam_gap, B4),
                ("tail", B4, D.overall_len))

    def build(self):
        body = stack(self.pieces())
        cutters = [
            # The slot spans the columns exactly, ending on the first and
            # last division rather than half a cell past them. Overrun and
            # a blank half-cell shows above the first reading and below
            # the last, which reads as a missing value.
            window(z0=B3 + D.power_margin,
                   length=D.power_col * len(LAYOUT.column_labels)),
            # Hub bore and keyway: a sliding fit with no shoulder to
            # bottom against, so the inner tube never carries bolt load.
            # It ends `tip_gap` below the seat and cannot reach it.
            cylinder(h=D.inner_end_z - B4 + D.tip_gap + EPS,
                     d=D.spigot_bore).up(B4 - EPS),
            self._keyway(),
            self._spring_pockets(),
            cylinder(h=D.overall_len + 2 * EPS, d=D.bolt_d).down(EPS),
        ]
        cutters += list(self._legends())
        return engrave(body, cutters)

    def _keyway(self):
        return keyway(B4, D.inner_end_z + D.tip_gap)

    def _spring_pockets(self):
        """Three blind pockets on a circle outside the hub.

        They open at the cap's end face and bottom on solid cap, so a
        spring can only ever push against the cap. Sitting outside the
        hub's radius, they run alongside the key engagement rather than
        beyond it, and the inner tube cannot reach one however the stack
        is tightened.
        """
        one = (
            cylinder(h=D.pocket_depth + EPS, d=D.pocket_dia)
            .translate([D.pocket_r, 0, D.pocket_z0])
        )
        return one.rotate_copy(angle=360.0 / int(D.spring_count),
                               n=int(D.spring_count), axis=[0, 0, 1])

    def text_specs(self):
        """Where every label on the cap's outside goes.

        Yielded as placements rather than cut straight to geometry so that
        `check_cap_text_clear` can measure the same numbers the build
        uses. Every mark on the rings is positioned by a scale's
        arithmetic. These are placed by hand against the slot, so a check
        is the only thing keeping any two of them off each other.
        """
        # The slot is a column of eight readings rather than one value, so
        # its name sits under the column instead of beside it, where it
        # would land on the aperture headings. Under it as the tool is
        # held: the cap has no material the other side of the slot.
        before, after = LAYOUT.legend
        head_z = B4 + D.legend_font + 2
        yield dict(label=" ".join(p for p in (before, after) if p),
                   z=head_z, angle=0, size=D.legend_font)
        yield dict(label=LAYOUT.heading, z=head_z, angle=ABOVE,
                   size=D.legend_font)

        # Aperture headings beside the slot, one per column.
        for a, label in enumerate(LAYOUT.column_labels):
            yield dict(label=label,
                       z=B3 + D.power_margin + (a + 0.5) * D.power_col,
                       angle=ABOVE, size=D.power_font)

        # On the back: the assumption the guide numbers are quoted under,
        # and a maker's line below it. Below in z, on the same meridian --
        # set side by side they would cut into each other, since a line of
        # legend at this font wraps most of a half turn of the barrel.
        power_mid = B3 + D.power_band / 2
        line_gap = D.legend_font + 2
        for label, dz in (("GN @ 50mm  ISO 100  m", +line_gap / 2),
                          ("BriansSparetime", -line_gap / 2)):
            yield dict(label=label, z=power_mid + dz, angle=180,
                       size=D.legend_font)

    def _legends(self):
        for spec in self.text_specs():
            yield engrave_text(od=D.outer_od, **spec)

        # A rule at each column boundary, so the eye can tell the columns
        # apart. It runs from the slot's edge out past the widest heading,
        # which puts the headings in ruled cells rather than floating
        # beside the slot.
        widest = max(LAYOUT.column_labels, key=len)
        inner = D.window_arc / 2 + 1
        outer = ABOVE + label_arc(D.outer_od, widest, D.power_font) / 2 + 1.5
        span = radians(outer - inner) * D.outer_od / 2
        for a in range(len(LAYOUT.column_labels) + 1):
            yield tick(z=B3 + D.power_margin + a * D.power_col,
                       angle=(inner + outer) / 2, length=span)
