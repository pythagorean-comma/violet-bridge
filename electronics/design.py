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

Everything outside RMC's drawing -- the bipolar supply, the analog switch
bank, input protection and decoupling -- is added here and flagged in
NOTES.md.

RMC's drawing is built around a bipolar ground but specifies a single
floating 12 V supply. Rather than manufacture that ground at half of one rail
-- which is what this board did until the respin -- a switched-capacitor
inverter makes a real -9 V from the 9 V pack, so AGND *is* the pack's
negative terminal. The op-amps then see +-9 V: 6 dB more swing than a
mid-rail 9 V gave, and 3.5 dB more than RMC's 12 V would have. Audio ground
stops floating above the battery, so bonding it to the DIN shield becomes
correct rather than a fault.
"""

from sexp import Sym, find

CHANNELS = 6

# Shared by the schematic, the board and the project scaffolding. The
# schematic's symbol UUIDs are derived from this name, and the board's
# footprints are linked back to those UUIDs, so the two generators must agree
# on it exactly -- hence one constant rather than three string literals.
PROJECT = "rmc-pizz-arco"

# The supply spec appears on the connector, the silkscreen and the schematic
# sheet. It has already drifted once, so it is written here and nowhere else.
#
# The range is now a single voltage, and that is a real narrowing rather than
# a tidy-up. Both rails are derived from this one: the inverter makes -V from
# +V, so the CD4066B sees twice whatever arrives here. At 9 V that is 18 V,
# the top of its recommended band; at 12 V it would be 24 V, past its 20 V
# absolute maximum. The old 9-15 V input would destroy this board.
SUPPLY_RANGE = "9V DC ONLY"
SUPPLY_INTENT = "9V regulated Li-ion pack (Fishman URBP), approx 4.2mA"

# Library registry: lib_id -> (nickname, stock library, symbol, rename).
# Two parts are not in the stock libraries and are borrowed from a
# pin-compatible sibling, then renamed:
#   OPA2191  <- OPA2197xD, the same SOIC-8 dual from the same TI family.
#   TC1044S  <- ICL7660, which is the same 8-pin 7660 body and pinout. The
#               TC1044S is the one to fit: it is rated to 12 V where the
#               ICL7660 stops at 10 V, and pin 1 is BOOST rather than NC.
# Both are fixed up in patch_symbol below.
LIBS = {
    "Device:R": ("Device", "Device", "R", None),
    "Device:C": ("Device", "Device", "C", None),
    "Device:Polyfuse": ("Device", "Device", "Polyfuse", None),
    "Device:D_Schottky": ("Device", "Device", "D_Schottky", None),
    "Device:D_TVS": ("Device", "Device", "D_TVS", None),
    "Connector_Generic:Conn_01x02": ("Connector_Generic", "Connector_Generic", "Conn_01x02", None),
    "Connector_Generic:Conn_01x03": ("Connector_Generic", "Connector_Generic", "Conn_01x03", None),
    "Connector_Generic:Conn_01x08": ("Connector_Generic", "Connector_Generic", "Conn_01x08", None),
    "Jumper:SolderJumper_2_Open": ("Jumper", "Jumper", "SolderJumper_2_Open", None),
    "rmc:OPA2191": ("rmc", "Amplifier_Operational", "OPA2197xD", "OPA2191"),
    "rmc:TC1044S": ("rmc", "Regulator_SwitchedCapacitor", "ICL7660", "TC1044S"),
    "Analog_Switch:CD4066BM": ("Analog_Switch", "Analog_Switch", "CD4066BM", None),
    "power:GNDA": ("power", "power", "GNDA", None),
    "power:PWR_FLAG": ("power", "power", "PWR_FLAG", None),
}

# PCBWay assembles this board in its entirety, so package choice is no longer
# limited by what a soldering iron can reach -- which is the only reason the
# first version was 0805 and SOIC throughout. 0402 is the default now.
R_FP = "Resistor_SMD:R_0402_1005Metric"
C_FP = "Capacitor_SMD:C_0402_1005Metric"

# Two deliberate exceptions, both protecting the high-impedance front end.
#
# The white element's bias network stays at 0805: R02 is 3M3 feeding a 20 pA
# input, and at 0402 the adjacent-pad gap is about 0.5 mm. Surface leakage
# across that gap -- through no-clean flux residue, or in humid air -- is not
# obviously negligible against 3M3, and this is the one node where it would
# matter most. Ninety square millimetres across six channels is cheap
# insurance, and the assembly notes ask for the flux to be cleaned anyway.
R_FP_HIZ = "Resistor_SMD:R_0805_2012Metric"
C_FP_HIZ = "Capacitor_SMD:C_0805_2012Metric"

# And the channel op-amps stay SOIC-8 for the same reason: 1.27 mm pitch
# leaves room to run an AGND guard ring around the buffer's + input, where
# 0.65 mm VSSOP does not. VSSOP would save about 100 mm2, three percent of
# the board, which is not worth losing the guard for.
OPAMP_FP = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
SWITCH_FP = "Package_SO:TSSOP-14_4.4x5mm_P0.65mm"
PUMP_FP = "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
BULK_FP = "Capacitor_SMD:C_1210_3225Metric"

# Every connector is surface-mount now. That removes PCBWay's separate manual
# through-hole soldering operation entirely, and stops thirty plated holes
# acting as keep-outs through all four layers -- which on a board this size
# costs more in routing than the pads do in area.
CONN_FP = {
    2: "Connector_JST:JST_SH_BM02B-SRSS-TB_1x02-1MP_P1.00mm_Vertical",
    3: "Connector_JST:JST_SH_BM03B-SRSS-TB_1x03-1MP_P1.00mm_Vertical",
    8: "Connector_JST:JST_SH_BM08B-SRSS-TB_1x08-1MP_P1.00mm_Vertical",
}

OPAMP_DATASHEET = "https://www.ti.com/lit/ds/symlink/opa2191.pdf"
OPAMP_DESCRIPTION = ("Dual 36V precision rail-to-rail op amp, 140 uA/ch, "
                     "20 pA bias current, SOIC-8")
SWITCH_DATASHEET = "https://www.ti.com/lit/ds/symlink/cd4066b.pdf"
PUMP_DATASHEET = "https://ww1.microchip.com/downloads/en/DeviceDoc/21348a.pdf"
PUMP_DESCRIPTION = ("Switched-capacitor voltage inverter, 1.5-12V, BOOST tied "
                    "high for a ~45 kHz oscillator, SOIC-8")


def _set_properties(definition, **values):
    """Overwrite named properties on a flattened symbol definition."""
    for item in definition:
        if isinstance(item, list) and str(item[0]) == "property":
            if item[1] in values:
                item[2] = values[item[1]]


def _retype_pin(definition, number, name, electrical_type):
    """Rename a pin and change its electrical type.

    Pins live one level down, inside the unit sub-symbols, so this walks in.
    Needed for the charge pump: the stock body types pin 1 as `no_connect`
    because on the MAX1044 it is NC, but on the TC1044S it is BOOST and we
    drive it. Wiring a `no_connect` pin is an ERC error, so the type has to
    change or the whole part cannot be used as intended.
    """
    for unit in definition:
        if not (isinstance(unit, list) and str(unit[0]) == "symbol"):
            continue
        for pin in unit:
            if not (isinstance(pin, list) and str(pin[0]) == "pin"):
                continue
            label = find(pin, "name")
            numbering = find(pin, "number")
            if numbering is None or numbering[1] != number:
                continue
            pin[1] = Sym(electrical_type)
            if label is not None:
                label[1] = name


def patch_symbol(lib_id, definition):
    """Property and pin overrides for symbols borrowed from another part.

    Applied identically when embedding a symbol in the schematic and when
    writing the project library, or ERC reports the two copies as differing.
    """
    if lib_id.endswith(":OPA2191"):
        _set_properties(definition, Datasheet=OPAMP_DATASHEET,
                        Description=OPAMP_DESCRIPTION)
    elif lib_id.endswith(":TC1044S"):
        _set_properties(definition, Datasheet=PUMP_DATASHEET,
                        Description=PUMP_DESCRIPTION)
        _retype_pin(definition, "1", "BOOST", "input")
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


def _resistor(design, ref, value, net_a, net_b, description="", footprint=None):
    design.add(Part(ref, value, "Device:R", footprint or R_FP,
                    description=description))
    design.connect(net_a, (ref, 1))
    design.connect(net_b, (ref, 2))


def _capacitor(design, ref, value, net_a, net_b, description="", footprint=None):
    design.add(Part(ref, value, "Device:C", footprint or C_FP,
                    description=description))
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

    design.add(Part(f"J{n}", "PZT", "Connector_Generic:Conn_01x03", CONN_FP[3],
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

    # The three parts on the white element's own node keep the larger
    # footprint -- see R_FP_HIZ. Everything downstream of the buffer is low
    # impedance and shrinks freely.
    _resistor(design, f"R{n}01", "1k", white, buf_in, "RF stopper",
              footprint=R_FP_HIZ)
    _resistor(design, f"R{n}02", "3M3", white, "AGND", "Piezo bias/load",
              footprint=R_FP_HIZ)
    _capacitor(design, f"C{n}01", "100p", buf_in, "AGND", "RF filter",
               footprint=C_FP_HIZ)
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
    # carrying four and two. On a 14-pin body the A and B cells have both
    # signal pins on the left (pins 1-7) while C and D have theirs on the
    # right. Channels arrive from the left and the control line comes down
    # the right, so using only A and B keeps the two apart entirely -- with C
    # and D in use the switched-node runs and the control line have to cross
    # each other, and there is nowhere good to put the crossing.
    #
    # That was a hard constraint of the old 88 x 112 layout. On the respun
    # board it is a *choice*: two packages using three cells each would save a
    # TSSOP-14 and two decoupling capacitors, about 4% of the board. Keeping
    # three is the safe default until the new placement is settled, because
    # the third package costs less than an unroutable switched node.
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

    design.add(Part("J8", "PIZZ/ARCO", "Connector_Generic:Conn_01x02", CONN_FP[2],
                    description="External SPST toggle; closed = inverted"))
    design.connect("SW_CTL", ("J8", 1))
    design.connect("V+", ("J8", 2))
    # Hold the control line at V- when the toggle is open, and slow the
    # transition so the change of polarity is not a step.
    #
    # V-, not AGND, and that survives the move to bipolar rails unchanged. A
    # 4066's control threshold sits midway between its own VSS and VDD, which
    # is now 0 V -- exactly where AGND is. Pulling the line down to AGND would
    # park the switch on its threshold rather than turning it off. The control
    # line has to swing the full V- to V+, as it always did.
    _resistor(design, "R701", "100k", "SW_CTL", "V-", "Control pull-down")
    _capacitor(design, "C703", "100n", "SW_CTL", "V-", "Control slew limit")


def power(design):
    """Make a real bipolar supply from the pack, about a real ground.

    RMC's schematic is drawn around a bipolar ground. The previous version of
    this board manufactured that ground at half of a single floating rail, so
    audio ground sat 4.5 V above the battery's negative terminal and the
    op-amps saw only +-4.5 V. Here a switched-capacitor inverter makes -9 V
    instead, and AGND *is* the pack's negative terminal.

    What that buys, in order of importance:

    - **Headroom.** +-9 V rather than +-4.5 V is 6 dB more swing, and 3.5 dB
      more than RMC's 12 V would have given through a mid-rail. The question
      of whether the elements' peaks fit is largely retired rather than
      answered.
    - **A ground that is a ground.** Bonding AGND to the DIN shield is now
      correct instead of a fault that shorts a buffer through 10 ohms. It also
      makes the pack safe to charge while connected: the Fishman pack's USB
      ground is common with its 9 V negative, which is this node.
    - **Seven parts fewer.** The divider, its filter, the isolation resistor,
      two bypass capacitors and a whole op-amp package all go.

    What it costs: the pack now supplies the same current across 18 V rather
    than 9 V, so drain roughly doubles to ~4.2 mA, and the input voltage stops
    being a range -- see SUPPLY_RANGE.
    """
    design.add(Part("J9", SUPPLY_RANGE, "Connector_Generic:Conn_01x02", CONN_FP[2],
                    description=f"{SUPPLY_RANGE} in: 1=+, 2=- (= AGND)"))
    design.connect("VIN", ("J9", 1))
    design.connect("AGND", ("J9", 2))

    design.add(Part("F701", "100mA", "Device:Polyfuse", "Fuse:Fuse_1206_3216Metric",
                    mpn="MF-MSMF010", description="Resettable fuse"))
    design.connect("VIN", ("F701", 1))
    design.connect("VFUSED", ("F701", 2))

    design.add(Part("D701", "B5819W", "Device:D_Schottky", "Diode_SMD:D_SOD-123",
                    description="Reverse-polarity protection"))
    design.connect("V+", ("D701", 1))       # pin 1 is the cathode
    design.connect("VFUSED", ("D701", 2))

    # Protection per rail to ground, not one device across the pair. With a
    # bipolar supply that is the right idiom, and it is also the only one that
    # works here: a rail-to-rail part big enough not to conduct at 18 V would
    # clamp well above the CD4066B's 20 V absolute maximum, destroying the
    # part it is meant to protect.
    #
    # 10 V standoff also does useful duty against the wrong supply. The pack
    # is 9 V, so these never conduct in normal use; feed the board 12 V and
    # they break down and take out F701 before the 4066 sees 24 V.
    for ref, high, low in (("D702", "V+", "AGND"), ("D703", "AGND", "V-")):
        design.add(Part(ref, "SMAJ10A", "Device:D_TVS", "Diode_SMD:D_SMA",
                        description="Rail clamp; also catches an over-volt supply"))
        design.connect(high, (ref, 1))
        design.connect(low, (ref, 2))

    _capacitor(design, "C701", "22u/16V", "V+", "AGND", "Input bulk",
               footprint=BULK_FP)
    _capacitor(design, "C704", "100n", "V+", "AGND", "Supply bypass")

    # -- the inverter ------------------------------------------------------
    # BOOST (pin 1) is tied high deliberately. Left open the oscillator runs
    # near 10 kHz, which is squarely in the audio band -- and the front end it
    # would be sitting beside is loaded by 3M3, so the coupling path that
    # matters is capacitive, not the op-amps' PSRR. Tying BOOST to V+ lifts it
    # to about 45 kHz, above anything that can be heard, and shrinks the
    # ripple as well. Pin 1 is NC on the borrowed MAX1044 body, which is why
    # patch_symbol has to retype it.
    #
    # LV (6) and OSC (7) are left unconnected on purpose. LV must be open
    # above 3.5 V, not grounded.
    design.add(Part("U7", "TC1044S", "rmc:TC1044S", PUMP_FP,
                    datasheet=PUMP_DATASHEET, mpn="TC1044SEOA713",
                    description="Charge-pump inverter: V+ in, V- out"))
    design.connect("V+", ("U7", 1), ("U7", 8))
    design.connect("CPFLY_P", ("U7", 2))
    design.connect("AGND", ("U7", 3))
    design.connect("CPFLY_N", ("U7", 4))
    design.connect("CPOUT", ("U7", 5))

    _capacitor(design, "C705", "10u", "CPFLY_P", "CPFLY_N", "Flying capacitor")
    _capacitor(design, "C706", "10u", "CPOUT", "AGND", "Inverter reservoir")

    # A first-order filter between the pump and the rail the signal circuitry
    # actually uses. 10R against 10u corners at 1.6 kHz, so what ripple
    # survives at 45 kHz is down another 29 dB. The 2 mA the negative rail
    # draws costs 20 mV across it, which nothing here notices.
    _resistor(design, "R702", "10R", "CPOUT", "V-", "Ripple filter")
    _capacitor(design, "C707", "10u", "V-", "AGND", "Ripple filter")
    _capacitor(design, "C708", "100n", "V-", "AGND", "Negative rail bypass")


def output(design):
    """Six channels out to RMC's DIN-8 instrument socket."""
    design.add(Part("J7", "DIN-8", "Connector_Generic:Conn_01x08", CONN_FP[8],
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


# Pins deliberately left open. verify.py treats any unconnected pin as an
# error -- which is the right default, and worth keeping -- so the exceptions
# are declared here with their reason rather than waved through in the
# checker. Both are on the inverter, and both matter: LV in particular is not
# a spare pin but one that must be left floating at this supply voltage.
NO_CONNECT = {
    ("U7", "6"): "TC1044S LV must be open above 3.5V, not grounded",
    ("U7", "7"): "TC1044S OSC unused; BOOST sets the oscillator instead",
}


def build_footprint(ref):
    """Footprint assigned to a reference, for the schematic writer."""
    return PARTS[ref].footprint


if __name__ == "__main__":
    d = build()
    print(f"{len(d.parts)} parts, {len(d.nets)} nets")
    for net in sorted(d.nets):
        print(f"  {net:10s} {len(d.nets[net]):3d} pins")
