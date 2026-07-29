"""Datum and output helpers shared by the two halves of the bridge.

The bridge is built as two parts that dock together: `bridge.py` makes the
saddle arc (the crown band) and `bridge_body.py` makes the decorated lower half.
They have to agree on where the arc centre is and what radius they meet at, so
those constants live here rather than being duplicated. The radius they meet at
is set by the saddles: the joint sits SADDLE_WEB below the slot floors, which is
as thin as the crown can be made and still hold a saddle.

Both parts build and export at module level, so neither may import the other --
hence this third module.

Datum: **y = 0 is the belly of the instrument**, x = 0 the centreline, and z runs
fore and aft through the thickness.
"""

import math
import os

import cadquery as cq

OUTPUT_PATH = "out"

# --- shared geometry, mm and degrees -------------------------------------
BRIDGE_HEIGHT = 65.0        # belly to the top of the highest saddle

# Every radius in either part is measured from here. The value follows from
# BRIDGE_HEIGHT and the highest saddle sitting at r = 72: the centre lands
# 6.768 mm below the belly.
ARC_CENTRE = (0.0, -6.768)

# The radial stack, outside in. The strings sit on STRING_ARC_R; everything
# below follows from what has to fit under them, and JOINT_R falls out at the
# bottom rather than being a number in its own right.
STRING_ARC_R = 72.0         # where the strings sit; mean of the drawing's six
                            # radial notes (2.820-2.860" @ 59-125 deg)
SADDLE_HEIGHT = 5.0         # block bottom to string
SEAT_R = STRING_ARC_R - SADDLE_HEIGHT       # 67.0, the arc's outer face
SLOT_DEPTH = 5.0            # the block sits fully home
SLOT_FLOOR_R = SEAT_R - SLOT_DEPTH          # 62.0
SADDLE_WEB = 2.0            # material left under the slot floors: all the crown
                            # needs to carry the saddles, and the reason the
                            # joint sits where it does

JOINT_R = SLOT_FLOOR_R - SADDLE_WEB         # 60.0: the two parts meet on this
                            # cylinder, which is the arc's underside and the
                            # body's top edge. Derived, not chosen -- put the
                            # joint anywhere lower and the crown is carrying
                            # weight it has no use for.
JOINT_HALF_ANGLE = 49.025   # how far the joint runs either side of vertical:
                            # the strings' own half-span of 33.025 deg plus
                            # 16 deg of margin. Sets the arc's angular extent
                            # and therefore how wide the body's top edge is.
                            # At JOINT_R the joint is 90.6 mm wide and its ends
                            # stand 32.58 mm above the belly.
BLANK_THICKNESS = 25.0      # both parts, front to back

# The string band. Shared because the fixing lanes are derived from it: the arc
# is drilled for them and the body is tapped for them, so both parts have to
# agree on where they fall. The body must never write those angles down.
STRING_COUNT = 6
STRING_PITCH = 13.21        # measured off the original, spread only 0.04 deg
STRING_CENTRE = 92.0        # the original's band sits 2 deg off vertical,
                            # relative to the baseline its feet stood on.
                            # Centring on 90 instead costs 1.0 mm of string
                            # height; this is deliberately not BODY_CENTRE.
SLOT_WIDTH = 5.0            # the saddle block's own width
BODY_CENTRE = 90.0          # the body sits square on its base even though the
                            # strings do not; the original is the same. With
                            # JOINT_HALF_ANGLE this fixes where the arc ends,
                            # which is one wall of the outer fixing lanes.

PREVIEW_OPTS = {            # the fast visual check
    "projectionDir": (1, -1, 0.8),
    "width": 800, "height": 800,
}

def point_at(radius, angle):
    """A point at `radius` and `angle` degrees about ARC_CENTRE."""
    cx, cy = ARC_CENTRE
    return (cx + radius * math.cos(math.radians(angle)),
            cy + radius * math.sin(math.radians(angle)))

def string_angles():
    """The six string positions, evenly pitched about STRING_CENTRE.

    Evenly pitched on purpose: the original's six gaps spread only 0.04 degrees,
    which is 0.05 mm at the string arc. Its *radii* do vary, by 1.0 mm, and that
    is not reproduced -- uniform saddles on a uniform arc leave the string
    heights within 0.56 mm of the original, which the setup absorbs.
    """
    middle = (STRING_COUNT - 1) / 2
    return [STRING_CENTRE + (i - middle) * STRING_PITCH for i in range(STRING_COUNT)]

def slot_edge_angle(angle, radius, side):
    """The angle at which a slot's wall crosses `radius`.

    A slot is a parallel-sided radial cut, so its walls are not radial lines:
    they close on the slot's own angle as the radius grows. `side` is -1 for the
    wall clockwise of the slot and +1 for the other.
    """
    return angle + side * math.degrees(math.asin((SLOT_WIDTH / 2) / radius))

def fixing_angles():
    """Where the arc bolts down to the body: three lanes, no slot in the way.

    The outer two sit *outboard* of the end slots, in the plain band between the
    last slot wall and the end of the arc, each centred in that band. It is much
    wider than the ribs between slots -- 18.6 and 13.9 mm at the seat -- and it
    puts the clamping load over the body's legs rather than over its arch. The
    middle lane is the midpoint of strings 3-4, the one gap wide enough to be
    worth using.

    Centred at SEAT_R, where the counterbore -- the largest tool on the lane --
    opens. Bisecting at JOINT_R instead moves the lanes 0.13 deg, so the radius
    barely matters; it only has to be chosen once.

    The two outer lanes are not mirror images. The string band is centred on
    STRING_CENTRE and the arc on BODY_CENTRE, 2 deg apart, so the band outboard
    of the first slot is wider than the one outboard of the last, and centring
    in each puts the lanes 2 deg apart in their offsets from the arc's centre.

    Lives here rather than in either part because both need it: the arc drills
    clearance on these lanes and the body is tapped on them.
    """
    strings = string_angles()
    return [
        (BODY_CENTRE - JOINT_HALF_ANGLE
         + slot_edge_angle(strings[0], SEAT_R, -1)) / 2,
        (strings[2] + strings[3]) / 2,
        (slot_edge_angle(strings[-1], SEAT_R, +1)
         + BODY_CENTRE + JOINT_HALF_ANGLE) / 2,
    ]

def export_step_file(model, name):
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    step_path = f"{OUTPUT_PATH}/{name}.step"
    cq.exporters.export(model, step_path)
    print("Exported:", step_path)

def export_svg_preview(model, name):
    """Write the shaded-line preview render for `model`."""
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    svg_path = f"{OUTPUT_PATH}/{name}.svg"
    cq.exporters.export(model, svg_path, opt=PREVIEW_OPTS)
    print("Exported:", svg_path)
