"""Adjustable saddle bridge: a section of a cylinder with a slot per string.

Each saddle is located by a 5 x 5 mm intonation block dropped into its own
radial slot, and moves fore and aft on an M3 screw to set intonation. That
travel runs along the part's thickness, which is why BLANK_THICKNESS is 25 mm --
it is the travel envelope, not stock to be carved away.

The only number this takes from docs/JEN-VDG.pdf is STRING_PITCH. See
profile_data.py and tools/extract_profile.py for where it came from.
"""

import math

import cadquery as cq

from common import (ARC_CENTRE, BLANK_THICKNESS, JOINT_HALF_ANGLE, JOINT_R,
                    SEAT_R, SLOT_DEPTH, SLOT_FLOOR_R, export_step_file,
                    export_svg_preview, fixing_angles, point_at, string_angles)

# --- geometry, mm and degrees -------------------------------------------
# The radii -- SEAT_R, SLOT_FLOOR_R, JOINT_R and the SLOT_DEPTH between them --
# come from common.py, because where the arc's underside lands is what the body
# has to dock on to. The string band and the fixing lanes live there for the
# same reason: the body is tapped on the lanes this part drills.
SLOT_WIDTH = 5.0
BODY_CENTRE = 90.0              # the body sits square on its base even though
                                # the strings do not; the original is the same

END_WALL = 1.5                  # front and back, anchors the M3 screws
M3_CLEARANCE = 3.2              # head bears on the wall, thread is in the block

FIXING_CLEARANCE_D = 3.4        # M3 clearance for the screws into the body
FIXING_COUNTERBORE_D = 6.0      # M3 cap head is 5.5; leaves 2.2 mm of lane
FIXING_COUNTERBORE_DEPTH = 3.5  # head sits 0.5 mm below the seat

WEDGE_REACH = 500.0             # far enough that the wedge's chord clears the body
SLOT_OVERCUT = 5.0              # push slots past SEAT_R for a clean cut

def body():
    """The bar: an annular sector about ARC_CENTRE.

    Cut from a ring rather than drawn as a profile, so the two arcs are exact.
    The wedge that trims it to the angular span can be a plain triangle -- with
    its far vertices at WEDGE_REACH its chord passes hundreds of mm out, well
    clear of anything the ring bounds.
    """
    half_span = JOINT_HALF_ANGLE
    ring = (cq.Workplane("XY")
            .center(*ARC_CENTRE)
            .circle(SEAT_R)
            .circle(JOINT_R)
            .extrude(BLANK_THICKNESS))
    wedge = (cq.Workplane("XY")
             .polyline([ARC_CENTRE,
                        point_at(WEDGE_REACH, BODY_CENTRE - half_span),
                        point_at(WEDGE_REACH, BODY_CENTRE + half_span)])
             .close()
             .extrude(BLANK_THICKNESS))
    return ring.intersect(wedge)

def cut_slots(model):
    """One radial slot per string, for the saddle's intonation block.

    Stops short of both faces by END_WALL so the M3 screws have something to
    bear on, which leaves the block free to travel between them.
    """
    half_width = SLOT_WIDTH / 2
    slots = cq.Workplane("XY", origin=(0, 0, END_WALL))
    for angle in string_angles():
        out = (math.cos(math.radians(angle)), math.sin(math.radians(angle)))
        side = (-out[1], out[0])
        cx, cy = ARC_CENTRE
        slots = slots.polyline([
            (cx + out[0] * radius + side[0] * offset,
             cy + out[1] * radius + side[1] * offset)
            for radius, offset in (
                (SLOT_FLOOR_R, -half_width),
                (SEAT_R + SLOT_OVERCUT, -half_width),
                (SEAT_R + SLOT_OVERCUT, half_width),
                (SLOT_FLOOR_R, half_width),
            )
        ]).close()
    return model.cut(slots.extrude(BLANK_THICKNESS - 2 * END_WALL))

def drill_screw_holes(model):
    """M3 clearance through both end walls, on each slot's centreline.

    Drilled the full thickness: everything between the walls is already slot,
    so this only takes material out of the walls themselves.
    """
    axis_r = SLOT_FLOOR_R + SLOT_DEPTH / 2
    drills = cq.Workplane("XY")
    for angle in string_angles():
        drills = drills.moveTo(*point_at(axis_r, angle)).circle(M3_CLEARANCE / 2)
    return model.cut(drills.extrude(BLANK_THICKNESS))

def cut_fixing_holes(model):
    """Counterbored M3 clearance for the screws that pull the arc onto the body.

    Cut radially inward from the seat, so the counterbore opens on the seat
    surface and the clearance hole breaks out on the arc's underside. The heads
    finish below the seat, and the saddles go in over them afterwards.
    """
    overcut = 1.0               # start outside the seat so the cut opens cleanly
    tools = []
    for angle in fixing_angles():
        inward = cq.Vector(-math.cos(math.radians(angle)),
                           -math.sin(math.radians(angle)), 0)
        start = cq.Vector(*point_at(SEAT_R + overcut, angle), BLANK_THICKNESS / 2)
        tools.append(cq.Solid.makeCylinder(
            FIXING_COUNTERBORE_D / 2, FIXING_COUNTERBORE_DEPTH + overcut, start, inward))
        tools.append(cq.Solid.makeCylinder(
            FIXING_CLEARANCE_D / 2,
            SEAT_R - JOINT_R + 2 * overcut, start, inward))
    return model.cut(cq.Workplane("XY").newObject(tools))

model = body()
model = cut_slots(model)
model = drill_screw_holes(model)
model = cut_fixing_holes(model)

export_step_file(model, "saddle_bridge")
export_svg_preview(model, "saddle_bridge")
