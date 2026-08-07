"""Scale tables and the stop arithmetic that ties them together.

The calculator is a logarithmic slide rule folded into a cylinder. Every
scale is indexed in *stops*: one detent of rotation is one stop on every
scale, so a single angular pitch serves all four bodies.

One stop means different things per quantity, but they all agree on
exposure:

    aperture   x sqrt(2)   (f/2 -> f/2.8)
    distance   x sqrt(2)   (4 m -> 5.6 m)
    ISO        x 2         (100 -> 200)
    power      / 2         (1/1 -> 1/2)
    guide no.  x sqrt(2)   (22 -> 32)

Guide number is defined as GN = aperture x distance at ISO 100 and full
power. Raising ISO by a stop or cutting power by a stop each move the
effective guide number by one stop, which gives the governing relation
used throughout this project:

    aperture + distance + power - ISO = GN                (all in stops)

`check()` proves that relation holds for every combination the printed
scales can express, and pins it against a reading from the original
paper prototype.

Guide numbers are quoted for metres, ISO 100, and 50 mm coverage. A zoom
head changes the guide number by an amount that varies per flash, so the
right move is to read the number off the flash's own table and dial that
in, rather than deriving it from a focal-length scale.
"""

from math import log2

# Each scale pairs its labels with the absolute stop value of index 0.
# Absolute stops use f/1, 1 metre, ISO 100 and full power as their
# respective origins, so the relation above closes without fudge factors.

APERTURES = ("2", "2.8", "4", "5.6", "8", "11", "16", "22")
APERTURE_ORIGIN = 2          # f/2 is 2 stops from f/1

DISTANCES_M = ("1", "1.4", "2", "2.8", "4", "5.6", "8", "11", "16")
DISTANCE_ORIGIN = 0          # 1 m is the origin

# The same physical detents, read in feet. Rounded from metres x 3.281,
# so the numbers are not a tidy series -- they cannot be, because feet
# and metres do not share a half-stop grid.
DISTANCES_FT = ("3.3", "4.6", "6.5", "9.2", "13", "18", "26", "37", "52")

ISOS = ("25", "50", "100", "200", "400", "800", "1600", "3200")
ISO_ORIGIN = -2              # ISO 25 is 2 stops below ISO 100

POWERS = ("1/1", "1/2", "1/4", "1/8", "1/16", "1/32", "1/64", "1/128")
POWER_ORIGIN = 0             # full power is the origin

# What actually gets engraved for power: the denominator alone, with the
# "1/" moved into the legend beside the slot. It is identical in all
# sixty-four cells and costs a third of the label's width, which sets the
# column pitch and so the length of the whole instrument.
POWER_MARKS = tuple(p.split("/")[1] for p in POWERS)

# Micro and pocket flashes at the low end, a Metz Mecablitz 45 at the high.
# Labelled on the same rounded sqrt(2) series as the apertures, so the two
# scales read alike.
GUIDE_NUMBERS = ("5.6", "8", "11", "16", "22", "32", "45", "64")
GUIDE_NUMBER_ORIGIN = 5      # GN 5.6 is 5 stops above GN 1 (metres, ISO 100)

# Detents around the circumference. Every scale is shorter than this, so
# unused slots read blank rather than colliding with a neighbour.
DETENTS = 12
DETENT_ANGLE = 360.0 / DETENTS

# Constant term of the governing relation once the origins are folded in:
#   (a + APERTURE_ORIGIN) + d + p - (i + ISO_ORIGIN) = g + GUIDE_NUMBER_ORIGIN
# rearranges to  a + d + p - i = g + OFFSET.
OFFSET = GUIDE_NUMBER_ORIGIN - APERTURE_ORIGIN + ISO_ORIGIN     # = 1


def power_index(*, gn, iso, aperture, distance):
    """Stops of power reduction needed, as an index into `POWERS`.

    All arguments are scale indices. A result outside `range(len(POWERS))`
    means the combination is off the printed scale: negative wants more
    light than the flash has, too large wants less than its lowest setting.
    """
    return gn + OFFSET + iso - aperture - distance


# ---------------------------------------------------------------------------
# Angular layout
# ---------------------------------------------------------------------------
#
# Every window sits on its body's zero meridian. Each scale is printed at
# `index * DETENT_ANGLE` from its own body's zero meridian, signed so the
# three relative rotations compose into the governing relation:
#
#   GN scale       (inner)     +g
#   ISO scale      (gn ring)   +i
#   distance scale (iso ring)  -d
#   power table    (dist ring) -(p + a - OFFSET)
#
# Chaining the three window readings puts the dist ring at (g + i - d)
# detents relative to the core, so the power column for aperture `a`
# shows p = g + OFFSET + i - a - d, which is `power_index` above.

# --- the setting the instrument lines up at -------------------------------
#
# Where each scale's zero sits is free: shifting one by a whole detent
# moves that ring's window round the circumference without touching any
# reading. Engraving every scale relative to the setting below, rather
# than to its own first mark, brings all three setting windows onto the
# readout slot's meridian at that setting, so a single view shows the
# whole tool being read. Every other setting scatters them as before.
#
# Change these three to line up somewhere else. GN and ISO are labels off
# their own scales, so a typo fails at import rather than printing wrong.
# The third is an index, since the layout decides what sits there: 0 is
# the first mark, full power or 1 m.
ALIGN_GN = "32"
ALIGN_ISO = "400"
ALIGN_THIRD = 0

ALIGN = {
    "gn": GUIDE_NUMBERS.index(ALIGN_GN),
    "iso": ISOS.index(ALIGN_ISO),
    "third": ALIGN_THIRD,
}

# The table has to move with them, by the sum of what the three settings
# moved, or the slot would show the wrong cell.
TABLE_PHASE = ALIGN["third"] - ALIGN["gn"] - ALIGN["iso"]


def reading(*, gn, iso, distance):
    """What the power window shows, as {aperture label: power label}.

    Apertures whose required power falls off the printed scale are
    omitted, matching the blank slots the ring actually shows.
    """
    out = {}
    for a, ap_label in enumerate(APERTURES):
        p = power_index(gn=gn, iso=iso, aperture=a, distance=distance)
        if 0 <= p < len(POWERS):
            out[ap_label] = POWERS[p]
    return out


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

# Every label is the standard photographic rounding of a power of sqrt(2).
# The coarsest is 11 for 11.31, about 0.08 stops. Allow a shade over that.
LABEL_TOLERANCE_STOPS = 0.09


def _exact(scale_index, origin):
    """Exact value of a scale position, in sqrt(2) steps from the origin."""
    return 2.0 ** ((scale_index + origin) / 2.0)


def check():
    """Verify the printed scales against the underlying photometry.

    Two independent claims are checked. First, that every printed label
    is an honest rounding of its exact position on the sqrt(2) ladder.
    Second, that `power_index` reproduces the flash equation exactly at
    those exact positions -- so any residual error a user sees is label
    rounding, never arithmetic.

    Raises AssertionError on any disagreement. Returns the number of
    in-range combinations checked.
    """
    # 1. Labels are honest roundings of their exact ladder positions.
    for name, labels, origin in (
        ("aperture", APERTURES, APERTURE_ORIGIN),
        ("distance", DISTANCES_M, DISTANCE_ORIGIN),
        ("guide number", GUIDE_NUMBERS, GUIDE_NUMBER_ORIGIN),
    ):
        for k, label in enumerate(labels):
            err = 2.0 * abs(log2(float(label) / _exact(k, origin)))
            assert err < LABEL_TOLERANCE_STOPS, (
                f"{name} label {label} is {err:.3f} stops from its detent"
            )

    # ISO and power labels are exact powers of two, so they must match.
    for k, label in enumerate(ISOS):
        assert float(label) == 100.0 * 2.0 ** (k + ISO_ORIGIN), label
    for k, label in enumerate(POWERS):
        assert float(label.split("/")[1]) == 2.0 ** k, label

    # Feet labels must describe the same detents as the metre labels.
    assert len(DISTANCES_FT) == len(DISTANCES_M)
    for m_label, ft_label in zip(DISTANCES_M, DISTANCES_FT):
        err = 2.0 * abs(log2(float(ft_label) / (float(m_label) * 3.28084)))
        assert err < LABEL_TOLERANCE_STOPS, (
            f"{m_label} m mislabelled as {ft_label} ft ({err:.3f} stops)"
        )

    # 2. The index arithmetic reproduces the flash equation exactly.
    checked = 0
    for g in range(len(GUIDE_NUMBERS)):
        gn_m = _exact(g, GUIDE_NUMBER_ORIGIN)
        for i in range(len(ISOS)):
            iso = 100.0 * 2.0 ** (i + ISO_ORIGIN)
            for d in range(len(DISTANCES_M)):
                dist_m = _exact(d, DISTANCE_ORIGIN)
                for a in range(len(APERTURES)):
                    f_number = _exact(a, APERTURE_ORIGIN)
                    p = power_index(gn=g, iso=i, aperture=a, distance=d)
                    if not 0 <= p < len(POWERS):
                        continue

                    # The flash's guide number at this ISO and power,
                    # divided by the distance, is the aperture that
                    # exposes correctly.
                    gn_at_iso = gn_m * (iso / 100.0) ** 0.5
                    gn_at_power = gn_at_iso * (2.0 ** -p) ** 0.5
                    ideal_f = gn_at_power / dist_m

                    err_stops = 2.0 * abs(log2(ideal_f / f_number))
                    assert err_stops < 1e-9, (
                        f"g={g} i={i} d={d} a={a} -> p={p}: off by "
                        f"{err_stops:.6f} stops"
                    )
                    checked += 1

    # A reading off the original paper prototype: a GN 38 flash at ISO 100
    # and 6.7 m showed full power at f/5.6. These scales quantise that to
    # GN 32 at 5.6 m, which must still land on f/5.6 at full power.
    shown = reading(
        gn=GUIDE_NUMBERS.index("32"),
        iso=ISOS.index("100"),
        distance=DISTANCES_M.index("5.6"),
    )
    assert shown["5.6"] == "1/1", f"reference reading gave {shown}"

    # Scales must fit in the available detents, with room left blank.
    for name, scale in (
        ("apertures", APERTURES), ("distances", DISTANCES_M),
        ("ISOs", ISOS), ("powers", POWERS), ("guide numbers", GUIDE_NUMBERS),
    ):
        assert len(scale) <= DETENTS, f"{name} needs more than {DETENTS} detents"

    return checked


# ---------------------------------------------------------------------------
# Layouts
# ---------------------------------------------------------------------------
#
# Which quantity is set at which interface is a free choice. Only two of
# the five are pinned: the guide number is set first because it changes
# per flash, and the film speed second because it changes per roll. The
# remaining three split into one more setting, the quantity indexed along
# the axis, and the quantity read out.
#
# Everything below is derived from one relation, so a layout is described
# by naming its parts rather than by re-deriving any angles:
#
#     sum over quantities of  coeff * (index + origin)  =  0
#
# Writing the relation this way makes both layouts fall out of the same
# arithmetic. `coeff` is +1 for the quantities that add exposure need and
# -1 for those that supply it.

_COEFF = {"aperture": +1, "distance": +1, "power": +1, "iso": -1, "gn": -1}
_ORIGIN = {
    "aperture": APERTURE_ORIGIN, "distance": DISTANCE_ORIGIN,
    "power": POWER_ORIGIN, "iso": ISO_ORIGIN, "gn": GUIDE_NUMBER_ORIGIN,
}
_LABELS = {
    "aperture": APERTURES, "distance": DISTANCES_M, "power": POWERS,
    "iso": ISOS, "gn": GUIDE_NUMBERS,
}

# What gets engraved, where that differs from the canonical label.
_MARKS = dict(_LABELS, power=POWER_MARKS)

UNIT_MARK = {"meters": "m", "feet": "ft"}


def window_legend(quantity, units="meters"):
    """What is engraved either side of a window showing `quantity`.

    Returns (before, after). The three read as one line around the
    barrel, with the value in the window between them: GN 32 m, or
    1/ 4 for a quarter power. The mark inside a window is bare, so the
    line either side of it has to carry both the name and the unit.
    """
    if quantity == "power":
        return "1/", ""             # reads 1/4; the value is the divisor
    if quantity == "distance":
        return "DIST", UNIT_MARK[units]
    if quantity == "gn":
        return "GN", "m"            # guide numbers are quoted in metres
    return "ISO", ""


class Layout:
    """One assignment of quantities to the instrument's four interfaces.

    `third` is the setting made at the outermost moving joint; `column`
    is indexed along the axis, one column per value; `value` is what the
    window shows. The guide number and film speed are always the first
    two settings.
    """

    def __init__(self, name, third, column, value, heading):
        self.name = name
        self.third = third
        self.column = column
        self.value = value
        self.heading = heading      # engraved beside the column marks
        # Which distance scale the slot is labelled in. The two are the
        # same detents relabelled, so this changes no geometry. Set once
        # from the command line, in `dims`.
        self.units = "meters"

        cv, cc = _COEFF[value], _COEFF[column]
        # Sign of each setting scale, so the three relative rotations
        # compose into the relation above.
        self.gn_sign = -cv * _COEFF["gn"]
        self.iso_sign = -cv * _COEFF["iso"]
        self.third_sign = -cv * _COEFF[third]
        self.column_sign = cv * cc
        self.constant = (
            cv * cc * _ORIGIN[column]
            + cv * sum(_COEFF[q] * _ORIGIN[q] for q in ("gn", "iso", third))
            + _ORIGIN[value]
        )

    @property
    def third_labels(self):
        return _LABELS[self.third]

    @property
    def column_labels(self):
        return _LABELS[self.column]

    @property
    def legend(self):
        """Engraved beside the slot."""
        return window_legend(self.value, self.units)

    @property
    def value_labels(self):
        if self.value == "distance" and self.units == "feet":
            return DISTANCES_FT
        return _LABELS[self.value]

    @property
    def value_marks(self):
        """What is engraved in the table, which may be shorter."""
        if self.value == "distance" and self.units == "feet":
            return DISTANCES_FT
        return _MARKS[self.value]

    @property
    def third_marks(self):
        return _MARKS[self.third]

    def setting_angle(self, which, index):
        sign = {"gn": self.gn_sign, "iso": self.iso_sign,
                "third": self.third_sign}[which]
        return sign * (index - ALIGN[which]) * DETENT_ANGLE

    def table_angle(self, value_index, column_index):
        """Where a table entry is engraved on the dist ring's spigot.

        Negated because the readout pair is the other way round from the
        settings: the table rides the outermost moving segment and the
        window sits on the end cap, which is keyed to the inner tube.
        """
        return -(value_index
                 + self.column_sign * column_index
                 + self.constant
                 + TABLE_PHASE) * DETENT_ANGLE

    def readout(self, *, gn, iso, third, column):
        """Index of the value shown in `column`, or None if off scale."""
        cv = _COEFF[self.value]
        total = (
            _COEFF["gn"] * (gn + _ORIGIN["gn"])
            + _COEFF["iso"] * (iso + _ORIGIN["iso"])
            + _COEFF[self.third] * (third + _ORIGIN[self.third])
            + _COEFF[self.column] * (column + _ORIGIN[self.column])
        )
        v = -cv * total - _ORIGIN[self.value]
        return v if 0 <= v < len(self.value_labels) else None

    def rotations(self, *, gn, iso, third):
        """World rotations of inner, gn ring, iso ring, dist ring."""
        inner = 0.0
        gn_ring = inner + self.setting_angle("gn", gn)
        iso_ring = gn_ring + self.setting_angle("iso", iso)
        dist_ring = iso_ring + self.setting_angle("third", third)
        return inner, gn_ring, iso_ring, dist_ring


# Power needed at each aperture. The original paper prototype's layout.
POWER_LAYOUT = Layout(
    "power", third="distance", column="aperture", value="power",
    heading="f/",
)

# Working distance at each aperture. Distance is what changes shot to
# shot, so seeing every distance at once without turning anything is
# worth more than seeing every power setting at once.
#
# Aperture stays the static heading in both layouts, and only distance
# and power trade places. That keeps the two variants as close as they
# can be: the aperture marks are engraved in the same place on the same
# piece either way, so only two of the five printed parts differ.
DISTANCE_LAYOUT = Layout(
    "distance", third="power", column="aperture", value="distance",
    heading="f/",
)

LAYOUTS = {l.name: l for l in (POWER_LAYOUT, DISTANCE_LAYOUT)}


def check_layouts():
    """Both layouts must reproduce the flash equation exactly."""
    for layout in LAYOUTS.values():
        n = 0
        for g in range(len(GUIDE_NUMBERS)):
            for i in range(len(ISOS)):
                for t in range(len(_LABELS[layout.third])):
                    for c in range(len(layout.column_labels)):
                        v = layout.readout(gn=g, iso=i, third=t, column=c)
                        if v is None:
                            continue
                        vals = {"gn": g, "iso": i, layout.third: t,
                                layout.column: c, layout.value: v}
                        total = sum(_COEFF[q] * (vals[q] + _ORIGIN[q])
                                    for q in _COEFF)
                        assert total == 0, (f"{layout.name}: {vals} "
                                            f"leaves {total}")
                        n += 1
        assert n > 100, f"{layout.name} produced only {n} readings"

    # The power layout must agree with the standalone functions it
    # replaces, so the generalisation cannot drift from the original.
    for g in range(len(GUIDE_NUMBERS)):
        for i in range(len(ISOS)):
            for d in range(len(DISTANCES_M)):
                for a in range(len(APERTURES)):
                    want = power_index(gn=g, iso=i, aperture=a, distance=d)
                    got = POWER_LAYOUT.readout(gn=g, iso=i, third=d, column=a)
                    if 0 <= want < len(POWERS):
                        assert got == want, (g, i, d, a, want, got)
                    else:
                        assert got is None, (g, i, d, a, want, got)
    return True


if __name__ == "__main__":
    n = check()
    check_layouts()
    print(f"{n} in-range combinations verified against photometry")
    print(f"layouts: {', '.join(LAYOUTS)} both reproduce it exactly")
    print(f"detents={DETENTS}  offset={OFFSET}")
    print()
    print("GN 32, ISO 100, 5.6 m:")
    for ap, pw in reading(gn=5, iso=2, distance=5).items():
        print(f"  f/{ap:<4} {pw}")
