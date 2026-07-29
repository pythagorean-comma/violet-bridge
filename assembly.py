"""The two halves written into one STEP: the crown seated on the bridge body.

Nothing is moved to assemble them. Both parts are built against the datum in
common.py -- the crown's underside is cut to JOINT_R and the body's top edge *is*
JOINT_R -- so each already sits in its assembled position, and the identity
location is the right one. Do not add a transform here; if the two ever look
wrong together, the fault is in a part, and report() below is what should catch
it.

Exported as a cq.Assembly rather than a fusion, so the components stay separate
and can be picked apart in a viewer. They are bolted together, not welded.

This imports both parts, and both build and export at import time, so running
this rewrites every STEP and SVG in out/ -- not just the assembly's. That is
deliberate: it makes a stale assembly impossible.
"""

import cadquery as cq

import bridge
import bridge_body
from common import (BRIDGE_HEIGHT, OUTPUT_PATH, export_svg_preview)

CROWN_COLOUR = cq.Color(0.85, 0.72, 0.45, 1.0)      # so the joint reads clearly
BODY_COLOUR = cq.Color(0.55, 0.62, 0.72, 1.0)       # in a viewer

def build():
    """Both parts in one assembly, each where its own script already put it."""
    return (cq.Assembly(name="violet_bridge")
            .add(bridge_body.model, name="bridge_body", color=BODY_COLOUR)
            .add(bridge.model, name="crown", color=CROWN_COLOUR))

def report(assy):
    """Print the assembled envelope, and prove the two parts do not interfere.

    The interference check is the point of this file. Either part can be changed
    on its own, and the joint is the one thing neither script can see; a change
    that pushes one into the other fails here rather than in a viewer.
    """
    body, crown = bridge_body.model.val(), bridge.model.val()
    bb, bc = body.BoundingBox(), crown.BoundingBox()
    shared = body.intersect(crown).Volume()

    print("--- assembly ---")
    print(f"body         {bb.xlen:.3f} x {bb.ylen:.3f} x {bb.zlen:.3f}"
          f"   y {bb.ymin:7.3f} to {bb.ymax:7.3f}   {body.Volume():.0f} mm^3")
    print(f"crown        {bc.xlen:.3f} x {bc.ylen:.3f} x {bc.zlen:.3f}"
          f"   y {bc.ymin:7.3f} to {bc.ymax:7.3f}   {crown.Volume():.0f} mm^3")

    box = assy.toCompound().BoundingBox()
    print(f"assembled    {box.xlen:.3f} x {box.ylen:.3f} x {box.zlen:.3f}"
          f"   {body.Volume() + crown.Volume():.0f} mm^3")
    print(f"joint        body top {bb.ymax:.3f} meets crown bottom {bc.ymin:.3f}")
    print(f"interference {shared:.3f} mm^3")
    assert shared < 1e-6, "the two parts overlap -- one has grown through the joint"

    # The assembly stops short of BRIDGE_HEIGHT on purpose, and it looks like an
    # error if you do not know why.
    print(f"height       {box.ymax:.3f} to the crown's seat; BRIDGE_HEIGHT is "
          f"{BRIDGE_HEIGHT:.1f} to the top of the highest saddle, which is not "
          f"modelled -- only its slot")

assy = build()
report(assy)

step_path = f"{OUTPUT_PATH}/bridge_assembly.step"
assy.export(step_path, "STEP")      # .save() is deprecated in CadQuery 2.8
print("Exported:", step_path)
export_svg_preview(assy.toCompound(), "bridge_assembly")
