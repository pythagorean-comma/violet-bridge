"""Build the PCB for the design in design.py.

Four layers: signals on F.Cu and B.Cu, a solid AGND plane on In1.Cu and a
V+ plane on In2.Cu. That choice is what keeps the routing simple and the
board quiet -- every supply and ground connection becomes a via rather than
a track, and the high-impedance piezo traces run directly over an unbroken
ground plane. V- is a pour on B.Cu.

The board is three blocks, each one OPA4191 serving two channels. The quad's
pinout does most of the work: every pin of buffers A and B is on the left of
the package and every pin of all-passes C and D is on the right, so a
channel's buffer feedback stays entirely left, its all-pass feedback entirely
right, and the only net that has to cross the package is BUFOUT -- which is a
low-impedance node and can go anywhere.

Track waypoints are given relative to real pad positions read back from the
placed footprints, so nothing here depends on guessing KiCad's rotation
conventions.
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
RIGHT_X = 62.0               # switch ICs, DIN header and control live here
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
    "R03": (16.0, 1, "series"),   # 1k buffer feedback, left of the package
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
    "R702": (RIGHT_X - 2.0, 33.0, 0),
    "R701": (RIGHT_X - 2.0, 37.0, 0),
    "C701": (RIGHT_X - 2.0, 41.0, 0),
    # Rail bypass, a pair at each end of the rails.
    "C901": (RIGHT_X + 7.5, 8.0, 0),
    "C902": (RIGHT_X + 7.5, 12.0, 0),
    "C903": (RIGHT_X + 7.5, 62.0, 0),
    "C904": (RIGHT_X + 7.5, 66.0, 0),
    # Tail connectors laid flat along the bottom edge: standing up, the 1x09
    # is 23.95mm tall and needs a column of its own.
    "J7":  (26.0, 76.0, 90),
    "J8":  (50.0, 76.0, 90),
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


def route_planes(board):
    """Drop every AGND and V+ pad onto its plane through a via beside the pad.

    V- is deliberately NOT a plane: at about 2 mA it never needed one, and a
    B.Cu pour is the project's worst failure mode -- fragmentation shows up as
    unconnected items far from the cause. V- is left for the router.
    """
    owner = circuit.DESIGN.pin_owner()
    quads = {f"U{i}" for i in range(1, circuit.CHANNELS // 2 + 1)}
    count = 0
    for (ref, number), net in sorted(owner.items()):
        if net not in PLANE_NETS:
            continue
        if ref.startswith("#"):
            continue
        if ref in quads:
            # Inboard, under the package body: the space between the two pad
            # columns is the only clear ground on a 1.27mm-pitch package.
            centre = to_mm(board.footprints[ref].GetPosition().x)
            pad = board.pad(ref, number)
            offset = (centre - pad[0] + (-0.9 if net == "V+" else 0.9), 0.0)
        else:
            offset = free_offset(board, ref, number,
                                 [(0.0, 1.6), (0.0, -1.6), (1.9, 0.0), (-1.9, 0.0),
                                  (1.5, 1.5), (-1.5, 1.5), (1.5, -1.5), (-1.5, -1.5)])
        board.stub_via(ref, number, offset)
        count += 1
    return count


def route_critical(board):
    """Hand-route only what the autorouter must not be trusted with.

    BUFIN is the 3M3 node -- the highest-impedance point in the design, where
    surface leakage and stray coupling actually matter. It gets the short
    direct path from the stopper to the buffer's + input, over unbroken In1
    ground, before the router sees the board. Everything else is fair game.
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
        turn = round(target[0] - 2.0, 4)
        net = f"BUFIN{channel}"
        board.track(net, [stopper, (turn, stopper[1]), (turn, target[1]), target])
        board.track(net, [filt, (filt[0], round(filt[1] - s * 2.7, 4)),
                          (turn, round(filt[1] - s * 2.7, 4)), (turn, stopper[1])])


def route_channel(board, channel):
    """Route one channel. Six identical calls, so a fix here is a fix everywhere.

    `s` points away from the quad: -1 for the odd channel on the row above,
    +1 for the even one below. Every offset is multiplied by it, so both
    halves of a block come out of the same code and cannot drift apart.

    B.Cu carries the two nets that must traverse the whole block -- OUT and
    the switched node -- while everything local stays on F.Cu. That split is
    only affordable because V- is no longer a pour: with B.Cu free, a crossing
    costs two vias instead of a hole in the negative rail.
    """
    s = -1 if channel % 2 else 1
    index = (channel + 1) // 2
    quad = f"U{index}"
    half = "odd" if channel % 2 else "even"
    _, (buf_out, buf_fb, _) = circuit.QUAD_UNITS[half]["buf"]
    _, (ap_out, ap_n, ap_p) = circuit.QUAD_UNITS[half]["ap"]
    n = channel

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
        return round(row_y(n) + s * k, 4)

    def hop(net, start, end, layer=pcbnew.B_Cu):
        """Dive to `layer` at `start` and surface at `end`."""
        board.via(net, *start)
        board.track(net, [start, end], layer=layer)
        board.via(net, *end)

    # -- white element in: J.2 out to a lane, then back to the stopper -------
    # J's three pads sit along the row, so nothing can leave the connector
    # along it -- the shield and the red element are in the way.
    white = f"IN_W{n}"
    board.track(white, [p("J", 2), (p("J", 2)[0], lane(2.6)),
                        (p("R01", 1)[0], lane(2.6)), p("R01", 1)])
    board.track(white, [(p("J", 2)[0], lane(2.6)), (p("R02", 1)[0], lane(2.6)),
                        p("R02", 1)])

    # -- buffer feedback and output -----------------------------------------
    board.track(f"BUFFB{n}", [q(buf_fb), (q(buf_fb)[0] - 3.5, q(buf_fb)[1]),
                              (q(buf_fb)[0] - 3.5, lane(4.10)),
                              (p("R03", 1)[0], lane(4.10)), p("R03", 1)])

    out_pad = q(buf_out)
    board.track(f"BUFOUT{n}", [out_pad, (out_pad[0] - 1.8, out_pad[1])])
    hop(f"BUFOUT{n}", (out_pad[0] - 1.8, out_pad[1]),
        (p("R04", 1)[0] - 2.4, out_pad[1]))
    board.track(f"BUFOUT{n}", [(p("R04", 1)[0] - 2.4, out_pad[1]), p("R04", 1)])
    board.track(f"BUFOUT{n}", [(p("R04", 1)[0] - 2.4, out_pad[1]),
                               (p("R04", 1)[0] - 1.6, p("R05", 1)[1]), p("R05", 1)])
    board.track(f"BUFOUT{n}", [(out_pad[0] - 1.8, out_pad[1]),
                               (out_pad[0] - 1.8, p("R03", 2)[1]), p("R03", 2)])

    # -- all-pass: inverting side, then the feedback pair --------------------
    board.track(f"APN{n}", [q(ap_n), (q(ap_n)[0] + 2.2, q(ap_n)[1]),
                            (q(ap_n)[0] + 2.2, lane(3.2)),
                            (p("R06", 1)[0], lane(2.15)), p("R06", 1)])
    board.track(f"APN{n}", [p("R04", 2), p("R06", 1)])
    board.track(f"APN{n}", [(p("C02", 1)[0], lane(3.2)), p("C02", 1)])

    board.track(f"APOUT{n}", [q(ap_out), (q(ap_out)[0] + 1.2, q(ap_out)[1]),
                              (q(ap_out)[0] + 1.2, lane(2.15)),
                              (p("C04", 1)[0], lane(3.2)), p("C04", 1)])
    board.track(f"APOUT{n}", [p("R06", 2), p("C04", 1)])
    board.track(f"APOUT{n}", [(p("C02", 2)[0], lane(2.15)), p("C02", 2)])

    # -- switched node: local on F.Cu, then under the block on B.Cu ----------
    swn = f"SWN{n}"
    board.track(swn, [q(ap_p), (q(ap_p)[0] + 3.2, q(ap_p)[1]),
                      (q(ap_p)[0] + 3.2, lane(4.0)),
                      (p("R05", 2)[0], lane(4.0)), p("R05", 2)])
    # C02 sits between R05 and C03 on the sub-row, so the switched node goes
    # under it. Via offsets are sized off C02's pad edges, not guessed.
    leave = (round(p("R05", 2)[0] + 1.0, 4), p("R05", 2)[1])
    land = (round(p("C03", 1)[0] - 1.4, 4), p("C03", 1)[1])
    board.track(swn, [p("R05", 2), leave])
    hop(swn, leave, land)
    board.track(swn, [land, p("C03", 1)])

    # -- red element straight through to the summing node -------------------
    # OUT is the high-impedance piezo node and has to cross the whole block,
    # so it goes under it rather than fighting for a lane on the front.
    out = f"OUT{n}"
    board.track(out, [p("J", 3), (p("J", 3)[0], lane(1.5))])
    hop(out, (p("J", 3)[0], lane(1.5)), (p("C04", 2)[0], lane(1.5)))
    board.track(out, [(p("C04", 2)[0], lane(1.5)), p("C04", 2)])


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
    """Hand the placed, part-routed board to the autorouter.

    Everything already laid down -- the plane stubs and the BUFIN runs -- is
    exported as existing wiring, so freerouting works around it rather than
    ripping it up.
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
    print(f"  DSN written for the autorouter; import the SES to finish routing")


if __name__ == "__main__":
    main()
