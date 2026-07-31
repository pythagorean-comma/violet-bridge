"""The whole bridge in one STEP: crown seated on the body, six saddles in place.

Nothing is moved to assemble the two halves. Both are built against the datum in
common.py -- the crown's underside is cut to JOINT_R and the body's top edge *is*
JOINT_R -- so each already sits in its assembled position, and the identity
location is the right one. Do not add a transform there; if the two ever look
wrong together, the fault is in a part, and report() below is what should catch
it.

Exported as a cq.Assembly rather than a fusion, so the components stay separate
and can be picked apart in a viewer. They are bolted together, not welded.

This imports both bridge parts, and both build and export at import time, so
running this rewrites every STEP and SVG in out/ -- not just the assembly's. That
is deliberate: it makes a stale assembly impossible.
"""

import math
import os
import random

import cadquery as cq

import bridge
import bridge_body
from common import (ARC_CENTRE, BLANK_THICKNESS, BRIDGE_HEIGHT, OUTPUT_PATH,
                    SEAT_R, SLOT_FLOOR_R, STRING_ARC_R, STRING_PITCH,
                    export_svg_preview, point_at, string_angles)


CROWN_COLOUR = cq.Color(0.85, 0.72, 0.45, 1.0)      # so the joint reads clearly
BODY_COLOUR = cq.Color(0.55, 0.62, 0.72, 1.0)
SADDLE_COLOUR = cq.Color(0.85, 0.72, 0.45, 1.0)

# The intonation carriage lives in its own repo and is not built here -- this
# reads whatever it last exported. Absolute because the two projects are
# siblings, not nested; if it is missing the bridge still assembles without it.
CARRIAGE_STEP = "out/intonation-carriage.step"

TRAVEL_SEED = 6     # Tim asked for the saddles set randomly fore and aft. Seeded
                    # so the file is the same on every run: a STEP that shuffled
                    # itself each build would be useless to diff or to check.
                    # 6 spreads them over 9.0 of the 11.0 available, which shows
                    # the travel; some seeds bunch all six at one end.

def load_saddle():
    """The intonation carriage, or None if its project has not been built.

    Checked against the crown as it loads, because everything downstream assumes
    the two were designed to the same radii. In its own frame the carriage is
    laid out z-up: the screw tab occupies local z below the seat plane and the
    top block above it, so seating the tab on SLOT_FLOOR_R fixes where the local
    origin lands, and the top face then has to come out on STRING_ARC_R.
    """
    if not os.path.exists(CARRIAGE_STEP):
        print(f"*** no saddles: {CARRIAGE_STEP} not found")
        print("*** build the intonation-carriage project to include them")
        return None

    shape = cq.importers.importStep(CARRIAGE_STEP).val()
    box = shape.BoundingBox()
    origin_r = SLOT_FLOOR_R - box.zmin
    assert abs(origin_r + box.zmax - STRING_ARC_R) < 1e-6, (
        f"the carriage is {box.zlen} deep, which puts its top face at "
        f"r = {origin_r + box.zmax:.3f} rather than on STRING_ARC_R "
        f"{STRING_ARC_R} -- it was not drawn for this crown")
    return shape

def travel_range(box):
    """How far along the thickness a saddle's centre may sit.

    The tab has to stay between the crown's end walls, which is what the M3
    screws bear on. The top block is clear of the crown entirely, so it is the
    tab that bounds this -- both are the same length, so the bounding box does.
    """
    return (bridge.END_WALL - box.ymin,
            BLANK_THICKNESS - bridge.END_WALL - box.ymax)

def saddle_location(angle, travel, origin_r):
    """Put a carriage in the slot at `angle`, `travel` along the thickness.

    The carriage's local axes map onto the bridge as +z radially out, +y along
    the thickness (its screw bore, and so the intonation travel), and +x
    tangential. Rotating 90 degrees about x swings y up to the bridge's z; the
    second rotation, angle + 90, then swings x onto the tangent and z onto the
    radius. Read right to left, as the multiplication applies them.

    `origin_r` is where the carriage's own origin lands, which follows from
    seating its tab on the slot floor -- see load_saddle().
    """
    return (cq.Location(cq.Vector(*point_at(origin_r, angle), travel))
            * cq.Location(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), angle + 90)
            * cq.Location(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 90))

def place_saddles(shape):
    """One carriage per string, each at its own random point in its travel.

    Returns (name, placed solid, angle, travel) rows -- the solids so report()
    can check them against the crown and each other, which is the only proof the
    frame above is right.
    """
    box = shape.BoundingBox()
    origin_r = SLOT_FLOOR_R - box.zmin
    low, high = travel_range(box)
    dice = random.Random(TRAVEL_SEED)
    return [(f"saddle_{i}",
             shape.moved(saddle_location(angle, travel, origin_r)),
             angle, travel)
            for i, (angle, travel) in enumerate(
                ((a, dice.uniform(low, high)) for a in string_angles()), start=1)]

def build(saddles):
    """Everything in one assembly, each part where its own frame puts it."""
    assy = (cq.Assembly(name="violet_bridge")
            .add(bridge_body.model, name="bridge_body", color=BODY_COLOUR)
            .add(bridge.model, name="crown", color=CROWN_COLOUR))
    for name, solid, _, _ in saddles:
        assy.add(solid, name=name, color=SADDLE_COLOUR)
    return assy

def report(assy, saddles):
    """Print the assembled envelope, and prove nothing interferes.

    The interference checks are the point of this file. Each part is built on its
    own and the joints are the one thing no single script can see, so a change
    that pushes one part into another fails here rather than in a viewer.
    """
    body, crown = bridge_body.model.val(), bridge.model.val()
    bb, bc = body.BoundingBox(), crown.BoundingBox()
    shared = body.intersect(crown).Volume()

    print("--- assembly ---")
    print(f"body         {bb.xlen:.3f} x {bb.ylen:.3f} x {bb.zlen:.3f}"
          f"   y {bb.ymin:7.3f} to {bb.ymax:7.3f}   {body.Volume():.0f} mm^3")
    print(f"crown        {bc.xlen:.3f} x {bc.ylen:.3f} x {bc.zlen:.3f}"
          f"   y {bc.ymin:7.3f} to {bc.ymax:7.3f}   {crown.Volume():.0f} mm^3")
    print(f"joint        body top {bb.ymax:.3f} meets crown bottom {bc.ymin:.3f}")
    print(f"interference {shared:.3f} mm^3")
    assert shared < 1e-6, "the two parts overlap -- one has grown through the joint"

    if saddles:
        report_saddles(crown, saddles)

    box = assy.toCompound().BoundingBox()
    total = body.Volume() + crown.Volume() + sum(s.Volume() for _, s, _, _ in saddles)
    print(f"assembled    {box.xlen:.3f} x {box.ylen:.3f} x {box.zlen:.3f}"
          f"   {total:.0f} mm^3 in {2 + len(saddles)} parts")

    if not saddles:
        print(f"height       {box.ymax:.3f} to the crown's seat; BRIDGE_HEIGHT is "
              f"{BRIDGE_HEIGHT:.1f} to the top of the highest saddle, not modelled here")
        return

    # The envelope overshoots BRIDGE_HEIGHT and that is not an error: a saddle's
    # top face is flat, a chord across the string arc, so its corners stand proud
    # of the arc. The string rides the middle of that face, and it is the string
    # that BRIDGE_HEIGHT measures.
    string_y = max(ARC_CENTRE[1] + STRING_ARC_R * math.sin(math.radians(angle))
                   for _, _, angle, _ in saddles)
    print(f"height       {string_y:.3f} to the highest string, against BRIDGE_HEIGHT "
          f"{BRIDGE_HEIGHT:.1f}")
    print(f"             {box.ymax:.3f} to the envelope -- a saddle's top face is a"
          f" chord, so its corners stand {box.ymax - string_y:.3f} above the string")
    assert abs(string_y - BRIDGE_HEIGHT) < 0.05, (
        "the saddles do not put the strings at BRIDGE_HEIGHT")

def report_saddles(crown, saddles):
    """Check every saddle sits in its slot without fouling anything.

    Radius is measured to the vertices, so the numbers run a little wide of the
    flat faces: the tab's bottom corners are filleted, and the top block's
    corners stand further out than its face because the face is a chord.
    """
    print(f"saddles      {len(saddles)}, travel seeded {TRAVEL_SEED}")
    cx, cy = ARC_CENTRE
    for name, solid, angle, travel in saddles:
        radii = [math.hypot(v.X - cx, v.Y - cy) for v in solid.Vertices()]
        fouled = solid.intersect(crown).Volume()
        print(f"   {name} at {angle:7.3f} deg, z {travel:6.3f}:  r {min(radii):.3f}"
              f" to {max(radii):.3f}   fouls the crown by {fouled:.4f} mm^3")
        assert fouled < 1e-6, f"{name} does not fit its slot"

    # Neighbours are the tight direction: the top block is wider than the tab and
    # the string pitch is angular, so the blocks are closest at their bottom edge.
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    gaps = []
    for (_, a, _, _), (_, b, _, _) in zip(saddles, saddles[1:]):
        probe = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
        probe.Perform()
        gaps.append(probe.Value())
    print(f"   neighbours clear by {min(gaps):.3f} mm at the tightest;"
          f" the slots are {SEAT_R * math.radians(STRING_PITCH):.3f} mm apart at the seat")
    assert min(gaps) > 0, "adjacent saddles touch"

saddle = load_saddle()
saddles = place_saddles(saddle) if saddle is not None else []

assy = build(saddles)
report(assy, saddles)

step_path = f"{OUTPUT_PATH}/bridge_assembly.step"
assy.export(step_path, "STEP")      # .save() is deprecated in CadQuery 2.8
print("Exported:", step_path)
export_svg_preview(assy.toCompound(), "bridge_assembly")
