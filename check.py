"""Checks that the printed instrument is correct and buildable.

    python check.py

Four kinds of claim get verified. The photometry lives in `scales`, and
`scales.check()` proves the index arithmetic reproduces the flash
equation exactly. This module adds the geometric claims that the Spec
rules in `dims` cannot express on their own:

    every label falls inside the window that has to show it
    no two labels collide with each other
    the label the equation calls for lands on the window's meridian\n    each column's heading and its values share an axial centre\n    every window frames its label without catching the next one\n    every segment threads onto the stack past everything in its way
    the spring is the only thing the end washer can land on\n    nothing obstructs a detent lifting, least of all the spanning tube\n    every segment lands in the axial band the layout assigns it

Label extents are measured off the real text geometry rather than
estimated, so the numbers here are the ones that get printed.
"""

from scadwright import bbox

import scales
from dims import LAYOUT, Dims as D
from parts import (
    B0, B1, B2, B3, B4, FOOT_ROW, METRE_ROW, DistRing, EndCap, GnRing,
    InnerTube, IsoRing, engrave_text,
)
from scales import (
    APERTURES, DISTANCES_FT, DISTANCES_M, GUIDE_NUMBERS, ISOS, POWERS,
)


def _label_span(**kwargs):
    """Axial extent (z_min, z_max) of a label as it will be cut."""
    bb = bbox(engrave_text(**kwargs))
    return bb.min[2], bb.max[2]


def _assert_inside(span, win, what):
    lo, hi = span
    w_lo, w_hi = win
    assert w_lo <= lo and hi <= w_hi, (
        f"{what}: label spans {lo:.2f}..{hi:.2f} but the window is "
        f"{w_lo:.2f}..{w_hi:.2f} (overhangs by "
        f"{max(w_lo - lo, hi - w_hi):.2f} mm)"
    )


def check_labels_fit_windows():
    """Every scale label must be fully visible through its window."""
    gn_win = (B0 + D.window_margin, B1 - D.window_margin)
    for g, label in enumerate(GUIDE_NUMBERS):
        _assert_inside(
            _label_span(od=D.spigot_od, z=(B0 + B1) / 2, label=label,
                        angle=LAYOUT.setting_angle("gn", g), size=D.scale_font),
            gn_win, f"GN {label}")

    iso_win = (B1 + D.window_margin, B2 - D.window_margin)
    for i, label in enumerate(ISOS):
        _assert_inside(
            _label_span(od=D.spigot_od, z=(B1 + B2) / 2, label=label,
                        angle=LAYOUT.setting_angle("iso", i), size=D.scale_font),
            iso_win, f"ISO {label}")

    # The third band carries whichever setting the layout puts there, laid
    # out exactly as `IsoRing.scale` cuts it: two rows for distance, one
    # for anything else.
    third_win = (B2 + D.window_margin, B3 - D.window_margin)
    span = B3 - B2
    if LAYOUT.third == "distance":
        rows = ((DISTANCES_M, METRE_ROW, " m"), (DISTANCES_FT, FOOT_ROW, " ft"))
    else:
        rows = ((LAYOUT.third_marks, 0.5, ""),)
    for labels, frac, unit in rows:
        for t, label in enumerate(labels):
            _assert_inside(
                _label_span(od=D.spigot_od, z=B2 + span * frac, label=label,
                            angle=LAYOUT.setting_angle("third", t), size=D.dist_font),
                third_win, f"{LAYOUT.third} {label}{unit}")

    value_win = (B3 + D.power_margin / 2,
                 B4 - D.power_margin / 2)
    for a in range(len(APERTURES)):
        col_mid = B3 + D.power_margin + (a + 0.5) * D.power_col
        for p, label in enumerate(LAYOUT.value_marks):
            _assert_inside(
                _label_span(od=D.spigot_od, z=col_mid, label=label,
                            angle=LAYOUT.table_angle(p, a), size=D.power_font),
                value_win, f"{LAYOUT.value} {label} at f/{APERTURES[a]}")


def check_power_columns_clear():
    """Adjacent aperture columns must not run into one another.

    At any one angle every column carries a label, the next column over
    showing the neighbouring mark, so the columns are neighbours in z at
    the same angle and the widest label decides the column pitch.
    """
    widest = 0.0
    worst = None
    for a in range(len(APERTURES) - 1):
        for p in range(1, len(LAYOUT.value_marks)):
            angle = LAYOUT.table_angle(p, a)
            here = _label_span(
                od=D.spigot_od,
                z=B3 + D.power_margin + (a + 0.5) * D.power_col,
                label=LAYOUT.value_marks[p], angle=angle, size=D.power_font)
            nxt = _label_span(
                od=D.spigot_od,
                z=B3 + D.power_margin + (a + 1.5) * D.power_col,
                label=LAYOUT.value_marks[p - 1], angle=angle, size=D.power_font)
            gap = nxt[0] - here[1]
            assert gap > 0, (
                f"f/{APERTURES[a]} {LAYOUT.value_labels[p]} overlaps "
                f"f/{APERTURES[a + 1]} {LAYOUT.value_labels[p - 1]} "
                f"by {-gap:.2f} mm"
            )
            if worst is None or gap < worst[0]:
                worst = (gap, APERTURES[a], LAYOUT.value_labels[p])
            widest = max(widest, here[1] - here[0])
    return widest, worst


def check_scales_fit_circumference():
    """One detent's worth of arc must hold a glyph without crowding.

    Labels run along the axis, so what has to fit around the cylinder is
    the glyph height, not the label's length. That is what lets the
    inner segment stay slim even though it carries the longest
    labels on the tool.
    """
    tightest = None
    for what, od, font in (
        ("GN", D.spigot_od, D.scale_font),
        ("power", D.spigot_od, D.power_font),
        ("ISO", D.spigot_od, D.scale_font),
        ("distance", D.spigot_od, D.dist_font),
    ):
        import math
        arc = math.pi * od / scales.DETENTS
        assert arc > font * 1.4, (
            f"{what} scale: one detent is {arc:.2f} mm of arc at OD {od}, "
            f"too tight for {font} mm glyphs"
        )
        if tightest is None or arc - font < tightest[0]:
            tightest = (arc - font, what, arc)
    return tightest


def check_windows_frame_labels():
    """A window must be wider than its label and narrower than its
    neighbour.

    Labels run along the axis, so what a window has to clear
    circumferentially is the glyph height -- and the glyph sits on the
    scale surface, at a smaller radius than the window it is seen
    through, so it subtends a wider angle than its height suggests. Too
    narrow and the label is clipped at an angle; too wide and the next
    detent's label creeps into view alongside the right one.
    """
    from math import degrees

    tightest = None
    for what, scale_od, font in (
        ("GN", D.spigot_od, D.scale_font),
        ("power", D.spigot_od, D.power_font),
        ("ISO", D.spigot_od, D.scale_font),
        ("distance", D.spigot_od, D.dist_font),
    ):
        label_arc = degrees(font / (scale_od / 2))
        assert D.window_arc > label_arc, (
            f"{what} label subtends {label_arc:.1f} deg on a "
            f"{scale_od:.0f} mm surface, wider than the "
            f"{D.window_arc:.0f} deg window: it will be clipped"
        )
        # The next detent's label starts half its width off the neighbour.
        intrudes = scales.DETENT_ANGLE - label_arc / 2
        assert D.window_arc / 2 < intrudes, (
            f"{what}: a {D.window_arc:.0f} deg window reaches the next "
            f"detent's label, which starts at {intrudes:.1f} deg"
        )
        margin = D.window_arc - label_arc
        if tightest is None or margin < tightest[0]:
            tightest = (margin, what, label_arc)
    return tightest


def check_readout_lands_in_window():
    """The right label must physically land on the window's meridian.

    Everything else checks the arithmetic. This checks the geometry that
    carries it: the three settings turn three bodies, and the label the
    flash equation says should be showing has to end up at the same angle
    as the end cap's slot, having gone round the chain. An error in a
    scale's sign or in the table's constant would leave the arithmetic
    right and the instrument wrong.
    """
    checked = 0
    for g in range(len(GUIDE_NUMBERS)):
        for i in range(len(ISOS)):
            for t in range(len(LAYOUT.third_labels)):
                inner_a, _, _, dist_a = LAYOUT.rotations(gn=g, iso=i, third=t)
                for c in range(len(LAYOUT.column_labels)):
                    v = LAYOUT.readout(gn=g, iso=i, third=t, column=c)
                    if v is None:
                        continue
                    shown = (dist_a + LAYOUT.table_angle(v, c)) % 360
                    want = inner_a % 360
                    assert abs(shown - want) < 1e-6, (
                        f"GN {GUIDE_NUMBERS[g]} ISO {ISOS[i]} "
                        f"{LAYOUT.third} {LAYOUT.third_labels[t]} at "
                        f"{LAYOUT.column_labels[c]}: "
                        f"{LAYOUT.value_labels[v]} sits at {shown:.2f} deg, "
                        f"window at {want:.2f} deg"
                    )
                    checked += 1
    return checked


def check_headings_line_up_with_values():
    """Each column's heading and its values must share an axial centre.

    They are engraved on different parts at different radii, so nothing
    but this makes them agree. The tolerance is what glyph side bearings
    cost: labels are centred on their advance widths, and the ink centre
    can sit slightly off that.
    """
    worst = 0.0
    for c, head in enumerate(LAYOUT.column_labels):
        z = B3 + D.power_margin + (c + 0.5) * D.power_col
        h_lo, h_hi = _label_span(od=D.outer_od, z=z, label=head,
                                 angle=-(D.window_arc / 2 + 12),
                                 size=D.power_font)
        for v, val in enumerate(LAYOUT.value_labels):
            v_lo, v_hi = _label_span(od=D.spigot_od, z=z, label=val,
                                     angle=LAYOUT.table_angle(v, c),
                                     size=D.power_font)
            off = abs((v_lo + v_hi) / 2 - (h_lo + h_hi) / 2)
            assert off < 0.4, (
                f"{val} sits {off:.2f} mm off centre under {head}"
            )
            worst = max(worst, off)
    return worst


def check_spring_bears_only_on_the_cap():
    """Nothing but the end cap may touch the spring.

    The inner tube runs the whole length, so if its far end reached the
    spring seat the spring would push it straight back to the head washer
    and the ring stack would never be loaded. That is a silent failure:
    the tool assembles, and no detent clicks. The seat is therefore solid
    cap across the whole spring bore, with the tube stopping below it.
    """
    gap = D.spring_seat_z - D.inner_end_z
    assert gap > D.tip_gap, (
        f"the inner tube ends {gap:.2f} mm below the spring seat, which is "
        f"not clear of it; the spring would short-circuit through the tube"
    )
    assert D.cap_seat_t >= 2, "the spring seat is too thin to be a floor"
    # The seat must be cap material right across whatever the spring rests
    # on, from the bolt out to the recess wall.
    assert D.spring_bore > D.bolt_d, "no annulus for the spring to sit on"
    return gap


def check_travel_is_unobstructed():
    """Turning a detent must not be stopped by the spanning tube.

    A detent lifts `bump_proud`, and everything on the spring side of it
    moves that far toward the spring. Two failure shapes matter, and both
    have already happened once: the tube reaching the spring so the load
    returns through it, and a gap closing so the stack bottoms out on the
    tube instead of compressing the spring.

    So every clearance the tube is involved in must either open under
    travel or exceed the lift, and the only gaps allowed to close are the
    sleeve seams between the moving segments themselves.
    """
    lift = D.bump_proud

    # These open as the stack lengthens; they only need to exist.
    assert D.spring_seat_z > D.inner_end_z, (
        "the tube reaches the spring seat"
    )
    assert D.seam_gap > 0, "the head washer would foul the first ring"

    # The cap rides the tube's key while the stack breathes, so the key
    # has to be longer than the travel by a sane margin.
    assert D.key_len > 4 * lift, (
        f"a {D.key_len:.1f} mm key is too short to slide {lift:.2f} mm "
        f"without risking disengagement"
    )

    # The seams are the gaps that do close. They must outlast a full lift.
    assert D.seam_gap > lift, (
        f"a {D.seam_gap:.2f} mm seam closes before a {lift:.2f} mm bump "
        f"clears its dimple: the sleeves bottom out and nothing clicks"
    )
    return D.seam_gap - lift


def check_threading():
    """Each ring must slide on past everything in its way.

    This is the constraint that decides the whole radial scheme. Rings go
    on from the right, so a ring's narrowest bore has to clear every
    outside diameter it travels over. The dist ring's tail is the tight
    one: it rides the inner segment directly, so it would foul the rings
    it skips if it ever had to travel left of them.
    """
    passes = [
        ("gn ring over the inner tube", D.spigot_bore, D.inner_od),
        ("iso ring over the inner tube", D.spigot_bore, D.inner_od),
        ("dist ring over the inner tube", D.spigot_bore, D.inner_od),
        ("gn ring sleeve over the inner spigot", D.sleeve_bore, D.spigot_od),
        ("iso ring sleeve over the gn spigot", D.sleeve_bore, D.spigot_od),
        ("dist ring sleeve over the iso spigot", D.sleeve_bore, D.spigot_od),
        ("end cap over the dist spigot", D.sleeve_bore, D.spigot_od),
        ("end cap hub over the inner tube", D.spigot_bore, D.inner_od),
    ]
    for what, bore, over in passes:
        assert bore > over, (
            f"{what}: bore {bore:.1f} will not pass OD {over:.1f}"
        )
    return min(bore - over for _, bore, over in passes) / 2


def check_spring_actually_loads():
    """The spring must be the only thing the nut washer lands on.

    This is the failure the previous design shipped with: a counterbore
    narrower than the washer let the washer bottom on its rim, so the
    spring never compressed. Everything looked assembled and nothing
    clicked. Both ends are checked, since a washer that drops into either
    end short-circuits the stack.
    """
    assert D.washer_od > D.outer_od, (
        f"a {D.washer_od:.0f} mm washer does not cap a {D.outer_od:.0f} mm "
        f"stack; it would drop in and bypass the spring"
    )
    assert D.spring_proud > D.bump_proud, (
        f"the spring stands {D.spring_proud:.2f} mm proud but a bump lifts "
        f"{D.bump_proud:.2f} mm: the cap's rim would stop the detent"
    )
    assert D.seam_gap > D.bump_proud, (
        "sleeves would touch before the detents lift"
    )
    return D.washer_od - D.outer_od, D.spring_proud - D.bump_proud


def check_parts_build():
    """Each segment must build and land in the z band the layout assigns."""
    expected = {
        InnerTube: (B0, D.inner_end_z),
        GnRing: (B0 + D.seam_gap, B2 + D.bump_proud),
        IsoRing: (B1 + D.seam_gap, B3 + D.bump_proud),
        DistRing: (B2 + D.seam_gap, B4 + D.bump_proud),
        EndCap: (B3 + D.seam_gap, D.overall_len),
    }
    for cls, (lo, hi) in expected.items():
        bb = bbox(cls())
        assert abs(bb.min[2] - lo) < 0.01 and abs(bb.max[2] - hi) < 0.01, (
            f"{cls.__name__} spans {bb.min[2]:.2f}..{bb.max[2]:.2f}, "
            f"expected {lo:.2f}..{hi:.2f}"
        )


if __name__ == "__main__":
    n = scales.check()
    print(f"photometry     {n} in-range combinations exact")

    check_labels_fit_windows()
    print("labels         every scale label fits its window")

    widest, worst = check_power_columns_clear()
    gap, ap, pw = worst
    print(f"slot columns   clear; widest label {widest:.2f} mm in a "
          f"{D.power_col:.1f} mm pitch")
    print(f"               tightest gap {gap:.2f} mm "
          f"(f/{ap} {pw} to its neighbour)")

    slack, what, arc = check_scales_fit_circumference()
    print(f"circumference  one detent is {arc:.2f} mm of arc on the "
          f"{what} scale, the tightest")

    margin, what, label_arc = check_windows_frame_labels()
    print(f"windows        {D.window_arc:.0f} deg clears every label; "
          f"tightest is {what} at {label_arc:.1f} deg")

    n_read = check_readout_lands_in_window()
    print(f"readout        {n_read} readings land on the window meridian exactly")

    off = check_headings_line_up_with_values()
    print(f"columns        headings centred on their values within "
          f"{off:.2f} mm of {D.power_col:.0f}")

    clr = check_threading()
    print(f"threading      every segment goes on; tightest {clr:.2f} mm per side")

    slack = check_travel_is_unobstructed()
    print(f"travel         nothing fouls a detent lifting "
          f"{D.bump_proud:.2f} mm; {slack:.2f} mm of seam to spare")

    gap = check_spring_bears_only_on_the_cap()
    print(f"spring seat    solid cap floor; inner tube stops {gap:.1f} mm short")

    cap, lift = check_spring_actually_loads()
    print(f"spring         washer overhangs the stack by {cap / 2:.1f} mm "
          f"per side; {lift:.2f} mm of lift to spare")

    check_parts_build()
    print("geometry       all five pieces build in their assigned bands")

    print()
    print(f"overall        {D.overall_len:.0f} x {D.outer_od:.0f} mm, "
          f"{scales.DETENTS} detents of {scales.DETENT_ANGLE:.0f} degrees, "
          f"5 printed parts")
