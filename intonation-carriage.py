import cadquery as cq

from common import (export_step_file, export_svg_preview)

TOP_BLOCK_LENGTH = 11
TOP_BLOCK_WIDTH = 14.5
TOP_BLOCK_DEPTH = 5.0
TOP_BLOCK_CORNER_FILLET = 1.0

SENSOR_HOLE_LENGTH = 8.0
SENSOR_HOLE_WIDTH = 11.5
SENSOR_HOLE_DEPTH = 2.0
SENSOR_HOLE_FILLET = 0.5

SENSOR_UNDERSIDE_HOLE_LENGTH = 6.0
SENSOR_UNDERSIDE_HOLE_WIDTH = 9.5
SENSOR_UNDERSIDE_HOLE_DEPTH = 4.0
SENSOR_UNDERSIDE_HOLE_FILLET = 0.5

INTONATION_SCREW_BLOCK_LENGTH = 11.0
INTONATION_SCREW_BLOCK_WIDTH = 5.0
INTONATION_SCREW_BLOCK_DEPTH = 5.0
INTONATION_SCREW_BLOCK_CORNER_FILLET = 1.0
INTONATION_SCREW_HOLE_DIAMETER = 2.5

SENSOR_CABLE_DIAMETER = 2.0
SENSOR_CABLE_CHANNEL_DEPTH = 3.0        # in from the +Y end face; the wall itself is 2.5
SENSOR_CABLE_CHANNEL_OVERSHOOT = 1.0    # above the top face, so the mouth is full width
SENSOR_CABLE_CHANNEL_FILLET = 0.5       # rounds the floor of the trough

# Sit the block directly beneath the top block: both are centred on Z=0 in their
# own right, so drop it by half of each depth to make the faces coincide.
INTONATION_SCREW_BLOCK_CENTRE_Z = -(TOP_BLOCK_DEPTH + INTONATION_SCREW_BLOCK_DEPTH) / 2

# =============================================================================
# Helper
# =============================================================================

def rounded_rect_sketch(width, height, radius):
    """Build a rounded-rectangle profile as a Sketch (for cutting)."""
    return cq.Sketch().rect(width, height).vertices().fillet(radius)

# =============================================================================
# Feature Functions
# =============================================================================

def make_top_block():
    """Create the main plate."""
    return (
        cq.Workplane("XY")
        .box(TOP_BLOCK_WIDTH, TOP_BLOCK_LENGTH, TOP_BLOCK_DEPTH)
        .edges("|Z")
        .fillet(TOP_BLOCK_CORNER_FILLET)
    )

def make_intonation_screw_block():
    """Create the tab, bored through its length for the intonation screw."""
    return (
        cq.Workplane("XY")
        .box(INTONATION_SCREW_BLOCK_WIDTH, INTONATION_SCREW_BLOCK_LENGTH, INTONATION_SCREW_BLOCK_DEPTH)
        .edges("|Z")
        .fillet(INTONATION_SCREW_BLOCK_CORNER_FILLET)
        .translate((0, 0, INTONATION_SCREW_BLOCK_CENTRE_Z))
        # The bore runs along the block's length (Y), so drill from the +Y end
        # face; CenterOfBoundBox is needed because the block no longer straddles
        # the global origin in Z.
        .faces(">Y")
        .workplane(centerOption="CenterOfBoundBox")
        .hole(INTONATION_SCREW_HOLE_DIAMETER)
    )


def join_intonation_screw_block(part):
    """Join the tab to the main plate."""
    return part.union(make_intonation_screw_block())

def cut_hole_for_sensor(part):
    """Cut the rounded-rectangle hole in the top block."""
    sk = rounded_rect_sketch(SENSOR_HOLE_WIDTH, SENSOR_HOLE_LENGTH, SENSOR_HOLE_FILLET)
    return (
        part
        .faces(">Z")
        # CenterOfBoundBox centres the pocket on the face itself; the default
        # would inherit the incoming workplane's origin and drag it off-centre.
        .workplane(centerOption="CenterOfBoundBox")
        .placeSketch(sk)
        .cutBlind(-SENSOR_HOLE_DEPTH)
    )

def cut_hole_for_sensor_underside(part):
    """Cut the rounded-rectangle hole in the top block."""
    sk = rounded_rect_sketch(SENSOR_UNDERSIDE_HOLE_WIDTH, SENSOR_UNDERSIDE_HOLE_LENGTH, SENSOR_UNDERSIDE_HOLE_FILLET)
    return (
        part
        .faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .placeSketch(sk)
        .cutBlind(-SENSOR_UNDERSIDE_HOLE_DEPTH)
    )

def cut_channel_for_sensor_cable(part):
    """Cut the open-topped cable channel through the top block's +Y end wall."""
    # The profile is the channel's end-on cross-section, so the fillet rounds the
    # floor of the trough. Sketching it in plan view instead puts the fillet on
    # the vertical corners and leaves the floor sharp.
    floor_z = TOP_BLOCK_DEPTH / 2 - SENSOR_UNDERSIDE_HOLE_DEPTH
    height = SENSOR_UNDERSIDE_HOLE_DEPTH + SENSOR_CABLE_CHANNEL_OVERSHOOT
    sk = rounded_rect_sketch(SENSOR_CABLE_DIAMETER, height, SENSOR_CABLE_CHANNEL_FILLET)
    # Normal along +Y so the cut runs into the end wall. The profile stands proud
    # of the top face so its upper fillets are trimmed away, leaving the mouth
    # full width; its floor sits on the underside pocket floor.
    plane = cq.Plane(
        origin=(0, TOP_BLOCK_LENGTH / 2, floor_z + height / 2),
        xDir=(1, 0, 0),
        normal=(0, 1, 0),
    )
    return (
        part
        .copyWorkplane(cq.Workplane(plane))
        .placeSketch(sk)
        .cutBlind(-SENSOR_CABLE_CHANNEL_DEPTH)
    )

part = make_top_block()
part = join_intonation_screw_block(part)
part = cut_hole_for_sensor(part)
part = cut_hole_for_sensor_underside(part)
part = cut_channel_for_sensor_cable(part)

export_step_file(part, "intonation-carriage")
export_svg_preview(part, "intonation-carriage")

