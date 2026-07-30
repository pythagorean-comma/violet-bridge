# RMC pizz/arco switching — 6 channel board

Source: `docs/Pizz-Arco-Switching-260729.png` (RMC, 2026-07-29), one channel drawn.
This board is that channel built six times, for the six saddles of the
viola da gamba bridge, plus the supply and switching the drawing leaves open.

## What the circuit does

Each channel sums two piezo elements from one saddle into a single
high-impedance output that behaves like a piezo, which is what the
Poly-Drive II expects to see.

- **PZT 1 (red)** goes straight to `OUT`, unbuffered.
- **PZT 2 (white)** is loaded by 3M3 to ground, filtered by 1k/100p
  (corner ≈1.6 MHz), buffered at unity gain, then passed through a
  first-order all-pass, then summed into `OUT` through 220p ‖ 1n5 = 1.72 nF.

The all-pass RC corner is 1/(2π·47k·100p) ≈ **34 kHz**, well above the audio
band. In band this stage is therefore a **polarity flip**, not a gradual phase
shift: switch open gives +1, switch closed grounds the non-inverting input and
gives −1. PZT 2 then sums with PZT 1 either in phase or in anti-phase, and that
is the pizz/arco character change.

The all-pass form (rather than a plain switched inverter) is what keeps gain
magnitude and source loading identical in both positions, so flipping the
switch produces no level jump. The 100 pF capacitors are doing HF stability and
RF rejection duty.

Nothing in RMC's circuit needed changing.

## What was added, and why

The drawing specifies a single floating +12 V supply but is drawn around a
bipolar ground, so:

- **Mid-rail split.** `AGND` — the ground in RMC's drawing — is generated at
  half supply by a 10k/10k divider buffered by U7A, giving the amplifiers
  ±6 V. Because the supply floats this costs nothing and **no coupling
  capacitors are needed anywhere in the signal path**. R704 (10R) isolates the
  bypass capacitance from the buffer's output while keeping it inside the
  feedback loop. U7B is a spare half, parked as a unity buffer.
- **Switching.** The drawing shows one switch per channel. Bussing six
  channels to a single mechanical SPST would short them all together when
  open, so each channel gets its own contact: six CD4066B analog switch cells
  driven from one control line. On-resistance ~100 Ω against 47 k is −54 dB,
  and the switched node carries no DC, so there is no click. R701/C703 slow
  the transition to about 10 ms.

  These sit in **three** packages (U8–U10) using only the A and B cells of
  each, not two packages using all four. On an SO-14 the A and B cells have
  both signal pins on the left side; C and D have theirs on the right. The
  channels arrive from the left and the control line comes down the right, so
  restricting to A and B keeps the two apart entirely — with C and D in use
  they have to cross, and there is nowhere left to put the crossing. Two spare
  cells per package is a cheap price. Each package also sits beside the pair of
  channels it serves, so the switched-node runs stay short.
- **Protection and decoupling.** Resettable fuse, series Schottky for reverse
  polarity, a 15 V TVS across the rail, bulk and per-package bypassing.

## Supply requirement — important

**The 12 V input must float** (no connection to mains earth). Its mid-point
becomes the audio ground, so an earth-referenced supply would short the
mid-rail buffer.

**Use a regulated 12 V supply.** The CD4066B is rated 18 V absolute maximum.
D702 clamps at 15 V and F701 will then trip, but an unregulated "12 V" wallwart
that sits at 17–18 V off-load is outside the design intent.

Total draw is about **2.5 mA** — twelve OPA2191 halves at 140 µA each, plus the
switches and reference. Almost any supply will do.

## Board

- 88 × 112 mm, 4 layers, all SMD 0805 / SOIC, hand-solderable.
- **Stackup:** F.Cu signals · In1.Cu solid AGND plane · In2.Cu solid V+ plane ·
  B.Cu V− pour and jumpers. Four layers rather than two is what keeps this
  tractable: every supply and ground pad reaches its rail through a single via,
  and the high-impedance piezo traces run over unbroken ground.
- Six identical channel tiles down the left at 14 mm pitch, each with its own
  3-pin pickup header; DIN header, the three switch packages and the toggle
  down the right; supply along the bottom.
- Per-saddle headers J1–J6 are wired **1 = shield, 2 = white, 3 = red**.

The size is set by six channels of through-hole-headered discrete circuitry.
If it has to be smaller, say so — reflowing to two columns of three, or moving
to 0402, would get it well under 70 × 70 mm.

## Status

- Schematic: **ERC clean.** The 18 remaining warnings are all one benign case
  (a 4066 signal pin tied to ground, which is intended).
- The generated schematic is read back through KiCad and compared against
  `design.py` net by net — 58 nets, 330 pin connections, exact match. See
  `verify.py`.
- Board: **fully routed, 0 unconnected items, DRC clean.**

## Sending it to a fab

`./build.sh` writes **`fab/rmc-pizz-arco-pcbway.zip`** — upload that and
nothing else. It holds only what a fab needs: four copper layers, two mask,
two silkscreen, `Edge_Cuts` and the drill file, plus a matching `.gbrjob` and
a copy of `ORDER.md`.

Read **`fab/ORDER.md`** before ordering. It lists the things gerbers cannot
carry, above all that this is a **4-layer** board — order forms default to 2,
which would silently drop both inner planes.

The zip is only written when DRC is clean. If the board has outstanding
errors, `build.sh` deletes any stale zip and says why, so a board with known
faults cannot reach a fab by accident.

Deliberately **not** in the zip: `F_Fab`/`B_Fab`, `F_Courtyard`/`B_Courtyard`,
`Adhesive`, `Margin` and the `User_*` layers. `F_Fab` in particular carries a
second closed board outline; if CAM picks that one up instead of `Edge_Cuts`
the board comes back the wrong shape.

For a stencil, add `F.Paste` to the `--layers` list in `build.sh`. For
assembly rather than a bare board, send `fab/rmc-pizz-arco-bom.csv` and
`fab/rmc-pizz-arco-pos.csv` as well.

## Questions for RMC

1. **DIN-8 pinout.** J7 is currently 1–6 = channels 1–6, 7 = ground,
   8 = reserved. Please confirm the pin assignment the Poly-Drive II expects.
2. **DIN pin 8.** Is it used — a ground, a shield, or a supply we could draw
   from instead of the wallwart? JP1 (unfitted) can tie it to ground.
3. **Which way round is pizz and which is arco?** The drawing labels the
   switch `[Space]`. On this board, switch **closed** = all-pass grounded =
   PZT 2 inverted relative to PZT 1.
4. **220 pF ‖ 1.5 nF = 1.72 nF.** Is one of these meant to be select-on-test,
   or is the pair simply how the value is made up? Both are fitted as drawn.
5. **3M3 bias against element capacitance.** The input high-pass corner is set
   by 3M3 and the element's own capacitance. For the bottom string of a gamba
   (D2, 73 Hz) this wants the element to be comfortably over 1 nF. Presumably
   fine, but worth confirming for the low strings.

## Regenerating

```bash
cd electronics && ./build.sh
```

Everything is generated from `design.py`, which is the single source of truth
for the circuit. `gen_sch.py` draws the schematic from it, `gen_pcb.py` builds
the board from it, and `verify.py` checks the drawn schematic still matches.
