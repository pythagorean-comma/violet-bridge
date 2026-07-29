"""Bridge body: the arch the saddle arc docks onto, and the legs under it.

A plain band on the joint cylinder -- ARCH_DEPTH deep radially, spanning exactly
the crown's own arc, with radial faces at each end that finish flush with the
crown's. Its outer surface *is* JOINT_R, the surface the crown's underside is cut
to, so the two meet on one shared cylinder rather than on two numbers that happen
to agree. The three blind holes take the threaded inserts the crown bolts into.

Two legs carry it down to the belly, each with a bore through it. They are placed
by BORE_DATUM rather than by an x: the datum is the position at which that bore
would have run 45 mm from the belly to the joint cylinder, and LEG_INSET then
moves them in from there to clear a threaded insert. The bore's own length
follows from where they ended up; it is no longer the 45.

Still open: how the Yamahiko adjusters mount in the legs, and decoration. Each
gets added, rendered and checked on its own; the first attempt built every feature
at once and two came out broken.
"""

import math

import cadquery as cq

from common import (ARC_CENTRE, BLANK_THICKNESS, BODY_CENTRE, JOINT_HALF_ANGLE,
                    JOINT_R, export_step_file, export_svg_preview,
                    fixing_angles, point_at)

# --- geometry, mm and degrees -------------------------------------------
ARCH_DEPTH = 10.0                   # radial, upper edge to lower
ARCH_R = JOINT_R - ARCH_DEPTH       # 50.0, concentric with the joint so the
                                    # band keeps the same depth all the way round
SPAN_START = BODY_CENTRE - JOINT_HALF_ANGLE     # 40.975, the crown's own extent
SPAN_END = BODY_CENTRE + JOINT_HALF_ANGLE       # 139.025

APEX_Y = ARC_CENTRE[1] + JOINT_R    # 53.232, the body's height on the centreline

BASE_Y = 0.0                        # the belly: the legs stand on the datum
LEG_WIDTH = 20.0                    # across; front to back they are the part's
                                    # own BLANK_THICKNESS, same as the arch
BORE_DATUM = 45.0                   # where the legs come from, not what the bore
                                    # measures: the x at which a bore up the
                                    # centreline would have run 45 mm from the
                                    # belly to the joint cylinder. The legs then
                                    # move inboard from there.
LEG_INSET = 5.0                     # in from the datum, to clear the 48.906 deg
                                    # threaded insert -- at the datum itself the
                                    # bore opened into it by 0.723 mm
BORE_D = 8.0                        # through, opening on the joint cylinder
# The bore is vertical, so at the datum it breaks out at y = BASE_Y + BORE_DATUM,
# and the centreline is wherever that height meets the joint cylinder. LEG_INSET
# then moves it in.
LEG_CENTRE_X = math.sqrt(
    JOINT_R**2 - (BASE_Y + BORE_DATUM - ARC_CENTRE[1])**2) - LEG_INSET   # 25.333
LEG_INNER_X = LEG_CENTRE_X - LEG_WIDTH / 2      # 15.333
LEG_OUTER_X = LEG_CENTRE_X + LEG_WIDTH / 2      # 35.333

# The bore's real length, which follows from where the legs ended up rather than
# placing them. It is BORE_DATUM only when LEG_INSET is zero.
BORE_LENGTH = ARC_CENTRE[1] + math.sqrt(JOINT_R**2 - LEG_CENTRE_X**2) - BASE_Y

INSERT_D = 5.0                      # tapping drill for an M3 threaded insert
INSERT_DEPTH = 6.0                  # blind, leaving 4 mm of the band below it
OVERCUT = 1.0                       # start cuts outside the surface so they
                                    # open cleanly instead of leaving
                                    # coincident faces

def arch():
    """The band: two concentric arcs closed by a radial face at each end.

    One closed wire, one extrude -- not a ring intersected with a wedge. Both
    arcs are drawn through their apex rather than by radius because radiusArc
    takes its side from the sign of the radius and picks the wrong one quietly;
    three points cannot be ambiguous.
    """
    return (cq.Workplane("XY")
            .moveTo(*point_at(JOINT_R, SPAN_START))
            .threePointArc((0, APEX_Y), point_at(JOINT_R, SPAN_END))
            .lineTo(*point_at(ARCH_R, SPAN_END))
            .threePointArc((0, ARC_CENTRE[1] + ARCH_R),
                           point_at(ARCH_R, SPAN_START))
            .close()
            .extrude(BLANK_THICKNESS))

def joint_angle_at(x):
    """The angle at which the vertical line `x` crosses the joint cylinder."""
    return math.degrees(math.acos(x / JOINT_R))

def legs():
    """The two legs, standing on the belly and running up into the band.

    One closed wire each, both extruded together: disjoint co-planar wires are
    read as separate profiles, and it is only *overlapping* ones CadQuery
    mis-reads as nested. Each is a rectangle whose top edge is cut away on the
    joint cylinder, so the leg stops exactly where the part does.

    That top edge rides JOINT_R rather than the band's inner surface, which means
    each leg overlaps the band it hangs from. Deliberate: the union then merges
    them into one solid instead of butting two faces together. The arc's third
    point is taken on the cylinder itself -- unambiguous, where radiusArc would
    take its side from the sign of the radius and pick quietly.
    """
    wires = cq.Workplane("XY")
    for side in (-1, 1):
        inner, outer = side * LEG_INNER_X, side * LEG_OUTER_X
        mid = (joint_angle_at(inner) + joint_angle_at(outer)) / 2
        wires = (wires
                 .moveTo(inner, BASE_Y)
                 .lineTo(outer, BASE_Y)
                 .lineTo(outer, ARC_CENTRE[1] + math.sqrt(JOINT_R**2 - outer**2))
                 .threePointArc(point_at(JOINT_R, mid),
                                (inner, ARC_CENTRE[1] + math.sqrt(JOINT_R**2 - inner**2)))
                 .close())
    return wires.extrude(BLANK_THICKNESS)

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

def drill_leg_bores(model):
    """The through bore up each leg, opening on the joint cylinder.

    Explicit cylinders in one cut, same as drill_insert_holes(): the axis is +Y,
    which no face selector on this part would give. Started below the belly and
    run past the apex so both ends open cleanly -- the apex is the highest the
    joint cylinder gets, so it clears the breakout at any x.
    """
    tools = []
    for side in (-1, 1):
        start = cq.Vector(side * LEG_CENTRE_X, BASE_Y - OVERCUT, BLANK_THICKNESS / 2)
        tools.append(cq.Solid.makeCylinder(
            BORE_D / 2, APEX_Y - BASE_Y + 2 * OVERCUT, start, cq.Vector(0, 1, 0)))
    return model.cut(cq.Workplane("XY").newObject(tools))

def insert_x_span(angle):
    """How far the insert void on `angle` reaches in x, mirrored to the +x leg.

    Its four extremes are the corners of the flat-bottomed cylinder: each end of
    the axis, offset by the hole's radius perpendicular to it. The out-of-plane
    offset does not move x.
    """
    a = math.radians(angle if angle < BODY_CENTRE else 180 - angle)
    xs = [radius * math.cos(a) + side * (INSERT_D / 2) * math.sin(a)
          for radius in (JOINT_R, JOINT_R - INSERT_DEPTH) for side in (-1, 1)]
    return min(xs), max(xs)

def insert_wall(angle):
    """Material between a leg bore and the insert on `angle`.

    Both features are centred on the same z and the bore is vertical, so the
    distance between them is measured in x alone -- and x alone settles it: the
    bore runs the full height of the part, so any insert void overlapping it in x
    necessarily meets it. A void is a hole in material, and material at a given x
    stops at the joint cylinder, which is exactly where the bore breaks out.

    Negative means they intersect.
    """
    lo, hi = insert_x_span(angle)
    gap = 0.0 if lo <= LEG_CENTRE_X <= hi else min(abs(LEG_CENTRE_X - lo),
                                                   abs(LEG_CENTRE_X - hi))
    return gap - BORE_D / 2

def check_clearances():
    """Print what this step depends on, before anything is cut.

    A breakout is far easier to read here than in the geometry afterwards. The
    band has only two ways to fail: a hole too near an end face, or a hole
    through the inner face.
    """
    assert ARCH_DEPTH < JOINT_R and ARCH_R > 0, "arch deeper than the joint radius"

    print("--- clearances, checked before cutting ---")
    print(f"band           r {ARCH_R:.1f} to {JOINT_R:.1f}  ({ARCH_DEPTH:.1f} mm deep)")
    print(f"span           {SPAN_START:.3f} to {SPAN_END:.3f} deg about the arc centre")
    print(f"width          {2 * JOINT_R * math.cos(math.radians(SPAN_START)):.3f}"
          f" at the joint, apex y = {APEX_Y:.3f}")

    # The bore runs up the leg to the band's inner surface, then through the
    # band's own chord on the same vertical. Checking the two sum to BORE_LENGTH
    # catches ARCH_R or JOINT_R drifting apart; it is not a check on the length
    # itself, which is derived from where the legs ended up.
    leg_height = ARC_CENTRE[1] + math.sqrt(ARCH_R**2 - LEG_CENTRE_X**2) - BASE_Y
    band_chord = (ARC_CENTRE[1] + math.sqrt(JOINT_R**2 - LEG_CENTRE_X**2)
                  - (ARC_CENTRE[1] + math.sqrt(ARCH_R**2 - LEG_CENTRE_X**2)))
    print(f"legs           |x| {LEG_INNER_X:.3f} to {LEG_OUTER_X:.3f}"
          f"  ({LEG_WIDTH:.3f} wide, {BLANK_THICKNESS:.1f} deep)")
    print(f"bore           {leg_height:.3f} through the leg + {band_chord:.3f} "
          f"through the band = {leg_height + band_chord:.3f}"
          f"   (datum was {BORE_DATUM:.3f}, inset {LEG_INSET:.1f})")
    assert abs(leg_height + band_chord - BORE_LENGTH) < 1e-9, \
        "the bore's two parts do not add up to its length"
    assert LEG_INNER_X > 0, "the legs meet on the centreline"

    # Only part of a leg's width lands on the band's inner surface; beyond the
    # inner corner it merges into the band's end region instead, which leaves the
    # arch's ends projecting outboard of the legs as shoulders.
    inner_corner_x = ARCH_R * math.cos(math.radians(SPAN_START))
    outer_corner_x = JOINT_R * math.cos(math.radians(SPAN_START))
    assert LEG_OUTER_X < outer_corner_x, "the legs stand outside the arch in plan"
    print(f"leg junction   {min(LEG_OUTER_X, inner_corner_x) - LEG_INNER_X:.3f} of "
          f"{LEG_WIDTH:.3f} lands on the inner surface"
          f" (inner corner at x = {inner_corner_x:.3f})")
    print(f"shoulders      the arch ends project {outer_corner_x - LEG_OUTER_X:.3f} mm"
          f" outboard of each leg")

    # the deepest point of a hole is its bottom rim, not its axis
    deepest = math.hypot(JOINT_R - INSERT_DEPTH, INSERT_D / 2)
    print(f"insert holes   {INSERT_D:.1f} dia x {INSERT_DEPTH:.1f} deep; "
          f"deepest material at r = {deepest:.3f}, "
          f"{deepest - ARCH_R:.3f} mm above the inner face")
    assert deepest > ARCH_R, "inserts break out of the band's inner face"

    for angle in fixing_angles():
        x, y = point_at(JOINT_R, angle)
        # perpendicular distance from the hole's axis to the nearer end face,
        # which is a radial plane: r * sin of the angle between them
        gap = JOINT_R * math.sin(math.radians(
            min(angle - SPAN_START, SPAN_END - angle)))
        over = "leg " if LEG_INNER_X <= abs(x) <= LEG_OUTER_X else "band"
        print(f"   lane {angle:7.3f} deg enters at ({x:8.3f}, {y:7.3f}) over the "
              f"{over}, {gap - INSERT_D / 2:6.3f} mm of band beside it to the end face")
        assert gap > INSERT_D / 2, f"lane {angle} breaks out of an end face"

    # The outer lanes -- first and last, the middle one sits between them -- were
    # once moved outboard so the crown would clamp onto the legs rather than onto
    # the arch. Insetting the legs to clear the bore gave that up: they now clamp
    # on the overhang, which Tim accepted deliberately. So this reports the load
    # path rather than asserting it -- the assertion was not left to rot, it was
    # retired when the design decided against it.
    rim = math.degrees(math.asin((INSERT_D / 2) / JOINT_R))
    lanes = fixing_angles()
    for angle in (lanes[0], lanes[-1]):
        edges = sorted(abs(JOINT_R * math.cos(math.radians(angle + side * rim)))
                       for side in (-1, 1))
        over = min(edges[1], LEG_OUTER_X) - max(edges[0], LEG_INNER_X)
        where = (f"{over:.3f} mm of its {edges[1] - edges[0]:.3f} mm opening bears"
                 " on the leg" if over > 0 else
                 f"clamps on the overhang, {edges[0] - LEG_OUTER_X:.3f} to "
                 f"{edges[1] - LEG_OUTER_X:.3f} mm outboard of the leg")
        print(f"   lane {angle:7.3f} deg: {where}")

    print(f"leg bores      {BORE_D:.1f} dia through, {BORE_LENGTH:.3f} mm on the axis;"
          f" breaks out from {ARC_CENTRE[1] + math.sqrt(JOINT_R**2 - (LEG_CENTRE_X + BORE_D / 2)**2):.3f}"
          f" to {ARC_CENTRE[1] + math.sqrt(JOINT_R**2 - (LEG_CENTRE_X - BORE_D / 2)**2):.3f}")
    for angle in fixing_angles():
        wall = insert_wall(angle)
        lo, hi = insert_x_span(angle)
        mark = "  <-- CLASH" if wall < 0 else ""
        print(f"   lane {angle:7.3f} deg: insert reaches x {lo:7.3f} to {hi:7.3f}, "
              f"wall to the bore {wall:+.3f} mm{mark}")
    warn_if_clashing()

def clashing_lanes():
    """Fixing lanes whose insert opens into a leg bore. Empty is the good case."""
    return [(angle, insert_wall(angle)) for angle in fixing_angles()
            if insert_wall(angle) < 0]

def warn_if_clashing():
    """Say plainly that the part cannot be made, if that is where it stands.

    Deliberately not an assert. Tim asked for the Ø8 bore knowing it runs into an
    insert, so the build has to complete -- but it must not complete quietly.
    """
    clashes = clashing_lanes()
    if not clashes:
        return
    print()
    print("*" * 72)
    print("*** NOT FIT TO MAKE: a leg bore opens into a threaded insert")
    for angle, wall in clashes:
        print(f"***   lane {angle:.3f} deg overlaps the {BORE_D:.1f} dia bore "
              f"by {-wall:.3f} mm")
    print("*** The M3 screw would break through into the bore. Fix by moving the")
    print("*** lane, shortening the insert, or shrinking the bore -- see the notes.")
    print("*" * 72)

def report(model):
    """Print the envelope, so the next step has a before/after to compare to."""
    assert len(model.solids().vals()) == 1, "the band came out as more than one solid"
    bb = model.val().BoundingBox()
    print("--- result ---")
    print(f"solids       {len(model.solids().vals())}")
    print(f"bounding box {bb.xlen:.3f} x {bb.ylen:.3f} x {bb.zlen:.3f}")
    print(f"volume       {model.val().Volume():.0f} mm^3")
    print(f"apex         y = {APEX_Y:.3f}, inner apex y = {ARC_CENTRE[1] + ARCH_R:.3f}")
    print(f"ends         outer ({point_at(JOINT_R, SPAN_START)[0]:.3f}, "
          f"{point_at(JOINT_R, SPAN_START)[1]:.3f})   inner "
          f"({point_at(ARCH_R, SPAN_START)[0]:.3f}, "
          f"{point_at(ARCH_R, SPAN_START)[1]:.3f})")
    print(f"legs         centres +-{LEG_CENTRE_X:.3f}, standing on y = {BASE_Y:.3f}")
    print(f"opening      {2 * LEG_INNER_X:.3f} wide between the legs")
    print(f"leg bores    {BORE_D:.1f} dia, {BORE_LENGTH:.3f} mm on the axis")
    warn_if_clashing()      # last thing printed, so it is the thing you see

check_clearances()

model = arch().union(legs())
model = drill_insert_holes(model)
model = drill_leg_bores(model)

report(model)
export_step_file(model, "bridge_body")
export_svg_preview(model, "bridge_body")
