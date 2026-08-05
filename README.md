# Analog flash calculator

A manual flash exposure calculator, printed as a stack of rotating rings
on a bolt. Dial in the flash's guide number, the film speed, and the
distance to the subject, then read the power setting needed at every
aperture from f/2 to f/22 at once.

It is an old exposure-calculator dial folded into a cylinder: the same
logarithmic slide rule, wrapped around an axis instead of laid out on a
disc. A paper prototype came first; this is the printed version of it,
with a fourth ring added so the guide number is a setting rather than
something baked into the scales.

122 x 30 mm. Five printed parts, one bolt, two washers, one spring.

## Using it

Three rings, set in order. Each has a window showing the value it is set
to, so nothing has to be remembered.

1. **GN** -- the flash's guide number, in metres at ISO 100 and 50 mm
   coverage. Read it off the flash's own table for the zoom setting you
   are using; do not derive it from the focal length.
2. **ISO** -- the film speed.
3. **DIST** -- the flash-to-subject distance, in metres and feet.

The long slot then shows the power needed under each aperture heading.
Blank means that aperture is off the scale at this setting: no power
setting exposes correctly there.

Worked example. A Metz Mecablitz 45 on ISO 400 film at four metres: set
GN 45, ISO 400, DIST 4. The slot reads 1/1 under f/22, 1/2 under f/16,
1/4 under f/11, and so on down to 1/128 under f/2. Checking by hand: the
guide number at ISO 400 is 45 x sqrt(4) = 90, and 90 / 4 m = f/22 at full
power. The rest follow a stop at a time.

To change a setting, just twist the two segments either side of the seam
against each other. The spring lets the bumps cam out of their dimples,
so nothing has to be pulled apart first; each segment further out rides
along with whichever of the two it sits on.

The windows do not stay in a row around the circumference: each rides on
the segment carrying it, and those have to turn relative to each other to
hold a setting. Roll the tool in your hand to bring each into view. The
paper original behaves the same way, and it costs little in use -- the
guide number is set once per flash, the film speed once per roll, and
only the distance ring moves between shots.

## Two readouts

The slot can show either of two things, chosen at build time:

```
scadwright build main.py                       # power needed at each aperture
scadwright build main.py --readout=distance    # distance reached at each aperture
```

Distance and power trade places; aperture stays put. Which one you want
depends on which side of depth of field you are solving for.

**Aperture over power** suits optimising depth of field at a fixed
distance. You are standing where you are standing, so set that distance
and the slot shows the power each aperture needs. Read across, pick the
aperture that gives the depth of field you want, and set the flash to the
power under it. Depth of field is the free variable; the flash absorbs
the difference.

**Aperture over distance** suits holding depth of field fixed across
changing distances. Set the aperture you need for the depth of field the
shot calls for, set the flash power, and the slot shows how far the flash
reaches at every aperture. Read off the distance under your aperture and
stand there. Depth of field is the constraint; distance is the free
variable.

The second is the more useful way round when distance is what changes
shot to shot, because every distance is visible at once without turning
anything.

Because only distance and power move, the two variants share most of
their parts. The inner tube and GN ring are identical; the end cap
differs only in the word engraved beside its slot. Printing two parts
converts one into the other.

## How it works

Every scale is logarithmic, and one detent of rotation is one stop on all
of them. That is what lets a single 30-degree pitch serve four different
quantities:

| quantity | one stop |
|---|---|
| aperture | x sqrt(2) |
| distance | x sqrt(2) |
| ISO | x 2 |
| power | / 2 |
| guide number | x sqrt(2) |

Guide number is defined as GN = aperture x distance at ISO 100 and full
power. Raising ISO a stop or cutting power a stop each move the effective
guide number by one stop, so the whole instrument reduces to one relation
in stops:

    aperture + distance + power - ISO = GN

Each pair of neighbouring segments contributes one term through its
window, and the four relative rotations sum to that identity. `scales.py`
states this and `check.py` proves it holds for all 2346 combinations the
printed scales can express.

### Why four segments

Every setting is one *relative* rotation between two segments, and the
readout is a fourth relative rotation closing the loop:

    inner --GN--> gn ring --ISO--> iso ring --DIST--> dist ring
          <------------------ POWER readout ------------------

Four links in a closed chain need four bodies. The paper original was the
three-body version of this -- ISO, distance, and the readout -- with the
guide number baked in as a constant. Making GN a setting is exactly what
adds the fourth.

The bolt cannot be one of them: it is the axis and the clamp, but the
inner segment carries two printed scales and has to hold an indexed
angular position. That inner segment is also the one that must span the
whole length, because the readout pairs the outermost segment with the
innermost, and in a concentric telescope those sit at opposite ends.

## Building the models

```
python3 -m venv .venv
.venv/bin/pip install -e ../SCADwright
.venv/bin/pip install "scadwright[curved-text]"     # proportional glyph spacing

.venv/bin/python check.py                            # verify before printing
.venv/bin/scadwright build main.py                   # print plate (default)
                                                     # writes into out/
.venv/bin/scadwright build main.py --variant=display
.venv/bin/scadwright build main.py --variant=exploded
.venv/bin/scadwright build main.py --variant=section
```

`check.py` is worth running after any change to a dimension. It measures
label extents off the real text geometry, so it catches an engraving that
has grown past its window or into the next aperture column -- neither of
which is visible in a render until you go looking. It also checks that
every segment can still be threaded onto the stack, which is the
constraint that decides the whole radial scheme.

## Pictures

```
python renders.py                    # every shot into rendered_img/
python renders.py hero power         # only shots matching these names
scadwright morph main.py assemble rendered_img/assembly.apng --frames=48
```

`renders.py` is the record of how each image was framed: every camera is
OpenSCAD's own seven-number gimbal form, so a shot can be reproduced or
nudged without hunting for the angle again. Distances are solved from the
subject width and the image size rather than hand-tuned, so reframing an
image does not silently crop the part.

The images use OpenSCAD's preview renderer, not a full CGAL render. A
single segment carries 248 extruded glyph solids and CGAL does not finish
on it in four minutes, with or without `force_render`. Preview takes three
seconds and looks the same at these sizes.

That choice has one visible consequence, and the shot list works with it
rather than against it. Preview fills the faces of a subtracted volume in
a contrasting colour. Seen straight down, that reads exactly like the
paint fill the finished part is meant to get, so the detail shots use it.
Seen at an angle it floods the inside of a window, making an opening look
solid, so the three-quarter shots switch to a scheme that colours every
face alike.

The pose in every image is GN 45, ISO 25, 1 m, which fills every aperture
column. Two straight-on shots cover the tool between them: `reading-line`
looks at the readout, `settings-line` at the three setting windows on the
opposite face. They have to be separate shots. Whenever the slot is full,
the setting windows land half a turn away from it, so no single view can
hold both.

## Printing

Every segment prints standing on its axis, as laid out by the print
variant. Bores stay round without support, the windows become vertical
slots needing only a short bridge at the top, and engraved text on a
vertical wall comes out crisp.

Which end goes down is set by the detents. A spherical dimple opening
downward loses about 0.13 mm of radius per 0.2 mm layer -- a 57 degree
overhang, which prints clean. A dome pointing downward does not. So every
segment is oriented bumps-up, which all four are as modelled.

Notes:

- The inner tube is a 16 mm column standing 111 mm tall. Use a brim.
- Thinnest wall is 3.4 mm, leaving 2.95 mm under an engraving beside a
  window.
- Running fits carry 0.2 mm of radial clearance. If your printer runs
  tight, raise `slip` in `dims.py` rather than sanding the segments.
- Engravings are 0.45 mm deep. A wipe of paint into them, or a filament
  change on the top surface, makes the scales far easier to read.

## Assembly

Parts, in order of assembly:

| part | what it does |
|---|---|
| `inner_segment` | GN scale at one end, power table at the other |
| `gn_ring` | GN window, ISO scale |
| `iso_ring` | ISO window, distance scale in metres and feet |
| `dist_ring` | distance window, power slot, aperture headings |

Hardware: one 1/4-20 bolt, 5 1/2 inches, **fully threaded** (a
part-threaded one has too long a plain shank for the nut to reach); one
nut; two 1/4
inch fender washers, 32 mm outside diameter; and one compression spring
about 16 mm across that seats in a 20 mm bore, stands a millimetre proud
of it, and compresses past that without going solid.

Both washers have to be wider than the 30 mm body. That is what makes
them cap the ends rather than drop into them, and it is what lets the
spring load the whole stack.

1. Thread `gn_ring`, then `iso_ring`, then `dist_ring` onto the inner
   segment from the right-hand end. Each slides over its plain outside
   and seats against the flange of the one before it.
2. Drop the spring into the cavity in the inner segment's left end face.
3. Bolt and ordinary washer through from the left, compressing the spring.
4. Fender washer and nut on the right. It has to be a fender washer: it
   bears on the dist ring's tail face, and an ordinary one would drop
   straight into the bore. Tighten until the segments click firmly but
   still turn by hand.

The spring is what makes it click, and it sits in series with the whole
stack, so a bump can lift out of its dimple without the assembly having
to stretch. Turning is just a twist -- the bumps cam out on their own,
nothing has to be pulled apart.

The inner tube runs the whole length, because one coupling always has to
reach end to end. Four bodies with four couplings cannot all be axially
adjacent, so exactly one spans the stack. The paper original does the
same thing: its inner sheet is the widest, and both outer sheets read it.

What that tube must not do is carry load. It is held between the head
washer and the GN ring's detent face, and past that it hangs free: its
far end stops short of the spring, whose seat is solid cap right across
the bore. If the tube could reach the spring, the spring would push it
straight back to the head washer and the ring stack would never be
loaded, which is a silent failure - the tool assembles and no detent
clicks.

Three interfaces join the four segments, so the two end segments carry
detent features on their one inward-facing side only. Their outward faces
are plain, because a washer does not turn with them.

## Scale ranges

- **Guide number** 5.6, 8, 11, 16, 22, 32, 45, 64 (metres, ISO 100, 50 mm)
- **ISO** 25 to 3200
- **Distance** 1 to 16 m (3.3 to 52 ft)
- **Aperture** f/2 to f/22
- **Power** 1/1 to 1/128

Guide numbers land on the same rounded sqrt(2) series as the apertures,
which means one-stop granularity: a GN 38 flash sits between the 32 and
45 marks. That is the price of a single detent pitch shared by every
scale, and it is within the margin by which published guide numbers are
optimistic anyway. Round down if you want the exposure.

Feet cannot land on round numbers when metres do, so the foot row is an
honest rounding of the same detents rather than a prettied-up second
series.

## Layout

```
scales.py   scale tables, stop arithmetic, photometric verification
dims.py     every shared measurement, as a Spec with its own rules
parts.py    the four printed segments
main.py     Design, variants, and the assembly morph
check.py    correctness and buildability checks
renders.py  beauty shots, and the camera settings that produce them
out/        generated .scad and .stl; not tracked
rendered_img/  published images; tracked
```
