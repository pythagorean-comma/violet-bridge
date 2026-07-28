"""Adjustable saddle bridge: a section of a cylinder with a slot per string.

Each saddle is located by a 5 x 5 mm intonation block dropped into its own
radial slot, and moves fore and aft on an M3 screw to set intonation. That
travel runs along the part's thickness, which is why BLANK_THICKNESS is 25 mm --
it is the travel envelope, not stock to be carved away.

The only number this takes from docs/JEN-VDG.pdf is STRING_PITCH. See
profile_data.py and tools/extract_profile.py for where it came from.
"""

import math
import os

import cadquery as cq

OUTPUT_PATH = "out"

# --- geometry, mm and degrees -------------------------------------------
ARC_CENTRE = (0.0, -37.5512)    # every radius below is measured from here

STRING_ARC_R = 72.0             # where the strings sit; mean of the drawing's
                                # six radial notes (2.820-2.860" @ 59-125 deg)
STRING_COUNT = 6
STRING_PITCH = 13.21            # measured off the original, spread only 0.04 deg

SADDLE_HEIGHT = 5.0             # block bottom to string
BODY_TOP_R = STRING_ARC_R - SADDLE_HEIGHT
SLOT_DEPTH = 5.0                # the block sits fully home
SLOT_FLOOR_R = BODY_TOP_R - SLOT_DEPTH
SLOT_WIDTH = 5.0
BODY_INNER_R = 53.9             # carried over from the original inner arc
BODY_MARGIN = 16.0              # degrees of body beyond the outer strings

BLANK_THICKNESS = 25.0          # intonation travel envelope
END_WALL = 1.5                  # front and back, anchors the M3 screws
M3_CLEARANCE = 3.2              # head bears on the wall, thread is in the block

WEDGE_REACH = 500.0             # far enough that the wedge's chord clears the body
SLOT_OVERCUT = 5.0              # push slots past BODY_TOP_R for a clean cut

PREVIEW_OPTS = {                # the fast visual check
    "projectionDir": (1, -1, 0.8),
    "width": 800, "height": 800,
}

def export_step_file(model, name):
    step_path = f"{OUTPUT_PATH}/{name}.step"
    cq.exporters.export(model, step_path)
    print("Exported:", step_path)

def export_svg_preview(model, name):
    """Write the shaded-line preview render for `model`."""
    svg_path = f"{OUTPUT_PATH}/{name}.svg"
    cq.exporters.export(model, svg_path, opt=PREVIEW_OPTS)
    print("Exported:", svg_path)

def point_at(radius, angle):
    """A point at `radius` and `angle` degrees about ARC_CENTRE."""
    cx, cy = ARC_CENTRE
    return (cx + radius * math.cos(math.radians(angle)),
            cy + radius * math.sin(math.radians(angle)))

def string_angles():
    """The six string positions, evenly pitched and centred on vertical.

    Uniform on purpose. The original's six gaps spread only 0.04 degrees, which
    is 0.05 mm at the string arc -- inside anything that can be cut or heard.
    """
    middle = (STRING_COUNT - 1) / 2
    return [90.0 + (i - middle) * STRING_PITCH for i in range(STRING_COUNT)]

def body():
    """The bar: an annular sector about ARC_CENTRE.

    Cut from a ring rather than drawn as a profile, so the two arcs are exact.
    The wedge that trims it to the angular span can be a plain triangle -- with
    its far vertices at WEDGE_REACH its chord passes hundreds of mm out, well
    clear of anything the ring bounds.
    """
    half_span = (STRING_COUNT - 1) * STRING_PITCH / 2 + BODY_MARGIN
    ring = (cq.Workplane("XY")
            .center(*ARC_CENTRE)
            .circle(BODY_TOP_R)
            .circle(BODY_INNER_R)
            .extrude(BLANK_THICKNESS))
    wedge = (cq.Workplane("XY")
             .polyline([ARC_CENTRE,
                        point_at(WEDGE_REACH, 90.0 - half_span),
                        point_at(WEDGE_REACH, 90.0 + half_span)])
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
                (BODY_TOP_R + SLOT_OVERCUT, -half_width),
                (BODY_TOP_R + SLOT_OVERCUT, half_width),
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

os.makedirs(OUTPUT_PATH, exist_ok=True)

model = body()
model = cut_slots(model)
model = drill_screw_holes(model)

export_step_file(model, "saddle_bridge")
export_svg_preview(model, "saddle_bridge")
