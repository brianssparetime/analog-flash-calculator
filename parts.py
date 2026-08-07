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
outside one constant cylinder. A spigot's end face meets the next
segment's sleeve floor, and that annulus, well inboard of the rim, is
where the detents live.

Assembly runs right to left: gn ring, iso ring, dist ring, end cap, each
sliding over the inner tube's plain body and seating on the one before.
"""

from scadwright import BBox, Component
from scadwright.boolops import difference, union
from scadwright.primitives import cube, cylinder, sphere
from scadwright.shapes import PieSlice, Tube

from dims import DETENT_BUMPS, DETENT_DIVOTS, LAYOUT, Dims
from scales import (
    DISTANCES_FT, DISTANCES_M, GUIDE_NUMBERS, ISOS, window_legend,
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

# Where the two distance rows sit within their band, as a fraction of it.
# The window legend and the scale itself both read from these, so the
# unit markers cannot drift off the rows they label.
METRE_ROW = 0.29
FOOT_ROW = 0.71

# Negative angles sit above a window when the tool is laid down and read.
ABOVE = -(D.window_arc / 2 + 12)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def engrave_text(*, od, z, label, angle, size, depth=None, font=SCALE_FONT):
    """An inset-text cutter centred at absolute height `z` on a wall of
    diameter `od`.

    Glyphs run along the axis and read left to right with +Z to the right,
    which is how the instrument is held.
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
        text_dir="axial",
        rotate_glyphs=True,
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


def tick(*, z, angle, length=3.5, width=0.8, depth=0.5):
    """A short circumferential index line cut into the outer surface."""
    return (
        cube([2 * depth, length, width], center="xyz")
        .translate([D.outer_od / 2, 0, 0])
        .rotate([0, 0, angle])
        .up(z)
    )


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


def sleeve(z0, z1):
    """A full-diameter section: the outside of the finished cylinder."""
    return Tube(h=z1 - z0, od=D.outer_od, id=D.sleeve_bore).up(z0)


def spigot(z0, z1):
    """A reduced-diameter section that runs under the next segment."""
    return Tube(h=z1 - z0, od=D.spigot_od, id=D.spigot_bore).up(z0)


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
    """A spigot carrying the GN scale, then a plain body running the
    length of the tool.

    Its left end face is the head of the stack: the bolt's washer bears
    there, and the ring stack piles up against the far side of the same
    spigot. The body is deliberately plain and thinner than every spigot
    bore, so each ring threads straight over it. The far end carries a key
    rib that the end cap slides onto.
    """

    def tight_bbox(self):
        return _extents(B0, D.inner_end_z, D.spigot_od)   # body outruns the bumps

    def build(self):
        body = union(
            spigot(B0, B1),
            cylinder(h=D.inner_end_z - B1 + EPS, d=D.inner_od).up(B1 - EPS),
            self._key(),
            bumps(B1),
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
    LEGEND = ""

    def tight_bbox(self):
        # The bumps stand proud of the spigot's end face.
        return _extents(self.READS[0] + D.seam_gap,
                        self.CARRIES[1] + D.bump_proud)

    def build(self):
        r0, r1 = self.READS
        c1 = self.CARRIES[1]
        body = union(
            sleeve(r0 + D.seam_gap, r1),
            spigot(r1, c1),
            bumps(c1),
        )
        cutters = [
            window(z0=r0 + D.window_margin,
                   length=(r1 - r0) - 2 * D.window_margin),
            divots(r1),
            engrave_text(
                od=D.outer_od, z=(r0 + r1) / 2, label=self.LEGEND,
                angle=D.window_arc / 2 + 13, size=D.legend_font,
            ),
        ]
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
    LEGEND = window_legend("gn")        # guide numbers are quoted in metres

    def scale(self):
        for i, label in enumerate(ISOS):
            yield engrave_text(
                od=D.spigot_od, z=(B1 + B2) / 2, label=label,
                angle=LAYOUT.setting_angle("iso", i), size=D.scale_font,
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
    LEGEND = "ISO"          # its window shows the film speed

    def scale(self):
        span = B3 - B2
        labels = LAYOUT.third_marks
        if LAYOUT.third != "distance":
            for t, label in enumerate(labels):
                yield engrave_text(
                    od=D.spigot_od, z=B2 + span / 2, label=label,
                    angle=LAYOUT.setting_angle("third", t), size=D.dist_font,
                )
            return
        for t, (m_label, ft_label) in enumerate(zip(DISTANCES_M, DISTANCES_FT)):
            angle = LAYOUT.setting_angle("third", t)
            yield engrave_text(od=D.spigot_od, z=B2 + span * METRE_ROW,
                               label=m_label, angle=angle, size=D.dist_font)
            yield engrave_text(od=D.spigot_od, z=B2 + span * FOOT_ROW,
                               label=ft_label, angle=angle, size=D.dist_font)


class DistRing(_SettingRing):
    """Turn against the ISO ring to dial in the flash-to-subject distance.

    Its spigot carries the answer: one column of power settings per
    aperture, read through the end cap's long slot.
    """

    READS = (B2, B3)
    CARRIES = (B3, B4)
    @property
    def LEGEND(self):
        # Its window shows the third setting, which the layout names. When
        # that is distance the two rows carry their own unit marks, so the
        # legend stays bare.
        if LAYOUT.third == "distance":
            return "DIST"
        return window_legend(LAYOUT.third, LAYOUT.units)

    def window_legends(self):
        """Units above the window, in the order the rows appear.

        Only the distance scale has two rows. They are labelled in the
        order they run along the axis, so the marker over each row is the
        one that names it whichever way round the rows are placed.
        """
        if LAYOUT.third != "distance":
            return
        span = B3 - B2
        for frac, unit in ((METRE_ROW, "m"), (FOOT_ROW, "ft")):
            yield engrave_text(
                od=D.outer_od, z=B2 + span * frac, label=unit,
                angle=ABOVE, size=D.legend_font,
            )

    def scale(self):
        for c in range(len(LAYOUT.column_labels)):
            col_mid = B3 + D.power_margin + (c + 0.5) * D.power_col
            for v, label in enumerate(LAYOUT.value_marks):
                yield engrave_text(
                    od=D.spigot_od, z=col_mid, label=label,
                    angle=LAYOUT.table_angle(v, c), size=D.power_font,
                )


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

    def build(self):
        body = union(
            sleeve(B3 + D.seam_gap, B4),
            cylinder(h=D.overall_len - B4, d=D.outer_od).up(B4),
        )
        cutters = [
            # Power slot, spanning every aperture column.
            window(z0=B3 + D.power_margin / 2,
                   length=D.power_band - D.power_margin),
            # Hub bore and keyway: a sliding fit with no shoulder to
            # bottom against, so the inner tube never carries bolt load.
            # It ends `tip_gap` below the seat and cannot reach it.
            cylinder(h=D.inner_end_z - B4 + D.tip_gap + EPS,
                     d=D.spigot_bore).up(B4 - EPS),
            self._keyway(),
            # Spring recess. Its floor is solid cap across the whole bore,
            # so the spring can only ever push on the cap.
            cylinder(h=D.spring_depth + EPS, d=D.spring_bore).up(D.spring_seat_z),
            cylinder(h=D.overall_len + 2 * EPS, d=D.bolt_d).down(EPS),
        ]
        cutters += list(self._legends())
        return engrave(body, cutters)

    def _keyway(self):
        return (
            cube([D.inner_od / 2 + D.key_h + D.key_slip / 2,
                  D.key_w + D.key_slip,
                  D.inner_end_z - B4 + D.tip_gap + 2 * EPS], center="y")
            .up(B4 - EPS)
        )

    def _legends(self):
        # The aperture row goes above the window, over the values inside
        # it, as on the paper original; the legend drops below.
        above = ABOVE
        below = D.window_arc / 2 + 30
        power_mid = B3 + D.power_band / 2

        yield engrave_text(
            od=D.outer_od, z=power_mid, label=LAYOUT.legend,
            angle=below, size=D.legend_font,
        )

        # Aperture headings beside the slot, one per column, with a tick
        # at each boundary so the eye can tell the columns apart.
        for a, label in enumerate(LAYOUT.column_labels):
            yield engrave_text(
                od=D.outer_od, z=B3 + D.power_margin + (a + 0.5) * D.power_col,
                label=label, angle=above, size=D.power_font,
            )
            yield tick(z=B3 + D.power_margin + a * D.power_col,
                       angle=-(D.window_arc / 2 + 5))
        yield tick(z=B3 + D.power_margin
                     + len(LAYOUT.column_labels) * D.power_col,
                   angle=-(D.window_arc / 2 + 5))

        # On the back: the assumption the guide numbers are quoted
        # under, and a maker's line below it.
        yield engrave_text(
            od=D.outer_od, z=power_mid, label="GN @ 50mm  ISO 100  m",
            angle=180, size=D.legend_font,
        )
        yield engrave_text(
            od=D.outer_od, z=power_mid, label="BriansSparetime",
            angle=180 + 17, size=D.legend_font,
        )
