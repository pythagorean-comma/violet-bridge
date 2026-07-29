"""Datum and output helpers shared by the two halves of the bridge.

The bridge is built as two parts that dock together: `bridge.py` makes the
saddle arc (the crown band) and `bridge_body.py` makes the decorated lower half.
They have to agree on where the arc centre is and what radius they meet at, so
those constants live here rather than being duplicated.

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

JOINT_R = 53.9              # the two parts meet on this cylinder: it is the
                            # arc's underside and the body's top edge
JOINT_HALF_ANGLE = 49.025   # how far the joint runs either side of vertical:
                            # the strings' own half-span of 33.025 deg plus
                            # 16 deg of margin. Sets the arc's angular extent
                            # and therefore how wide the body's top edge is.
BLANK_THICKNESS = 25.0      # both parts, front to back

PREVIEW_OPTS = {            # the fast visual check
    "projectionDir": (1, -1, 0.8),
    "width": 800, "height": 800,
}

def point_at(radius, angle):
    """A point at `radius` and `angle` degrees about ARC_CENTRE."""
    cx, cy = ARC_CENTRE
    return (cx + radius * math.cos(math.radians(angle)),
            cy + radius * math.sin(math.radians(angle)))

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
