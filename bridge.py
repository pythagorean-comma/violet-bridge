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
                    export_svg_preview, point_at)

# --- geometry, mm and degrees -------------------------------------------
# The radii -- SEAT_R, SLOT_FLOOR_R, JOINT_R and the SLOT_DEPTH between them --
# come from common.py, because where the arc's underside lands is what the body
# has to dock on to.
STRING_COUNT = 6
STRING_PITCH = 13.21            # measured off the original, spread only 0.04 deg
STRING_CENTRE = 92.0            # the original's band sits 2 deg off vertical,
                                # relative to the baseline its feet stood on.
                                # Centring on 90 instead costs 1.0 mm of string
                                # height; this is deliberately not BODY_CENTRE.

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

def string_angles():
    """The six string positions, evenly pitched about STRING_CENTRE.

    Evenly pitched on purpose: the original's six gaps spread only 0.04 degrees,
    which is 0.05 mm at the string arc. Its *radii* do vary, by 1.0 mm, and that
    is not reproduced -- uniform saddles on a uniform arc leave the string
    heights within 0.56 mm of the original, which the setup absorbs.
    """
    middle = (STRING_COUNT - 1) / 2
    return [STRING_CENTRE + (i - middle) * STRING_PITCH for i in range(STRING_COUNT)]

def fixing_angles():
    """Where the arc bolts down to the body: three lanes, no slot in the way.

    Taken as the midpoints between string pairs 1-2, 3-4 and 5-6, so they track
    `string_angles()` rather than being written down separately. The outer pairs
    are used rather than the inner ones because they spread the fixings wider.
    """
    strings = string_angles()
    return [(strings[i] + strings[i + 1]) / 2 for i in (0, 2, 4)]

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
