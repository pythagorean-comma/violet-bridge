"""The RMC pizz/arco phase-switching preamp, as a netlist.

This is the authoritative circuit. The schematic is drawn from it and the
board is built from it, and the generated schematic is read back through
KiCad and compared against it, so a drawing mistake cannot quietly reach the
PCB.

Per string channel, following RMC's schematic of 2026-07-29:

    PZT1 (red)  ---------------------------------+--> OUT
                                                 |
    PZT2 (white) -- 1k --> [buffer] -- 47k --> [+-1 stage] -- 1n72 --+

The second stage is a first-order all-pass whose RC corner sits at 34 kHz,
well above the audio band, so in-band it is a polarity flip: switch open
gives +1, switch closed grounds the non-inverting input and gives -1. The
all-pass form keeps gain magnitude and source loading identical either way,
so flipping it produces no level jump.

Everything outside RMC's drawing -- the mid-rail split of the floating 12 V
supply, the analog switch bank, input protection and decoupling -- is added
here and flagged in NOTES.md.
"""

CHANNELS = 6

# Shared by the schematic, the board and the project scaffolding. The
# schematic's symbol UUIDs are derived from this name, and the board's
# footprints are linked back to those UUIDs, so the two generators must agree
# on it exactly -- hence one constant rather than three string literals.
PROJECT = "rmc-pizz-arco"

# Library registry: lib_id -> (nickname, stock library, symbol, rename).
# OPA2191 is not in the stock libraries; OPA2197xD is the same SOIC-8 dual
# from the same TI family, so it supplies the body and we rename it.
LIBS = {
    "Device:R": ("Device", "Device", "R", None),
    "Device:C": ("Device", "Device", "C", None),
    "Device:C_Polarized": ("Device", "Device", "C_Polarized", None),
    "Device:Polyfuse": ("Device", "Device", "Polyfuse", None),
    "Device:D_Schottky": ("Device", "Device", "D_Schottky", None),
    "Device:D_TVS": ("Device", "Device", "D_TVS", None),
    "Connector_Generic:Conn_01x02": ("Connector_Generic", "Connector_Generic", "Conn_01x02", None),
    "Connector_Generic:Conn_01x03": ("Connector_Generic", "Connector_Generic", "Conn_01x03", None),
    "Connector_Generic:Conn_01x08": ("Connector_Generic", "Connector_Generic", "Conn_01x08", None),
    "Jumper:SolderJumper_2_Open": ("Jumper", "Jumper", "SolderJumper_2_Open", None),
    "rmc:OPA2191": ("rmc", "Amplifier_Operational", "OPA2197xD", "OPA2191"),
    "Analog_Switch:CD4066BM": ("Analog_Switch", "Analog_Switch", "CD4066BM", None),
    "power:GNDA": ("power", "power", "GNDA", None),
    "power:PWR_FLAG": ("power", "power", "PWR_FLAG", None),
}

R_FP = "Resistor_SMD:R_0805_2012Metric"
C_FP = "Capacitor_SMD:C_0805_2012Metric"
OPAMP_FP = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
SWITCH_FP = "Package_SO:SO-14_3.9x8.65mm_P1.27mm"

OPAMP_DATASHEET = "https://www.ti.com/lit/ds/symlink/opa2191.pdf"
OPAMP_DESCRIPTION = ("Dual 36V precision rail-to-rail op amp, 140 uA/ch, "
                     "20 pA bias current, SOIC-8")
SWITCH_DATASHEET = "https://www.ti.com/lit/ds/symlink/cd4066b.pdf"


def patch_symbol(lib_id, definition):
    """Property overrides for symbols borrowed from another part.

    Applied identically when embedding a symbol in the schematic and when
    writing the project library, or ERC reports the two copies as differing.
    """
    if lib_id.endswith(":OPA2191"):
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


def _resistor(design, ref, value, net_a, net_b, description=""):
    design.add(Part(ref, value, "Device:R", R_FP, description=description))
    design.connect(net_a, (ref, 1))
    design.connect(net_b, (ref, 2))


def _capacitor(design, ref, value, net_a, net_b, description=""):
    design.add(Part(ref, value, "Device:C", C_FP, description=description))
    design.connect(net_a, (ref, 1))
    design.connect(net_b, (ref, 2))


def channel(design, index):
    """One string channel: RMC's drawing, part for part."""
    n = index
    out = f"OUT{n}"          # summing node: red element straight to the DIN
    white = f"IN_W{n}"       # white element, before the input network
    buf_in = f"BUFIN{n}"
    buf_fb = f"BUFFB{n}"
    buf_out = f"BUFOUT{n}"
    ap_n = f"APN{n}"         # all-pass inverting input
    ap_p = f"SWN{n}"         # all-pass non-inverting input -- the switched node
    ap_out = f"APOUT{n}"

    design.add(Part(f"J{n}", "PZT", "Connector_Generic:Conn_01x03",
                    "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
                    description=f"Saddle {n} piezo: 1=shield, 2=white, 3=red"))
    design.connect("AGND", (f"J{n}", 1))
    design.connect(white, (f"J{n}", 2))
    design.connect(out, (f"J{n}", 3))

    design.add(Part(f"U{n}", "OPA2191", "rmc:OPA2191", OPAMP_FP, units=3,
                    datasheet=OPAMP_DATASHEET, mpn="OPA2191IDR",
                    description="Buffer + all-pass, one string channel"))
    # Unit A: unity-gain buffer for the white element.
    design.connect(buf_out, (f"U{n}", 1))
    design.connect(buf_fb, (f"U{n}", 2))
    design.connect(buf_in, (f"U{n}", 3))
    # Unit B: the switched all-pass.
    design.connect(ap_p, (f"U{n}", 5))
    design.connect(ap_n, (f"U{n}", 6))
    design.connect(ap_out, (f"U{n}", 7))
    # Unit C: supply pins.
    design.connect("V-", (f"U{n}", 4))
    design.connect("V+", (f"U{n}", 8))

    _resistor(design, f"R{n}01", "1k", white, buf_in, "RF stopper")
    _resistor(design, f"R{n}02", "3M3", white, "AGND", "Piezo bias/load")
    _capacitor(design, f"C{n}01", "100p", buf_in, "AGND", "RF filter")
    _resistor(design, f"R{n}03", "1k", buf_fb, buf_out, "Buffer feedback")
    _resistor(design, f"R{n}04", "47k", buf_out, ap_n, "All-pass input")
    _resistor(design, f"R{n}05", "47k", buf_out, ap_p, "All-pass lag")
    _resistor(design, f"R{n}06", "47k", ap_n, ap_out, "All-pass feedback")
    _capacitor(design, f"C{n}02", "100p", ap_n, ap_out, "All-pass feedback")
    _capacitor(design, f"C{n}03", "100p", ap_p, "AGND", "All-pass lag")
    _capacitor(design, f"C{n}04", "220p", ap_out, out, "Sum into red element")
    _capacitor(design, f"C{n}05", "1n5", ap_out, out, "Sum into red element")
    _capacitor(design, f"C{n}06", "100n", "V+", "AGND", f"U{n} decoupling")
    _capacitor(design, f"C{n}07", "100n", "V-", "AGND", f"U{n} decoupling")


def switch_bank(design):
    """Six analog switches so one toggle flips all six channels at once.

    The schematic draws a switch per channel. Bussing six channels to a
    single mechanical SPST would short them together when open, so each
    channel gets its own contact and one control line drives the lot.
    """
    # Three packages carrying two channels each, rather than two packages
    # carrying four and two. On an SO-14 the A and B cells have both signal
    # pins on the left (pins 1-7) while C and D have theirs on the right.
    # Channels arrive from the left and the control line comes down the
    # right, so using only A and B keeps the two apart entirely -- with C
    # and D in use the switched-node runs and the control line have to cross
    # each other, and on a 4-layer board there is nowhere left to put them.
    # Two spare cells per package is a cheap price for that.
    PACKAGES = ("U8", "U9", "U10")
    for position, ref in enumerate(PACKAGES):
        design.add(Part(ref, "CD4066B", "Analog_Switch:CD4066BM", SWITCH_FP, units=5,
                        datasheet=SWITCH_DATASHEET, mpn="CD4066BM96",
                        description="Quad analog switch, pizz/arco"))
        design.connect("V-", (ref, 7))
        design.connect("V+", (ref, 14))

        # Cell A carries the odd channel, cell B the even one.
        for cell, (pin_a, pin_b, ctrl) in enumerate(((1, 2, 13), (3, 4, 5))):
            index = position * 2 + cell + 1
            design.connect(f"SWN{index}", (ref, pin_a))
            design.connect("AGND", (ref, pin_b))
            design.connect("SW_CTL", (ref, ctrl))

        # Cells C and D unused: signal pins parked on AGND, controls held at
        # V- so no CMOS input is ever left floating.
        for pin_a, pin_b, ctrl in ((8, 9, 6), (10, 11, 12)):
            design.connect("AGND", (ref, pin_a), (ref, pin_b))
            design.connect("V-", (ref, ctrl))

        _capacitor(design, f"C80{position * 2 + 1}", "100n", "V+", "AGND",
                   f"{ref} decoupling")
        _capacitor(design, f"C80{position * 2 + 2}", "100n", "V-", "AGND",
                   f"{ref} decoupling")

    design.add(Part("J8", "PIZZ/ARCO", "Connector_Generic:Conn_01x02",
                    "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
                    description="External SPST toggle; closed = inverted"))
    design.connect("SW_CTL", ("J8", 1))
    design.connect("V+", ("J8", 2))
    # Hold the control line at V- when the toggle is open, and slow the
    # transition so the change of polarity is not a step.
    _resistor(design, "R701", "100k", "SW_CTL", "V-", "Control pull-down")
    _capacitor(design, "C703", "100n", "SW_CTL", "V-", "Control slew limit")


def power(design):
    """Split the floating 12 V into +/-6 V about the audio ground.

    RMC's schematic is drawn around a bipolar ground but specifies a single
    floating 12 V supply, so signal ground has to sit at half the supply.
    Because the supply floats, this costs nothing and no coupling capacitors
    are needed anywhere in the signal path.
    """
    design.add(Part("J9", "9-15V DC", "Connector_Generic:Conn_01x02",
                    "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
                    description="Floating 9-15 V in: 1=+, 2=-"))
    design.connect("VIN", ("J9", 1))
    design.connect("V-", ("J9", 2))

    design.add(Part("F701", "100mA", "Device:Polyfuse", "Fuse:Fuse_1206_3216Metric",
                    mpn="MF-MSMF010", description="Resettable fuse"))
    design.connect("VIN", ("F701", 1))
    design.connect("VFUSED", ("F701", 2))

    design.add(Part("D701", "B5819W", "Device:D_Schottky", "Diode_SMD:D_SOD-123",
                    description="Reverse-polarity protection"))
    design.connect("V+", ("D701", 1))       # pin 1 is the cathode
    design.connect("VFUSED", ("D701", 2))

    design.add(Part("D702", "SMAJ15A", "Device:D_TVS", "Diode_SMD:D_SMA",
                    description="Rail clamp; CD4066B is 18 V absolute max"))
    design.connect("V+", ("D702", 1))
    design.connect("V-", ("D702", 2))

    design.add(Part("C701", "100u/25V", "Device:C_Polarized",
                    "Capacitor_SMD:CP_Elec_6.3x5.4", description="Bulk"))
    design.connect("V+", ("C701", 1))
    design.connect("V-", ("C701", 2))
    _capacitor(design, "C702", "10u", "V+", "V-", "Bulk ceramic")
    _capacitor(design, "C704", "100n", "V+", "V-", "Supply bypass")

    # Mid-rail reference, buffered.
    # 100k rather than 10k: the divider is a continuous drain, and 450 uA of a
    # 2.5 mA budget is worth reclaiming when the source is an onboard battery.
    # The buffer's 20 pA bias current makes 50k of source impedance cost about
    # a microvolt, and C705 still filters the reference -- its corner simply
    # moves from 3 Hz to 0.3 Hz. The cost is a ~2 s settle at power-on.
    _resistor(design, "R702", "100k", "V+", "MIDREF", "Mid-rail divider")
    _resistor(design, "R703", "100k", "MIDREF", "V-", "Mid-rail divider")
    _capacitor(design, "C705", "10u", "MIDREF", "V-", "Reference filter")

    design.add(Part("U7", "OPA2191", "rmc:OPA2191", OPAMP_FP, units=3,
                    datasheet=OPAMP_DATASHEET, mpn="OPA2191IDR",
                    description="Mid-rail buffer (A); spare (B)"))
    design.connect("AGND_DRV", ("U7", 1))
    design.connect("AGND", ("U7", 2))       # feedback taken beyond R704
    design.connect("MIDREF", ("U7", 3))
    design.connect("AGND", ("U7", 5))       # spare half, unity buffer
    design.connect("SPARE", ("U7", 6))
    design.connect("SPARE", ("U7", 7))
    design.connect("V-", ("U7", 4))
    design.connect("V+", ("U7", 8))

    # Isolation resistor keeps the bypass capacitance off the op-amp's output
    # while leaving it inside the feedback loop.
    _resistor(design, "R704", "10R", "AGND_DRV", "AGND", "Output isolation")
    _capacitor(design, "C706", "10u", "AGND", "V+", "Ground bypass")
    _capacitor(design, "C707", "10u", "AGND", "V-", "Ground bypass")
    _capacitor(design, "C708", "100n", "V+", "AGND", "U7 decoupling")
    _capacitor(design, "C709", "100n", "V-", "AGND", "U7 decoupling")


def output(design):
    """Six channels out to RMC's DIN-8 instrument socket."""
    design.add(Part("J7", "DIN-8", "Connector_Generic:Conn_01x08",
                    "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical",
                    description="To RMC DIN-8S socket / Poly-Drive II"))
    for index in range(1, CHANNELS + 1):
        design.connect(f"OUT{index}", ("J7", index))
    design.connect("AGND", ("J7", 7))
    design.connect("DIN8", ("J7", 8))

    # Pin 8's function is RMC's to confirm; the jumper lets it be grounded
    # without cutting a track. Left unfitted.
    design.add(Part("JP1", "DNP", "Jumper:SolderJumper_2_Open",
                    "Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm", dnp=True,
                    description="Optional: DIN pin 8 to ground"))
    design.connect("DIN8", ("JP1", 1))
    design.connect("AGND", ("JP1", 2))


def flags(design):
    """PWR_FLAGs so ERC knows the rails are fed from the connector."""
    for index, net in enumerate(("V+", "V-", "AGND"), start=1):
        ref = f"#FLG{index:02d}"
        design.add(Part(ref, "PWR_FLAG", "power:PWR_FLAG", ""))
        design.connect(net, (ref, 1))


def build():
    design = Design()
    for index in range(1, CHANNELS + 1):
        channel(design, index)
    switch_bank(design)
    power(design)
    output(design)
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
