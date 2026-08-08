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
the cap earns its keep: it takes the nut, houses the springs, and closes
the readout end. Everything then threads on from the right, in order.

Detents
-------
A spigot's end face meets the next segment's sleeve floor, an annulus at
`detent_r`, well inboard of the outside. That is as far toward the axis
as two nested segments can meet: only the inner tube reaches the bolt, so
any face shared by two concentric segments sits at the nesting radius.

That floor is also what holds a segment together. A sleeve rides the
spigot beneath it and so has to bore wider than it, which leaves a
segment's own sleeve and its own spigot `slip` apart with no length in
common. The floor is the annulus that joins the two, and it costs the
band it reads `floor_t`.

Sleeves never touch each other. Consecutive sleeve ends are held apart by
`seam_gap`, which is wider than a bump is tall, so the detent faces are
the only place the stack can bottom out and a bump can always lift clear.

Force path
----------
Nut -> washer -> springs -> end cap -> dist ring -> iso ring -> gn ring ->
inner tube -> washer -> bolt head. One path, with the springs in series,
so a bump can climb out of its dimple without the assembly stretching.

The end cap slides on its key rather than seating against a shoulder, so
the inner tube cannot take the bolt load in parallel and leave the rings
loose. Three springs stand `spring_proud` above the cap's end face, so
the nut washer meets them before it meets the face, and the face becomes
a hard stop that bounds travel, tuned at the nut. Springs sunk flush
would let the washer bottom on the face and bypass them entirely, which
is a silent failure: everything looks assembled and nothing clicks.

The pockets sit on a circle outside the hub, so they run alongside the
key engagement rather than beyond it. That is worth ten millimetres of
length, and it also puts the springs at a radius the inner tube cannot
reach, which retires the failure a central spring has to be checked for.
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

        # The scale surface sets the size of the whole tool. Labels run
        # around the circumference, so each one has to fit inside the arc
        # of a single detent: at 12 detents that is pi * spigot_od / 12,
        # and the longest label on the instrument is ISO 1600. Solve the
        # spigot wall from the surface rather than the other way round.
        spigot_od = 36
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
        # A band only has to be as long as a glyph is tall, plus the
        # margin that keeps the label off the window's ends. The setting's
        # name and unit sit either side of the window on the same line,
        # not above or below it, so they cost arc rather than length.
        gn_band = 8
        iso_band = 8
        # Two rows when the third setting is distance, which is printed in
        # metres and feet together; one row, and a band the same height as
        # the two above it, when it is power.
        dist_band = {12 if LAYOUT.third == "distance" else 8}
        power_col = 3.8                 # one aperture column
        power_margin = 3                # keeps the end labels off the slot ends
        power_band = power_col * {len(LAYOUT.column_labels)} + 2 * power_margin

        seam_gap = 1.0                  # sleeves never touch; > bump_proud

        # A sleeve's bore and its own spigot's outside are `slip` apart and
        # share no length, so nothing joins them: without an annulus
        # bridging the two, a segment prints as two loose shells. The floor
        # fills the top of the sleeve's bore, and the spigot it reads
        # retreats by the same amount so the floor has somewhere to sit.
        # The floor's underside is then the detent face.
        #
        # It has to come out of the read band rather than sit above it:
        # above the band boundary is `seam_gap`, and the next sleeve starts
        # there. The end cap is the exception, and the reason it can be:
        # its floor grows upward into the tail, where nothing else is, so
        # band D's face stays on the boundary.
        floor_t = 1.5

        # What separates the inner tube's tip from the end cap's bore
        # ceiling, and the only place the stack's length error can go: four
        # segments' worth of layer quantisation accumulates here. If it
        # closes, the tube takes the bolt load in parallel and the springs
        # never compress -- the same silent no-click failure the washer is
        # guarded against below, reached from the other end.
        tip_gap = 2.0

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
        washer_od = 51                  # 2 in fender washer, 1/4 in bore

        # Small springs in their own pockets, on a circle outside the hub.
        # Sitting at a radius the hub does not use, they run alongside the
        # key engagement instead of beyond it, which is what keeps the tail
        # short.
        #
        # Three is enough once the springs are properly compressed. Each is
        # about 2.5 N/mm, so three at three millimetres of preload come to
        # 22 N at the stop, which is a firm click and about 0.24 Nm to turn
        # against. Six would be 45 N, where the drag on every sliding face
        # starts to outweigh the detent, and it would halve the number of
        # turns of the nut the useful range is spread over. Three points
        # also seat the washer without rocking. The circle holds fourteen
        # before `pocket_web` runs out, if a much firmer tool is wanted.
        spring_count = 3
        spring_od = 3.5                 # stock 3.5 x 0.5 wire x 10 free
        pocket_slip = 0.5
        pocket_dia = spring_od + pocket_slip
        pocket_r = (inner_od / 2 + key_h + key_slip / 2
                    + outer_od / 2 - sleeve_wall) / 2
        pocket_web = 2 * pi * pocket_r / spring_count - pocket_dia

        # How far the springs stand out of their pockets is the whole
        # adjustment range at the nut, so the pocket is cut well short of
        # the spring rather than a hair short. Three millimetres is about
        # two and a half turns of a 1/4-20 nut to play with, where one
        # millimetre would be under a turn from loose to hard against the
        # stop. It also has to exceed `bump_proud`, or a detent could not
        # lift at all once the washer is down.
        spring_free = 10                # 3.5 x 0.5 wire x 10 stock spring
        pocket_depth = 7
        spring_proud = spring_free - pocket_depth

        # The inner tube stops short of the cap's end face, which is solid
        # but for the bolt hole. The pockets sit outside the tube's radius
        # altogether, so unlike a central spring there is no way for the
        # tube to reach one and short-circuit the ring stack.
        end_t = 1.5                     # closes the cap over the tube's tip
        inner_end_z = power_z1 + cap_web_t + key_len
        overall_len = inner_end_z + tip_gap + end_t
        pocket_z0 = overall_len - pocket_depth

        # --- windows ------------------------------------------------------
        window_arc = 28                 # degrees; see check_windows_frame_labels
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
        scale_font = 2.7
        dist_font = 2.5
        power_font = 2.05
        legend_font = 2.4

        # --- rules --------------------------------------------------------
        bolt_d, inner_od, slip, tip_gap, seam_gap > 0
        min_wall >= 2.0                 # printable under an engraving
        spigot_wall - engrave >= 2.0
        inner_wall >= 2.0
        spigot_bore > inner_od          # running fits, not interference
        sleeve_bore > spigot_od
        seam_gap > bump_proud           # sleeves cannot bottom out first
        floor_t > divot_deep            # a divot cannot cut through it
        # The spigot being read stops `floor_t` short of the band, so this
        # is what keeps the scale surface covering the whole window.
        floor_t < window_margin
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
        pocket_dia > spring_od          # the spring drops in, not presses
        pocket_r + pocket_dia / 2 < outer_od / 2 - sleeve_wall   # keeps its wall
        pocket_r - pocket_dia / 2 > inner_od / 2 + key_h + key_slip / 2
        pocket_z0 > power_z1 + cap_web_t           # floor stays out of the slot
        pocket_web >= 2                 # printable web between the pockets
        spring_proud > 2 * bump_proud   # room to climb out of a detent
        overall_len - inner_end_z > tip_gap     # tube clear of the end
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
