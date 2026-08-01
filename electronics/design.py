"""The RMC pizz/arco phase-switching preamp, as a netlist.

This is the authoritative circuit. The schematic is drawn from it and the
board is built from it, and the generated schematic is read back through
KiCad and compared against it, so a drawing mistake cannot quietly reach the
PCB.

Per string channel, following RMC's schematic of 2026-07-29:

    PZT1 (red)  ---------------------------------+--> OUT
                                                 |
    PZT2 (white) -- 1k --> [buffer] -- 47k --> [+-1 stage] -- 1n8 --+

The second stage is a first-order all-pass whose RC corner sits at 34 kHz,
well above the audio band, so in-band it is a polarity flip: switch open
gives +1, switch closed grounds the non-inverting input and gives -1. The
all-pass form keeps gain magnitude and source loading identical either way,
so flipping it produces no level jump.

The elements are wired out of phase on the transducer plate, so closing the
switch brings them *into* phase. In phase is pizz; out of phase is arco.

Power comes from the Poly-Drive II as +/-4.5V on DIN pins 7 and 8, with the
shell as ground, so there is no supply section here at all -- see the AGND
rule on `_GROUND_RULE` below, which is the one thing on this board that must
not be broken.
"""

CHANNELS = 6

# Shared by the schematic, the board and the project scaffolding. The
# schematic's symbol UUIDs are derived from this name, and the board's
# footprints are linked back to those UUIDs, so the two generators must agree
# on it exactly -- hence one constant rather than three string literals.
PROJECT = "rmc-pizz-arco"

# The supply spec appears on the connector, the silkscreen and the schematic
# sheet. It has already drifted twice, so it is written here and nowhere else.
# verify.check_supply_annotations() asserts this string reaches both.
SUPPLY_RANGE = "+/-4.5V from Poly-Drive II"
SUPPLY_INTENT = ("DIN-8 pin 7 = +4.5V, pin 8 = -4.5V, shell = ground; "
                 "approx 2mA, drawn symmetrically")

_GROUND_RULE = """
No DC path from either rail to AGND, anywhere on this board.

The Poly-Drive's ground is the midpoint of a transistor rail splitter, and it
reaches us down the DIN shell -- the same single conductor carrying the six
string returns. Any imbalance between the +4.5V and -4.5V drains flows in that
one wire, which is why RMC ask for the drains to be symmetrical and for the
ground terminal to carry audio only.

Satisfied by construction today: the op-amps draw V+ to V- through the die,
the CD4066 has no ground pin at all, and the control network runs
V+ -> 20k -> SW_CTL -> 1M -> V- with no ground leg. Everything touching AGND
is either an audio return or a capacitor.

So this forbids, permanently: an indicator LED, a rail-to-ground divider, a
single-ended pull-up, and asymmetric bypassing.
"""

# Library registry: lib_id -> (nickname, stock library, symbol, rename).
# OPA4191 is not in the stock libraries; OPA4197xD is the same SOIC-14 quad
# from the same TI family, so it supplies the body and we rename it.
LIBS = {
    "Device:R": ("Device", "Device", "R", None),
    "Device:C": ("Device", "Device", "C", None),
    "Connector_Generic:Conn_01x02": ("Connector_Generic", "Connector_Generic", "Conn_01x02", None),
    "Connector_Generic:Conn_01x03": ("Connector_Generic", "Connector_Generic", "Conn_01x03", None),
    "Connector_Generic:Conn_01x09": ("Connector_Generic", "Connector_Generic", "Conn_01x09", None),
    "rmc:OPA4191": ("rmc", "Amplifier_Operational", "OPA4197xD", "OPA4191"),
    "Analog_Switch:CD4066BM": ("Analog_Switch", "Analog_Switch", "CD4066BM", None),
    "power:GNDA": ("power", "power", "GNDA", None),
    "power:PWR_FLAG": ("power", "power", "PWR_FLAG", None),
}

# 1206 rather than 0805 throughout, on RMC's advice and on measurement: the
# clear gap between a part's own pads is 0.80mm at 0805 and 1.80mm at 1206,
# which is one routing lane against two. The board is ~80% air, so the ~4%
# of extra land buys a second lane through every passive.
R_FP = "Resistor_SMD:R_1206_3216Metric"
C_FP = "Capacitor_SMD:C_1206_3216Metric"
OPAMP_FP = "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm"
SWITCH_FP = "Package_SO:SO-14_3.9x8.65mm_P1.27mm"
CONN_FP = {
    2: "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    3: "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
    9: "Connector_PinHeader_2.54mm:PinHeader_1x09_P2.54mm_Vertical",
}

OPAMP_DATASHEET = "https://www.ti.com/lit/ds/symlink/opa4191.pdf"
OPAMP_DESCRIPTION = ("Quad 36V precision rail-to-rail op amp, 140 uA/ch, "
                     "20 pA bias current, SOIC-14")
SWITCH_DATASHEET = "https://www.ti.com/lit/ds/symlink/cd4066b.pdf"

# Pins deliberately left unconnected. verify.py treats every other floating
# pin as an error, so this is where an intentional one is declared -- next to
# the circuit rather than buried in the checker.
#
# Empty, and it should stay that way: twelve op-amp halves fill three quads
# exactly, and both spare CD4066 cells are parked on AGND and V-. If anything
# lands here, the quad assignment or the spare-cell parking is wrong.
NO_CONNECT = ()

# How one OPA4191 serves two channels.
#
# Units are A=(1,2,3) B=(5,6,7) C=(8,9,10) D=(12,13,14), power=(4,11), with
# pins 1-7 down the left of the package and 8-14 back up the right. So the
# level pairs are 1<->14, 3<->12, 5<->10, 7<->8.
#
# Both buffers take A and B, which puts both high-impedance + inputs on pins 3
# and 5 -- the connector side, where the 3M3 nodes want to be. Only the buffer
# *outputs* cross to the right-hand half, and those are low impedance.
#
# The pairing then matters as much as the split: A pairs with D and B with C,
# because A and D are both in the upper half of the package and B and C both
# in the lower. Each channel gets one horizontal half and the two never
# interleave. Pairing A with C instead sends both channels diagonally across
# the footprint.
# Each entry is (schematic unit, (out, -in, +in)). All four amplifier units
# draw at identical local coordinates, so one routine can place any of them.
QUAD_UNITS = {
    "odd":  {"buf": (1, (1, 2, 3)),  "ap": (4, (14, 13, 12))},   # A + D
    "even": {"buf": (2, (7, 6, 5)),  "ap": (3, (8, 9, 10))},     # B + C
}
QUAD_POWER = {"V+": 4, "V-": 11}
QUAD_POWER_UNIT = 5

# CD4066B, SO-14: cell -> (terminal a, terminal b, control).
SWITCH_CELLS = {"A": (1, 2, 13), "B": (3, 4, 5), "C": (8, 9, 6), "D": (10, 11, 12)}
SWITCH_POWER = {"V+": 14, "V-": 7}


def patch_symbol(lib_id, definition):
    """Property overrides for symbols borrowed from another part.

    Applied identically when embedding a symbol in the schematic and when
    writing the project library, or ERC reports the two copies as differing.
    """
    if lib_id.endswith(":OPA4191"):
        for item in definition:
            if isinstance(item, list) and str(item[0]) == "property":
                if item[1] == "Datasheet":
                    item[2] = OPAMP_DATASHEET
                elif item[1] == "Description":
                    item[2] = OPAMP_DESCRIPTION
    return definition


class Part:
    def __init__(self, ref, value, lib_id, footprint, units=1,
                 datasheet="~", description="", dnp=False, mpn=""):
        self.ref = ref
        self.value = value
        self.lib_id = lib_id
        self.footprint = footprint
        self.units = units
        self.datasheet = datasheet
        self.description = description
        self.dnp = dnp
        self.mpn = mpn


class Design:
    def __init__(self):
        self.parts = {}
        self.nets = {}

    def add(self, part):
        assert part.ref not in self.parts, f"duplicate reference {part.ref}"
        self.parts[part.ref] = part
        return part

    def connect(self, net, *pins):
        """Attach (ref, pin) pairs to a net."""
        entries = self.nets.setdefault(net, [])
        for ref, pin in pins:
            assert ref in self.parts, f"{net}: unknown part {ref}"
            entry = (ref, str(pin))
            assert entry not in entries, f"{net}: {ref}.{pin} attached twice"
            entries.append(entry)

    def pin_owner(self):
        """Map (ref, pin) -> net, checking nothing is connected twice."""
        owner = {}
        for net, entries in self.nets.items():
            for entry in entries:
                assert entry not in owner, (
                    f"{entry} on both {owner[entry]} and {net}")
                owner[entry] = net
        return owner

    def check(self):
        self.pin_owner()
        for net, entries in self.nets.items():
            assert len(entries) >= 2, f"net {net} has only {entries}"
        self.check_ground_rule()

    def check_ground_rule(self):
        """Enforce _GROUND_RULE: nothing resistive between a rail and AGND.

        A resistor with one end on a rail and the other on AGND is the exact
        shape of the mistake -- an indicator LED's dropper, a divider, a
        pull-up. It would put DC in the DIN shell alongside six string
        returns, and nothing downstream would catch it: ERC, the netlist
        comparison and DRC would all pass.
        """
        owner = self.pin_owner()
        for ref, part in self.parts.items():
            if part.lib_id != "Device:R":
                continue
            nets = {owner.get((ref, str(pin))) for pin in (1, 2)}
            if "AGND" in nets and nets & {"V+", "V-"}:
                raise AssertionError(
                    f"{ref} puts DC between {sorted(nets)} -- see _GROUND_RULE")


def _resistor(design, ref, value, net_a, net_b, description=""):
    design.add(Part(ref, value, "Device:R", R_FP, description=description))
    design.connect(net_a, (ref, 1))
    design.connect(net_b, (ref, 2))


def _capacitor(design, ref, value, net_a, net_b, description=""):
    design.add(Part(ref, value, "Device:C", C_FP, description=description))
    design.connect(net_a, (ref, 1))
    design.connect(net_b, (ref, 2))


def quad(design, index):
    """One OPA4191, serving two channels. Units per QUAD_UNITS."""
    ref = f"U{index}"
    design.add(Part(ref, "OPA4191", "rmc:OPA4191", OPAMP_FP, units=5,
                    datasheet=OPAMP_DATASHEET, mpn="OPA4191IDR",
                    description=f"Buffers + all-passes, channels "
                                f"{index * 2 - 1} and {index * 2}"))
    for net, pin in QUAD_POWER.items():
        design.connect(net, (ref, pin))
    return ref


def channel(design, index, quad_ref, half):
    """One string channel: RMC's drawing, part for part.

    `half` selects which pair of units on `quad_ref` this channel uses.
    """
    n = index
    out = f"OUT{n}"          # summing node: red element straight to the DIN
    white = f"IN_W{n}"       # white element, before the input network
    buf_in = f"BUFIN{n}"
    buf_fb = f"BUFFB{n}"
    buf_out = f"BUFOUT{n}"
    ap_n = f"APN{n}"         # all-pass inverting input
    ap_p = f"SWN{n}"         # all-pass non-inverting input -- the switched node
    ap_out = f"APOUT{n}"

    design.add(Part(f"J{n}", "PZT", "Connector_Generic:Conn_01x03", CONN_FP[3],
                    description=f"Saddle {n} piezo: 1=shield, 2=white, 3=red"))
    design.connect("AGND", (f"J{n}", 1))
    design.connect(white, (f"J{n}", 2))
    design.connect(out, (f"J{n}", 3))

    _, (buf_out_pin, buf_fb_pin, buf_in_pin) = QUAD_UNITS[half]["buf"]
    _, (ap_out_pin, ap_n_pin, ap_p_pin) = QUAD_UNITS[half]["ap"]
    design.connect(buf_out, (quad_ref, buf_out_pin))
    design.connect(buf_fb, (quad_ref, buf_fb_pin))
    design.connect(buf_in, (quad_ref, buf_in_pin))
    design.connect(ap_out, (quad_ref, ap_out_pin))
    design.connect(ap_n, (quad_ref, ap_n_pin))
    design.connect(ap_p, (quad_ref, ap_p_pin))

    _resistor(design, f"R{n}01", "1k", white, buf_in, "RF stopper")
    _resistor(design, f"R{n}02", "3M3", white, "AGND", "Piezo bias/load")
    _capacitor(design, f"C{n}01", "100p", buf_in, "AGND", "RF filter")
    _resistor(design, f"R{n}03", "1k", buf_fb, buf_out, "Buffer feedback")
    _resistor(design, f"R{n}04", "47k 1%", buf_out, ap_n, "All-pass input")
    _resistor(design, f"R{n}05", "47k 1%", buf_out, ap_p, "All-pass lag")
    _resistor(design, f"R{n}06", "47k 1%", ap_n, ap_out, "All-pass feedback")
    _capacitor(design, f"C{n}02", "100p", ap_n, ap_out, "All-pass feedback")
    _capacitor(design, f"C{n}03", "100p", ap_p, "AGND", "All-pass lag")
    # Matched to the element's own 1700 pF so the two elements sum at equal
    # weight -- string balance, not tolerance fussiness. C0G/NP0 is not
    # optional: X7R at this value drifts with temperature and signal voltage.
    # All six should come from one reel, because RMC's requirement is that the
    # channels match each other rather than the nominal.
    _capacitor(design, f"C{n}04", "1n8 C0G", ap_out, out, "Sum into red element")


def switch_bank(design):
    """Six analog switches so one toggle flips all six channels at once.

    The schematic draws a switch per channel. Bussing six channels to a
    single mechanical SPST would short them together when open, so each
    channel gets its own cell and one control line drives the lot.

    Two packages, three cells each, so each sits beside the trio it serves.
    """
    for position, ref in enumerate(("U4", "U5")):
        design.add(Part(ref, "CD4066B", "Analog_Switch:CD4066BM", SWITCH_FP, units=5,
                        datasheet=SWITCH_DATASHEET, mpn="CD4066BM96",
                        description="Quad analog switch, pizz/arco"))
        # The CD4066 has no ground pin: Vss is the negative rail, and the
        # switch cells themselves float. Grounding one side of each cell is
        # the circuit's doing, not the package's.
        for net, pin in SWITCH_POWER.items():
            design.connect(net, (ref, pin))

        for cell, letter in enumerate("ABC"):
            index = position * 3 + cell + 1
            pin_a, pin_b, ctrl = SWITCH_CELLS[letter]
            design.connect(f"SWN{index}", (ref, pin_a))
            design.connect("AGND", (ref, pin_b))
            design.connect("SW_CTL", (ref, ctrl))

        # Cell D unused: both terminals parked on AGND and the control held at
        # V-, so no CMOS input is ever left floating.
        pin_a, pin_b, ctrl = SWITCH_CELLS["D"]
        design.connect("AGND", (ref, pin_a), (ref, pin_b))
        design.connect("V-", (ref, ctrl))

    design.add(Part("J8", "PIZZ/ARCO", "Connector_Generic:Conn_01x02", CONN_FP[2],
                    description="External SPST toggle; closed = pizz"))
    design.connect("SW_TOG", ("J8", 1))
    design.connect("SW_CTL", ("J8", 2))

    # RMC's control network. R702 sits on the *rail* side of the toggle, so a
    # short anywhere in the toggle cable is limited to about 450 uA rather
    # than shorting V+ -- the cable leaves the board and can be pinched.
    # Closed, the divider holds SW_CTL within 0.2V of V+ and draws 8.8 uA
    # from V+ straight through to V-, so the drain stays symmetrical.
    _resistor(design, "R702", "20k", "V+", "SW_TOG", "Control series limit")
    _resistor(design, "R701", "1M", "SW_CTL", "V-", "Control pull-down")
    _capacitor(design, "C701", "10n", "SW_CTL", "AGND", "Switch de-bounce")


def output(design):
    """Six channels and both rails out to RMC's DIN-8 instrument socket.

    Nine ways, not eight: DIN pins 7 and 8 now carry power, so ground has no
    numbered pin of its own -- it is the shell. Pins 1..8 of this header map
    one-to-one onto the DIN pins and pin 9 is the shell, which is what makes
    the loom checkable by counting.
    """
    design.add(Part("J7", "DIN-8", "Connector_Generic:Conn_01x09", CONN_FP[9],
                    description="To RMC DIN-8S socket: 1-6=strings, "
                                "7=+4.5V, 8=-4.5V, 9=shell/ground"))
    for index in range(1, CHANNELS + 1):
        design.connect(f"OUT{index}", ("J7", index))
    design.connect("V+", ("J7", 7))
    design.connect("V-", ("J7", 8))
    design.connect("AGND", ("J7", 9))


def bypass(design):
    """RMC: "a pair of 4.7uF/25V caps at each end of the power rails".

    Four capacitors, replacing the eighteen local ones the old board carried.
    Taken on RMC's authority as the circuit's designer; the In1/In2 plane pair
    supplies the local V+ to AGND decoupling the deleted caps used to.
    """
    for position, (plus, minus) in enumerate((("C901", "C902"), ("C903", "C904"))):
        end = "DIN end" if position == 0 else "far end"
        _capacitor(design, plus, "4u7/25V", "V+", "AGND", f"Rail bypass, {end}")
        _capacitor(design, minus, "4u7/25V", "V-", "AGND", f"Rail bypass, {end}")


def flags(design):
    """PWR_FLAGs so ERC knows the rails are fed from the connector."""
    for index, net in enumerate(("V+", "V-", "AGND"), start=1):
        ref = f"#FLG{index:02d}"
        design.add(Part(ref, "PWR_FLAG", "power:PWR_FLAG", ""))
        design.connect(net, (ref, 1))


def build():
    design = Design()
    for index in range(1, CHANNELS // 2 + 1):
        ref = quad(design, index)
        channel(design, index * 2 - 1, ref, "odd")
        channel(design, index * 2, ref, "even")
    switch_bank(design)
    output(design)
    bypass(design)
    flags(design)
    design.check()
    return design


DESIGN = build()
PARTS = DESIGN.parts
NETS = DESIGN.nets


def build_footprint(ref):
    """Footprint assigned to a reference, for the schematic writer."""
    return PARTS[ref].footprint


if __name__ == "__main__":
    d = build()
    print(f"{len(d.parts)} parts, {len(d.nets)} nets")
    for net in sorted(d.nets):
        print(f"  {net:10s} {len(d.nets[net]):3d} pins")
