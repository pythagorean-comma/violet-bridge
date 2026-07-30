# Where the redesign has got to

Written 2026-07-30, mid-rework, as a hand-off. Read this before running
anything in `electronics/`.

## Status in one line

**Blocked, waiting on RMC.** Four questions were sent on 2026-07-30 (below).
No rework should start until they answer, because this is the second time an
assumption about the supply has forced a redo.

---

## Where the code is

**`main` is the original 88 × 112 mm hand-buildable board** (`8c425fb`), plus
this document. Nothing on `main` implements the redesign, and the generators
and `fab/` outputs there are self-consistent — they are simply the old board.

**The superseded ±9 V exploration lives on `supply-charge-pump`** (`57c62b8`,
pushed to `origin`). That branch implements a bipolar supply from a charge
pump with an onboard battery, and it is complete and internally consistent —
`verify.py` matches the schematic to the netlist exactly, 58 nets and 322 pin
connections, and the board lays out at 56 × 94 mm with DRC nearly clean.

**It is superseded.** RMC's reply of 2026-07-30 established that the board
takes **bipolar power from the Poly-Drive II down the DIN-8**, so there is no
battery, no charge pump, and no power section at all. Do not fabricate from
that branch's `fab/` outputs.

### What is worth retrieving from the branch

| | |
| --- | --- |
| `verify.py` | Gained a `NO_CONNECT` mechanism so deliberately-floating pins are declared in `design.py` rather than waved through in the checker. **Worth keeping**, though it may not be needed — it existed for the TC1044S's floating LV and OSC pins, and the pump is gone. |
| `RMC-QUESTIONS.md` | The original seven questions, as sent. |
| `ENCLOSURE.md` | Tail-block enclosure study. The mounting analysis and the 18-wire loom problem still stand; everything about the battery bay, charging hatch and mass budget does not. |
| `design.py`, `gen_pcb.py` | The channel circuit and the measured layout findings below. The supply sections are dead. |

`NOTES.md` on `main` describes the original board accurately, but its supply
reasoning — the whole 9 V vs 12 V argument and the grounding warnings that
follow from a mid-rail — is now known to be answering a question that did not
exist. See below.

---

## What RMC's reply changed

Their answer of 2026-07-30 settled five of the seven original questions and
corrected two of our own decisions.

### Power — the big one

> "Power can be drawn from the PD2 power rails via DIN-8 connection... pins 1
> thru 6 are separate string signals while bipolar power can travel on pins 7
> & 8. Shell/Shield is Ground — no need for multiple Grounds here."

So RMC's original "12 V floating supply" was about an outboard, mains-powered
box, exactly as `NOTES.md` speculated it might be. It carried no information
about headroom. The entire supply argument — 9 V vs 12 V, floating vs earthed,
mid-rail vs charge pump — was answering a question that did not exist.

**Deleted:** J9, F701, D701, D702, D703, C701, C704, U7 (the pump), C705,
C706, R702, C707, C708.

> **`JP1` must be deleted, not merely left unfitted.** It ties DIN pin 8 to
> ground, and pin 8 is now a supply rail. Fitting it would short the
> Poly-Drive's rail to ground.

### Corrections to our own work

- **Three CD4066 packages should be two.** Our stated reason for three
  (`NOTES.md:203`, keeping signal and control apart) was wrong: one side of
  every switch is grounded and the control lines are all paralleled, so there
  is very little to route. Six cells, two quads.
- **Quad op-amps are now right.** They were rejected earlier on arithmetic —
  14 halves needs 4 quads, which was worse than 7 SOIC-8. Losing the mid-rail
  buffer drops us to **12 halves, exactly 3 quads, nothing wasted**.
- **Passives may need to get *bigger*, not smaller.** RMC: "Whenever you need
  to pass 2 lines side-by-side between a component's terminals, you can use a
  1206 size component and that way you can eliminate a lot of vias and
  layers." This directly attacks what we measured to be the real size
  constraint — routing lanes, not part size. See "The size lesson" below.

### Component values now settled

- **Element capacitance is 1700 pF.** Against R02's 3M3 that puts the input
  corner at **28 Hz**, well below the bottom string at 73 Hz. No change needed.
- **The 220 pF ‖ 1n5 pair was approximating that 1700 pF**, and collapses to a
  single capacitor. The cap matches the element deliberately: the red element
  works into it directly, so equal capacitance means equal weighting at the
  summing node. That is why RMC require them matched — it is string balance,
  not tolerance fussiness.
- **The 100 pF capacitors have no audible effect**; they are there for
  oscillation and HF rejection only.
- **The elements are out of phase on the plate**, so closing the switch brings
  them *into* phase.
- **Inverter resistors want ±1%.**

---

## The agreed target design

### Per channel (×6) — 10 passives, down from 13

R01 1k · R02 3M3 · C01 100p · R03 1k · R04/R05/R06 47k **±1%** ·
C02/C03 100p · **C04 1n8 C0G ±2%**

### Shared

- 3 × **OPA4191, SOIC-14**. Chosen over TSSOP-14 to keep 1.27 mm pitch, so an
  AGND guard ring still fits around each buffer's + input — the 3M3 node where
  surface leakage matters. ~156 mm² against ~176 mm² for six SOIC-8.
- 2 × CD4066B.
- Control network **per RMC**: R701 1 MΩ to Vss, R702 20 kΩ in series from the
  switch to Vdd, C701 10 nF to ground.
- Bypass **per RMC**: "a pair of 4.7 µF/25 V caps at each end of the power
  rails" — four capacitors, replacing our eighteen. Taken on RMC's authority
  as the circuit's designer; the design goes to them for review.
- 6 input connectors, 1 output connector.

**~79 placements against 120.** Draw falls to ~1.7 mA (12 halves × 140 µA).

### Quad assignment — get this right

A quad serves two channels, and how the halves are assigned decides where the
connectors can live.

**Assign the two buffers to A and B, and the two all-passes to C and D.**

Both buffer inputs are then pins 3 and 5, on the same side as the connectors,
and only the buffer *outputs* cross to the right-hand half — low-impedance
nodes that can run anywhere. The obvious alternative (channel 1 on A+B,
channel 2 on C+D) puts channel 2's buffer input on pin 10, dragging a 3M3
high-impedance node across the whole footprint, and forces the six pickup
connectors onto both edges of the board.

---

## The size lesson, measured

Worth recording because it was counter-intuitive and cost a full layout pass.

| | Area | Land utilisation |
| --- | --- | --- |
| Original 88 × 112 | 9856 mm² | 17% |
| Shrunk 56 × 94 | 5264 mm² | ~20% |

Shrinking the parts did **not** densify the board — it stayed ~80% air. The
binding constraint is that each channel must get five nets past its own
op-amp, each needing ~0.65 mm of width and clearance. Tile pitches of 9.5 mm
and 10 mm were both tried and both failed: at 10 mm the gap between the SOIC's
edge and the passive row is 0.44 mm, and a track needs 0.65 mm. **12 mm is
what the routing demanded.**

Two further measured results:

- **SMD connectors were not an area win.** A JST SH 1x03 courtyard is
  6.89 × 5.29 mm against ~8.6 × 3.5 mm for the 2.54 mm header. The gain was
  removing 30 plated holes that blocked routing on all four layers.
- **0.65 mm-pitch pins cannot take stub vias in a row.** A 0.6 mm via needs
  0.8 mm of pitch; every TSSOP plane connection had to move inboard under the
  package body, alternating between two columns.

Which is why RMC's 1206 suggestion matters. Pad gaps: 0402 ~0.5 mm (no track
fits), 0805 ~0.9 mm (one), **1206 ~1.6 mm (two)**. Going bigger on the parts
that lanes must cross buys more than going smaller ever did.

---

## Questions sent to RMC, 2026-07-30

1. **Rail voltage, polarity and current on pins 7 and 8.** What voltage do the
   rails supply, and which of pin 7 (Purple) and pin 8 (Grey) is positive?
   Total draw ~1.7 mA — is that comfortably available?
2. **Ground return.** Confirming the shell/shield is the only ground, shared
   by the six string returns and the power return.
3. **Summing capacitor tolerance.** Hand-selection is impossible on a
   machine-assembled board; proposing 1.8 nF C0G/NP0 ±2% (1.764 nF ±36 pF)
   instead. Does that meet the string-balance requirement?
4. **Switch labelling.** Which position is *pizz* and which *arco*?

**Question 1 is the one that could change the circuit rather than the
layout.** RMC's remark that "CD4066 will function properly from ±4.5 VDC"
hints at a modest rail. If the Poly-Drive supplies ±4.5 V, that is the
headroom position this whole exercise was trying to escape — and with no
battery there is no longer any lever to pull.

## RMC advice we are deliberately not taking

Three of their suggestions assume a self-built board:

- **"Select 1.8 nF capacitors with a 1.7 nF ±50 pF value."** Impossible on a
  turnkey line — hence question 3.
- **"Through-hole jumpers (wire-wrap AWG #30)."** Reintroduces manual
  operations to a board PCBWay is building in one pass. Solve with the 1206
  trick instead.
- **"Manual assembly isn't difficult with 0805 and SOIC."** True, and why the
  board started that way — but turnkey assembly is what freed the package
  choice.

**C0G/NP0 is not optional** for the 1n8 and 100 pF parts. X7R at these values
drifts with temperature and signal voltage and would destroy exactly the
string balance RMC ask for.

---

## Next steps, in order

1. **Wait for RMC on the rails.** Do not start the rework — this is the second
   time an assumption about the supply has forced a redo.
2. Branch from `main` for the rework. Take `RMC-QUESTIONS.md`, `ENCLOSURE.md`
   and the `verify.py` `NO_CONNECT` change across from `supply-charge-pump`;
   leave the generators behind and rework them from `main`, since the supply
   section there is dead and the channel circuit has changed too.
3. Rework `design.py` to the target design above, then `gen_sch.py`, then
   `gen_pcb.py`.
4. Rewrite `NOTES.md` — its supply, grounding, switching-off, flat-battery and
   outboard-enclosure sections are all now wrong.
5. Revise `ENCLOSURE.md` — the mounting analysis stands; the battery bay,
   charging hatch and mass budget do not. The box is now a board and a socket,
   perhaps 35 g rather than 100 g.
6. Update `fab/ORDER.md`: new board size, all-SMT, C0G and ±1% requirements,
   and remove the claim that the board was sized for hand-building.
