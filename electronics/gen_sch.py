"""Draw the schematic for the design in design.py.

One channel row is laid out once in local coordinates and instantiated six
times, which is why the six channels are guaranteed identical. Rows come in
pairs sharing an OPA4191, so the sheet carries three blocks rather than six.
Rails and the switched nodes travel by global label; everything inside a
channel is drawn with real wires so the sheet reads the way RMC's original
does.

Lane constants below are the horizontal tracks a channel is built on, chosen
so nothing crosses without a junction.
"""

import pathlib

import design as circuit
from kisch import Schematic

# Channel lanes, relative to the row origin.
Y_OUT = -12.7      # red element straight through to the DIN
Y_FBR = -7.62      # all-pass feedback resistor
Y_FBC = -2.54      # all-pass feedback capacitor
Y_MAIN = 2.54      # buffer input path, and the all-pass inverting input
Y_BUFFB = 12.7     # buffer's own feedback
Y_APP = 22.86      # all-pass non-inverting input -- the switched lane

ROW_PITCH = 55.88          # between the two channel rows sharing a quad
BLOCK_PITCH = 116.84       # between quads
BLOCK_ORIGIN = (25.4, 33.02)
SWITCH_ORIGIN = (261.62, 33.02)
OUTPUT_ORIGIN = (419.1, 33.02)
BYPASS_ORIGIN = (419.1, 143.51)
FLAG_ORIGIN = (419.1, 205.74)


def place_passive(sch, ref, position, angle=0):
    """Place a resistor or capacitor from the design by reference."""
    part = circuit.PARTS[ref]
    return sch.place(ref, part.lib_id, part.value, position[0], position[1],
                     footprint=part.footprint, angle=angle,
                     extra={"dnp": part.dnp} if part.dnp else None)


_PIN_NET = circuit.DESIGN.pin_owner()


def pin_for(ref, net):
    """Which pin of `ref` design.py puts on `net`."""
    for (part_ref, pin), owner in _PIN_NET.items():
        if part_ref == ref and owner == net:
            return pin
    raise KeyError(f"{ref} has no pin on {net}")


def hang(sch, ref, position, upper_net, lower_net, axis=(0, 180)):
    """Place a two-pin part vertically between two nets.

    Which physical pin goes to which net is read from design.py rather than
    assumed, so a part whose pin 1 belongs at the bottom is simply rotated.
    Returns (part, upper_point, lower_point).

    `axis` is (angle with pin 1 uppermost, angle with pin 1 lowermost).
    """
    upper_pin = pin_for(ref, upper_net)
    part = place_passive(sch, ref, position,
                         angle=axis[0] if upper_pin == "1" else axis[1])
    return part, part.pin(upper_pin), part.pin(pin_for(ref, lower_net))


def opamp(sch, ref, unit, x, y, mirror=None):
    """Place one unit of a shared OPA4191.

    All four amplifier units draw at identical local coordinates, so the odd
    and even halves of a block differ only in unit and pin numbers.
    """
    return sch.place(ref, "rmc:OPA4191", circuit.PARTS[ref].value, x, y,
                     footprint=circuit.build_footprint(ref), unit=unit,
                     mirror=mirror, extra={"datasheet": circuit.OPAMP_DATASHEET})


def channel_row(sch, index, quad_ref, half, origin):
    """Draw one string channel. Mirrors design.channel()."""
    ox, oy = origin
    n = index

    def at(x, y):
        return (ox + x, oy + y)

    def ground(x, y):
        """Drop a GNDA symbol at (x, y); caller wires down to it."""
        return sch.power("power:GNDA", *at(x, y), value="AGND")

    buf_unit, (buf_out, buf_fb, buf_in) = circuit.QUAD_UNITS[half]["buf"]
    ap_unit, (ap_out, ap_n, ap_p) = circuit.QUAD_UNITS[half]["ap"]

    # -- input connector ------------------------------------------------
    j = sch.place(f"J{n}", "Connector_Generic:Conn_01x03", circuit.PARTS[f"J{n}"].value,
                  *at(0, Y_MAIN), footprint=circuit.build_footprint(f"J{n}"),
                  angle=180)
    sch.wire(j.pin(1), at(5.08, 8.89))
    ground(5.08, 8.89)
    # Red element: up to the top lane and straight across to the output.
    sch.wire(j.pin(3), at(11.43, 0), at(11.43, Y_OUT), at(170.18, Y_OUT))
    sch.label(f"OUT{n}", *at(170.18, Y_OUT))

    # -- white element input network ------------------------------------
    sch.wire(j.pin(2), at(20.32, Y_MAIN))
    bias = place_passive(sch, f"R{n}02", at(20.32, 8.89))
    sch.wire(at(20.32, Y_MAIN), bias.pin(1))
    sch.wire(bias.pin(2), at(20.32, 16.51))
    ground(20.32, 16.51)

    stopper = place_passive(sch, f"R{n}01", at(29.21, Y_MAIN), angle=90)
    sch.wire(at(20.32, Y_MAIN), stopper.pin(1))
    sch.wire(stopper.pin(2), at(40.64, Y_MAIN))

    rf = place_passive(sch, f"C{n}01", at(40.64, 8.89))
    sch.wire(at(40.64, Y_MAIN), rf.pin(1))
    sch.wire(rf.pin(2), at(40.64, 16.51))
    ground(40.64, 16.51)

    # -- unity-gain buffer ----------------------------------------------
    buf = opamp(sch, quad_ref, buf_unit, *at(55.88, 5.08))
    sch.wire(at(40.64, Y_MAIN), buf.pin(buf_in))
    sch.wire(buf.pin(buf_fb), at(44.45, 7.62), at(44.45, Y_BUFFB))

    fb = place_passive(sch, f"R{n}03", at(55.88, Y_BUFFB), angle=90)
    sch.wire(at(44.45, Y_BUFFB), fb.pin(1))
    sch.wire(fb.pin(2), at(68.58, Y_BUFFB))
    # Buffer output column feeds both all-pass legs.
    sch.wire(buf.pin(buf_out), at(68.58, 5.08))
    sch.wire(at(68.58, Y_MAIN), at(68.58, Y_APP))

    # -- all-pass stage --------------------------------------------------
    r_in = place_passive(sch, f"R{n}04", at(78.74, Y_MAIN), angle=90)
    sch.wire(at(68.58, Y_MAIN), r_in.pin(1))
    sch.wire(r_in.pin(2), at(93.98, Y_MAIN))

    r_lag = place_passive(sch, f"R{n}05", at(78.74, Y_APP), angle=90)
    sch.wire(at(68.58, Y_APP), r_lag.pin(1))
    sch.wire(r_lag.pin(2), at(101.6, Y_APP))

    allpass = opamp(sch, quad_ref, ap_unit, *at(116.84, Y_BUFFB), mirror="x")
    # Inverting input column, running up to the feedback pair.
    sch.wire(at(93.98, Y_FBR), at(93.98, 10.16), allpass.pin(ap_n))
    # Non-inverting (switched) column.
    sch.wire(at(101.6, 15.24), allpass.pin(ap_p))
    sch.wire(at(101.6, 15.24), at(101.6, 27.94))
    lag = place_passive(sch, f"C{n}03", at(101.6, 31.75))
    sch.wire(at(101.6, 27.94), lag.pin(1))
    sch.wire(lag.pin(2), at(101.6, 39.37))
    ground(101.6, 39.37)
    # Out to the switch bank.
    sch.wire(at(101.6, Y_APP), at(111.76, Y_APP))
    sch.label(f"SWN{n}", *at(111.76, Y_APP))

    r_fb = place_passive(sch, f"R{n}06", at(105.41, Y_FBR), angle=90)
    sch.wire(at(93.98, Y_FBR), r_fb.pin(1))
    sch.wire(r_fb.pin(2), at(132.08, Y_FBR))
    c_fb = place_passive(sch, f"C{n}02", at(105.41, Y_FBC), angle=90)
    sch.wire(at(93.98, Y_FBC), c_fb.pin(1))
    sch.wire(c_fb.pin(2), at(132.08, Y_FBC))

    sch.wire(allpass.pin(ap_out), at(132.08, Y_BUFFB))
    sch.wire(at(132.08, Y_FBR), at(132.08, Y_BUFFB))

    # -- summing capacitor into the red element --------------------------
    # One capacitor, not the drawing's 220p || 1n5: RMC confirmed the pair was
    # approximating the element's own 1700 pF, and a single 1n8 C0G does it.
    summing = place_passive(sch, f"C{n}04", at(144.78, Y_FBR), angle=90)
    sch.wire(at(132.08, Y_FBR), summing.pin(1))
    sch.wire(summing.pin(2), at(157.48, Y_FBR))
    sch.wire(at(157.48, Y_OUT), at(157.48, Y_FBR))


def quad_block(sch, quad_index, origin):
    """Two channel rows sharing one OPA4191, plus that package's supply unit."""
    ox, oy = origin
    ref = f"U{quad_index}"
    channel_row(sch, quad_index * 2 - 1, ref, "odd", origin)
    channel_row(sch, quad_index * 2, ref, "even", (ox, oy + ROW_PITCH))

    # The supply unit sits between the two rows it feeds.
    supply = opamp(sch, ref, circuit.QUAD_POWER_UNIT, ox + 190.5, oy + 27.94)
    sch.wire(supply.pin(circuit.QUAD_POWER["V+"]), (ox + 182.88, oy + 20.32))
    sch.label("V+", ox + 182.88, oy + 20.32, angle=180)
    sch.wire(supply.pin(circuit.QUAD_POWER["V-"]), (ox + 182.88, oy + 35.56))
    sch.label("V-", ox + 182.88, oy + 35.56, angle=180)


def switch_section(sch, origin):
    """Six analog switch cells across two packages, plus the control network."""
    ox, oy = origin

    def at(x, y):
        return (ox + x, oy + y)

    packages = ("U4", "U5")
    columns = {ref: position * 71.12 for position, ref in enumerate(packages)}
    # Units 2 and 4 of a 4066 carry their signal pins the opposite way round
    # to units 1 and 3; mirroring them makes all eight draw identically, with
    # the switched node on the left and ground on the right.
    cell_units = {"A": (1, None), "B": (2, "y"), "C": (3, None), "D": (4, "y")}

    for position, ref in enumerate(packages):
        x = columns[ref]
        for letter, (unit, mirror) in cell_units.items():
            pin_a, pin_b, ctrl = circuit.SWITCH_CELLS[letter]
            y = (unit - 1) * 27.94
            part = sch.place(ref, "Analog_Switch:CD4066BM", circuit.PARTS[ref].value,
                             *at(x, y), footprint=circuit.build_footprint(ref),
                             unit=unit, mirror=mirror,
                             extra={"datasheet": circuit.SWITCH_DATASHEET})
            if letter == "D":
                # Spare cell: both terminals parked on ground, control at V-.
                sch.wire(part.pin(pin_a), at(x - 15.24, y), at(x - 15.24, y + 5.08))
                sch.power("power:GNDA", *at(x - 15.24, y + 5.08), value="AGND")
                sch.wire(part.pin(ctrl), at(x, y + 12.7))
                sch.label("V-", *at(x, y + 12.7), angle=270)
            else:
                index = position * 3 + unit
                sch.wire(part.pin(pin_a), at(x - 20.32, y))
                sch.label(f"SWN{index}", *at(x - 20.32, y), angle=180)
                sch.wire(part.pin(ctrl), at(x, y + 12.7))
                sch.label("SW_CTL", *at(x, y + 12.7), angle=270)
            sch.wire(part.pin(pin_b), at(x + 15.24, y), at(x + 15.24, y + 5.08))
            sch.power("power:GNDA", *at(x + 15.24, y + 5.08), value="AGND")

        # Supply unit. The CD4066 has no ground pin: Vss is the negative rail.
        y = 118.11
        supply = sch.place(ref, "Analog_Switch:CD4066BM", circuit.PARTS[ref].value,
                           *at(x, y), footprint=circuit.build_footprint(ref),
                           unit=5, extra={"datasheet": circuit.SWITCH_DATASHEET})
        sch.wire(supply.pin(circuit.SWITCH_POWER["V+"]), at(x, y - 12.7))
        sch.label("V+", *at(x, y - 12.7), angle=90)
        sch.wire(supply.pin(circuit.SWITCH_POWER["V-"]), at(x, y + 12.7))
        sch.label("V-", *at(x, y + 12.7), angle=270)

    # -- control network, to RMC's values ---------------------------------
    # R702 sits on the rail side of the toggle, so a pinched toggle cable is
    # limited to about 450 uA rather than shorting V+.
    _, r702_top, r702_bottom = hang(sch, "R702", at(0, 154.94), "V+", "SW_TOG")
    sch.wire(r702_top, at(0, 148.59))
    sch.label("V+", *at(0, 148.59), angle=90)
    sch.wire(r702_bottom, at(0, 161.29))
    sch.label("SW_TOG", *at(0, 161.29), angle=270)

    j8 = sch.place("J8", "Connector_Generic:Conn_01x02", circuit.PARTS["J8"].value,
                   *at(48.26, 149.86), footprint=circuit.build_footprint("J8"),
                   angle=180)
    sch.wire(j8.pin(1), at(63.5, 149.86))
    sch.label("SW_TOG", *at(63.5, 149.86))
    sch.wire(j8.pin(2), at(63.5, 152.4))
    sch.label("SW_CTL", *at(63.5, 152.4))

    _, r701_top, r701_bottom = hang(sch, "R701", at(17.78, 154.94), "SW_CTL", "V-")
    sch.wire(r701_top, at(17.78, 148.59))
    sch.label("SW_CTL", *at(17.78, 148.59), angle=90)
    sch.wire(r701_bottom, at(17.78, 161.29))
    sch.label("V-", *at(17.78, 161.29), angle=270)

    _, c701_top, c701_bottom = hang(sch, "C701", at(31.75, 154.94), "SW_CTL", "AGND")
    sch.wire(c701_top, at(31.75, 148.59))
    sch.label("SW_CTL", *at(31.75, 148.59), angle=90)
    sch.wire(c701_bottom, at(31.75, 161.29))
    sch.power("power:GNDA", *at(31.75, 161.29), value="AGND")


def output_section(sch, origin):
    """Six channels and both rails out to RMC's DIN-8 instrument socket."""
    ox, oy = origin
    j7 = sch.place("J7", "Connector_Generic:Conn_01x09", circuit.PARTS["J7"].value,
                   ox, oy, footprint=circuit.build_footprint("J7"), angle=180)
    for index in range(1, circuit.CHANNELS + 1):
        pin = j7.pin(index)
        sch.wire(pin, (pin[0] + 15.24, pin[1]))
        sch.label(f"OUT{index}", pin[0] + 15.24, pin[1])
    for pin_number, net in ((7, "V+"), (8, "V-")):
        pin = j7.pin(pin_number)
        sch.wire(pin, (pin[0] + 15.24, pin[1]))
        sch.label(net, pin[0] + 15.24, pin[1])
    # Pin 9 is the DIN shell, which is the only ground in the system.
    shell = j7.pin(9)
    sch.wire(shell, (shell[0] + 10.16, shell[1]), (shell[0] + 10.16, shell[1] + 6.35))
    sch.power("power:GNDA", shell[0] + 10.16, shell[1] + 6.35, value="AGND")


def bypass_section(sch, origin):
    """RMC's four rail capacitors, a pair at each end of the rails."""
    ox, oy = origin
    for offset, (ref, net) in enumerate((("C901", "V+"), ("C902", "V-"),
                                         ("C903", "V+"), ("C904", "V-"))):
        x = ox + offset * 15.24
        _, top, bottom = hang(sch, ref, (x, oy), net, "AGND")
        sch.wire(top, (x, oy - 6.35))
        sch.label(net, x, oy - 6.35, angle=90)
        sch.wire(bottom, (x, oy + 6.35))
        sch.power("power:GNDA", x, oy + 6.35, value="AGND")


def flags(sch, origin):
    """PWR_FLAGs so ERC knows the rails are fed from the connector."""
    ox, oy = origin
    for offset, (ref, net) in enumerate((("#FLG01", "V+"), ("#FLG02", "V-"),
                                         ("#FLG03", "AGND"))):
        x = ox + offset * 15.24
        flag = sch.place(ref, "power:PWR_FLAG", "PWR_FLAG", x, oy)
        sch.wire(flag.pin(1), (x, oy + 5.08))
        if net == "AGND":
            sch.power("power:GNDA", x, oy + 5.08, value="AGND")
        else:
            sch.label(net, x, oy + 5.08, angle=270)


def build(path):
    sch = Schematic(circuit.PROJECT,
                    title="RMC pizz/arco phase switching -- 6 channel",
                    rev="B", company="violet-bridge",
                    date="2026-08-01", paper="A2")
    for lib_id, (nick, libname, symname, rename) in circuit.LIBS.items():
        sch.use(nick, libname, symname, rename=rename,
                patch=circuit.patch_symbol)

    for index in range(1, circuit.CHANNELS // 2 + 1):
        origin = (BLOCK_ORIGIN[0], BLOCK_ORIGIN[1] + (index - 1) * BLOCK_PITCH)
        quad_block(sch, index, origin)

    switch_section(sch, SWITCH_ORIGIN)
    output_section(sch, OUTPUT_ORIGIN)
    bypass_section(sch, BYPASS_ORIGIN)
    flags(sch, FLAG_ORIGIN)

    # These reach the schematic PDF, which is what gets sent to RMC, so the
    # supply figures come from design.py rather than being written out again.
    # The board is SLAVED to the Poly-Drive: ground is the DIN shell, and the
    # rails must not float. An earlier revision said the opposite.
    sch.text(f"SUPPLY: {circuit.SUPPLY_RANGE}. Ground is the DIN shell -- "
             f"the board has no supply of its own.", 261.62, 241.3, size=2.0)
    sch.text(f"{circuit.SUPPLY_INTENT}.", 261.62, 246.38, size=2.0)
    sch.text("Drains must stay symmetrical: no DC path from either rail to "
             "AGND anywhere.", 261.62, 251.46, size=2.0)
    sch.text("Switch CLOSED = all-pass inverted = elements in phase = PIZZ. "
             "Open = ARCO.", 261.62, 256.54, size=2.0)

    sch.auto_junctions()
    sch.save(path)
    return sch


if __name__ == "__main__":
    out = pathlib.Path(__file__).parent / "rmc-pizz-arco" / "rmc-pizz-arco.kicad_sch"
    out.parent.mkdir(parents=True, exist_ok=True)
    schematic = build(out)
    print(f"wrote {out} ({len(schematic.parts)} symbol instances, "
          f"{len(schematic.wires)} wires, {len(schematic.junctions)} junctions)")
