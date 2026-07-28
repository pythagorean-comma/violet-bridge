import math
import os

import cadquery as cq

import profile_data

OUTPUT_PATH = "out"

BLANK_THICKNESS = 25.0      # oversize stock; the carving passes reduce this

# Telling the drawn straight edges from its curves. The plot tessellates curves
# finely (segments under 1.05 mm) but draws the arch crown and the outer leg
# edges coarsely, at ~3 mm a segment, so length alone is not enough. What does
# separate them: a tessellated curve turns only 2-5 degrees between segments,
# while a real straight edge meets its neighbours at a distinct corner.
LINE_MIN_LENGTH = 1.5       # mm
CORNER_ANGLE = 6.0          # degrees

PREVIEW_OPTS = {            # the fast visual check
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

def turn_angle(points, i):
    """Degrees the polyline turns through at vertex `i`."""
    n = len(points)
    ax, ay = points[(i - 1) % n]
    bx, by = points[i]
    cx, cy = points[(i + 1) % n]
    ux, uy = bx - ax, by - ay
    vx, vy = cx - bx, cy - by
    return abs(math.degrees(math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)))

def straight_segments(points):
    """Flag each segment of the closed outline as a straight edge or not."""
    n = len(points)
    flags = []
    for i in range(n):
        length = math.dist(points[i], points[(i + 1) % n])
        corners = turn_angle(points, i) >= CORNER_ANGLE and \
                  turn_angle(points, (i + 1) % n) >= CORNER_ANGLE
        flags.append(length >= LINE_MIN_LENGTH and corners)
    return flags

def outline_wire():
    """The front-view silhouette as one closed wire on the XY plane.

    Straight runs become lines and curved runs become splines through the
    drawing's own points, so the wire follows the plot rather than smoothing
    across its corners.
    """
    points = profile_data.OUTLINE
    flags = straight_segments(points)
    n = len(points)

    # Start just after a straight segment, so the wire ends on one and `close`
    # reproduces it exactly instead of guessing.
    last = max(i for i, straight in enumerate(flags) if straight)
    points = points[last + 1:] + points[:last + 1]
    flags = flags[last + 1:] + flags[:last + 1]

    wire = cq.Workplane("XY").moveTo(*points[0])
    i = 0
    while i < n - 1:
        if flags[i]:
            wire = wire.lineTo(*points[i + 1])
            i += 1
        else:
            run = i
            while run < n - 1 and not flags[run]:
                run += 1
            wire = wire.spline(points[i + 1:run + 1], includeCurrent=True)
            i = run
    return wire.close()

def blank(wire):
    """Extrude the silhouette to a constant-thickness plank."""
    return wire.extrude(BLANK_THICKNESS)

def cut_string_holes(model):
    """The 7 drilled through-holes.

    The drawing shows these as closed circles, which reads as real holes for the
    sympathetic strings. Drop this call if that turns out to be wrong.
    """
    drills = cq.Workplane("XY")
    for x, y, radius in profile_data.HOLES:
        drills = drills.moveTo(x, y).circle(radius)
    return model.cut(drills.extrude(BLANK_THICKNESS))

os.makedirs(OUTPUT_PATH, exist_ok=True)

profile = outline_wire()
model = blank(profile)
model = cut_string_holes(model)

export_step_file(model, "bridge_blank")
export_svg_preview(model, "bridge_blank")
