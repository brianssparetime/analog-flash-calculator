"""Every measurement the segments share, in one place.

Outer shape
-----------
One clean cylinder at `outer_od` along the whole length. Each segment is
a full-diameter *sleeve* over the band it reads, and a reduced-diameter
*spigot* over the band it is read through. Material is built up where a
segment sits on the outside and thinned where it runs underneath, so the
radius from the axis to the outside never changes:

    band A   GN       inner spigot   |  gn ring sleeve
    band B   ISO      gn spigot      |  iso ring sleeve
    band C   DIST     iso spigot     |  dist ring sleeve
    band D   POWER    dist spigot    |  end cap sleeve

Only two diameters exist, so every window reads through one wall and the
stack is never more than two layers deep at any reading.

Why there is an end cap
-----------------------
The readout pairs the outermost moving segment with the innermost, and
those sit at opposite ends. So the inner tube must be built up at band A
*and* be read at band D, while running through the middle thinner than
every spigot bore in between. Nothing with a spigot bore can thread past
that dumbbell from either end.

Splitting the inner tube's far end into a separate cap resolves it, and
the cap earns its keep: it takes the nut, houses the spring, and closes
the readout end. Everything then threads on from the right, in order.

Detents
-------
A spigot's end face meets the next segment's sleeve floor, an annulus at
`detent_r`, well inboard of the outside. That is as far toward the axis
as two nested segments can meet: only the inner tube reaches the bolt, so
any face shared by two concentric segments sits at the nesting radius.

Sleeves never touch each other. Consecutive sleeve ends are held apart by
`seam_gap`, which is wider than a bump is tall, so the detent faces are
the only place the stack can bottom out and a bump can always lift clear.

Force path
----------
Nut -> washer -> spring -> end cap -> dist ring -> iso ring -> gn ring ->
inner tube -> washer -> bolt head. One path, with the spring in series,
so a bump can climb out of its dimple without the assembly stretching.

The end cap slides on its key rather than seating against a shoulder, so
the inner tube cannot take the bolt load in parallel and leave the rings
loose. The washer is *wider* than the spring counterbore, so it spans the
recess and meets the spring standing `spring_proud` above the rim. The
rim then becomes a hard stop that bounds travel, tuned at the nut. A
spring sunk flush would let the washer bottom on that rim and bypass the
spring entirely, which is a silent failure: everything looks assembled
and nothing clicks.
"""

from scadwright import Spec, arg

from scales import DETENTS, LAYOUTS, UNIT_MARK

# Which quantity the long slot reads out. `distance` is the default: set
# an aperture and a power, and the slot shows how far the flash reaches at
# every aperture, which is the useful way round because distance is what
# changes shot to shot and this way every distance is visible without
# turning anything. `power` swaps the roles of distance and power, giving
# the original paper prototype: the power needed at every aperture.
LAYOUT = LAYOUTS[arg("readout", default="distance", type=str,
                     help="main readout: distance | power")]

# Which distance scale the slot is labelled in. The slot has room for one
# row per column, so it has to be chosen; the third ring, where distance
# is a setting rather than the answer, prints both rows and ignores this.
# Metres and feet mark the same detents, so nothing but the labels moves.
UNITS = arg("units", default="meters", type=str,
            help="distance units in the slot: meters | feet")
if UNITS not in UNIT_MARK:
    raise ValueError(f"units must be one of {sorted(UNIT_MARK)}, not {UNITS!r}")
LAYOUT.units = UNITS

# Counts, not measurements, so they stay out of the Spec: a `?`-typed int
# there would make every dimension instance-only to read.
#
# One divot per data slot, so the detents land exactly where the markings
# do. Three bumps rather than twelve: three engaging twelve still gives
# twelve stop positions, but they seat without fighting each other when
# print tolerance makes the features slightly unequal.
DETENT_BUMPS = 3
DETENT_DIVOTS = DETENTS


class Dims(Spec):
    equations = f"""
        # --- radial -------------------------------------------------------
        bolt_d = 6.8                    # 1/4 in (6.35) plus clearance
        inner_od = 16                   # the tube that runs the whole length
        slip = 0.4                      # diametral clearance, rotating fits

        spigot_wall = 3.2
        sleeve_wall = 3.4
        spigot_bore = inner_od + slip
        spigot_od = spigot_bore + 2 * spigot_wall
        sleeve_bore = spigot_od + slip
        outer_od = sleeve_bore + 2 * sleeve_wall

        inner_wall = (inner_od - bolt_d) / 2
        min_wall = sleeve_wall - engrave    # left under an engraving

        # Where a spigot end meets the next sleeve floor.
        detent_r = (spigot_bore + spigot_od) / 4

        # --- axial --------------------------------------------------------
        gn_band = 12
        iso_band = 14
        dist_band = 20                  # two rows: metres and feet
        power_col = 6                   # one aperture column
        power_margin = 3                # keeps the end labels off the slot ends
        power_band = power_col * {len(LAYOUT.column_labels)} + 2 * power_margin

        seam_gap = 1.0                  # sleeves never touch; > bump_proud
        tip_gap = 0.5                   # non-detent faces stay apart

        gn_z0 = 0
        iso_z0 = gn_z0 + gn_band
        dist_z0 = iso_z0 + iso_band
        power_z0 = dist_z0 + dist_band
        power_z1 = power_z0 + power_band

        # --- end cap ------------------------------------------------------
        key_len = 8                     # engagement on the inner tube
        cap_web_t = 3                   # closes the sleeve in to the hub
        # Both washers are wider than anything in the stack, so each
        # caps its end rather than dropping into it. The spring stands
        # proud of its recess by one bump height plus clearance, so the
        # nut washer meets the spring first and the cap's rim becomes a
        # hard stop: total axial travel is bounded, and tuned at the nut.
        washer_od = 32
        spring_bore = 20
        spring_depth = 8                # recess in the cap's end face
        spring_proud = bump_proud + 0.3 # stand-off at rest
        cap_seat_t = 3                  # solid floor the spring pushes on

        # The inner tube stops here, and the cap's seat is a solid floor
        # above it with only a bolt hole through. The tube therefore
        # cannot reach the spring: if it could, the spring would push it
        # back to the head washer and the rings would never be loaded.
        inner_end_z = power_z1 + cap_web_t + key_len
        spring_seat_z = inner_end_z + tip_gap + cap_seat_t
        overall_len = spring_seat_z + spring_depth

        # --- windows ------------------------------------------------------
        window_arc = 19                 # degrees; see check_windows_frame_labels
        window_margin = 2               # axial gap to the band's ends

        # --- detents ------------------------------------------------------
        bump_sphere_r = 1.0
        bump_proud = 0.5
        divot_sphere_r = 1.1
        divot_deep = 0.6

        # --- key ----------------------------------------------------------
        # A single rib, so the cap can only seat one way round. A hex or a
        # spline proper would allow several, each a whole detent out.
        key_w = 3
        key_h = 2
        key_slip = 0.3

        # --- text ---------------------------------------------------------
        engrave = 0.45
        scale_font = 3.2
        dist_font = 2.9
        power_font = 2.4
        legend_font = 2.8

        # --- rules --------------------------------------------------------
        bolt_d, inner_od, slip, tip_gap, seam_gap > 0
        min_wall >= 2.0                 # printable under an engraving
        spigot_wall - engrave >= 2.0
        inner_wall >= 2.0
        spigot_bore > inner_od          # running fits, not interference
        sleeve_bore > spigot_od
        seam_gap > bump_proud           # sleeves cannot bottom out first
        window_arc < {360.0 / DETENTS}  # one slot at a time
        power_margin, window_margin, key_len, cap_web_t > 0
        divot_sphere_r + detent_r < spigot_od / 2
        detent_r - divot_sphere_r > spigot_bore / 2
        # Off the rim entirely: the detents live inside the spigot, so
        # they sit under the outer wall rather than on the seam.
        detent_r < outer_od / 2 - sleeve_wall
        # The rules that matter for the spring actually doing anything.
        # A washer narrower than the stack drops onto a rim and bypasses
        # the spring: the assembly then looks right and nothing clicks.
        washer_od > outer_od            # caps the end, never enters it
        spring_proud > bump_proud       # a bump can lift before the cap
        spring_bore > bolt_d
        spring_bore < outer_od - 2 * sleeve_wall   # cap keeps its wall
        spring_depth > 2 * bump_proud   # room to climb out of a detent
        spring_seat_z - inner_end_z > tip_gap   # tube clear of the seat
        cap_seat_t >= 2                 # the seat is a real floor
    """


if __name__ == "__main__":
    d = Dims
    print(f"overall length   {d.overall_len:.1f} mm   OD {d.outer_od:.1f} mm "
          f"(constant)")
    print(f"walls            sleeve {d.sleeve_wall:.1f}, spigot "
          f"{d.spigot_wall:.1f}, inner {d.inner_wall:.1f} mm")
    print(f"  under engraving{d.min_wall:>7.2f} mm")
    print(f"radial clearance {d.slip / 2:.2f} mm per side")
    print()
    print(f"detents at r     {d.detent_r:.2f} mm, in a body of "
          f"r {d.outer_od / 2:.2f} "
          f"({100 * d.detent_r / (d.outer_od / 2):.0f}% out from the axis)")
    print(f"scale surface    r {d.spigot_od / 2:.2f} mm")
