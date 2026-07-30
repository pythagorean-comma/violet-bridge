"""Draw the schematic for the design in design.py.

One channel block is laid out once in local coordinates and instantiated six
times, which is why the six channels are guaranteed identical. Rails and the
switched nodes travel by global label; everything inside a channel is drawn
with real wires so the sheet reads the same way as RMC's original.

Lane constants below are the horizontal tracks a channel is built on, chosen
so nothing crosses without a junction.
"""

import pathlib

import design as circuit
from kisch import Schematic

# Channel lanes, relative to the block origin.
Y_OUT = -12.7      # red element straight through to the DIN
Y_FBR = -7.62      # all-pass feedback resistor
Y_FBC = -2.54      # all-pass feedback capacitor
Y_MAIN = 2.54      # buffer input path, and the all-pass inverting input
Y_BUFFB = 12.7     # buffer's own feedback
Y_APP = 22.86      # all-pass non-inverting input -- the switched lane

BLOCK_PITCH = 55.88
BLOCK_ORIGIN = (25.4, 33.02)
POWER_ORIGIN = (299.72, 40.64)
SWITCH_ORIGIN = (299.72, 175.26)


def channel_block(sch, index, origin):
    """Draw one string channel. Mirrors design.channel()."""
    ox, oy = origin
    n = index

    def at(x, y):
        return (ox + x, oy + y)

    def ground(x, y):
        """Drop a GNDA symbol at (x, y); caller wires down to it."""
        return sch.power("power:GNDA", *at(x, y), value="AGND")

    # -- input connector ------------------------------------------------
    j = sch.place(f"J{n}", "Connector_Generic:Conn_01x03", "PZT",
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
    buf = sch.place(f"U{n}", "rmc:OPA2191", "OPA2191", *at(55.88, 5.08),
                    footprint=circuit.build_footprint(f"U{n}"), unit=1,
                    extra={"datasheet": circuit.OPAMP_DATASHEET})
    sch.wire(at(40.64, Y_MAIN), buf.pin(3))
    sch.wire(buf.pin(2), at(44.45, 7.62), at(44.45, Y_BUFFB))

    fb = place_passive(sch, f"R{n}03", at(55.88, Y_BUFFB), angle=90)
    sch.wire(at(44.45, Y_BUFFB), fb.pin(1))
    sch.wire(fb.pin(2), at(68.58, Y_BUFFB))
    # Buffer output column feeds both all-pass legs.
    sch.wire(buf.pin(1), at(68.58, 5.08))
    sch.wire(at(68.58, Y_MAIN), at(68.58, Y_APP))

    # -- all-pass stage --------------------------------------------------
    r_in = place_passive(sch, f"R{n}04", at(78.74, Y_MAIN), angle=90)
    sch.wire(at(68.58, Y_MAIN), r_in.pin(1))
    sch.wire(r_in.pin(2), at(93.98, Y_MAIN))

    r_lag = place_passive(sch, f"R{n}05", at(78.74, Y_APP), angle=90)
    sch.wire(at(68.58, Y_APP), r_lag.pin(1))
    sch.wire(r_lag.pin(2), at(101.6, Y_APP))

    allpass = sch.place(f"U{n}", "rmc:OPA2191", "OPA2191", *at(116.84, Y_BUFFB),
                        footprint=circuit.build_footprint(f"U{n}"), unit=2,
                        mirror="x", extra={"datasheet": circuit.OPAMP_DATASHEET})
    # Inverting input column, running up to the feedback pair.
    sch.wire(at(93.98, Y_FBR), at(93.98, 10.16), allpass.pin(6))
    # Non-inverting (switched) column.
    sch.wire(at(101.6, 15.24), allpass.pin(5))
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

    sch.wire(allpass.pin(7), at(132.08, Y_BUFFB))
    sch.wire(at(132.08, Y_FBR), at(132.08, Y_BUFFB))

    # -- summing capacitors into the red element -------------------------
    c220 = place_passive(sch, f"C{n}04", at(144.78, Y_FBR), angle=90)
    sch.wire(at(132.08, Y_FBR), c220.pin(1))
    sch.wire(c220.pin(2), at(157.48, Y_FBR))
    c1n5 = place_passive(sch, f"C{n}05", at(144.78, Y_FBC), angle=90)
    sch.wire(at(132.08, Y_FBC), c1n5.pin(1))
    sch.wire(c1n5.pin(2), at(157.48, Y_FBC))
    sch.wire(at(157.48, Y_OUT), at(157.48, Y_FBC))

    # -- supply pins and decoupling --------------------------------------
    supply = sch.place(f"U{n}", "rmc:OPA2191", "OPA2191", *at(190.5, Y_BUFFB),
                       footprint=circuit.build_footprint(f"U{n}"), unit=3,
                       extra={"datasheet": circuit.OPAMP_DATASHEET})
    sch.wire(at(182.88, 5.08), supply.pin(8))
    sch.label("V+", *at(182.88, 5.08), angle=180)
    sch.wire(at(182.88, 20.32), supply.pin(4))
    sch.label("V-", *at(182.88, 20.32), angle=180)

    _, dec_p_top, dec_p_bottom = hang(sch, f"C{n}06", at(201.93, 8.89), "V+", "AGND")
    sch.wire(supply.pin(8), dec_p_top)
    _, dec_n_top, dec_n_bottom = hang(sch, f"C{n}07", at(212.09, 16.51), "AGND", "V-")
    sch.wire(supply.pin(4), dec_n_bottom)
    sch.wire(dec_p_bottom, dec_n_top)
    sch.wire(at(207.01, Y_BUFFB), at(207.01, 17.78))
    ground(207.01, 17.78)


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

    `axis` is (angle with pin 1 uppermost, angle with pin 1 lowermost);
    symbols drawn horizontally, like the diodes, need (270, 90).
    """
    upper_pin = pin_for(ref, upper_net)
    part = place_passive(sch, ref, position,
                         angle=axis[0] if upper_pin == "1" else axis[1])
    return part, part.pin(upper_pin), part.pin(pin_for(ref, lower_net))


def power_section(sch, origin):
    ox, oy = origin

    def at(x, y):
        return (ox + x, oy + y)

    def rail(x, y, net, angle):
        """Short stub to a rail label -- keeps the power block free of
        long buses that would have to cross the signal wiring."""
        sch.label(net, ox + x, oy + y, angle=angle)

    # -- input chain -----------------------------------------------------
    j9 = sch.place("J9", "Connector_Generic:Conn_01x02", "12V DC", *at(0, 0),
                   footprint=circuit.build_footprint("J9"), angle=180)
    sch.wire(j9.pin(2), at(12.7, -2.54))
    rail(12.7, -2.54, "V-", 0)

    fuse = place_passive(sch, "F701", at(22.86, 0), angle=90)
    sch.wire(j9.pin(1), fuse.pin(1))
    diode = place_passive(sch, "D701", at(38.1, 0), angle=180)
    sch.wire(fuse.pin(2), diode.pin(2))
    sch.wire(diode.pin(1), at(53.34, 0))
    rail(53.34, 0, "V+", 0)

    # -- rail furniture, each hung between two stubs ----------------------
    for x, ref, axis in ((0, "D702", (270, 90)), (13.97, "C701", (0, 180)),
                         (26.67, "C702", (0, 180)), (39.37, "C704", (0, 180))):
        _, top, bottom = hang(sch, ref, at(x, 15.24), "V+", "V-", axis=axis)
        sch.wire(top, at(x, 7.62))
        rail(x, 7.62, "V+", 90)
        sch.wire(bottom, at(x, 22.86))
        rail(x, 22.86, "V-", 270)

    # -- mid-rail reference ----------------------------------------------
    div_top = place_passive(sch, "R702", at(0, 34.29))
    sch.wire(div_top.pin(1), at(0, 29.21))
    rail(0, 29.21, "V+", 90)
    div_bottom = place_passive(sch, "R703", at(0, 46.99))
    sch.wire(div_top.pin(2), div_bottom.pin(1))
    sch.wire(div_bottom.pin(2), at(0, 54.61))
    rail(0, 54.61, "V-", 270)

    filt = place_passive(sch, "C705", at(12.7, 46.99))
    sch.wire(div_bottom.pin(1), filt.pin(1))
    sch.wire(filt.pin(2), at(12.7, 54.61))
    rail(12.7, 54.61, "V-", 270)

    buffer_unit = sch.place("U7", "rmc:OPA2191", "OPA2191", *at(35.56, 45.72),
                            footprint=circuit.build_footprint("U7"), unit=1,
                            extra={"datasheet": circuit.OPAMP_DATASHEET})
    sch.wire(filt.pin(1), buffer_unit.pin(3))

    iso = place_passive(sch, "R704", at(55.88, 45.72), angle=90)
    sch.wire(buffer_unit.pin(1), iso.pin(1))
    # The ground bus is drawn as a polyline with a vertex at every pin that
    # lands on it: KiCad connects a pin at a wire end, but not mid-span.
    sch.wire(iso.pin(2), at(66.04, 45.72), at(69.85, 45.72), at(88.9, 45.72),
             at(101.6, 45.72), at(114.3, 45.72), at(127.0, 45.72))
    # Feedback is taken beyond the isolation resistor, so the loop still
    # holds the bypassed ground node at the reference voltage.
    sch.wire(buffer_unit.pin(2), at(24.13, 48.26), at(24.13, 58.42),
             at(66.04, 58.42), at(66.04, 45.72))
    sch.wire(at(69.85, 45.72), at(69.85, 52.07))
    sch.power("power:GNDA", *at(69.85, 52.07), value="AGND")

    for x, ref, upper in ((88.9, "C706", True), (101.6, "C707", False),
                          (114.3, "C708", True), (127.0, "C709", False)):
        if upper:
            _, top, bottom = hang(sch, ref, at(x, 41.91), "V+", "AGND")
            sch.wire(top, at(x, 34.29))
            rail(x, 34.29, "V+", 90)
            sch.wire(bottom, at(x, 45.72))
        else:
            _, top, bottom = hang(sch, ref, at(x, 49.53), "AGND", "V-")
            sch.wire(top, at(x, 45.72))
            sch.wire(bottom, at(x, 57.15))
            rail(x, 57.15, "V-", 270)

    # -- spare half, parked as a unity buffer -----------------------------
    spare = sch.place("U7", "rmc:OPA2191", "OPA2191", *at(35.56, 74.93),
                      footprint=circuit.build_footprint("U7"), unit=2,
                      extra={"datasheet": circuit.OPAMP_DATASHEET})
    sch.wire(spare.pin(5), at(20.32, 72.39), at(20.32, 76.2))
    sch.power("power:GNDA", *at(20.32, 76.2), value="AGND")
    sch.wire(spare.pin(6), at(24.13, 77.47), at(24.13, 83.82),
             at(48.26, 83.82), at(48.26, 74.93), spare.pin(7))

    supply = sch.place("U7", "rmc:OPA2191", "OPA2191", *at(74.93, 74.93),
                       footprint=circuit.build_footprint("U7"), unit=3,
                       extra={"datasheet": circuit.OPAMP_DATASHEET})
    sch.wire(supply.pin(8), at(74.93, 63.5))
    rail(74.93, 63.5, "V+", 90)
    sch.wire(supply.pin(4), at(74.93, 86.36))
    rail(74.93, 86.36, "V-", 270)

    # -- ERC power flags --------------------------------------------------
    for offset, (ref, net, angle) in enumerate((("#FLG01", "V+", 270),
                                                ("#FLG02", "V-", 270),
                                                ("#FLG03", "AGND", 270))):
        x = 149.86 + offset * 15.24
        flag = sch.place(ref, "power:PWR_FLAG", "PWR_FLAG", *at(x, 10.16))
        sch.wire(flag.pin(1), at(x, 15.24))
        if net == "AGND":
            sch.power("power:GNDA", *at(x, 15.24), value="AGND")
        else:
            rail(x, 15.24, net, angle)


def switch_section(sch, origin):
    """The six analog switches, plus U9's two spares parked safely."""
    ox, oy = origin

    def at(x, y):
        return (ox + x, oy + y)

    packages = ("U8", "U9", "U10")
    columns = {ref: position * 71.12 for position, ref in enumerate(packages)}
    # Units 2 and 4 of a 4066 carry their signal pins the opposite way round
    # to units 1 and 3; mirroring them makes all twelve draw identically, with
    # the switched node on the left and ground on the right.
    placements = []
    for position, ref in enumerate(packages):
        placements.append((ref, 1, 1, 2, 13, f"SWN{position * 2 + 1}", None))
        placements.append((ref, 2, 3, 4, 5, f"SWN{position * 2 + 2}", "y"))
        placements.append((ref, 3, 8, 9, 6, None, None))
        placements.append((ref, 4, 10, 11, 12, None, "y"))

    for ref, unit, pin_a, pin_b, ctrl, net, mirror in placements:
        x = columns[ref]
        y = (unit - 1) * 27.94
        part = sch.place(ref, "Analog_Switch:CD4066BM", "CD4066B", *at(x, y),
                         footprint=circuit.build_footprint(ref), unit=unit,
                         mirror=mirror,
                         extra={"datasheet": circuit.SWITCH_DATASHEET})
        if net:
            sch.wire(part.pin(pin_a), at(x - 20.32, y))
            sch.label(net, *at(x - 20.32, y), angle=180)
            sch.wire(part.pin(ctrl), at(x, y + 12.7))
            sch.label("SW_CTL", *at(x, y + 12.7), angle=270)
        else:
            # Spare switch: signal pins parked on ground, control at V-.
            sch.wire(part.pin(pin_a), at(x - 15.24, y), at(x - 15.24, y + 5.08))
            sch.power("power:GNDA", *at(x - 15.24, y + 5.08), value="AGND")
            sch.wire(part.pin(ctrl), at(x, y + 12.7))
            sch.label("V-", *at(x, y + 12.7), angle=270)
        sch.wire(part.pin(pin_b), at(x + 15.24, y), at(x + 15.24, y + 5.08))
        sch.power("power:GNDA", *at(x + 15.24, y + 5.08), value="AGND")

    # Supply units and decoupling for each switch package.
    for offset, (ref, caps) in enumerate((("U8", ("C801", "C802")),
                                          ("U9", ("C803", "C804")),
                                          ("U10", ("C805", "C806")))):
        x = columns[ref]
        y = 118.11
        supply = sch.place(ref, "Analog_Switch:CD4066BM", "CD4066B", *at(x, y),
                           footprint=circuit.build_footprint(ref), unit=5,
                           extra={"datasheet": circuit.SWITCH_DATASHEET})
        sch.wire(supply.pin(14), at(x, y - 12.7))
        sch.label("V+", *at(x, y - 12.7), angle=90)
        sch.wire(supply.pin(7), at(x, y + 12.7))
        sch.label("V-", *at(x, y + 12.7), angle=270)

        _, top_high, top_low = hang(sch, caps[0], at(x + 20.32, y - 6.35), "V+", "AGND")
        sch.wire(top_high, at(x + 20.32, y - 12.7))
        sch.label("V+", *at(x + 20.32, y - 12.7), angle=90)
        sch.wire(top_low, at(x + 20.32, y))
        _, bottom_high, bottom_low = hang(sch, caps[1], at(x + 20.32, y + 6.35), "AGND", "V-")
        sch.wire(bottom_high, at(x + 20.32, y))
        sch.wire(bottom_low, at(x + 20.32, y + 12.7))
        sch.label("V-", *at(x + 20.32, y + 12.7), angle=270)
        sch.wire(at(x + 20.32, y), at(x + 27.94, y))
        sch.power("power:GNDA", *at(x + 27.94, y), value="AGND")

    # -- toggle input ------------------------------------------------------
    j8 = sch.place("J8", "Connector_Generic:Conn_01x02", "PIZZ/ARCO",
                   *at(55.88, 149.86), footprint=circuit.build_footprint("J8"),
                   angle=180)
    sch.wire(j8.pin(1), at(71.12, 149.86))
    sch.label("SW_CTL", *at(71.12, 149.86))
    sch.wire(j8.pin(2), at(71.12, 147.32))
    sch.label("V+", *at(71.12, 147.32))

    pulldown = place_passive(sch, "R701", at(20.32, 154.94))
    sch.wire(pulldown.pin(1), at(20.32, 148.59))
    sch.label("SW_CTL", *at(20.32, 148.59), angle=90)
    sch.wire(pulldown.pin(2), at(20.32, 161.29))
    sch.label("V-", *at(20.32, 161.29), angle=270)

    slew = place_passive(sch, "C703", at(35.56, 154.94))
    sch.wire(slew.pin(1), at(35.56, 148.59))
    sch.label("SW_CTL", *at(35.56, 148.59), angle=90)
    sch.wire(slew.pin(2), at(35.56, 161.29))
    sch.label("V-", *at(35.56, 161.29), angle=270)


def output_section(sch, origin):
    ox, oy = origin

    def at(x, y):
        return (ox + x, oy + y)

    j7 = sch.place("J7", "Connector_Generic:Conn_01x08", "DIN-8", *at(0, 0),
                   footprint=circuit.build_footprint("J7"), angle=180)
    for index in range(1, circuit.CHANNELS + 1):
        pin = j7.pin(index)
        sch.wire(pin, (pin[0] + 15.24, pin[1]))
        sch.label(f"OUT{index}", pin[0] + 15.24, pin[1])

    ground_pin = j7.pin(7)
    sch.wire(ground_pin, (ground_pin[0] + 10.16, ground_pin[1]),
             (ground_pin[0] + 10.16, ground_pin[1] + 6.35))
    sch.power("power:GNDA", ground_pin[0] + 10.16, ground_pin[1] + 6.35, value="AGND")

    reserved = j7.pin(8)
    jumper = sch.place("JP1", "Jumper:SolderJumper_2_Open", "DNP",
                       reserved[0] + 20.32, reserved[1],
                       footprint=circuit.build_footprint("JP1"), angle=90,
                       extra={"dnp": True})
    sch.wire(reserved, jumper.pin(1))
    sch.wire(jumper.pin(2), (jumper.pin(2)[0] + 7.62, jumper.pin(2)[1]),
             (jumper.pin(2)[0] + 7.62, jumper.pin(2)[1] + 6.35))
    sch.power("power:GNDA", jumper.pin(2)[0] + 7.62, jumper.pin(2)[1] + 6.35, value="AGND")


def build(path):
    sch = Schematic("rmc-pizz-arco",
                    title="RMC pizz/arco phase switching -- 6 channel",
                    rev="A", company="violet-bridge",
                    date="2026-07-29", paper="A2")
    for lib_id, (nick, libname, symname, rename) in circuit.LIBS.items():
        sch.use(nick, libname, symname, rename=rename,
                patch=circuit.patch_symbol)

    for index in range(1, circuit.CHANNELS + 1):
        origin = (BLOCK_ORIGIN[0], BLOCK_ORIGIN[1] + (index - 1) * BLOCK_PITCH)
        channel_block(sch, index, origin)

    power_section(sch, POWER_ORIGIN)
    switch_section(sch, SWITCH_ORIGIN)
    output_section(sch, (500.38, 190.5))

    sch.text("Signal ground (GNDA) is mid-supply: the 12 V input must float.", 300.0, 150.0, size=2.0)
    sch.text("Switch closed = all-pass grounded = inverted (-1).", 300.0, 155.0, size=2.0)

    sch.auto_junctions()
    sch.save(path)
    return sch


if __name__ == "__main__":
    out = pathlib.Path(__file__).parent / "rmc-pizz-arco" / "rmc-pizz-arco.kicad_sch"
    out.parent.mkdir(parents=True, exist_ok=True)
    schematic = build(out)
    print(f"wrote {out} ({len(schematic.parts)} symbol instances, "
          f"{len(schematic.wires)} wires, {len(schematic.junctions)} junctions)")
