# Where the redesign has got to

Written 2026-07-30, mid-rework, as a hand-off. Read this before running
anything in `electronics/`.

## Starting a fresh session

The rework is meant to begin in a new session briefed by this document. Paste
the following, with RMC's answers filled in:

> Read `electronics/STATE.md` before doing anything else. It is a hand-off
> document for a PCB redesign that was paused waiting on the manufacturer, and
> it carries the decisions, the measured findings, and the traps.
>
> RMC have now answered the four open questions:
>
> [PASTE RMC'S REPLY HERE]
>
> Work through what those answers change, then **plan the rework before
> editing anything**.
>
> Three things from STATE.md that are easy to miss and expensive to get wrong:
>
> - **`main` holds the *original* 88 × 112 mm board.** The generators there
>   are the starting point, not the redesign.
> - **The abandoned ±9 V charge-pump attempt is on `supply-charge-pump`.** Take
>   `RMC-QUESTIONS.md`, `ENCLOSURE.md` and the `verify.py` `NO_CONNECT` change
>   from it. Rework the generators from `main`, *not* from that branch — its
>   `design.py` looks like a head start and isn't.
> - **`electronics/` is a circuit-agnostic KiCad toolchain plus a
>   circuit-specific layer.** Keep the toolchain verbatim, rewrite the circuit
>   layer. STATE.md says exactly where the line falls and why.
>
> If the Poly-Drive rails come back at ±4.5 V, stop and flag it rather than
> designing around it. That is the headroom question this project has already
> been round twice, and with power coming from the DIN there is no battery
> left as a fallback.

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

## How to approach the rework: keep the toolchain, rewrite the circuit layer

`electronics/` is not one codebase. It is a **circuit-agnostic KiCad
toolchain** with a **circuit-specific layer** on top, and the seam is clean.
Neither "refactor everything" nor "start fresh" is right.

### Keep verbatim — ~1020 lines with no circuit knowledge at all

| File | Lines | What it is |
| --- | --- | --- |
| `sexp.py` | 103 | S-expression reader/writer. Remembers which atoms were quoted, which is what makes KiCad load the output at all. |
| `symlib.py` | 105 | Reads stock symbols and **flattens `extends`** — most stock parts are derived. Reports pin coordinates so wires land on real connection points. |
| `kicad.py` | 161 | Finds the KiCad install. |
| `kisch.py` | 343 | The schematic writer: placement, wires, junctions, labels, no-connects, **deterministic UUIDs**, the 1.27 mm grid check. |
| `verify.py` | 226 | Exports KiCad's netlist and compares it to `design.NETS`. Touches the design only through its public surface. |
| `build.sh` | 85 | Orchestration, including running `gen_pcb.py` under KiCad's bundled interpreter. |

Two pieces here are expensive to rebuild and silent when wrong:

- **The deterministic UUID scheme.** `kisch._uuid` derives symbol UUIDs from a
  name hash, and `gen_pcb.py` imports *that same helper* to link footprints
  back to symbols. It is what makes cross-probing work and stops *Update PCB
  from Schematic* offering to re-add every footprint. Nothing about it changes
  with the circuit.
- **`symlib.flatten`.** Merging a parent's body with a child's properties and
  renaming unit sub-symbols is fiddly, and it already handles the
  borrow-and-rename pattern the design depends on.

### Rewrite rather than adapt

The circuit-specific functions only:

- **`design.py`** — keep `Part`, `Design`, `_resistor`, `_capacitor`,
  `patch_symbol`, `build_footprint`, the constants block. Rewrite `channel()`,
  `switch_bank()`, `output()`; `power()` mostly *deletes*.
- **`gen_sch.py`** — keep `place_passive()`, `pin_for()`, `hang()` and the
  `build()` skeleton. Rewrite the section drawers.
- **`gen_pcb.py`** — keep the whole `Board` class (`place`, `pad`, `track`,
  `via`, `stub_via`, `zone`, `outline`, `text`). Rewrite placement and routing.

These change shape too much to bend: one op-amp per channel becomes one quad
per *two* channels, so the tile becomes a two-channel block, and the power
section disappears entirely. Adapting `route_channel()` would drag across
placement constants that no longer mean anything.

### A latent bug to fix on the way past

`gen_project.symbol_library()` hard-codes exactly one part:

```python
symbol = symlib.flatten("Amplifier_Operational", "OPA2197xD", rename="OPA2191")
```

The charge-pump branch added `rmc:TC1044S` to `LIBS` and used it, but never
updated this — so `rmc.kicad_sym` would have been written without TC1044S.
**Nothing in the build catches it.** The schematic embeds its own copy of every
symbol in `lib_symbols`, so ERC passes and `verify.py` passes; the fault only
shows when a human opens the project in KiCad and finds a broken library link
on that symbol.

Fix by driving `symbol_library()` off `circuit.LIBS` — iterate the entries
whose nickname is `rmc` — exactly as `library_tables()` already does. Then
adding a borrowed part to `LIBS` is sufficient and the two cannot drift.

Also in `gen_project.py`: `netclass_patterns` still lists `VIN` and `VFUSED`,
which go with the power section.

### One verification step the build does not cover

`build.sh` checks the netlist, ERC and DRC, but nothing checks the *project
library*. Once per session, open `rmc-pizz-arco/rmc-pizz-arco.kicad_pro` in
KiCad and confirm no symbol shows a broken library link. That is the check
that would have caught the bug above.

---

## Practical notes for whoever does the rework

Things that cost real time on the abandoned attempt. None are obvious from
reading the code.

### Toolchain

- `./build.sh` regenerates schematic *and* board from `design.py`. Anything
  changed in the KiCad GUI is destroyed on the next run.
- `gen_pcb.py` must run under KiCad's own bundled interpreter (`pcbnew` lives
  there); everything else runs under `../.venv/bin/python`. `build.sh` handles
  this, but standalone runs need it done by hand:
  `"$(../.venv/bin/python kicad.py python)" gen_pcb.py`
- Running `gen_sch.py` or `verify.py` standalone needs `KICAD10_SYMBOL_DIR`
  and `KICAD10_FOOTPRINT_DIR` exported — see the top of `build.sh`.
- **`kisch` enforces a 1.27 mm grid** on every wire endpoint and pin, and
  raises with a list of offenders. Every schematic coordinate must be a
  multiple of 1.27. This is a feature; it catches real mistakes.
- `verify.py` skips the board-linkage check when the board file is absent, so
  the schematic can be iterated on its own before the board exists.

### Layout

- **Never predict rotated pad positions — measure them.** Place the parts,
  then dump real pad coordinates and courtyards from the placed footprints and
  write the routing against those. Guessing KiCad's rotation conventions was
  the single largest source of wasted iterations.
- **B.Cu is the V− pour.** Heavy B.Cu routing fragments it, and the symptom is
  `unconnected_items` on V− in distant parts of the board, not anything that
  looks like a routing error.
- **SMD connector pads are F.Cu only.** A B.Cu run to a connector needs a via
  to get there. The old board's through-hole headers hid this; it broke every
  B.Cu approach when the connectors went SMD.
- **A 0.65 mm pin pitch cannot take a row of stub vias.** A 0.6 mm via needs
  0.8 mm. Move them inboard under the package body and alternate between two
  columns.
- **Two parallel components between the same two nets always interleave** when
  laid side by side in a row — one of the two nets has to cross the other.
  Either stack them, or put one net on a jumper layer. This applies to the
  all-pass feedback pair, and it applied to the summing pair before RMC
  collapsed it to a single capacitor.
- **Lane pitch:** a lane that ends in a via needs ≥0.625 mm to its neighbour;
  lanes carrying no vias can go down to 0.5 mm.
- **Fan-in ordering matters.** With the output header *below* the tiles,
  channel 1 needs the outermost lane and the lowest approach row, and the
  header's pin 1 at the far end. Get it backwards and every lane crosses every
  other. The original board had the header at the top, which is why its
  ordering looks inverted.
- **DRC workflow:** group violations by rule and by board region. The six
  channels are identical, so one tile fault shows up six times — fix it once
  and the count drops by six. Going 316 → 227 → 69 → 29 → 13 → 5 took five
  passes done this way.

---

## RMC's reply, 2026-07-30 — verbatim

Kept in full because every paraphrase above is an interpretation, and the
details of the control network and bypass are specific.

> Well noted that you're switching using CD4066 which eliminates the need for
> a physical multi-pole switch. It's a quad switch package, one side of each
> switch is Grounded and the control lines are all paralleled, so the line
> count is low around the IC, so I'm not sure why you're using 3 of those...
>
> Yes, OPA2191 or OPA4191 keeps the board more compact and the power lines
> shorter.
>
> Power can be drawn from the PD2 power rails via DIN-8 connection. Since this
> is a 6-string instrument, pins 1 thru 6 are separate string signals while
> bipolar power can travel on pins 7 & 8. Shell/Shield is Ground - no need for
> multiple Grounds here. DIN-8 Purple #7 and Grey #8 wires must be
> disconnected from the preamp inputs in order to be carrying power.
>
> Drawing power from the preamp rails eliminates power management circuitry on
> the new board.
>
> CD4066 will function properly from ±4.5VDC. The control lines are parallelled
> and resistively tied to Vss via 1MΩ. The switch shorts the Control lines to
> Vdd via a low-value series resistor like 20KΩ. The control line should have a
> 0.01µF cap to Ground to de-bounce the switch.
>
> Power bypass to Ground near the IC's can be a pair of 4.7µF/25V caps at each
> end of the power rails on the new board.
>
> The piezos are out-of-phase on the transducer plate, so they're effectively
> in-phase when the switch is closed to create the inverter function.
>
> FYI, the 100pF capacitors have no audible effect. Their presence is only
> required for preventing oscillation & HF interference.
>
> The equivalent capacitance of each piezo element is 1700 pF, so I used 1.5nF
> & 220pF in my model to approximate that value. In practice one might want to
> select 1.8nF capacitors with a 1.7 nF ±50pF value and they should all be
> about the same value to maintain good string balance and uniform polar
> characteristics.
>
> Always check the capacitance of the caps you're installing because the actual
> value is typically less than the nominal value. Resistors in the inverter
> portion of the circuit should be ±1% tolerance and there's usually no need to
> test those, although better safe than sorry when prototyping.
>
> The DIN-8S connection has no built-in switching function. The socket contacts
> are fork-type which accept a pin.
>
> Shrinking the board is a good idea.
>
> Manual assembly isn't difficult if you're using 0805 passives and SOIC
> packages. Just ease-off on the soldering temperature.
>
> Whenever you need to pass 2 lines side-by-side between a component's
> terminals, you can use a 1206 size component and that way you can eliminate a
> lot of vias and layers while keeping the layout simple & compact.
>
> It's also OK to use through-hole jumpers (wire-wrap AWG #30 wire) when a long
> jump is a pain in the ass layout-wise. The operating frequencies are so low
> that any resulting inductance is negligible as long as the printed power rails
> have bypass caps. When prototyping you have options that would be avoided in
> mass-production in order to minimize labor.

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
