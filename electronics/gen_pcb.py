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

TILE_PITCH = 14.0
TILE_ORIGIN = (4.0, 4.0)     # top-left of channel 1's tile, in board coords
CORRIDOR_X = 48.0            # OUT and SWN run up this lane to the right column
RIGHT_X = 62.0               # switch ICs, DIN header and power live here
BOARD_MARGIN = 3.0

# Tile-local placement: ref suffix -> (x, y, rotation).
# Rotation 90 stands a two-pad part on end with pad 1 lowermost; 270 puts
# pad 1 uppermost. Positions are chosen so the op-amp's own pin order does
# the routing work: the buffer lives on its left, the all-pass on its right.
TILE_PLACEMENT = {
    "J":   (2.5, 2.0, 0),        # 1=shield (top), 2=white, 3=red (bottom)
    "R02": (6.5, 8.547, 270),    # 3M3 bias, pin 1 sits on the white lane
    "R01": (11.0, 7.635, 0),     # 1k stopper, in line with the white lane
    "C01": (14.0, 8.585, 270),   # 100p RF filter, pin 1 on the buffer input
    "R03": (18.3, 5.73, 90),     # 1k buffer feedback, beside pins 1 and 2
    "U":   (23.0, 7.0, 0),       # OPA2191
    "C06": (26.5, 3.2, 0),       # V+ decoupling, level with pin 8
    "C07": (17.5, 10.3, 180),    # V- decoupling, level with pin 4
    "R06": (32.0, 3.2, 0),       # all-pass feedback pair, top row
    "C02": (37.0, 3.2, 0),
    "C04": (42.0, 3.2, 0),       # summing capacitors into the red element
    "C05": (42.0, 6.0, 0),
    "R04": (32.0, 12.5, 0),      # the two 47k from the buffer, bottom row
    "R05": (37.0, 12.5, 0),
    "C03": (42.0, 12.5, 0),      # all-pass lag capacitor
}

# Tile-local lanes used by the routing below.
Y_OUT_LANE = 0.7
Y_BUFOUT_LANE = 1.9
Y_APN_JUMPER = 2.4       # on B.Cu, under the top row
Y_APOUT_LANE = 4.3
Y_SWN_LANE = 9.8
Y_BUFOUT_JUMPER = 14.0   # on B.Cu, below the bottom row
X_BUFOUT_DROP = 24.0     # B.Cu drop from the top lane, under the package
TILE_EXIT_X = 50.0

# Board-level placement: ref -> (x, y, rotation).
BOARD_PLACEMENT = {
    "J7":  (RIGHT_X + 2.0, 2.0, 0),        # DIN-8 out, pins 1..8 downwards
    # One switch package per pair of channels, sat beside the pair it serves,
    # so each switched-node run stays short.
    "U8":  (70.0, 26.0, 0),
    "U9":  (70.0, 52.0, 0),
    "U10": (70.0, 84.0, 0),
    "C801": (82.0, 22.0, 0),
    "C802": (82.0, 30.0, 0),
    "C803": (82.0, 48.0, 0),
    "C804": (82.0, 56.0, 0),
    "C805": (82.0, 80.0, 0),
    "C806": (82.0, 88.0, 0),
    "J8":  (80.0, 64.0, 0),                # pizz/arco toggle
    "R701": (74.0, 68.0, 0),
    "C703": (74.0, 72.0, 0),
    "J9":  (4.0, 100.5, 0),                 # 12 V in, bottom left
    "F701": (10.0, 100.5, 0),
    "D701": (16.0, 100.5, 180),             # pin 1 (cathode) faces the rail
    "D702": (22.0, 100.5, 0),
    "C701": (31.0, 100.5, 0),               # bulk electrolytic
    "C702": (38.0, 100.5, 0),
    "C704": (42.5, 100.5, 0),
    "R702": (47.0, 97.0, 0),               # mid-rail divider
    "R703": (47.0, 103.0, 180),             # pin 1 faces the reference node
    "C705": (52.0, 105.0, 0),
    "U7":  (58.0, 100.5, 0),                # mid-rail buffer
    "R704": (52.0, 98.595, 180),           # isolation, pin 1 toward U7 pin 1
    "C706": (66.0, 98.0, 0),               # rail bypass: every pad is a via
    "C707": (66.0, 103.0, 0),
    "C708": (72.0, 98.0, 0),
    "C709": (72.0, 103.0, 0),
    "JP1": (69.0, 19.78, 0),               # beside DIN pin 8
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

    Almost everything lives on F.Cu. Three links have to cross the fan-out
    from the op-amp's right-hand pins, so they hop to B.Cu and back: the
    buffer output on its way down to the bottom row, and the inverting-input
    net on its way up to the feedback pair. AGND, V+ and V- never travel --
    they drop straight onto their planes through a via beside the pad.
    """
    ox, oy = tile_origin(index)
    n = index

    def at(x, y):
        return (round(ox + x, 4), round(oy + y, 4))

    def pad(suffix, number):
        return board.pad(tile_ref(suffix, n), number)

    def ground(suffix, number, offset):
        board.stub_via(tile_ref(suffix, n), number, offset)

    # -- the red element straight through to the output -------------------
    board.track(f"OUT{n}", [pad("J", 3), at(1.0, 7.08), at(1.0, Y_OUT_LANE),
                            at(TILE_EXIT_X, Y_OUT_LANE)])
    board.track(f"OUT{n}", [at(42.95, Y_OUT_LANE), pad("C04", 2), pad("C05", 2)])

    # -- white element input network --------------------------------------
    board.track(f"IN_W{n}", [pad("J", 2), at(4.2, 4.54), at(4.2, 7.635),
                             pad("R02", 1), pad("R01", 1)])
    board.track(f"BUFIN{n}", [pad("R01", 2), pad("C01", 1), pad("U", 3)])

    # -- buffer ------------------------------------------------------------
    board.track(f"BUFFB{n}", [pad("U", 2), at(19.3, 6.365), at(19.3, 6.642),
                              pad("R03", 1)])
    board.track(f"BUFOUT{n}", [pad("U", 1), at(19.0, 5.095), at(19.0, 4.818),
                               pad("R03", 2)])
    # Up and over the package, then down the back side to the bottom row.
    board.track(f"BUFOUT{n}", [pad("U", 1), at(20.525, Y_BUFOUT_LANE),
                               at(X_BUFOUT_DROP, Y_BUFOUT_LANE)])
    board.via(f"BUFOUT{n}", *at(X_BUFOUT_DROP, Y_BUFOUT_LANE))
    board.track(f"BUFOUT{n}",
                [at(X_BUFOUT_DROP, Y_BUFOUT_LANE), at(X_BUFOUT_DROP, Y_BUFOUT_JUMPER),
                 (pad("R04", 1)[0], at(0, Y_BUFOUT_JUMPER)[1]),
                 (pad("R05", 1)[0], at(0, Y_BUFOUT_JUMPER)[1])],
                layer=pcbnew.B_Cu)
    for suffix in ("R04", "R05"):
        x = pad(suffix, 1)[0]
        board.via(f"BUFOUT{n}", x, at(0, Y_BUFOUT_JUMPER)[1])
        board.track(f"BUFOUT{n}", [(x, at(0, Y_BUFOUT_JUMPER)[1]), pad(suffix, 1)])

    # -- all-pass: inverting input up to the feedback pair, on B.Cu --------
    board.track(f"APN{n}", [pad("U", 6), at(27.0, 7.635)])
    board.via(f"APN{n}", *at(27.0, 7.635))
    board.track(f"APN{n}",
                [at(27.0, 7.635), at(27.0, Y_APN_JUMPER),
                 (pad("R06", 1)[0], at(0, Y_APN_JUMPER)[1]),
                 (pad("C02", 1)[0], at(0, Y_APN_JUMPER)[1])],
                layer=pcbnew.B_Cu)
    for suffix in ("R06", "C02"):
        x = pad(suffix, 1)[0]
        board.via(f"APN{n}", x, at(0, Y_APN_JUMPER)[1])
        board.track(f"APN{n}", [(x, at(0, Y_APN_JUMPER)[1]), pad(suffix, 1)])
    # R04's far end joins the same B.Cu run from below.
    drop = (pad("R04", 2)[0], at(0, 10.8)[1])
    board.track(f"APN{n}", [pad("R04", 2), drop])
    board.via(f"APN{n}", *drop)
    board.track(f"APN{n}", [drop, (drop[0], at(0, Y_APN_JUMPER)[1])], layer=pcbnew.B_Cu)

    # -- all-pass output: one clear lane along the top row -----------------
    board.track(f"APOUT{n}", [pad("U", 7), at(27.2, 6.365), at(27.2, Y_APOUT_LANE),
                              (pad("R06", 2)[0], at(0, Y_APOUT_LANE)[1])])
    board.track(f"APOUT{n}", [(pad("R06", 2)[0], at(0, Y_APOUT_LANE)[1]), pad("R06", 2)])
    for suffix in ("C02", "C04"):
        x = pad(suffix, 2 if suffix == "C02" else 1)[0]
        board.track(f"APOUT{n}", [(pad("R06", 2)[0], at(0, Y_APOUT_LANE)[1]),
                                  (x, at(0, Y_APOUT_LANE)[1])])
        board.track(f"APOUT{n}", [(x, at(0, Y_APOUT_LANE)[1]),
                                  pad(suffix, 2 if suffix == "C02" else 1)])
    board.track(f"APOUT{n}", [(pad("C04", 1)[0], at(0, Y_APOUT_LANE)[1]), pad("C05", 1)])

    # -- switched node, out to the switch bank -----------------------------
    board.track(f"SWN{n}", [pad("U", 5), at(27.8, 8.905), at(27.8, Y_SWN_LANE),
                            at(TILE_EXIT_X, Y_SWN_LANE)])
    for suffix in ("R05", "C03"):
        x = pad(suffix, 2 if suffix == "R05" else 1)[0]
        board.track(f"SWN{n}", [(x, at(0, Y_SWN_LANE)[1]),
                                pad(suffix, 2 if suffix == "R05" else 1)])

    # -- supplies and ground ----------------------------------------------
    board.track("V+", [pad("U", 8), at(25.475, 3.2), pad("C06", 1)], width=POWER_TRACK)
    board.via("V+", *at(25.0, 3.2))
    board.track("V-", [pad("U", 4), at(20.525, 10.3), pad("C07", 1)], width=POWER_TRACK)
    board.via("V-", *at(20.0, 10.3))

    for suffix, number, offset in (("J", 1, (2.2, 0.0)),
                                   ("R02", 2, (0.0, 1.2)),
                                   ("C01", 2, (0.0, 1.2)),
                                   ("C06", 2, (1.3, 0.0)),
                                   ("C07", 2, (-1.3, 0.0)),
                                   ("C03", 2, (1.3, 0.0))):
        ground(suffix, number, offset)


def route_outputs(board):
    """Six OUT nets up the corridor to the DIN header.

    Each gets its own vertical lane, ordered so that a lane's horizontal
    runs always fall clear of the lanes belonging to lower-numbered
    channels -- which is why none of the six cross.
    """
    for index in range(1, circuit.CHANNELS + 1):
        _, oy = tile_origin(index)
        lane = 54.4 + (index - 1) * 0.8
        exit_y = round(oy + Y_OUT_LANE, 4)
        target = board.pad("J7", index)
        board.track(f"OUT{index}",
                    [(TILE_ORIGIN[0] + TILE_EXIT_X, exit_y), (lane, exit_y),
                     (lane, target[1])])
        # The last hop crosses the switched-node lanes, so it goes underneath.
        # J7 is through-hole, so the back layer reaches its pad directly.
        board.via(f"OUT{index}", lane, target[1])
        board.track(f"OUT{index}", [(lane, target[1]), target], layer=pcbnew.B_Cu)


def route_switched_nodes(board):
    """Six SWN nets from the tiles to the analog switches.

    Two of the eight switch cells on a 4066 sit entirely on the far side of
    the package, so those two hop to B.Cu and cross underneath it.
    """
    targets = {1: ("U8", 1), 2: ("U8", 3), 3: ("U9", 1),
               4: ("U9", 3), 5: ("U10", 1), 6: ("U10", 3)}
    for index in range(1, circuit.CHANNELS + 1):
        _, oy = tile_origin(index)
        lane = 59.4 + (index - 1) * 0.9
        exit_y = round(oy + Y_SWN_LANE, 4)
        ref, pin = targets[index]
        target = board.pad(ref, pin)
        net = f"SWN{index}"
        approach = (lane, target[1])
        # Both horizontals run on B.Cu and only the vertical lane on F.Cu, so
        # a lane and a horizontal can never meet -- the fan needs no ordering.
        exit_point = (TILE_ORIGIN[0] + TILE_EXIT_X, exit_y)
        board.via(net, *exit_point)
        board.track(net, [exit_point, (lane, exit_y)], layer=pcbnew.B_Cu)
        board.via(net, lane, exit_y)
        board.track(net, [(lane, exit_y), approach])
        board.via(net, *approach)
        landing = (target[0] - 2.6, target[1])
        board.track(net, [approach, landing], layer=pcbnew.B_Cu)
        board.via(net, *landing)
        board.track(net, [landing, target])


def route_switch_control(board):
    """One control line to all six switch cells, run on B.Cu."""
    spine_x = 86.5
    packages = ("U8", "U9", "U10")
    source = board.pad("J8", 1)
    # The spine has to span every branch off it, including the ones that
    # come over the top of the first package.
    board.track("SW_CTL", [source, (spine_x, source[1])], layer=pcbnew.B_Cu)
    board.track("SW_CTL", [(spine_x, 18.5), (spine_x, 84.0)], layer=pcbnew.B_Cu)
    for ref, pin in [(ref, pin) for ref in packages for pin in (13, 5)]:
        target = board.pad(ref, pin)
        if pin == 13:
            # Right-hand side: straight in from the spine.
            landing = (target[0] + 2.4, target[1])
            board.track("SW_CTL", [(spine_x, target[1]), landing], layer=pcbnew.B_Cu)
        else:
            # Left-hand side. Coming in level with the pin would run through
            # this package's own vias, so drop down the outside instead: over
            # the top of the package, then down a clear column at x = 66.
            centre = to_mm(board.footprints[ref].GetPosition().y)
            over = centre - 7.5
            landing = (66.0, target[1])
            board.track("SW_CTL", [(spine_x, over), (66.0, over), landing],
                        layer=pcbnew.B_Cu)
        board.via("SW_CTL", *landing)
        board.track("SW_CTL", [landing, target])
    for ref, pin in (("R701", 1), ("C703", 1)):
        landing = board.stub_via(ref, pin, (-1.5, 0.0))
        # Return above the last package, not across its ground vias.
        board.track("SW_CTL", [landing, (landing[0], 76.0), (spine_x, 76.0)],
                    layer=pcbnew.B_Cu)


def route_power(board):
    """The input chain, then everything else drops onto a plane."""
    board.track("VIN", [board.pad("J9", 1), board.pad("F701", 1)], width=POWER_TRACK)
    board.track("VFUSED", [board.pad("F701", 2), board.pad("D701", 2)], width=POWER_TRACK)
    board.track("V+", [board.pad("D701", 1), board.pad("D702", 1)], width=POWER_TRACK)
    board.stub_via("J9", 2, (0.0, 3.0))
    board.stub_via("D702", 1, (0.0, -2.2))
    board.stub_via("D702", 2, (0.0, 2.2))

    # Mid-rail divider, kept clear of the isolation resistor between them.
    board.track("MIDREF", [board.pad("R702", 2), (48.2, 97.0), (48.2, 103.0),
                           board.pad("R703", 1)])
    board.track("MIDREF", [(48.2, 103.0), (48.2, 105.0), board.pad("C705", 1)])
    board.track("MIDREF", [(48.2, 101.135), board.pad("U7", 3)])
    board.track("AGND_DRV", [board.pad("U7", 1), board.pad("R704", 1)])
    board.track("SPARE", [board.pad("U7", 6), board.pad("U7", 7)])

    # Everything else meets its rail through the planes.
    for ref, pin, offset in (("R702", 1, (0.0, -2.2)),
                             ("R703", 2, (0.0, 2.2)),
                             ("R704", 2, (-2.2, 0.0)),
                             ("C705", 2, (0.0, 2.2)),
                             ("U7", 8, (0.0, -2.2)),
                             ("U7", 4, (0.0, 2.2)),
                             ("U7", 5, (2.2, 0.0)),
                             ("U7", 2, (-2.2, 0.0)),
                             ("C701", 1, (0.0, -3.4)), ("C701", 2, (0.0, 3.4)),
                             ("C702", 1, (0.0, -2.2)), ("C702", 2, (0.0, 2.2)),
                             ("C704", 1, (0.0, -2.2)), ("C704", 2, (0.0, 2.2)),
                             ("C706", 1, (0.0, -2.2)), ("C706", 2, (0.0, 2.2)),
                             ("C707", 1, (0.0, -2.2)), ("C707", 2, (0.0, 2.2)),
                             ("C708", 1, (0.0, -2.2)), ("C708", 2, (0.0, 2.2)),
                             ("C709", 1, (0.0, -2.2)), ("C709", 2, (0.0, 2.2))):
        board.stub_via(ref, pin, offset)


def route_right_column(board):
    """Switch-package supplies, decoupling and the DIN header."""
    for ref, plus, minus in (("U8", 14, 7), ("U9", 14, 7), ("U10", 14, 7)):
        board.stub_via(ref, plus, (0.0, -2.4))
        board.stub_via(ref, minus, (0.0, 2.4))
    # Spare switch cells and the switched-node returns all sit on ground.
    grounded = [(ref, pin) for ref in ("U8", "U9", "U10")
                for pin in (2, 4, 8, 9, 10, 11)]
    for ref, pin in grounded:
        pad = board.pad(ref, pin)
        offset = (2.2, 0.0) if pad[0] > 70.0 else (-2.2, 0.0)
        board.stub_via(ref, pin, offset)
    for ref in ("U8", "U9", "U10"):
        for pin in (6, 12):
            board.stub_via(ref, pin, (-2.2, 0.0) if pin == 6 else (2.2, 0.0))
    for ref in ("C801", "C802", "C803", "C804", "C805", "C806"):
        board.stub_via(ref, 1, (-1.5, 0.0))
        board.stub_via(ref, 2, (1.5, 0.0))

    board.stub_via("J7", 7, (2.5, 0.0))
    board.track("DIN8", [board.pad("J7", 8), board.pad("JP1", 1)])
    board.stub_via("JP1", 2, (1.3, 0.0))
    board.stub_via("J8", 2, (2.5, 0.0))
    board.stub_via("R701", 2, (1.3, 0.0))
    board.stub_via("C703", 2, (1.3, 0.0))


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
    board.text("RMC pizz/arco  6 channel  rev A", middle, top + 1.8, size=1.4)
    # "FLOATING" is the part that breaks things if ignored, so it stays first.
    board.text("FLOATING SUPPLY ONLY   9-15V DC", middle, bottom - 1.8, size=1.2)
    for index in range(1, circuit.CHANNELS + 1):
        _, oy = tile_origin(index)
        board.text(f"CH{index} G/W/R", TILE_ORIGIN[0] + 6.0, oy - 1.4, size=0.9)


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

    _, last_y = tile_origin(circuit.CHANNELS)
    rectangle = (0.0, 0.0, 88.0, 112.0)
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
