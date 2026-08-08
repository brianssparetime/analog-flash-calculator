"""Checks that the printed instrument is correct and buildable.

    python check.py

Four kinds of claim get verified. The photometry lives in `scales`, and
`scales.check()` proves the index arithmetic reproduces the flash
equation exactly. This module adds the geometric claims that the Spec
rules in `dims` cannot express on their own:

    every label falls inside the window that has to show it
    no two labels collide with each other
    the label the equation calls for lands on the window's meridian
    each column's heading and its values share an axial centre
    every window frames its label without catching the next one
    nothing engraved on the end cap runs into anything else on it
    every segment is one solid, not two shells that only look like one
    every segment threads onto the stack past everything in its way
    the spring is the only thing the end washer can land on
    nothing obstructs a detent lifting, least of all the spanning tube
    every segment lands in the axial band the layout assigns it

Label extents are measured off the real text geometry rather than
estimated, so the numbers here are the ones that get printed.
"""

import math

from scadwright import bbox

import scales
from dims import LAYOUT, Dims as D
from parts import (
    B0, B1, B2, B3, B4, BAND, DistRing, EndCap, GnRing, InnerTube, IsoRing,
    engrave_text, window_rows,
)
from scales import (
    APERTURES, DISTANCES_FT, DISTANCES_M, GUIDE_NUMBERS, ISOS, POWERS,
)


def _label_span(**kwargs):
    """Axial extent (z_min, z_max) of a label as it will be cut."""
    bb = bbox(engrave_text(**kwargs))
    return bb.min[2], bb.max[2]


def _label_arc_deg(od, label, size):
    """How much of the circumference a label takes, in degrees.

    The glyphs lie on the surface, so a point at angle t sits at
    y = r sin t. Measuring the cut geometry rather than guessing from the
    font size catches proportional spacing, which varies the width of a
    label by more than a millimetre between "11" and "3200".
    """
    bb = bbox(engrave_text(od=od, z=0, label=label, angle=0, size=size))
    r = od / 2
    return 2 * math.degrees(math.asin(max(abs(bb.min[1]), abs(bb.max[1])) / r))


def _label_arc_mm(od, label, size):
    return math.radians(_label_arc_deg(od, label, size)) * od / 2


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
    if LAYOUT.third == "distance":
        metre_z, foot_z = window_rows(B2, B3)
        rows = ((DISTANCES_M, metre_z, " m"), (DISTANCES_FT, foot_z, " ft"))
    else:
        rows = ((LAYOUT.third_marks, sum(window_rows(B2, B3)) / 2, ""),)
    for labels, z, unit in rows:
        for t, label in enumerate(labels):
            _assert_inside(
                _label_span(od=D.spigot_od, z=z, label=label,
                            angle=LAYOUT.setting_angle("third", t), size=D.dist_font),
                third_win, f"{LAYOUT.third} {label}{unit}")

    # The slot as `EndCap.build` actually cuts it, not the band it sits
    # in: the margin is at both ends, so testing against half of it passed
    # labels that the opening would have clipped by 1.5 mm.
    value_win = (B3 + D.power_margin,
                 B3 + D.power_margin + D.power_col * len(LAYOUT.column_labels))
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


def _longest(labels):
    return max(labels, key=len)


def _scales_to_measure():
    """Every scale on the tool, with its longest label and its font."""
    return (
        ("GN", _longest(GUIDE_NUMBERS), D.scale_font),
        ("ISO", _longest(ISOS), D.scale_font),
        ("third", _longest(LAYOUT.third_marks), D.dist_font),
        ("readout", _longest(LAYOUT.value_marks), D.power_font),
    )


def check_scales_fit_circumference():
    """One detent's worth of arc must hold a whole label.

    Labels run around the circumference, so what has to fit between one
    detent and the next is the label's full length, not a glyph's height.
    This is the constraint that sets the diameter of the instrument: the
    longest label on any scale, at the detent pitch, decides how big
    around the scale surface has to be.
    """
    arc = math.pi * D.spigot_od / scales.DETENTS
    tightest = None
    for what, label, font in _scales_to_measure():
        used = _label_arc_mm(D.spigot_od, label, font)
        assert used < arc, (
            f"{what} scale: '{label}' is {used:.2f} mm around, and one "
            f"detent is only {arc:.2f} mm of arc at OD {D.spigot_od:.1f}. "
            f"It would run into its neighbour."
        )
        if tightest is None or arc - used < tightest[0]:
            tightest = (arc - used, what, arc)
    return tightest


def check_windows_frame_labels():
    """A window must be wider than its label and narrower than its
    neighbour.

    Labels run around the circumference, so a window has to clear the
    whole length of one. Too narrow and the label is clipped at its ends;
    too wide and the next detent's label creeps into view beside the
    right one, which would show two readings at once.
    """
    tightest = None
    for what, label, font in _scales_to_measure():
        label_arc = _label_arc_deg(D.spigot_od, label, font)
        assert D.window_arc > label_arc, (
            f"{what}: '{label}' subtends {label_arc:.1f} deg on a "
            f"{D.spigot_od:.0f} mm surface, wider than the "
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
    """Nothing but the end cap may touch a spring.

    A central spring had to be checked against the inner tube reaching its
    seat, which would push the tube back to the head washer and leave the
    ring stack unloaded: the tool assembles and no detent clicks. Pockets
    on a circle outside the hub retire that failure by geometry rather
    than by clearance, and this checks the geometry still holds.
    """
    tube_r = D.inner_od / 2
    pocket_inner_r = D.pocket_r - D.pocket_dia / 2
    assert pocket_inner_r > tube_r, (
        f"a pocket reaches in to r {pocket_inner_r:.2f}, inside the tube's "
        f"r {tube_r:.2f}: the tube could bottom on a spring"
    )
    wall = D.outer_od / 2 - D.sleeve_wall - (D.pocket_r + D.pocket_dia / 2)
    assert wall > 0, f"pockets break out through the cap wall by {-wall:.2f} mm"
    # Each pocket must bottom on solid cap, not open into the readout slot.
    floor = D.pocket_z0 - D.power_z1
    assert floor > 0, "a pocket floor opens into the readout slot"
    # Raising the count is how the detent is made firmer, so the web
    # between neighbours is the thing that bounds it.
    assert D.pocket_web >= 2, (
        f"{int(D.spring_count)} pockets leave {D.pocket_web:.2f} mm of web "
        f"between neighbours, too thin to print"
    )
    return pocket_inner_r - tube_r, wall, floor


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

    # What the tube can actually reach is the cap's bore ceiling, `end_t`
    # inside the outer face -- comparing against the face flattered this
    # by the thickness of the cap's end. That gap is also the only place
    # four segments' worth of layer quantisation can go, so it has to
    # cover a lift and then some, not just exist.
    assert D.tip_gap > 2 * lift, (
        f"{D.tip_gap:.2f} mm from the tube's tip to the cap's bore ceiling "
        f"will not take a {lift:.2f} mm lift and the stack's length error: "
        f"closed, the tube carries the bolt load and nothing clicks"
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
    return D.seam_gap - lift, D.tip_gap - lift


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


def check_segments_hold_together():
    """Each piece of a segment must overlap the next by real area.

    This is the failure that hides from everything else. A sleeve rides
    the spigot beneath it, so it bores wider than that spigot is round; a
    segment's own spigot is that same diameter less `slip`, and begins
    exactly where its sleeve ends. Radially disjoint, sharing no length,
    the two union into a part that meshes, previews, slices and renders
    exactly like one solid and comes off the bed in two pieces.

    Every piece of every segment is an annulus about the axis, and each
    says so in its `pieces()` -- the same list `stack()` builds it from,
    so this cannot be testing a shape the part no longer has. Two annuli
    are joined when their lengths meet at all and their radii overlap by
    more than nothing; a segment holds together when its pieces are one
    group under that.
    """
    tightest = None
    for cls in (InnerTube, GnRing, IsoRing, DistRing, EndCap):
        pieces = list(cls().pieces())
        group = list(range(len(pieces)))        # group[i]: piece i's island
        for i, (n1, a0, a1) in enumerate(pieces):
            for j, (n2, b0, b1) in enumerate(pieces[i + 1:], i + 1):
                r1, r2 = BAND[n1], BAND[n2]
                shares = min(r1[1], r2[1]) - max(r1[0], r2[0])
                meets = min(a1, b1) - max(a0, b0)
                if meets < 0 or shares <= 0:
                    continue
                if tightest is None or shares < tightest[0]:
                    tightest = (shares, f"{cls.__name__} {n1} to {n2}")
                old, new = group[j], group[i]
                group = [new if g == old else g for g in group]

        islands = {}
        for g, piece in zip(group, pieces):
            islands.setdefault(g, []).append(piece[0])
        assert len(islands) == 1, (
            f"{cls.__name__} is not one solid: "
            + "; ".join(" + ".join(v) for v in islands.values())
            + ". It will mesh, slice and render exactly like one part and "
              "come off the bed in pieces."
        )
    return tightest


def _arc_overlap_deg(c1, h1, c2, h2):
    """How far two circumferential labels overlap, in degrees.

    Both are centred arcs, so the separation is what is left after the two
    half-widths are taken off it. Positive means they collide.
    """
    sep = abs((c2 - c1 + 180) % 360 - 180)
    return (h1 + h2) - sep


def check_cap_text_clear():
    """Nothing engraved on the cap's outside may run into anything else.

    Every mark on the rings is placed by a scale's arithmetic, so the
    checks above settle them. The headings beside the slot, the slot's own
    name, and the note on the back are all placed by hand, and nothing but
    this stops two of them landing on the same patch of barrel. A maker's
    line meant to sit below the note, offset round the circumference
    instead of along the axis, cut straight through it.

    Two labels collide only if they overlap in both z and angle, so the
    slot itself goes in the list as well.
    """
    placed = [("the readout slot",
               (B3 + D.power_margin,
                B3 + D.power_margin + D.power_col * len(LAYOUT.column_labels)),
               0.0, D.window_arc / 2)]
    for spec in EndCap().text_specs():
        bb = bbox(engrave_text(od=D.outer_od, **spec))
        placed.append((
            repr(spec["label"]),
            (bb.min[2], bb.max[2]),
            spec["angle"],
            _label_arc_deg(D.outer_od, spec["label"], spec["size"]) / 2,
        ))

    tightest = None
    for i, (what, z, c, h) in enumerate(placed):
        for other, z2, c2, h2 in placed[i + 1:]:
            dz = min(z[1], z2[1]) - max(z[0], z2[0])
            da = _arc_overlap_deg(c, h, c2, h2)
            assert dz <= 0 or da <= 0, (
                f"{what} and {other} overlap by {dz:.2f} mm and {da:.1f} deg "
                f"on the cap's outside"
            )
            # Whichever way they miss by is the clearance that matters.
            clear = max(-dz, math.radians(-da) * D.outer_od / 2)
            if tightest is None or clear < tightest[0]:
                tightest = (clear, what, other)
    return tightest


def check_key_ends_up_inside_the_cap():
    """Assembled, the key may sit in the cap and nowhere else.

    The cap is keyed so the two turn as one body, which is what makes the
    readout mean anything. Every other segment turns, and each carries a
    channel for the key on its own window meridian. Those channels exist
    to let a ring thread past the key during assembly and are empty once
    it is together. If the key ever reached a turning ring, that ring
    could only sit at the one angle where its channel lined up, and the
    setting under it would be stuck there.
    """
    key0, key1 = D.inner_end_z - D.key_len, D.inner_end_z
    turning = [
        ("gn ring", D.gn_z0, D.dist_z0),
        ("iso ring", D.iso_z0, D.power_z0),
        ("dist ring", D.dist_z0, D.power_z1),
    ]
    tightest = None
    for what, z0, z1 in turning:
        clear = key0 - z1
        assert clear > 0, (
            f"the key reaches {-clear:.2f} mm into the {what}, which turns: "
            f"it would lock that ring to the channel's meridian"
        )
        if tightest is None or clear < tightest[0]:
            tightest = (clear, what)
    # And it must actually engage the cap, or the two are not coupled.
    assert key0 >= D.power_z1 + D.cap_web_t, "the key starts inside the slot"
    assert key1 <= D.overall_len, "the key runs out of the cap's far end"
    return tightest


def check_key_passes_every_bore():
    """The inner tube's key has to get through every ring on the way down.

    The rings thread on from the key end, so the key sweeps the full
    length of each one. It stands proud of the tube by more than any
    spigot bore clears, which is why each ring carries a channel on its
    window meridian. Without that channel nothing assembles, and the plain
    bore-versus-OD comparison above cannot see it.
    """
    key_r = D.inner_od / 2 + D.key_h
    bore_r = D.spigot_bore / 2
    assert key_r > bore_r, (
        "the key no longer stands proud of the spigot bore, so the "
        "keyways are dead weight: drop them or the check"
    )
    channel_r = D.inner_od / 2 + D.key_h + D.key_slip / 2
    assert channel_r > key_r, (
        f"keyway reaches {channel_r:.2f} mm, the key {key_r:.2f} mm: "
        f"the key will not pass"
    )
    assert D.key_w + D.key_slip > D.key_w, "keyway is not wider than the key"
    return key_r - bore_r, D.key_slip / 2


def check_spring_actually_loads():
    """The spring must be the only thing the nut washer lands on.

    This is the failure the previous design shipped with: a counterbore
    narrower than the washer let the washer bottom on its rim, so the
    spring never compressed. Everything looked assembled and nothing
    clicked. Both ends are checked, since a washer that drops into either
    end short-circuits the stack.
    """
    reach = D.washer_od / 2 - (D.pocket_r + D.pocket_dia / 2)
    assert reach > 0, (
        f"a {D.washer_od:.0f} mm washer does not cover the pocket circle; "
        f"it would miss a spring by {-reach:.2f} mm"
    )
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
    """Each segment must build and land in the z band the layout assigns.

    Both bboxes are taken, and they answer different questions. Every part
    declares a `tight_bbox`, because the framework cannot tighten a
    difference this wide without evaluating the CSG, and `bbox(cls())`
    returns that declaration -- so on its own it only proves the
    declaration matches the layout. Measuring `cls().build()` instead
    walks the geometry, and the two agreeing is what says the declaration
    is honest: a part that quietly grew or moved would show up here rather
    than in `arrange_on_bed` putting it through its neighbour.
    """
    expected = {
        InnerTube: (B0, D.inner_end_z),
        GnRing: (B0 + D.seam_gap, B2 - D.floor_t + D.bump_proud),
        IsoRing: (B1 + D.seam_gap, B3 - D.floor_t + D.bump_proud),
        DistRing: (B2 + D.seam_gap, B4 + D.bump_proud),
        EndCap: (B3 + D.seam_gap, D.overall_len),
    }
    for cls, (lo, hi) in expected.items():
        for name, bb in (("declares", bbox(cls())),
                         ("builds", bbox(cls().build()))):
            assert abs(bb.min[2] - lo) < 0.01 and abs(bb.max[2] - hi) < 0.01, (
                f"{cls.__name__} {name} {bb.min[2]:.2f}..{bb.max[2]:.2f}, "
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

    clear, a, b = check_cap_text_clear()
    print(f"cap text       nothing on the cap overlaps anything else; "
          f"closest {a} to {b} at {clear:.2f} mm")

    key_proud, key_clear = check_key_passes_every_bore()
    print(f"keyway         the key stands {key_proud:.2f} mm proud of every "
          f"bore; channels clear it by {key_clear:.2f} mm")

    gap, nearest = check_key_ends_up_inside_the_cap()
    print(f"key seat       assembled, the key sits in the cap alone; "
          f"{gap:.1f} mm clear of the {nearest}")

    clr = check_threading()
    print(f"threading      every segment goes on; tightest {clr:.2f} mm per side")

    overlap, join = check_segments_hold_together()
    print(f"one piece      every segment's parts overlap; tightest "
          f"{overlap:.2f} mm at {join}")

    seam, tip = check_travel_is_unobstructed()
    print(f"travel         nothing fouls a detent lifting "
          f"{D.bump_proud:.2f} mm; {seam:.2f} mm of seam and {tip:.2f} mm "
          f"of tip gap to spare")

    clear_r, wall, floor = check_spring_bears_only_on_the_cap()
    print(f"spring seat    {int(D.spring_count)} pockets clear the tube by "
          f"{clear_r:.1f} mm and the wall by {wall:.1f} mm; "
          f"{D.pocket_web:.1f} mm of web between them")

    cap, lift = check_spring_actually_loads()
    print(f"spring         washer overhangs the stack by {cap / 2:.1f} mm "
          f"per side; {lift:.2f} mm of lift to spare")

    check_parts_build()
    print("geometry       all five pieces build in their assigned bands")

    print()
    print(f"overall        {D.overall_len:.0f} x {D.outer_od:.0f} mm, "
          f"{scales.DETENTS} detents of {scales.DETENT_ANGLE:.0f} degrees, "
          f"5 printed parts")
