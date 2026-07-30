"""Build the PCB for the design in design.py.

Four layers: signals on F.Cu and B.Cu, a solid AGND plane on In1.Cu and a
V+ plane on In2.Cu. That choice is what keeps the routing simple and the
board quiet -- every supply and ground connection becomes a via rather than
a track, and the high-impedance piezo traces run directly over an unbroken
ground plane. V- is a pour on B.Cu.

One channel is placed and routed once in tile-local coordinates and repeated
six times, so the six channels are physically identical.

Track waypoints are given relative to real pad positions read back from the
placed footprints, so nothing here depends on guessing KiCad's rotation
conventions.
"""

import os
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

# The board is machine-assembled now, so the layout is spaced for a placement
# head rather than a soldering iron. That alone is most of the size change:
# the old board carried the same circuit at 17% land utilisation.
#
# The op-amp is still SOIC-8, so the tile's *vertical* structure is unchanged
# -- every lane in a channel is derived from a SOIC pin, and those have not
# moved. What shrinks is the horizontal spacing between passives, and how
# close the top and bottom rows can sit to the package now they are 0402.
#
# 12 mm pitch is what the tile actually needs, and it is set by routing rather
# than by parts. A channel has to carry five lanes past its op-amp -- OUT
# above, BUFOUT and the APN jumper over the package, APOUT below them, and SWN
# underneath -- and each wants 0.65 mm of width and clearance. Squeezing the
# rows closer than this leaves the lanes nowhere to go, which is the thing
# that actually limits the tile, not the size of an 0402.
TILE_PITCH = 12.0
TILE_ORIGIN = (2.0, 3.0)     # top-left of channel 1's tile, in board coords
BOARD_MARGIN = 3.0

BOARD_W = 56.0
BOARD_H = 94.0

# Tile-local placement: ref suffix -> (x, y, rotation).
# Rotation 90 stands a two-pad part on end with pad 1 lowermost; 270 puts
# pad 1 uppermost. Positions are chosen so the op-amp's own pin order does
# the routing work: the buffer lives on its left, the all-pass on its right.
TILE_PLACEMENT = {
    "J":   (3.2, 5.5, 90),       # 3=red (top), 2=white, 1=shield (bottom)
    "R02": (7.6, 7.047, 270),    # 3M3 bias, pin 1 sits on the white lane
    "R01": (10.8, 6.135, 0),     # 1k stopper, in line with the white lane
    "C01": (14.0, 7.085, 270),   # 100p RF filter, pin 1 on the buffer input
    "R03": (16.3, 4.23, 90),     # 1k buffer feedback, beside pins 1 and 2
    "U":   (21.0, 5.5, 0),       # OPA2191
    # Top row. R04 sits here rather than below the package: it is the one 47k
    # that lands on APN, and keeping every APN pad in a single row confines
    # the interleave with APOUT to one place where the B.Cu jumper can deal
    # with it. Below the package it collided with both the SWN lane and the
    # BUFOUT jumper, which have nowhere else to run.
    "C06": (21.0, 1.2, 0),       # V+ decoupling, clear of R04's pad
    "R04": (24.6, 1.2, 0),       # 47k, buffer out to the all-pass input
    "R06": (26.8, 1.2, 0),       # all-pass feedback pair
    "C02": (29.0, 1.2, 0),
    "C04": (31.2, 1.2, 0),       # summing capacitors into the red element
    "C05": (33.4, 1.2, 0),
    # Bottom row, deliberately sparse -- the SWN lane and the BUFOUT jumper
    # both have to get past it.
    "C07": (17.0, 10.0, 180),    # V- decoupling, clear of the BUFOUT drop
    "R05": (28.8, 10.0, 0),      # 47k, all-pass lag
    "C03": (31.2, 10.0, 0),      # all-pass lag capacitor
}

# Tile-local lanes used by the routing below.
#
# The op-amp is unchanged, so these still derive from its pins: with U at
# y = 5.5, pin 1 sits at 3.595, pins 2/7 at 4.865, pins 3/6 at 6.135 and
# pins 4/5 at 7.405.
Y_OUT_LANE = -0.1        # in the clear band between this tile and the one above
Y_BUFOUT_LANE = 2.2      # F.Cu, over the package to R04 in the top row
Y_APN_JUMPER = 2.2       # B.Cu, under the top row; clear of the lane above it
Y_APOUT_LANE = 3.2       # F.Cu, below the APN jumper
Y_SWN_LANE = 8.9         # between the package and the bottom row
Y_BUFOUT_JUMPER = 11.0   # B.Cu, below the bottom row
X_APOUT_CLIMB = 25.5     # the column APOUT uses to leave pin 7
X_BUFOUT_DROP = 19.6     # B.Cu drop under the package to the bottom row
TILE_EXIT_X = 36.0

# The corridor between the tiles and the switch column. Twelve lanes, a TSSOP
# and two landing columns have to share 17.7 mm, which is what sets the 0.6 mm
# lane pitch -- tight, but every pair still clears by 0.4 mm or better.
# OUT carries no vias in the corridor, so its lanes can sit at 0.5 mm. The
# switched-node lanes each end in a via, and a 0.6 mm via beside a neighbouring
# track needs 0.625 mm of pitch, so those get 0.65.
LANE_PITCH = 0.5
SWN_PITCH = 0.65
OUT_LANE_X = 38.8        # six OUT lanes, one per channel
SWN_LANE_X = 42.0        # six switched-node lanes
CTL_LEFT_X = 46.2        # where the control line lands for the left-hand cells
SPINE_X = 54.6           # the control spine, outboard of the switch packages
DIN_APPROACH_Y = 75.0    # OUT fans in below channel 6's BUFOUT jumper
DIN_APPROACH_PITCH = 0.5

# Board-level placement: ref -> (x, y, rotation).
#
# Two zones. A switch column down the right, each package beside the pair of
# channels it serves so the switched-node runs stay short; and a supply strip
# across the bottom in three rows -- connectors, then the power semiconductors,
# then the small stuff. The connectors that leave the instrument (J7 to the
# DIN, J9 to the pack) are both on the bottom edge, which is the end the
# enclosure mounts at.
SWITCH_X = 50.0
ROW_CONN = 80.0          # bottom strip: connectors
ROW_POWER = 86.5         # bottom strip: diodes, fuse, bulk, the inverter
ROW_SMALL = 91.5         # bottom strip: 0402 furniture

BOARD_PLACEMENT = {
    # One switch package per pair of channels. Their decoupling sits above and
    # below each package rather than beside it -- there is no width left to
    # the right of a TSSOP on a 56 mm board.
    "U8":  (SWITCH_X, 14.75, 0),
    "U9":  (SWITCH_X, 33.75, 0),
    "U10": (SWITCH_X, 52.75, 0),
    "C801": (SWITCH_X, 10.75, 0),
    "C802": (SWITCH_X, 18.75, 0),
    "C803": (SWITCH_X, 29.75, 0),
    "C804": (SWITCH_X, 37.75, 0),
    "C805": (SWITCH_X, 48.75, 0),
    "C806": (SWITCH_X, 56.75, 0),

    "J9":  (3.5, ROW_CONN, 0),             # pack in
    "J7":  (18.0, ROW_CONN, 180),          # DIN-8 out; pin 1 rightmost so
                                       # the fan-in never crosses
                                       # itself -- see route_outputs
    "JP1": (8.5, ROW_CONN, 180),           # beside DIN pin 8, turned so
                                       # its ground pad faces away
                                       # from the incoming track
    "J8":  (50.0, ROW_CONN, 0),            # pizz/arco toggle, by the switches

    "F701": (4.0, ROW_POWER, 0),
    "D701": (10.0, ROW_POWER, 180),        # pin 1 (cathode) faces the rail
    "D702": (18.0, ROW_POWER, 0),          # V+ clamp
    "D703": (27.0, ROW_POWER, 0),          # V- clamp
    "C701": (34.0, ROW_POWER, 0),          # input bulk
    "U7":  (43.0, ROW_POWER, 0),           # the inverter
    "C705": (38.0, ROW_POWER + 0.635, 270),  # flying capacitor, on the
                                       # pump's CAP+/CAP- side

    "C704": (6.0, ROW_SMALL, 0),           # V+ bypass, by the input chain
    # The inverter's output furniture stays beside the inverter.
    "C706": (40.0, ROW_SMALL, 0),          # reservoir
    "R702": (44.0, ROW_SMALL, 0),          # ripple filter
    "C707": (26.0, ROW_SMALL, 0),
    "C708": (31.0, ROW_SMALL, 0),
    "R701": (48.0, ROW_SMALL, 0),          # control pull-down, by the toggle
    "C703": (52.0, ROW_SMALL, 0),
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

    def stub_via(self, ref, number, offset, width=None):
        """Short track from a pad to a via beside it -- how AGND, V+ and V-
        pads reach their planes.

        The net comes from design.py rather than the caller, so a via can
        never be dropped onto the wrong rail. Vias sit beside the pad, never
        in it, which keeps the board buildable with plain fab processes.
        """
        net = circuit.DESIGN.pin_owner()[(ref, str(number))]
        pad = self.pad(ref, number)
        target = (round(pad[0] + offset[0], 4), round(pad[1] + offset[1], 4))
        self.track(net, [pad, target], width=width or (
            POWER_TRACK if net in ("V+", "V-", "AGND") else TRACK))
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


def tile_origin(index):
    return (TILE_ORIGIN[0], TILE_ORIGIN[1] + (index - 1) * TILE_PITCH)


def tile_ref(suffix, index):
    """Tile-local part name -> the design's reference (R02 -> R102)."""
    if suffix in ("U", "J"):
        return f"{suffix}{index}"
    return f"{suffix[0]}{index}{suffix[1:]}"


def place_channels(board):
    for index in range(1, circuit.CHANNELS + 1):
        ox, oy = tile_origin(index)
        for suffix, (x, y, rotation) in TILE_PLACEMENT.items():
            board.place(tile_ref(suffix, index), ox + x, oy + y, rotation)


def place_rest(board):
    for ref, (x, y, rotation) in BOARD_PLACEMENT.items():
        board.place(ref, x, y, rotation)


def route_channel(board, index):
    """Route one tile.

    Almost everything lives on F.Cu. Two links have to cross the fan-out from
    the op-amp's right-hand pins, so they hop to B.Cu and back: the buffer
    output on its way down to R05 in the bottom row, and the inverting-input
    net where it has to get past APOUT's pads in the top row. AGND, V+ and V-
    never travel -- they drop straight onto their planes through a via beside
    the pad.
    """
    ox, oy = tile_origin(index)
    n = index

    def at(x, y):
        return (round(ox + x, 4), round(oy + y, 4))

    def pad(suffix, number):
        return board.pad(tile_ref(suffix, n), number)

    def ground(suffix, number, offset):
        board.stub_via(tile_ref(suffix, n), number, offset)

    def lane_of(p, y):
        """The point directly above or below pad `p` on tile-local lane `y`."""
        return (p[0], at(0, y)[1])

    # -- the red element straight through to the output -------------------
    # Out sideways from the connector first: pins 1 and 2 sit directly below
    # pin 3 in the same column, so climbing from the pad would short them.
    board.track(f"OUT{n}", [pad("J", 3), at(4.525, Y_OUT_LANE),
                            at(TILE_EXIT_X, Y_OUT_LANE)])
    # The two summing capacitors reach the same lane from below, each on its
    # own stub. Nothing crosses, because the lane is above the whole row.
    for suffix in ("C04", "C05"):
        board.track(f"OUT{n}", [pad(suffix, 2), lane_of(pad(suffix, 2), Y_OUT_LANE)])

    # -- white element input network --------------------------------------
    board.track(f"IN_W{n}", [pad("J", 2), at(6.0, 5.5), at(6.0, 6.135),
                             pad("R02", 1), pad("R01", 1)])
    board.track(f"BUFIN{n}", [pad("R01", 2), pad("C01", 1), pad("U", 3)])

    # -- buffer ------------------------------------------------------------
    board.track(f"BUFFB{n}", [pad("U", 2), at(16.3, 4.865), pad("R03", 1)])
    board.track(f"BUFOUT{n}", [pad("U", 1), at(16.3, 3.595), pad("R03", 2)])
    # Up over the package on F.Cu to R04, which is why R04 is in the top row.
    board.track(f"BUFOUT{n}", [pad("U", 1), at(18.525, Y_BUFOUT_LANE),
                               lane_of(pad("R04", 1), Y_BUFOUT_LANE),
                               pad("R04", 1)])
    # R05 is in the bottom row, so that leg drops under the package on B.Cu.
    drop = at(X_BUFOUT_DROP, Y_BUFOUT_LANE)
    board.via(f"BUFOUT{n}", *drop)
    board.track(f"BUFOUT{n}",
                [drop, at(X_BUFOUT_DROP, Y_BUFOUT_JUMPER),
                 lane_of(pad("R05", 1), Y_BUFOUT_JUMPER)],
                layer=pcbnew.B_Cu)
    landing = lane_of(pad("R05", 1), Y_BUFOUT_JUMPER)
    board.via(f"BUFOUT{n}", *landing)
    board.track(f"BUFOUT{n}", [landing, pad("R05", 1)])

    # -- all-pass inverting input, on B.Cu under the top row ---------------
    # R04, R06 and C02 all put an APN pad in the top row, interleaved with the
    # APOUT pads of the same parts. One net has to go underneath; APN is the
    # one, because APOUT has further to travel afterwards.
    entry = at(24.9, 6.135)
    board.track(f"APN{n}", [pad("U", 6), entry])
    board.via(f"APN{n}", *entry)
    apn_pads = [pad("R04", 2), pad("R06", 1), pad("C02", 1)]
    board.track(f"APN{n}",
                [entry, at(24.9, Y_APN_JUMPER)] +
                [lane_of(p, Y_APN_JUMPER) for p in apn_pads],
                layer=pcbnew.B_Cu)
    for p in apn_pads:
        board.via(f"APN{n}", *lane_of(p, Y_APN_JUMPER))
        board.track(f"APN{n}", [lane_of(p, Y_APN_JUMPER), p])

    # -- all-pass output: its own F.Cu lane below the jumper ---------------
    apout_pads = [pad("R06", 2), pad("C02", 2), pad("C04", 1), pad("C05", 1)]
    board.track(f"APOUT{n}", [pad("U", 7), at(X_APOUT_CLIMB, 4.865),
                              at(X_APOUT_CLIMB, Y_APOUT_LANE)] +
                             [lane_of(p, Y_APOUT_LANE) for p in apout_pads])
    for p in apout_pads:
        board.track(f"APOUT{n}", [lane_of(p, Y_APOUT_LANE), p])

    # -- switched node, out to the switch bank -----------------------------
    board.track(f"SWN{n}", [pad("U", 5), at(X_APOUT_CLIMB, 7.405),
                            at(X_APOUT_CLIMB, Y_SWN_LANE),
                            at(TILE_EXIT_X, Y_SWN_LANE)])
    for suffix, number in (("R05", 2), ("C03", 1)):
        board.track(f"SWN{n}", [lane_of(pad(suffix, number), Y_SWN_LANE),
                                pad(suffix, number)])

    # -- supplies and ground ----------------------------------------------
    # Both rails and ground reach their plane through a via beside the pad;
    # nothing is bussed. The op-amp's own V+ via sits clear of the APOUT climb.
    board.track("V-", [pad("U", 4), at(18.525, 8.6)], width=POWER_TRACK)
    board.via("V-", *at(18.525, 8.6))
    board.track("V+", [pad("U", 8), at(22.2, 3.595)], width=POWER_TRACK)
    board.via("V+", *at(22.2, 3.595))

    for suffix, number, offset in (("J", 1, (1.6, 1.0)),
                                   ("R02", 2, (0.0, 1.3)),
                                   ("C01", 2, (0.0, 1.3)),
                                   ("C06", 1, (-1.2, 0.0)),
                                   ("C06", 2, (1.2, 0.0)),
                                   ("C07", 1, (1.2, 0.0)),
                                   ("C07", 2, (-1.2, 0.0)),
                                   ("C03", 2, (1.2, 0.0))):
        ground(suffix, number, offset)


def route_outputs(board):
    """Six OUT nets down the corridor to the DIN header.

    Entirely on F.Cu, and entirely without vias. B.Cu in this corridor belongs
    to the switched-node horizontals, which cross every lane on their way out
    of the tiles, so putting OUT down there would short the two.

    Nothing crosses, and the ordering is what does it. The header is below the
    tiles, so the lanes run downwards -- which means channel 1, whose tile is
    furthest from the header, needs the *outermost* lane and the *lowest*
    approach row, not the innermost and highest. Reverse both, and put J7's
    pin 1 at the right-hand end, and every crossing disappears: a channel's
    exit only ever passes lanes that have not started yet, and its approach
    row only ever passes drops that have already finished.
    """
    last = circuit.CHANNELS - 1
    for index in range(1, circuit.CHANNELS + 1):
        _, oy = tile_origin(index)
        lane = round(OUT_LANE_X + (last - index + 1) * LANE_PITCH, 4)
        approach = round(DIN_APPROACH_Y + (last - index + 1) * DIN_APPROACH_PITCH, 4)
        exit_y = round(oy + Y_OUT_LANE, 4)
        target = board.pad("J7", index)
        board.track(f"OUT{index}",
                    [(TILE_ORIGIN[0] + TILE_EXIT_X, exit_y), (lane, exit_y),
                     (lane, approach), (target[0], approach), target])


def route_switched_nodes(board):
    """Six SWN nets from the tiles to the analog switches.

    Cells A and B of each package take their signal on the left-hand side, so
    every switched node arrives from the corridor without crossing the control
    line, which comes down the right.
    """
    targets = {1: ("U8", 1), 2: ("U8", 3), 3: ("U9", 1),
               4: ("U9", 3), 5: ("U10", 1), 6: ("U10", 3)}
    for index in range(1, circuit.CHANNELS + 1):
        _, oy = tile_origin(index)
        lane = SWN_LANE_X + (index - 1) * SWN_PITCH
        exit_y = round(oy + Y_SWN_LANE, 4)
        ref, pin = targets[index]
        target = board.pad(ref, pin)
        net = f"SWN{index}"
        # Both horizontals run on B.Cu and only the vertical lane on F.Cu, so
        # a lane and a horizontal can never meet -- the fan needs no ordering.
        exit_point = (TILE_ORIGIN[0] + TILE_EXIT_X, exit_y)
        board.via(net, *exit_point)
        board.track(net, [exit_point, (lane, exit_y)], layer=pcbnew.B_Cu)
        board.via(net, lane, exit_y)
        board.track(net, [(lane, exit_y), (lane, target[1])])
        board.track(net, [(lane, target[1]), target])


def route_switch_control(board):
    """One control line to all six switch cells, run on B.Cu down the right."""
    source = board.stub_via("J8", 1, (0.0, 1.7))
    board.track("SW_CTL", [source, (SPINE_X, source[1])], layer=pcbnew.B_Cu)
    board.track("SW_CTL", [(SPINE_X, 10.0), (SPINE_X, ROW_SMALL - 3.0)],
                layer=pcbnew.B_Cu)
    for ref in ("U8", "U9", "U10"):
        for pin in (13, 5):
            target = board.pad(ref, pin)
            if pin == 13:
                # Right-hand side: the spine itself is the landing point.
                landing = (SPINE_X, target[1])
            else:
                # Left-hand side. Pin 5 sits at the same y as pin 10, whose via
                # is in the way, so this goes over the top of the package and
                # down the reserved column rather than straight across.
                over = board.pad(ref, 14)[1] - 1.2
                landing = (CTL_LEFT_X, target[1])
                board.track("SW_CTL", [(SPINE_X, over), (CTL_LEFT_X, over),
                                       landing], layer=pcbnew.B_Cu)
            board.via("SW_CTL", *landing)
            board.track("SW_CTL", [landing, target])
    for ref, pin in (("R701", 1), ("C703", 1)):
        landing = board.stub_via(ref, pin, (0.0, -1.3))
        board.track("SW_CTL", [landing, (landing[0], ROW_SMALL - 3.0),
                               (SPINE_X, ROW_SMALL - 3.0)],
                    layer=pcbnew.B_Cu)


def route_power(board):
    """The input chain and the inverter; everything else drops onto a plane."""
    j9 = board.pad("J9", 1)
    board.track("VIN", [j9, (2.6, j9[1]), board.pad("F701", 1)],
                width=POWER_TRACK)
    board.track("VFUSED", [board.pad("F701", 2), board.pad("D701", 2)],
                width=POWER_TRACK)
    board.track("V+", [board.pad("D701", 1), board.pad("D702", 1)],
                width=POWER_TRACK)

    # The flying capacitor is the only part that has to stay beside the pump.
    board.track("CPFLY_P", [board.pad("U7", 2), (38.0, board.pad("U7", 2)[1]),
                            board.pad("C705", 1)])
    board.track("CPFLY_N", [board.pad("U7", 4), (38.0, board.pad("U7", 4)[1]),
                            board.pad("C705", 2)])
    # Output down to the reservoir and the filter, on a lane of its own between
    # the inverter's row and the small stuff below it.
    lane = ROW_SMALL - 2.2
    board.track("CPOUT", [board.pad("U7", 5), (46.5, board.pad("U7", 5)[1]),
                          (46.5, lane), (board.pad("R702", 1)[0], lane),
                          (board.pad("C706", 1)[0], lane),
                          board.pad("C706", 1)])
    board.track("CPOUT", [(board.pad("R702", 1)[0], lane), board.pad("R702", 1)])

    # DIN pin 8 to the unfitted jumper, kept below the header rather than
    # above it, where the OUT nets are fanning in.
    # DIN pin 8 leaves to the left, away from the six drops fanning into the
    # header from above.
    din8 = board.pad("J7", 8)
    board.track("DIN8", [din8, (11.5, din8[1]), (11.5, ROW_CONN),
                         board.pad("JP1", 1)])

    for ref, pin, offset in (("J9", 2, (0.0, 2.0)),
                             ("D702", 2, (1.9, 0.0)),
                             ("D703", 1, (-1.9, 0.0)),
                             ("D703", 2, (1.9, 0.0)),
                             # C701's rails leave vertically: its neighbours
                             # already own the space either side of it.
                             ("C701", 1, (0.0, -2.2)),
                             ("C701", 2, (0.0, 2.2)),
                             ("U7", 1, (-1.4, -1.0)),
                             ("U7", 3, (-1.4, 0.0)),
                             ("U7", 8, (1.4, 0.0)),
                             ("C704", 1, (-1.2, 0.0)), ("C704", 2, (1.2, 0.0)),
                             ("C706", 2, (1.2, 0.0)),
                             ("R702", 2, (0.0, 1.3)),
                             ("C707", 1, (-1.2, 0.0)), ("C707", 2, (1.2, 0.0)),
                             ("C708", 1, (-1.2, 0.0)), ("C708", 2, (1.2, 0.0)),
                             ("J7", 7, (0.0, 2.0)),
                             ("JP1", 2, (1.3, 0.0)),
                             ("J8", 2, (0.0, 3.0)),
                             ("R701", 2, (0.0, 1.3)),
                             ("C703", 2, (0.0, 1.3))):
        board.stub_via(ref, pin, offset)


def route_right_column(board):
    """Switch-package supplies, decoupling and the grounded spare cells."""
    # Every non-signal pin drops onto its plane through a via *inside* the
    # package outline. Outboard there is no room -- the switched-node lanes
    # come up the left and the control spine runs down the right -- and the
    # pins are on a 0.65 mm pitch, so the vias also alternate between two
    # columns: a 0.6 mm via needs 0.8 mm of pitch to clear its neighbour.
    NEAR, FAR = 1.5, 2.4
    inboard = {2: NEAR, 4: NEAR, 6: NEAR, 7: FAR,          # left-hand pins
               8: -NEAR, 9: -FAR, 10: -NEAR, 11: -FAR,     # right-hand pins
               12: -NEAR, 14: -FAR}
    for ref in ("U8", "U9", "U10"):
        for pin, dx in inboard.items():
            board.stub_via(ref, pin, (dx, 0.0), width=TRACK)
    for ref in ("C801", "C802", "C803", "C804", "C805", "C806"):
        board.stub_via(ref, 1, (-1.2, 0.0))
        board.stub_via(ref, 2, (1.2, 0.0))


def add_copper(board, rectangle):
    """AGND on In1, V+ on In2, V- poured on the back.

    The planes are what make this layout tractable: every supply and ground
    pad reaches its rail through a single via, and the high-impedance piezo
    traces on the front run over unbroken ground.
    """
    board.zone("AGND", pcbnew.In1_Cu, rectangle)
    board.zone("V+", pcbnew.In2_Cu, rectangle)
    board.zone("V-", pcbnew.B_Cu, rectangle)


def report(board):
    print("pad positions for channel 1:")
    for suffix in TILE_PLACEMENT:
        ref = {"U": "U1", "J": "J1"}.get(suffix, f"{suffix[0]}1{suffix[1:]}")
        pads = []
        for pad in board.footprints[ref].Pads():
            x, y = board.pad(ref, pad.GetNumber())
            pads.append(f"{pad.GetNumber()}:({x:.3f},{y:.3f})")
        print(f"  {ref:6s} {' '.join(sorted(pads))}")


def silkscreen(board, rectangle):
    left, top, right, bottom = rectangle
    # PCB_TEXT is centred on its position, so titles sit at mid-span.
    middle = (left + right) / 2
    board.text("RMC pizz/arco  6 channel  rev B", middle, top + 1.6, size=1.2)
    # The supply is the thing that breaks the board if it is got wrong, and it
    # is no longer a range -- both rails are derived from this one, so 12 V
    # here puts 24 V across the CD4066B. The figure comes from design.py so it
    # cannot drift from the sheet.
    board.text(f"{circuit.SUPPLY_RANGE}   AGND = PACK NEGATIVE",
               middle, bottom - 1.6, size=1.0)
    for index in range(1, circuit.CHANNELS + 1):
        _, oy = tile_origin(index)
        board.text(f"CH{index} R/W/G", TILE_ORIGIN[0] + 1.0, oy - 1.2, size=0.8)


def main():
    board = Board()
    place_channels(board)
    place_rest(board)

    for index in range(1, circuit.CHANNELS + 1):
        route_channel(board, index)
    route_outputs(board)
    route_switched_nodes(board)
    route_switch_control(board)
    route_power(board)
    route_right_column(board)

    rectangle = (0.0, 0.0, BOARD_W, BOARD_H)
    board.outline(rectangle)
    inner = (rectangle[0] + 0.3, rectangle[1] + 0.3,
             rectangle[2] - 0.3, rectangle[3] - 0.3)
    add_copper(board, inner)
    silkscreen(board, rectangle)

    filler = pcbnew.ZONE_FILLER(board.board)
    filler.Fill(board.board.Zones())

    destination = pathlib.Path(__file__).parent / "rmc-pizz-arco" / "rmc-pizz-arco.kicad_pcb"
    pcbnew.SaveBoard(str(destination), board.board)
    print(f"wrote {destination}")
    print(f"  {len(board.footprints)} footprints, "
          f"{len(list(board.board.GetTracks()))} track/via items, "
          f"board {rectangle[2]:.0f} x {rectangle[3]:.0f} mm")


if __name__ == "__main__":
    main()
