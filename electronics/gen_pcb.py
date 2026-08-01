"""Build the PCB for the design in design.py.

Four layers: signals on F.Cu and B.Cu, a solid AGND plane on In1.Cu and a
V+ plane on In2.Cu. That choice is what keeps the routing simple and the
board quiet -- every supply and ground connection becomes a via rather than
a track, and the high-impedance piezo traces run directly over an unbroken
ground plane.

V- is NOT a plane. At about 2mA it never needed one, and a B.Cu pour was this
project's worst failure mode: fragmenting it produced unconnected items in
parts of the board nowhere near the cause. It is routed like any other net,
in route_supply(), and B.Cu is a second signal layer.

The board is three blocks, each one OPA4191 serving two channels. The quad's
pinout does most of the work: every pin of buffers A and B is on the left of
the package and every pin of all-passes C and D is on the right, so a
channel's buffer feedback stays entirely left, its all-pass feedback entirely
right, and the only net that has to cross the package is BUFOUT -- which is a
low-impedance node and can go anywhere.

Track waypoints are given relative to real pad positions read back from the
placed footprints, so nothing here depends on guessing KiCad's rotation
conventions.

Reading order, roughly outwards: route_planes() drops every plane pad onto
its plane; route_critical() lays BUFIN before anything can take its space;
route_channel() does one channel and is called six times; route_board()
carries OUT and the switched nodes out to the tail connector and the
switches; route_supply() does V- and the control net.
"""

import pathlib
import sys

import pcbnew

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import design as circuit  # noqa: E402
import kicad  # noqa: E402
# The schematic writer's UUID helper, so the board derives exactly the same
# symbol identifiers the schematic wrote rather than re-implementing the hash.
from kisch import _uuid as symbol_uuid  # noqa: E402

FOOTPRINT_DIR = kicad.FOOTPRINT_DIR

TRACK = 0.25
POWER_TRACK = 0.5
VIA_DIAMETER = 0.6
VIA_DRILL = 0.3
CLEARANCE = 0.2

BLOCK_PITCH = 23.0           # between quads
BLOCK_ORIGIN = (3.0, 14.0)   # centreline of block 1, in board coords
ROW_OFFSET = 4.6             # channel rows, above and below the quad centre
CORRIDOR_X = 51.0            # OUT and SWN run up this lane to the right column
# The right-hand column. 64 rather than 62 because the corridor between the
# switched-node bus and the OUT bus has to be wide enough to land a via in:
# channel 6's switched node crosses U3's V- run, and one of the two has to
# change layer where they meet.
RIGHT_X = 64.0               # switch ICs, DIN header and control live here
BOARD_MARGIN = 3.0

# Channel placement, relative to the row: ref suffix -> (x, rank, kind).
#
# `rank` 0 sits on the row line itself, 1 on a sub-row further from the quad.
# `kind` decides orientation: "series" parts lie along the row, "shunt" parts
# stand on end so their grounded pad hangs clear of the signal lane -- a
# horizontal shunt would put its ground pad in the middle of the lane its own
# signal pad is feeding.
#
# The split into two sub-rows is what keeps the block narrow: R04/R06/C04 form
# the series chain BUFOUT -> APN -> APOUT -> OUT, while R05/C02/C03 hang off it.
ROW_PLACEMENT = {
    "J":   (5.0, 0, "conn"),      # 1=shield, 2=white (on the lane), 3=red
    "R02": (5.0, 1, "shunt"),     # 3M3 bias to ground
    "C01": (10.5, 1, "shunt"),    # 100p RF filter
    "R01": (15.0, 0, "series"),   # 1k stopper
    # R03 sits east of R01 rather than under it. Both of the buffer's own
    # feedback nets have to cross the row line to reach it, and every gap in
    # the row line west of R01.2 is spoken for -- by the connector pads, by
    # IN_W and by the lane that carries C01 up to BUFIN. East of R01.2 the row
    # is clear all the way to R04, so R03's own two pads become the crossings.
    "R03": (19.5, 1, "series"),   # 1k buffer feedback, left of the package
    "R04": (33.0, 0, "series"),   # 47k into the all-pass inverting input
    "R05": (33.0, 1, "series"),   # 47k lag into the switched node
    "R06": (38.5, 0, "series"),   # 47k all-pass feedback
    "C02": (38.5, 1, "series"),   # 100p across it
    "C04": (44.0, 0, "series"),   # 1n8 summing into the red element
    "C03": (44.0, 1, "shunt"),    # 100p lag to ground
}

SUB_ROW = 5.5        # between rank 0 and rank 1, measured away from the quad

# Quad position relative to the block centreline.
QUAD_X = 25.5

# Board-level placement: ref -> (x, y, rotation).
BOARD_PLACEMENT = {
    # Switch packages, each beside the three channels it serves.
    "U4":  (RIGHT_X, 19.0, 0),
    "U5":  (RIGHT_X, 51.0, 0),
    # Control network, between the two packages where the spine passes.
    # Spread rather than evenly spaced: y = 37 is block 2's centreline, which
    # is where that quad's V- pin has to come out, and a control part there
    # blocks the only clear row it has.
    "R702": (RIGHT_X - 2.0, 30.0, 0),
    "R701": (RIGHT_X - 2.0, 34.0, 0),
    "C701": (RIGHT_X - 2.0, 44.0, 0),
    # Rail bypass, a pair at each end of the rails. The gap to the switch
    # packages is 9.5mm rather than the 7.5 the parts need, because the strip
    # between the two carries the V- spine and the control riser -- the only
    # north-south route on the board that is east of every switched node.
    "C901": (RIGHT_X + 9.5, 8.0, 0),
    "C902": (RIGHT_X + 9.5, 12.0, 0),
    "C903": (RIGHT_X + 9.5, 62.0, 0),
    "C904": (RIGHT_X + 9.5, 66.0, 0),
    # Tail connectors laid flat along the bottom edge: standing up, the 1x09
    # is 23.95mm tall and needs a column of its own.
    "J7":  (26.0, 76.5, 90),
    "J8":  (50.0, 76.5, 90),
}


def to_mm(value):
    return pcbnew.ToMM(value)


def point(x, y):
    return pcbnew.VECTOR2I_MM(float(x), float(y))
class Board:
    def __init__(self):
        self.board = pcbnew.BOARD()
        self.board.SetCopperLayerCount(4)
        self.nets = {}
        self.footprints = {}
        self._make_nets()

    # -- nets and parts ---------------------------------------------------
    def _make_nets(self):
        for name in sorted(circuit.NETS):
            net = pcbnew.NETINFO_ITEM(self.board, name)
            self.board.Add(net)
            self.nets[name] = net

    def net(self, name):
        return self.nets[name]

    def place(self, ref, x, y, rotation):
        part = circuit.PARTS[ref]
        library, name = part.footprint.split(":", 1)
        footprint = pcbnew.FootprintLoad(str(FOOTPRINT_DIR / f"{library}.pretty"), name)
        if footprint is None:
            raise SystemExit(f"could not load footprint {part.footprint} for {ref}")
        self.board.Add(footprint)
        # FootprintLoad returns the footprint under its bare name; without the
        # library nickname KiCad cannot tie it back to a library, so
        # "Update Footprints from Library" has nothing to work from.
        footprint.SetFPIDAsString(part.footprint)
        # Link back to the schematic symbol of the same reference. The UUIDs
        # are derived from the project name, so both generators compute the
        # same value independently -- this is what makes cross-probing work
        # and stops "Update PCB from Schematic" treating every footprint as
        # a new part. Multi-unit parts link via their first unit.
        footprint.SetPath(pcbnew.KIID_PATH(
            f"/{symbol_uuid(f'{circuit.PROJECT}:part:{ref}:1')}"))
        footprint.SetSheetname("/")
        footprint.SetSheetfile(f"{circuit.PROJECT}.kicad_sch")
        footprint.SetPosition(point(x, y))
        if rotation:
            footprint.SetOrientationDegrees(rotation)
        footprint.SetReference(ref)
        footprint.SetValue(part.value)
        footprint.Reference().SetVisible(True)
        footprint.Value().SetVisible(False)
        if part.dnp:
            footprint.SetDNP(True)
        self.footprints[ref] = footprint

        # Attach every pad to the net design.py put it on.
        owner = circuit.DESIGN.pin_owner()
        for pad in footprint.Pads():
            key = (ref, pad.GetNumber())
            if key in owner:
                pad.SetNet(self.net(owner[key]))
        return footprint

    def pad(self, ref, number):
        """Absolute position of a pad, in millimetres."""
        for candidate in self.footprints[ref].Pads():
            if candidate.GetNumber() == str(number):
                position = candidate.GetPosition()
                return (round(to_mm(position.x), 4), round(to_mm(position.y), 4))
        raise KeyError(f"{ref} has no pad {number}")

    # -- copper -----------------------------------------------------------
    def track(self, net, points, layer=pcbnew.F_Cu, width=TRACK):
        for start, end in zip(points, points[1:]):
            if start == end:
                continue
            segment = pcbnew.PCB_TRACK(self.board)
            segment.SetStart(point(*start))
            segment.SetEnd(point(*end))
            segment.SetWidth(pcbnew.FromMM(width))
            segment.SetLayer(layer)
            segment.SetNet(self.net(net))
            self.board.Add(segment)

    def via(self, net, x, y):
        item = pcbnew.PCB_VIA(self.board)
        item.SetPosition(point(x, y))
        item.SetWidth(pcbnew.FromMM(VIA_DIAMETER))
        item.SetDrill(pcbnew.FromMM(VIA_DRILL))
        item.SetViaType(pcbnew.VIATYPE_THROUGH)
        item.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        item.SetNet(self.net(net))
        self.board.Add(item)

    def stub_via(self, ref, number, offset):
        """Short track from a pad to a via beside it -- how AGND, V+ and V-
        pads reach their planes.

        The net comes from design.py rather than the caller, so a via can
        never be dropped onto the wrong rail. Vias sit beside the pad, never
        in it, which keeps the board buildable with plain fab processes.
        """
        net = circuit.DESIGN.pin_owner()[(ref, str(number))]
        pad = self.pad(ref, number)
        target = (round(pad[0] + offset[0], 4), round(pad[1] + offset[1], 4))
        self.track(net, [pad, target], width=POWER_TRACK if net in
                   ("V+", "V-", "AGND") else TRACK)
        self.via(net, *target)
        return target

    def zone(self, net, layer, rectangle, priority=0):
        left, top, right, bottom = rectangle
        item = pcbnew.ZONE(self.board)
        item.SetLayer(layer)
        item.SetNet(self.net(net))
        item.SetAssignedPriority(priority)
        item.SetLocalClearance(pcbnew.FromMM(CLEARANCE))
        item.SetMinThickness(pcbnew.FromMM(0.2))
        outline = item.Outline()
        outline.NewOutline()
        for x, y in ((left, top), (right, top), (right, bottom), (left, bottom)):
            outline.Append(pcbnew.FromMM(float(x)), pcbnew.FromMM(float(y)))
        self.board.Add(item)
        return item

    def outline(self, rectangle):
        left, top, right, bottom = rectangle
        corners = [(left, top), (right, top), (right, bottom), (left, bottom), (left, top)]
        for start, end in zip(corners, corners[1:]):
            shape = pcbnew.PCB_SHAPE(self.board)
            shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
            shape.SetStart(point(*start))
            shape.SetEnd(point(*end))
            shape.SetLayer(pcbnew.Edge_Cuts)
            shape.SetWidth(pcbnew.FromMM(0.1))
            self.board.Add(shape)

    def text(self, body, x, y, size=1.0, layer=pcbnew.F_SilkS):
        item = pcbnew.PCB_TEXT(self.board)
        item.SetText(body)
        item.SetPosition(point(x, y))
        item.SetLayer(layer)
        item.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
        item.SetTextThickness(pcbnew.FromMM(size * 0.15))
        self.board.Add(item)



def block_centre(index):
    """Y of block `index`'s centreline -- the quad sits on it."""
    return BLOCK_ORIGIN[1] + (index - 1) * BLOCK_PITCH


def row_y(channel):
    """Y of a channel's passive row.

    Odd channels take the row above their quad and even channels the row
    below, matching the package: buffer A and all-pass D occupy the top half
    of the pinout, buffer B and all-pass C the bottom half.
    """
    centre = block_centre((channel + 1) // 2)
    return centre - ROW_OFFSET if channel % 2 else centre + ROW_OFFSET


def row_ref(suffix, channel):
    """Row-local part name -> the design's reference (R02 -> R102)."""
    if suffix == "J":
        return f"J{channel}"
    return f"{suffix[0]}{channel}{suffix[1:]}"


def place_blocks(board):
    """Place three quads and their six channel rows.

    `s` is the direction away from the quad for this channel: negative for the
    odd channel, which takes the row above, positive for the even one below.
    Everything about a row is mirrored through it, so both channels are laid
    out by the same code and cannot drift apart.
    """
    for index in range(1, circuit.CHANNELS // 2 + 1):
        centre = block_centre(index)
        board.place(f"U{index}", BLOCK_ORIGIN[0] + QUAD_X, centre, 0)
        for channel in (index * 2 - 1, index * 2):
            s = -1 if channel % 2 else 1
            row = row_y(channel)
            for suffix, (dx, rank, kind) in ROW_PLACEMENT.items():
                x = BLOCK_ORIGIN[0] + dx
                y = row + s * rank * SUB_ROW
                if kind == "conn":
                    # Laid flat: standing up, the 1x03 header is 8.71mm tall
                    # and becomes the tallest thing in the block, forcing the
                    # block pitch wider than the passives need.
                    rotation = 90
                else:
                    rotation = 0
                board.place(row_ref(suffix, channel), x, y, rotation)


def place_rest(board):
    for ref, (x, y, rotation) in BOARD_PLACEMENT.items():
        board.place(ref, x, y, rotation)


def free_offset(board, ref, number, candidates, clearance=0.55):
    """Pick the first stub direction that clears every other pad.

    Hand-tuning fifty-odd via offsets is where the previous board burned its
    iterations. This tries a few directions and takes the first that is far
    enough from foreign copper, so adding a part cannot silently push a via
    into its neighbour.
    """
    origin = board.pad(ref, number)
    others = [board.pad(r, p.GetNumber())
              for r, fp in board.footprints.items()
              for p in fp.Pads()
              if not (r == ref and p.GetNumber() == str(number))]
    for dx, dy in candidates:
        target = (origin[0] + dx, origin[1] + dy)
        if all(abs(target[0] - ox) > clearance or abs(target[1] - oy) > clearance
               for ox, oy in others):
            return (dx, dy)
    raise SystemExit(f"no clear stub direction for {ref}.{number}")


PLANE_NETS = {"AGND": pcbnew.In1_Cu, "V+": pcbnew.In2_Cu}


def channel_signs():
    """ref -> the direction away from that part's quad, for row parts only.

    The two halves of a block are mirror images, so a stub offset that is
    right for the odd channel is wrong for the even one. Without this the
    offsets are chosen by trial order alone, and the odd channel's ground
    stubs land clear while the even channel's land in the lane -- a fault
    that shows up on exactly half the board and looks like a routing error.
    """
    return {row_ref(suffix, channel): (-1 if channel % 2 else 1)
            for channel in range(1, circuit.CHANNELS + 1)
            for suffix in ROW_PLACEMENT}


def route_planes(board):
    """Drop every AGND and V+ pad onto its plane through a via beside the pad.

    V- is deliberately NOT a plane: at about 2 mA it never needed one, and a
    B.Cu pour is the project's worst failure mode -- fragmentation shows up as
    unconnected items far from the cause. V- is left for the router.
    """
    owner = circuit.DESIGN.pin_owner()
    # Every 14-pin package on this board is on a 1.27mm pitch and too narrow
    # for a row of stub vias beside its pads, the switches as much as the
    # op-amps.
    quads = {ref for ref, part in circuit.PARTS.items()
             if "-14_" in part.footprint and part.footprint.endswith("_P1.27mm")}
    signs = channel_signs()
    count = 0
    for (ref, number), net in sorted(owner.items()):
        if net not in PLANE_NETS:
            continue
        if ref.startswith("#"):
            continue
        if ref in quads:
            # Inboard, under the package body: the space between the two pad
            # columns is the only clear ground on a 1.27mm-pitch package. Each
            # column keeps to its own side of the centreline, so two pads at
            # the same height -- which the 4066s have and the op-amps do not --
            # cannot be given the same via.
            centre = to_mm(board.footprints[ref].GetPosition().x)
            pad = board.pad(ref, number)
            inboard = -0.9 if pad[0] < centre else 0.9
            offset = (centre - pad[0] + inboard, 0.0)
        else:
            # Towards the quad first. From a row part that is the empty strip
            # inboard of the row; from a sub-row part it is the far side of
            # the band from the lanes. The same choice for both halves of a
            # block, which is what keeps them symmetrical.
            s = signs.get(ref, -1)
            offset = free_offset(board, ref, number,
                                 [(0.0, -s * 1.6), (0.0, s * 1.6),
                                  (1.9, 0.0), (-1.9, 0.0),
                                  (1.5, 1.5), (-1.5, 1.5), (1.5, -1.5), (-1.5, -1.5)])
        board.stub_via(ref, number, offset)
        count += 1
    return count


# Lanes in the band -- the clear strip between the row pads and the sub-row
# pads, measured from the row and running away from the quad. Only three nets
# ever travel along it; everything else merely crosses it, so it is spacing
# between these three that matters and they are set a full via's width apart.
OUT_LANE = 1.35      # B.Cu, the full width of the block
IN_LANE = 2.2        # F.Cu, connector to stopper
BUFIN_LANE = 3.1     # F.Cu, C01 up to the stopper -- deeper than IN_W
APOUT_LANE = 2.4     # B.Cu, all-pass output across the right-hand half


def route_critical(board):
    """Route BUFIN first, before anything else can take the space it needs.

    BUFIN is the 3M3 node -- the highest-impedance point in the design, where
    surface leakage and stray coupling actually matter. It gets the short
    direct path from the stopper to the buffer's + input, on F.Cu over
    unbroken In1 ground for its whole length, with no via anywhere on it.

    The path leaves R01.2 *away* from the row, into the clear strip between
    the row and the block centreline, and runs east at the height of the pin
    it is aiming at. That strip is empty -- the two feedback nets that share
    this side of the package travel it on B.Cu -- so BUFIN never crosses
    anything and never changes layer.
    """
    for channel in range(1, circuit.CHANNELS + 1):
        s = -1 if channel % 2 else 1
        index = (channel + 1) // 2
        quad = f"U{index}"
        half = "odd" if channel % 2 else "even"
        _, (_, _, buf_in) = circuit.QUAD_UNITS[half]["buf"]
        target = board.pad(quad, buf_in)
        stopper = board.pad(row_ref("R01", channel), 2)
        filt = board.pad(row_ref("C01", channel), 1)
        net = f"BUFIN{channel}"
        board.track(net, [stopper, (stopper[0], target[1]), target])
        # C01 joins from the sub-row on the far side of IN_W's lane: it comes
        # up to a lane of its own, runs east past where IN_W turns down, and
        # drops onto the stopper pad. Deeper than IN_W, so their verticals
        # never meet.
        joint = round(row_y(channel) + s * BUFIN_LANE, 4)
        board.track(net, [filt, (filt[0], joint), (stopper[0], joint), stopper])


def route_channel(board, channel):
    """Route one channel. Six identical calls, so a fix here is a fix everywhere.

    `s` points away from the quad: -1 for the odd channel on the row above,
    +1 for the even one below. Every offset is multiplied by it, so both
    halves of a block come out of the same code and cannot drift apart.

    Two structural facts decide the whole thing.

    **The row line is the only place a net can change sides.** Row parts and
    sub-row parts sit on two parallel lines with the band between them, and
    the quad sits on the far side of the row. So every net that leaves the
    package for a sub-row part crosses the row line exactly once, and the
    crossings have to be shared out between the gaps in it. The gaps are
    measured, not assumed: a 1206 leaves 1.8mm between its own two pads, and
    that is where most of the crossings go.

    **A net leaving the package deeper than another cannot turn towards the
    row inside the other's span.** The three right-hand pins come out at
    three different depths, and their targets run the opposite way along the
    row -- so the natural order is exactly backwards. APOUT, the shallowest
    pin with the furthest target, is the one that has to give: it crosses the
    row line immediately and makes its traverse on B.Cu, under the band, and
    the other two then cross it without touching it. It is a low-impedance
    op-amp output, so the layer change costs nothing.

    B.Cu carries what has to traverse the block -- OUT, APOUT, the switched
    node's jump under C02, and both buffer feedback nets under the package.
    That is only affordable because V- is no longer a pour: a crossing costs
    two vias rather than a hole in the negative rail.
    """
    s = -1 if channel % 2 else 1
    index = (channel + 1) // 2
    quad = f"U{index}"
    half = "odd" if channel % 2 else "even"
    _, (buf_out, buf_fb, _) = circuit.QUAD_UNITS[half]["buf"]
    _, (ap_out, ap_n, ap_p) = circuit.QUAD_UNITS[half]["ap"]
    n = channel
    row = row_y(n)
    sub = round(row + s * SUB_ROW, 4)

    def p(suffix, number):
        return board.pad(row_ref(suffix, n), number)

    def q(number):
        return board.pad(quad, number)

    def lane(k):
        """A track offset k mm from the row, away from the quad.

        The clear band runs from the edge of the row pads to the edge of the
        sub-row pads. Straying outside it puts a track straight through a pad
        row, which DRC reports as dozens of shorts far from the real mistake --
        exactly how SWN was routed along the sub-row itself for a while.
        """
        assert 1.175 < k < SUB_ROW - 1.175, (
            f"lane({k}) is outside the clear band "
            f"(1.175 .. {SUB_ROW - 1.175}) -- it would cross a pad row")
        return round(row + s * k, 4)

    def between(left, right):
        """x midway between two pads -- where a crossing of the row line goes.

        Taking the midpoint of the two pad centres rather than a fixed offset
        means the gap is always found even if a part moves, and a 1206's own
        1.8mm pad gap is wide enough that the midpoint is comfortable.
        """
        return round((left[0] + right[0]) / 2, 4)

    def hop(net, start, end, layer=pcbnew.B_Cu):
        """Dive to `layer` at `start` and surface at `end`."""
        board.via(net, *start)
        board.track(net, [start, end], layer=layer)
        board.via(net, *end)

    # -- white element in: J.2 out to a lane, then back to the stopper -------
    # J's three pads sit along the row, so nothing can leave the connector
    # along it -- the shield and the red element are in the way.
    white = f"IN_W{n}"
    board.track(white, [p("J", 2), (p("J", 2)[0], lane(IN_LANE)),
                        (p("R01", 1)[0], lane(IN_LANE)), p("R01", 1)])
    board.track(white, [(p("J", 2)[0], lane(IN_LANE)),
                        (p("R02", 1)[0], lane(IN_LANE)), p("R02", 1)])

    # -- red element straight through to the summing node -------------------
    # OUT is the high-impedance piezo node and has to cross the whole block,
    # so it goes under it rather than fighting for a lane on the front. Its
    # B.Cu run is the reason every other crossing of the band is on F.Cu.
    out = f"OUT{n}"
    dive = (p("J", 3)[0], lane(OUT_LANE))
    land = (p("C04", 2)[0], lane(OUT_LANE))
    board.track(out, [p("J", 3), dive])
    hop(out, dive, land)
    board.track(out, [land, p("C04", 2)])

    # -- buffer feedback and output -----------------------------------------
    # The buffer's three pins sit in one column, so anything leaving pin 1 or
    # pin 2 leftward crosses whatever arrives at pin 3 from the left. BUFIN is
    # the 3M3 node and must have the short direct approach, so it keeps that
    # strip to itself and the other two dive inboard -- between the pad
    # columns, the same clear ground the power stubs use -- and travel west
    # under the package on B.Cu at the height of their own pin. They surface
    # on the row line at R03's own two pads, which is why R03 sits east of
    # R01: those two pads are the only crossings left on this side.
    fbnet = f"BUFFB{n}"
    fb_pin = q(buf_fb)
    fb_dive = (round(fb_pin[0] + 2.6, 4), fb_pin[1])
    fb_cross = (p("R03", 1)[0], row)
    board.track(fbnet, [fb_pin, fb_dive])
    board.via(fbnet, *fb_dive)
    board.track(fbnet, [fb_dive, (fb_cross[0], fb_dive[1]), fb_cross],
                layer=pcbnew.B_Cu)
    board.via(fbnet, *fb_cross)
    board.track(fbnet, [fb_cross, p("R03", 1)])

    # BUFOUT leaves the same way but goes both ways from its via: west to the
    # feedback resistor and east to the all-pass input pair, staying under
    # the row the whole way so it never enters the band.
    outnet = f"BUFOUT{n}"
    out_pin = q(buf_out)
    out_dive = (round(out_pin[0] + 1.5, 4), out_pin[1])
    out_west = (p("R03", 2)[0], row)
    out_east = (between(p("R04", 1), p("R04", 2)), row)
    board.track(outnet, [out_pin, out_dive])
    board.via(outnet, *out_dive)
    for corner in (out_west, out_east):
        board.track(outnet, [out_dive, (corner[0], out_dive[1]), corner],
                    layer=pcbnew.B_Cu)
        board.via(outnet, *corner)
    board.track(outnet, [out_west, (out_west[0], sub)])
    board.track(outnet, [out_east, p("R04", 1)])
    board.track(outnet, [out_east, (out_east[0], sub), p("R05", 1)])

    # -- all-pass output: across the block on B.Cu, under the band -----------
    # Taken first because it is what lets the other two right-hand nets stay
    # on F.Cu: it crosses the row line at once, in the gap between the quad
    # and R04, and surfaces again only at its own crossing further east.
    apout = f"APOUT{n}"
    ao_pin = q(ap_out)
    ao_turn = between(ao_pin, p("R04", 1))
    ao_cross = between(p("R06", 2), p("C04", 1))
    ao_dive = (ao_turn, lane(APOUT_LANE))
    ao_land = (ao_cross, lane(APOUT_LANE))
    board.track(apout, [ao_pin, (ao_turn, ao_pin[1]), ao_dive])
    hop(apout, ao_dive, ao_land)
    board.track(apout, [ao_land, (ao_cross, row)])
    board.track(apout, [p("R06", 2), p("C04", 1)])
    board.track(apout, [ao_land, (ao_cross, sub), p("C02", 2)])

    # -- all-pass inverting input -------------------------------------------
    # Runs east at its own pin height and drops through R06's 1206 gap, which
    # puts it on the row run between R04.2 and R06.1 and directly under C02.1.
    apn = f"APN{n}"
    an_pin = q(ap_n)
    an_cross = between(p("R06", 1), p("R06", 2))
    board.track(apn, [an_pin, (an_cross, an_pin[1]), (an_cross, row)])
    board.track(apn, [(an_cross, row), p("R06", 1)])
    board.track(apn, [p("R04", 2), p("R06", 1)])
    board.track(apn, [(an_cross, row), (an_cross, sub), p("C02", 1)])

    # -- switched node ------------------------------------------------------
    # The deepest of the three right-hand pins, so it crosses the row line
    # furthest east -- through C04's own pad gap, past both the others. From
    # there it works back west along the sub-row, jumping under C02 on B.Cu
    # because C02 and R06 are stacked and block the sub-row between them.
    swn = f"SWN{n}"
    sw_pin = q(ap_p)
    sw_cross = between(p("C04", 1), p("C04", 2))
    sw_jump = between(p("R05", 2), p("C02", 1))
    board.track(swn, [sw_pin, (sw_cross, sw_pin[1]), (sw_cross, sub)])
    board.track(swn, [(sw_cross, sub), p("C03", 1)])
    hop(swn, (sw_cross, sub), (sw_jump, sub))
    board.track(swn, [(sw_jump, sub), p("R05", 2)])


# The corridor between the blocks and the right-hand column. Twelve nets
# leave the blocks here -- six OUT and six SWN -- and the two families pull in
# opposite directions, which is what decides the layers.
#
# OUT leaves at the top of the board and has to reach a header pin at the
# bottom, and J7's pins run the same way as the channels while the corridor
# fills from the outside in. So OUT's corridor lane order and its fan-in
# order are reversed with respect to each other and cannot both be satisfied
# on one layer: the descent goes on B.Cu and only the fan-in surfaces.
#
# SWN stays entirely on F.Cu, which is why the two never meet.
OUT_BUS_X = 55.4         # channel 6's lane; channel 1 is the outermost
OUT_BUS_PITCH = 0.6
# Channel 1's approach row is the one nearest the header, because its header
# pin is the furthest west: it has to leave the bus before any of the others
# and pass under none of their drops. Only the drop onto the pin surfaces --
# the fan-in itself stays on B.Cu, which is what lets the bus keep channel 1
# outermost at the same time.
OUT_FANIN_Y = 75.15      # channel 1, just clear of the header pads
OUT_FANIN_PITCH = -0.765
SWN_BUS_X = 50.4         # channel 1's lane; the bus fills outwards
SWN_BUS_PITCH = 0.7
SWITCH_CLEARANCE = 2.2   # below a switch package, for the right-column cells
# Lane order on the SWN bus, innermost lane first. Channel 2 leaves its block
# below channel 1's cell, so channel 1 has to turn off the bus outside it --
# otherwise the row channel 1 leaves on and the lane channel 2 arrives on run
# 0.08mm apart. Everywhere else the channel order already matches the cells.
SWN_BUS_ORDER = (2, 1, 3, 4, 5, 6)


def route_board(board):
    """Carry OUT and the switched nodes out of the blocks.

    Both families leave a block at a height the channel already established
    -- OUT on its own B.Cu spine, SWN at the height of the quad pin it came
    from -- so neither needs a lane inside the block to get here.
    """
    switches = {ref: to_mm(board.footprints[ref].GetPosition().x)
                for ref in ("U4", "U5")}
    count = 0
    for channel in range(1, circuit.CHANNELS + 1):
        s = -1 if channel % 2 else 1
        row = row_y(channel)
        index = (channel + 1) // 2
        half = "odd" if channel % 2 else "even"
        _, (_, _, ap_p) = circuit.QUAD_UNITS[half]["ap"]

        # -- OUT: B.Cu the whole way down, surfacing only to fan in ---------
        # Channel 1 takes the outermost lane and the highest approach row:
        # its header pin is the furthest west, so it has to leave the bus
        # before any of the others and cross none of their drops.
        net = f"OUT{channel}"
        head = board.pad(row_ref("C04", channel), 2)
        bus = round(OUT_BUS_X + (circuit.CHANNELS - channel) * OUT_BUS_PITCH, 4)
        fan = round(OUT_FANIN_Y + (channel - 1) * OUT_FANIN_PITCH, 4)
        assert fan > row + s * SUB_ROW + 1.2, (
            f"OUT{channel} approach row at {fan} clips the last sub-row")
        spine = round(row + s * OUT_LANE, 4)
        pin = board.pad("J7", channel)
        board.track(net, [(head[0], spine), (bus, spine), (bus, fan),
                          (pin[0], fan)], layer=pcbnew.B_Cu)
        board.via(net, pin[0], fan)
        board.track(net, [(pin[0], fan), pin])

        # -- SWN: F.Cu out to its switch cell -------------------------------
        # The cells on the package's right-hand column cannot be reached
        # along their own row without crossing the package, so those come
        # round underneath it instead.
        net = f"SWN{channel}"
        leave = round((board.pad(row_ref("C04", channel), 1)[0] +
                       board.pad(row_ref("C04", channel), 2)[0]) / 2, 4)
        lane = board.pad(f"U{index}", ap_p)[1]
        bus = round(SWN_BUS_X + SWN_BUS_ORDER.index(channel) * SWN_BUS_PITCH, 4)
        cell = next((ref, number) for ref, number in circuit.NETS[net]
                    if ref in switches)
        target = board.pad(*cell)
        if target[0] > switches[cell[0]]:
            box = board.footprints[cell[0]].GetCourtyard(pcbnew.F_CrtYd).BBox()
            approach = round(to_mm(box.GetBottom()) + SWITCH_CLEARANCE, 4)
            tail = [(target[0], approach), target]
        else:
            approach = target[1]
            tail = [target]
        board.track(net, [(leave, lane), (bus, lane), (bus, approach)] + tail)
        count += 2
    return count


# The three nets that have to get past the corridor rather than into it.
#
# OUT fills B.Cu from top to bottom and SWN fills F.Cu, so between them the
# corridor is closed to anything travelling the length of the board. All three
# of these run instead down the strip between the switch packages and the
# bypass caps -- the one column east of every switched node -- and reach the
# tail connectors along the bottom edge, below the headers rather than above,
# where the OUT fan-in already occupies every row.
VMINUS_X = 69.0          # B.Cu spine, tapped by every V- pin on the board
CTL_RISER_X = 70.4       # B.Cu, beside it, for the two right-column cells
CTL_SPINE_X = 59.3       # between the OUT bus and the control network's pads
TOG_RISER_X = 76.8       # outboard of everything, in the margin past the caps
# The three approach rows above the tail connectors, on F.Cu. The row order
# is set by how far west each one has to drop: V- reaches the furthest, so it
# turns off first and takes the row furthest from the pads.
TAIL_Y = {"V-": 72.0, "SW_TOG": 73.0, "SW_CTL": 74.0}
V_STEP = 1.19            # how far a switch's pin 7 steps clear of the package


def route_supply(board):
    """V-, the switch control net and the toggle line.

    V- is an ordinary net here rather than a pour, which is the whole point of
    the stackup change: at about 2mA it never needed copper, and a fragmented
    B.Cu pour was this project's worst failure mode. What it costs is this
    function.
    """
    F, B = pcbnew.F_Cu, pcbnew.B_Cu
    p = board.pad

    def tap(net, pad, x, y=None, layer=F):
        """Run from a pad to the spine at `x` and drop a via onto it."""
        y = pad[1] if y is None else y
        board.track(net, [pad, (pad[0], y), (x, y)], layer=layer)
        board.via(net, x, y)

    def hop(net, x, top, bottom, layer=B):
        board.via(net, x, top)
        board.track(net, [(x, top), (x, bottom)], layer=layer)
        board.via(net, x, bottom)

    # -- V- ----------------------------------------------------------------
    # Every V- pin taps the same B.Cu spine. The two bottom-left switch pins
    # are the only ones that cannot go straight out: pin 8 of each package
    # sits at the same height on the other column, so they step down first,
    # into the gap the switched node's own approach row leaves free.
    board.track("V-", [(VMINUS_X, 12.0), (VMINUS_X, 66.0)], layer=B,
                width=POWER_TRACK)
    tap("V-", p("C902", 1), VMINUS_X)
    tap("V-", p("C904", 1), VMINUS_X)
    tap("V-", p("R701", 2), VMINUS_X)
    for switch in ("U4", "U5"):
        box = board.footprints[switch].GetCourtyard(pcbnew.F_CrtYd).BBox()
        # Pin 7 is the bottom of the left column and pin 8 the bottom of the
        # right, at the same height -- so pin 7 cannot leave along its own row,
        # and the row below is the one the switched node arrives on. It drops
        # to B.Cu instead, in the gap between the two.
        step = round(p(switch, 7)[1] + V_STEP, 4)
        assert step < to_mm(box.GetBottom()) + SWITCH_CLEARANCE, (
            f"{switch} V- step at {step} is under the switched node's row")
        tap("V-", p(switch, 12), VMINUS_X)
        board.track("V-", [p(switch, 7), (p(switch, 7)[0], step)])
        board.via("V-", p(switch, 7)[0], step)
        board.track("V-", [(p(switch, 7)[0], step), (VMINUS_X, step)], layer=B)
    # The quads reach it along their own centrelines -- the one row in a block
    # with no channel routing on it, because the two halves are mirrored about
    # it. Each still has to get past the two buses, and each does it
    # differently because what blocks it differs.
    #
    # U1: channel 1's switched node crosses the centreline on the SWN bus, so
    # this one dives under the bus and comes up beyond it.
    centre = p("U1", 11)[1]
    board.track("V-", [p("U1", 11), (50.0, centre)])
    board.via("V-", 50.0, centre)
    board.track("V-", [(50.0, centre), (52.0, centre)], layer=B)
    board.via("V-", 52.0, centre)
    board.track("V-", [(52.0, centre), (52.0, 12.0), (p("C902", 1)[0], 12.0)])
    # U2: nothing crosses y=37, which is why the control network was moved
    # off it, so this one runs straight out.
    board.track("V-", [p("U2", 11), (VMINUS_X, p("U2", 11)[1])])
    board.via("V-", VMINUS_X, p("U2", 11)[1])
    # U3: channel 6's switched node crosses this row on its way up the bus,
    # and it is the one crossing on the board that cannot be designed away --
    # the pin, the lane and the cell are all fixed. So V- dives under it, in
    # the gap deliberately left between the two buses.
    centre = p("U3", 11)[1]
    board.track("V-", [p("U3", 11), (53.0, centre)])
    board.via("V-", 53.0, centre)
    board.track("V-", [(53.0, centre), (54.65, centre)], layer=B)
    board.via("V-", 54.65, centre)
    board.track("V-", [(54.65, centre), (VMINUS_X, centre)])
    board.via("V-", VMINUS_X, centre)
    # Down to the DIN pin. The rows above the header are free on F.Cu --
    # the OUT fan-in is all on B.Cu and its drops are all west of here -- so
    # the riser surfaces and the last stretch runs on the front.
    board.track("V-", [(VMINUS_X, 66.0), (VMINUS_X, TAIL_Y["V-"])], layer=B,
                width=POWER_TRACK)
    board.via("V-", VMINUS_X, TAIL_Y["V-"])
    board.track("V-", [(VMINUS_X, TAIL_Y["V-"]),
                       (p("J7", 8)[0], TAIL_Y["V-"]), p("J7", 8)])

    # -- SW_CTL ------------------------------------------------------------
    # Nine pins on one net, spread over both switch packages and the control
    # network. The spine runs on B.Cu wherever it has to pass one of the
    # switched nodes' approach rows or a quad's V- run, and surfaces only
    # where something taps it.
    ctl = "SW_CTL"
    board.track(ctl, [p("U4", 5), (CTL_SPINE_X, p("U4", 5)[1])])
    board.track(ctl, [p("U4", 6), (CTL_SPINE_X, p("U4", 6)[1])])
    board.track(ctl, [(CTL_SPINE_X, p("U4", 5)[1]), (CTL_SPINE_X, 24.0)])
    hop(ctl, CTL_SPINE_X, 24.0, 32.5)
    board.track(ctl, [(CTL_SPINE_X, 32.5), (CTL_SPINE_X, 35.5)])
    board.track(ctl, [(CTL_SPINE_X, p("R701", 1)[1]), p("R701", 1)])
    hop(ctl, CTL_SPINE_X, 35.5, 42.5)
    board.track(ctl, [(CTL_SPINE_X, 42.5), (CTL_SPINE_X, 45.5)])
    board.track(ctl, [(CTL_SPINE_X, p("C701", 1)[1]), p("C701", 1)])
    hop(ctl, CTL_SPINE_X, 45.5, 51.0)
    board.track(ctl, [(CTL_SPINE_X, 51.0), (CTL_SPINE_X, p("U5", 6)[1])])
    board.track(ctl, [(CTL_SPINE_X, p("U5", 5)[1]), p("U5", 5)])
    board.track(ctl, [(CTL_SPINE_X, p("U5", 6)[1]), p("U5", 6)])
    # The two right-column cells and the toggle get their own riser, joined
    # to the spine on the one row between the control parts that is free.
    board.track(ctl, [(CTL_SPINE_X, 39.5), (CTL_RISER_X, 39.5)])
    board.via(ctl, CTL_SPINE_X, 39.5)
    board.via(ctl, CTL_RISER_X, 39.5)
    board.track(ctl, [(CTL_RISER_X, p("U4", 13)[1]),
                      (CTL_RISER_X, TAIL_Y[ctl])], layer=B)
    tap(ctl, p("U4", 13), CTL_RISER_X)
    tap(ctl, p("U5", 13), CTL_RISER_X)
    board.via(ctl, CTL_RISER_X, TAIL_Y[ctl])
    board.track(ctl, [(CTL_RISER_X, TAIL_Y[ctl]),
                      (p("J8", 2)[0], TAIL_Y[ctl]), p("J8", 2)])

    # -- SW_TOG ------------------------------------------------------------
    # One resistor to one header pin, but the whole board is in between.
    tog = "SW_TOG"
    tap(tog, p("R702", 2), TOG_RISER_X)
    board.track(tog, [(TOG_RISER_X, p("R702", 2)[1]),
                      (TOG_RISER_X, TAIL_Y[tog])], layer=B)
    board.via(tog, TOG_RISER_X, TAIL_Y[tog])
    board.track(tog, [(TOG_RISER_X, TAIL_Y[tog]),
                      (p("J8", 1)[0], TAIL_Y[tog]), p("J8", 1)])


def add_copper(board, rectangle):
    """AGND on In1, V+ on In2. B.Cu is a signal layer, not a V- pour.

    Two planes rather than three: every supply and ground pad reaches its rail
    through a single via, and the high-impedance piezo traces on the front run
    over unbroken ground. V- is routed like any other net.
    """
    board.zone("AGND", pcbnew.In1_Cu, rectangle)
    board.zone("V+", pcbnew.In2_Cu, rectangle)


def silkscreen(board, rectangle):
    left, top, right, bottom = rectangle
    middle = (left + right) / 2
    board.text("RMC pizz/arco  6 channel  rev B", middle, top + 1.8, size=1.4)
    # The polarity is the thing that destroys the board if the loom is built
    # backwards, and there is deliberately no reverse-protection diode -- at
    # 9V total a series Schottky would cost about 0.6dB of headroom we do not
    # have. This silkscreen is the only defence.
    board.text("J7  1-6=STRINGS  7=+4.5V  8=-4.5V  9=SHELL/GND",
               middle, bottom - 3.4, size=1.2)
    board.text(f"POWERED FROM POLY-DRIVE II  {circuit.SUPPLY_RANGE}  "
               f"CHECK POLARITY BEFORE FIRST POWER-UP", middle, bottom - 1.4, size=1.0)
    for channel in range(1, circuit.CHANNELS + 1):
        board.text(f"CH{channel} G/W/R", BLOCK_ORIGIN[0] + 6.0,
                   row_y(channel) - 2.6, size=0.9)
    board.text("PIZZ=CLOSED", BOARD_PLACEMENT["J8"][0] - 6.0,
               BOARD_PLACEMENT["J8"][1] - 3.2, size=0.9)


def board_extent(board):
    """Outline from the placed parts, so the board is never bigger than it is."""
    xs, ys = [], []
    for footprint in board.footprints.values():
        box = footprint.GetCourtyard(pcbnew.F_CrtYd).BBox()
        xs += [to_mm(box.GetLeft()), to_mm(box.GetRight())]
        ys += [to_mm(box.GetTop()), to_mm(box.GetBottom())]
    return (0.0, 0.0,
            round(max(xs) + BOARD_MARGIN, 1), round(max(ys) + BOARD_MARGIN, 1))


def export_dsn(board, path):
    """Write the Specctra design alongside the board.

    The board is fully routed here, so nothing needs an autorouter -- this is
    kept because it is the one export that carries placement, netlist and
    existing copper together, which makes it the file to hand to any external
    tool that wants to re-route a region by hand.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if not pcbnew.ExportSpecctraDSN(board.board, str(path)):
        raise SystemExit(f"Specctra DSN export failed: {path}")
    return path


def main():
    board = Board()
    place_blocks(board)
    place_rest(board)

    stubs = route_planes(board)
    route_critical(board)
    for channel in range(1, circuit.CHANNELS + 1):
        route_channel(board, channel)
    route_board(board)
    route_supply(board)

    rectangle = board_extent(board)
    board.outline(rectangle)
    inner = (rectangle[0] + 0.3, rectangle[1] + 0.3,
             rectangle[2] - 0.3, rectangle[3] - 0.3)
    add_copper(board, inner)
    silkscreen(board, rectangle)

    here = pathlib.Path(__file__).parent
    destination = here / circuit.PROJECT / f"{circuit.PROJECT}.kicad_pcb"
    pcbnew.ZONE_FILLER(board.board).Fill(board.board.Zones())
    pcbnew.SaveBoard(str(destination), board.board)
    export_dsn(board, here / "build" / f"{circuit.PROJECT}.dsn")

    print(f"wrote {destination}")
    print(f"  {len(board.footprints)} footprints, {stubs} plane stubs, "
          f"{len(list(board.board.GetTracks()))} track/via items")
    print(f"  board {rectangle[2]:.1f} x {rectangle[3]:.1f} mm "
          f"= {rectangle[2] * rectangle[3]:.0f} mm2")
    print("  DSN written alongside it for external tools")


if __name__ == "__main__":
    main()
