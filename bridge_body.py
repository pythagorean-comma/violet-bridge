"""Bridge body: the decorated lower half, from the joint down to the feet.

This is the part the saddle arc docks onto. Its top edge *is* the joint
cylinder -- the same JOINT_R the arc's underside is cut to -- so the two meet on
an exact shared surface rather than on two numbers that happen to agree.

Built the way the part would be made: start from a blank whose top edge already
carries the arc, then take material out of it. Right now this file is only the
blank. The arch, feet, insert bosses and piercings each get added as their own
step, rendered and checked before the next one goes in -- the previous attempt
built all of them at once and two came out broken.

Everything is placed against edge_x() rather than by eye. The top edge pinches
in hard above y = 25.5, so anything sitting high has to sit near the centre.
"""

import math

import cadquery as cq

from common import (ARC_CENTRE, BLANK_THICKNESS, JOINT_HALF_ANGLE, JOINT_R,
                    SEAT_R, export_step_file, export_svg_preview, fixing_angles,
                    point_at)

# --- geometry, mm and degrees -------------------------------------------
# As wide as the arc's seat, not as wide as the joint: the arc is 101.17 across
# the top but only lands on 90.60 of it, and matching the seat lines the two
# parts up in plan. The 5.3 mm either side where the arc has ended but the
# blank has not becomes a shoulder falling away on the joint radius.
HALF_WIDTH = SEAT_R * math.cos(math.radians(90 - JOINT_HALF_ANGLE))

APEX_Y = ARC_CENTRE[1] + JOINT_R    # 53.232, the body's height on the centreline
CORNER_Y = ARC_CENTRE[1] + math.sqrt(JOINT_R**2 - HALF_WIDTH**2)  # arc meets side

ARCH_DEPTH = 10.0                   # radial, upper edge to lower
ARCH_R = JOINT_R - ARCH_DEPTH       # 50.0, concentric with the joint so the
                                    # band keeps the same depth all the way round
LEG_WIDTH = 25.0                    # square section: 25 across by the part's
                                    # own 25 mm thickness. Setting the outer
                                    # faces flush with the blank also leaves the
                                    # outer face 25.5 tall -- 25 x 25 whichever
                                    # two dimensions you meant.
LEG_INNER_X = HALF_WIDTH - LEG_WIDTH            # 25.585
SPRING_Y = ARC_CENTRE[1] + math.sqrt(ARCH_R**2 - LEG_INNER_X**2)  # arch springs

INSERT_D = 5.0                      # tapping drill for an M3 threaded insert
INSERT_DEPTH = 6.0                  # blind, leaving 4 mm of the arch below it
OVERCUT = 1.0                       # start cuts outside the surface so they
                                    # open cleanly instead of leaving
                                    # coincident faces

def edge_x(y):
    """The blank's half-width at height `y`.

    The boundary every later cut has to stay inside of. Assert against this
    *before* cutting -- a breakout then shows up in a print statement rather
    than as a mystery in the geometry.
    """
    if y >= APEX_Y:
        return 0.0
    reach = JOINT_R**2 - (y - ARC_CENTRE[1])**2
    return min(HALF_WIDTH, math.sqrt(reach)) if reach > 0 else 0.0

def top_y(x):
    """Height of the blank's top edge at `x`, for hanging features off the arc.

    Raises rather than returning 0.0 off the end of the blank: 0.0 is the
    baseline, so a silent one would read as a real answer.
    """
    if abs(x) > HALF_WIDTH + 1e-9:
        raise ValueError(f"x = {x} is outside the blank (half-width {HALF_WIDTH:.3f})")
    return ARC_CENTRE[1] + math.sqrt(JOINT_R**2 - min(abs(x), HALF_WIDTH)**2)

def blank():
    """The stock: a rectangle whose top edge is the joint cylinder.

    One closed wire, one extrude -- not a rectangle intersected with a disc.
    The arc is drawn through its apex rather than by radius because radiusArc
    takes its side from the sign of the radius and picks the wrong one quietly;
    three points cannot be ambiguous.
    """
    return (cq.Workplane("XY")
            .moveTo(-HALF_WIDTH, 0)
            .lineTo(HALF_WIDTH, 0)
            .lineTo(HALF_WIDTH, CORNER_Y)
            .threePointArc((0, APEX_Y), (-HALF_WIDTH, CORNER_Y))
            .close()
            .extrude(BLANK_THICKNESS))

def cut_arch(model):
    """Open the arch, leaving a leg either side.

    One cut, not three: everything between r = ARCH_R and the joint stays solid
    right across the width, and that band running unbroken into the legs is what
    makes it an arch rather than a lintel. The opening is a closed profile --
    two vertical leg faces joined over the top by the ARCH_R arc.

    Drawn through the apex rather than by radius, same as blank(): radiusArc
    takes its side from the sign of the radius and picks the wrong one quietly.
    """
    opening = (cq.Workplane("XY", origin=(0, 0, -OVERCUT))
               .moveTo(-LEG_INNER_X, -OVERCUT)
               .lineTo(LEG_INNER_X, -OVERCUT)
               .lineTo(LEG_INNER_X, SPRING_Y)
               .threePointArc((0, ARC_CENTRE[1] + ARCH_R), (-LEG_INNER_X, SPRING_Y))
               .close()
               .extrude(BLANK_THICKNESS + 2 * OVERCUT))
    return model.cut(opening)

def drill_insert_holes(model):
    """Blind radial holes for the threaded inserts the crown bolts into.

    On the same lanes the crown drills its clearance holes, taken from
    `fixing_angles()` in common.py so the two parts cannot drift apart. Cut as
    explicit cylinders because the axes are radial and face selectors do not
    work on the joint's curved surface.
    """
    tools = []
    for angle in fixing_angles():
        inward = cq.Vector(-math.cos(math.radians(angle)),
                           -math.sin(math.radians(angle)), 0)
        start = cq.Vector(*point_at(JOINT_R + OVERCUT, angle), BLANK_THICKNESS / 2)
        tools.append(cq.Solid.makeCylinder(
            INSERT_D / 2, INSERT_DEPTH + OVERCUT, start, inward))
    return model.cut(cq.Workplane("XY").newObject(tools))

def check_clearances():
    """Print what this step depends on, before anything is cut.

    A breakout is far easier to read here than in the geometry afterwards.
    """
    print("--- clearances, checked before cutting ---")
    print(f"arch band      r {ARCH_R:.1f} to {JOINT_R:.1f}  ({ARCH_DEPTH:.1f} mm deep)")
    print(f"legs           |x| {LEG_INNER_X:.3f} to {HALF_WIDTH:.3f}"
          f"  ({LEG_WIDTH:.3f} wide, {BLANK_THICKNESS:.1f} deep)")
    print(f"leg height     {SPRING_Y:.3f} inner face, {CORNER_Y:.3f} outer face")
    print(f"opening        {2 * LEG_INNER_X:.3f} wide x "
          f"{ARC_CENTRE[1] + ARCH_R:.3f} tall at the centreline")

    # the deepest point of a hole is its bottom rim, not its axis
    deepest = math.hypot(JOINT_R - INSERT_DEPTH, INSERT_D / 2)
    floor = deepest - ARCH_R
    print(f"insert holes   {INSERT_D:.1f} dia x {INSERT_DEPTH:.1f} deep; "
          f"deepest material at r = {deepest:.3f}, {floor:.3f} mm above the arch")
    assert floor > 2.0, f"only {floor:.2f} mm of arch left under the inserts"

    for angle in fixing_angles():
        x, y = point_at(JOINT_R, angle)
        assert abs(x) <= edge_x(y) + 1e-6, f"lane {angle} is off the top edge"
        print(f"   lane {angle:6.2f} deg enters at ({x:8.3f}, {y:7.3f})")

    assert LEG_INNER_X < HALF_WIDTH, "legs wider than the blank"
    assert SPRING_Y < APEX_Y, "arch springs above the body's apex"

def report(model):
    """Print the envelope, so the next step has a before/after to compare to."""
    bb = model.val().BoundingBox()
    print("--- result ---")
    print(f"solids       {len(model.solids().vals())}")
    print(f"bounding box {bb.xlen:.3f} x {bb.ylen:.3f} x {bb.zlen:.3f}")
    print(f"volume       {model.val().Volume():.0f} mm^3")
    print(f"apex         y = {APEX_Y:.3f}")
    print(f"arc meets side at (+-{HALF_WIDTH:.3f}, {CORNER_Y:.3f})")
    print("half-width by height:")
    for y in (0, 10, 20, 25.5, 32.576, 40, 45, 50):
        print(f"   y = {y:6.2f}   {edge_x(y):6.2f}")

check_clearances()

model = blank()
model = cut_arch(model)
model = drill_insert_holes(model)

report(model)
export_step_file(model, "bridge_body")
export_svg_preview(model, "bridge_body")
