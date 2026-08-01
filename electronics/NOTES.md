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
  first-order all-pass, then summed into `OUT` through a single **1.8 nF**.

RMC have since confirmed the element's own capacitance is **1700 pF**, which
is what the summing capacitor is matching: the red element works into it
directly, so equal capacitance means equal weighting at the summing node. That
is why the six must match each other — it is string balance, not tolerance
fussiness. Against the 3M3 bias resistor, 1700 pF puts the input corner at
**28 Hz**, well below the bottom string at 73 Hz.

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

The drawing shows one channel and leaves the supply and the switching open.
Only two things were added, and both are smaller than they once were:

- **Switching.** The drawing shows one switch per channel. Bussing six
  channels to a single mechanical SPST would short them all together when
  open, so each channel gets its own contact: six CD4066B cells driven from
  one control line. On-resistance ~100 Ω against 47 k is −54 dB, and the
  switched node carries no DC, so there is no click. R701/C701 slow the
  transition to about 10 ms.

  These sit in **two** packages, U4 and U5, using three cells of each with one
  spare. An earlier revision used three packages restricted to the A and B
  cells, on the theory that keeping signal and control apart mattered; RMC
  pointed out that this is wrong — one side of every cell is grounded and the
  control lines are all paralleled, so there is very little to route around
  the package. Each package sits beside the three channels it serves, and the
  spare cell in each is parked with its signal pins on AGND and its control on
  V−.
- **Decoupling.** Four 4.7 µF/25 V capacitors, a V+→AGND and a V−→AGND pair at
  each end of the rails, exactly as RMC specified. This replaces the eighteen
  local capacitors an earlier revision carried: the In1/In2 plane pair already
  supplies the local V+-to-AGND decoupling those were doing.

**What is no longer here at all:** the mid-rail buffer and its divider, the
resettable fuse, the series Schottky, the TVS, and the whole power section.
The supply arrives ready-made from the Poly-Drive II, and the deletion of the
mid-rail buffer in particular is what makes the grounding rule below free
rather than expensive — it was the one real source of DC in the ground
return.

## Supply — read this before wiring anything

> **This board has no supply of its own.** No battery, no power section, no
> regulator, no protection. It is powered entirely by the Poly-Drive II, over
> the same DIN-8 that carries the audio.

**±4.5 V arrives on DIN pins 7 and 8, with the shell as ground.** RMC settled
this over three rounds and recommend it explicitly: power management happens
only in the Poly-Drive II, and the instrument electronics are slaved to it.

| | |
| --- | --- |
| **Pin 7** | **+4.5 V** |
| **Pin 8** | **−4.5 V** |
| Shell / shield | ground, both audio and DC |
| Source | a 9 V battery in the PD2 through a transistor rail splitter |
| Our draw | ~2 mA, of an under-6 mA total shared with the PD2's own 3.5 mA |

**Pins 7 and 8 are spare preamp inputs as the PD2 ships**, and they have to be
disconnected from the preamp before they can carry power. **RMC do that
themselves when they assemble our unit** — it is not an aftermarket job on
someone else's hardware, and there is nothing for us to open.

### Polarity — the fault that destroys the board

**There is deliberately no reverse-protection diode.** A series Schottky per
rail would cost about 0.6 V of a 9 V total supply, roughly 0.6 dB of headroom
this design does not have to spare. A loom built backwards therefore puts 9 V
backwards across every op-amp and destroys the board.

The mitigation is procedural, not electrical: **pin 7 = +4.5 V, pin 8 =
−4.5 V**, printed on the silkscreen, repeated here, in `ENCLOSURE.md` and in
`fab/ORDER.md`. **Continuity-check the loom from the DIN plug to J7 before
first power-up.** The polarity is ours to define — RMC called their own pin
7 = + "arbitrary… just my knee-jerk response" — so it is the board that sets
the convention and the loom that follows it.

### Headroom, and what happens when it runs out

The rails allow about **±4.35 V** of swing. There is no gain anywhere on the
board — the buffer is unity and the all-pass is ±1 — so the requirement is
simply the white element's own peak output.

**RMC's answer (2026-08-01) is that this is fine, and that clipping on hard
pizzicato is acceptable when it happens.** There is no single peak figure to
quote, because output depends on excitation, string tension and break angle:

- **Arco cannot clip.** A bowed attack is a short noisy fade-in with no large
  percussive transient, and out of phase the two elements cancel vertical
  force variations at the summing node.
- **Pizz can, and it is inaudible.** In phase, vertical sensitivity is at its
  maximum and a picking transient may saturate the buffer. But the red element
  bypasses the electronics entirely and dominates for those milliseconds, so
  what you get is an extremely short change in polar pattern, not a click or
  a buzz.

**This rests on the amplifier not latching up, which was checked rather than
assumed.** OPA191/2191/4191 datasheet SBOS701D §8.3.3: the family has internal
phase-reversal protection, and input signals beyond the rails do not cause
phase reversal — the output simply limits into the appropriate rail.

One consequence worth knowing when servicing: the datasheet's absolute maximum
on an input pin is only 0.5 V beyond the rail, with a ±10 mA input current
limit. **R01, the 1 kΩ stopper in each channel, is what keeps the input clamps
inside that rating** — even 5 V of overdrive draws 5 mA, half the limit. It was
put there as a stopper and it is also what makes accepting clipping safe.
**Do not reduce it.**

If clipping ever does prove audible, the fix needs no respin: a capacitor in
parallel with R02 (3M3) divides against the element's own 1700 pF and
attenuates the white signal into the buffer, and increasing C04 loads the red
element correspondingly to restore the balance. Component values only.

## Board

- **78.8 × 81.3 mm, 4 layers.** 80 placements: 72 SMD (1206 passives, SOIC-14
  and SO-14 packages) and 8 through-hole 2.54 mm pin headers.
- **Stackup:** F.Cu signals · In1.Cu solid AGND plane · In2.Cu solid V+ plane ·
  B.Cu signals. Four layers rather than two is what keeps this tractable:
  every supply and ground pad reaches its rail through a single via, and the
  high-impedance piezo traces run over unbroken ground.
- **V− is not a plane.** At about 2 mA it never needed one, and a B.Cu pour was
  this project's worst failure mode — fragmenting it produced unconnected items
  in parts of the board nowhere near the cause. It is routed like any other
  net, and B.Cu is a second signal layer.
- **Three blocks** down the left, each one OPA4191 quad serving two channels,
  with the two channels mirrored above and below it. Each has its own 3-pin
  pickup header. Then a corridor for the six outputs and six switched nodes,
  the two switch packages and the control network, and the tail connectors laid
  flat along the bottom.
- Per-saddle headers J1–J6 are wired **1 = shield, 2 = white, 3 = red**.

**1206 passives throughout, not 0805.** This is RMC's advice — "whenever you
need to pass 2 lines side-by-side between a component's terminals, you can use
a 1206 size component and that way you can eliminate a lot of vias" — applied
uniformly. Measured clear gap between pads: 0805 gives 0.80–0.90 mm, 1206 gives
**1.80 mm**. At 0.65 mm lane pitch that is one lane against two, and on this
board a 1206's own pad gap is where most of the routing crosses from one side
of a channel to the other. Going bigger bought more than going smaller ever
did.

**The board is not dense, and that is the point.** Land utilisation is about
14%, lower than either previous revision. What sets the size is not area for
parts but room for lanes — which is why the right-hand column sits 2 mm
further out than the parts need and the tail connector 0.5 mm lower than it
has to. Both were spent on measured crossings. A smaller number from an
unroutable placement is not a smaller board.

## Installing it

Every pin number below comes from `design.py`, which is the source of truth;
`verify.py` checks the schematic still agrees with it on each build.

### The signal chain

```
6 saddles -- each RMC pizz/arco holds TWO piezo elements
  red --+   white --+   shield --+       3 wires per saddle, 18 in total
        v           v            v
   J1..J6:       pin 3        pin 2     pin 1
        |
        +-- red -------------------------------------+   never sees an op-amp
        |                                             |
        +-- white -> 3M3 bias -> 1k/100p -> buffer -> +-1 --+ via 1.8 nF
                                     (polarity from J8)     v
                                                        OUT (1 of 6)

   6 x OUT + ground + the two supply rails, all on the same connector
        v
   J7, 9-way --> instrument DIN-8 socket --> RMC cable --> Poly-Drive II
```

Two things follow from this that are easy to get wrong:

- **The red element never passes through the electronics.** It runs straight
  from the saddle to the DIN. Only the white one is buffered and
  polarity-switched, then summed back into the red through 1.8 nF.
- **The board applies no gain, and its output is still piezo-like** -- high
  impedance, with no load resistor on board. That is deliberate: it is what
  the Poly-Drive II expects to see, and the Poly-Drive supplies the load.
  The board exists to do the two-element mix, which the Poly-Drive cannot,
  because it has only one input per string.

### Connectors

| | Pin 1 | Pin 2 | Pin 3 | |
| --- | --- | --- | --- | --- |
| **J1–J6** saddle 1–6 | shield | white | red | |
| **J7** to DIN-8 | pins 1–6 = channels 1–6 | 7 = **+4.5 V**, 8 = **−4.5 V** | 9 = shell / ground | check polarity before power-up |
| **J8** pizz/arco toggle | switch | control | | DC only, no audio |

**J7 has nine pins for an eight-pin DIN.** Pins 1–8 are the DIN's own pins and
pin 9 is the shell, which is the ground connection.

Switch **closed** grounds the all-pass and inverts the white element relative
to the red. RMC have confirmed which way round that is:

| Toggle | Control line | CD4066 | All-pass | Elements | Mode |
| --- | --- | --- | --- | --- | --- |
| closed | +4.5 V via 20 kΩ | ON | −1 | in phase | **PIZZ** (picking) |
| open | −4.5 V via 1 MΩ | OFF | +1 | out of phase | **ARCO** (bowing) |

In-phase is for picking, because it maximises vertical sensitivity;
out-of-phase is for bowing, because it maximises horizontal sensitivity.

> **The rest state is ARCO.** The control line is pulled to the negative rail
> through 1 MΩ, so that is what the instrument does with the toggle
> disconnected, the loom broken, or the switch not yet wired. If a newly built
> instrument sounds like it is permanently in arco, suspect the toggle wiring
> before suspecting the board.

### Grounding — read before wiring

> **Ground is the DIN shell, and there is nothing else.** No mid-rail, no
> battery negative, no second ground. RMC: "Shell/Shield is Ground — no need
> for multiple Grounds here."

This is a real simplification over the previous revision, where audio ground
was a buffered mid-rail and bonding it to anything was a serious fault. That
buffer is gone with the power section.

What replaces it is a design rule, and it is one that must not be broken later:

> **No DC path from either rail to AGND anywhere on the board.**

The reason is structural. The PD2's ground is the midpoint of a transistor
rail splitter, and it reaches this board down the DIN shell — the same single
conductor that carries all six string returns. Any DC imbalance flows in that
one conductor, straight through the audio return path. RMC put it as "the
current flowing in the Ground terminal is only related to the Audio signals",
and asked that the drain on the two rails be symmetrical.

Audited against what is built, the rule holds: the only things on AGND are the
six saddle shields, the six 3M3 bias resistors, the RF and all-pass capacitors,
the grounded side of each 4066 cell, C701 and the four bypass capacitors. Total
DC into ground is leakage only. Everything else runs rail-to-rail — the
OPA4191s draw V+ to V− through the die, and **the CD4066 has no ground pin at
all** (pin 7 is Vss = −4.5 V, pin 14 is Vdd = +4.5 V).

**What this forbids, if the board is ever modified:** no power LED, no
rail-to-ground divider, no single-ended pull-up, no asymmetric bypass. All four
are the sort of thing that looks harmless and puts DC in the audio return.

The toggle on J8 carries DC only, so its wiring is uncritical; just keep its
terminals clear of anything grounded.

### Switching it off

**There is nothing to switch off here.** The board has no supply of its own —
it is live exactly when the Poly-Drive II is live, and goes away with it.
Whatever power switching the PD2 has is the power switching this instrument
has, and that is now RMC's side of the connector.

The earlier revision needed a switch in the battery lead, because a pack left
connected went flat in about ten days. That problem left with the battery.

### If the PD2's battery goes flat

**Everything stops, including the passive path.** This is a change from the
previous revision and worth stating plainly, because the old failure signature
is now completely wrong.

Previously the red element reached the DIN through copper alone and survived a
dead battery, so a flat battery gave a thinner, quieter instrument with the
pizz/arco switch doing nothing. **That no longer applies.** The battery now
lives in the Poly-Drive II, which is the preamp the whole instrument feeds; if
it is flat there is no output at all, from either element, whatever this board
is doing.

**There is no low-battery warning, and there cannot be one.** RMC specify a
regulated USB-rechargeable pack, which holds 9 V for its whole life and then
falls off a cliff — so a preamp watching battery voltage has nothing to watch.
Their answer is a habit rather than a circuit: **charge it once a week.** At
about 70 hours of playing per charge that covers a week comfortably, and
charging takes under an hour.

This is worth telling whoever plays the instrument, because it is the one
maintenance task the design has and the one failure mode with no warning.

### Alternative: an outboard enclosure

Housing the board and battery in an external pedal was considered and not
taken. Recorded here because the reasoning is not obvious.

**A footswitch, however, is free today.** J8 carries DC control only — the
CD4066 keeps the toggle out of the signal path entirely — so the pizz/arco
switch can sit on an arbitrarily long two-conductor cable in a footswitch box
with no audio penalty at all, and the audio stays in the instrument. It will
be click-free: the switched node carries no DC, and R701/C703 already slow the
transition to about 10 ms. If hands-free switching is what is wanted, this is
the whole answer.

Moving the *board* out is harder:

- **Conductor count is the blocker.** The instrument currently sends six
  signals plus ground — each one a saddle's two elements already combined —
  which is exactly what the 8-pin DIN carries, and that only works because the
  combining happens at the bridge. Outboard, the raw elements have to travel:
  2 per saddle × 6 = **12**, plus ground. A 13-pin DIN (the Roland GK
  connector) fits exactly, but it is a different socket and cable, and the
  chain becomes instrument → 13-pin → pedal → 8-pin → Poly-Drive.
- **It relocates the highest-impedance node in the design.** The white
  element's 3M3 load and its buffer would move to the far end of that cable.
  Cable capacitance forms a divider against the element — how much loss
  depends on the element's own capacitance, now known to be 1700 pF — and twelve
  high-impedance lines sharing a multicore risk crosstalk, which attacks
  precisely the per-string separation a hex system exists to provide. Roland
  GK cables work because the GK pickup buffers *at the instrument*, for this
  reason.
- **Powering it is now the hard part, not the easy part.** The board's rails
  arrive from the Poly-Drive II over the DIN, so an outboard box would either
  have to carry those rails down the same cable that is already full of
  high-impedance element signals, or generate its own — which is exactly the
  local power management RMC have twice recommended against.

## Status

- Schematic: **ERC clean.** The 10 remaining warnings are all one benign case
  — a CD4066 bidirectional pin meeting a power flag, which is what those pins
  are.
- The generated schematic is read back through KiCad and compared against
  `design.py` net by net — **53 nets, 233 pin connections, exact match**. See
  `verify.py`, which also checks that every footprint on the board is linked
  back to its symbol.
- Board: **fully routed, 0 DRC violations, 0 unconnected items.** Routing is
  entirely in `gen_pcb.py`; no autorouter is involved.
- Three checks the build cannot make: open the project in KiCad once and
  confirm no symbol has a broken library link; re-audit AGND by hand against
  the list under "Grounding"; and confirm `design.NO_CONNECT` is still empty.

## Opening it in KiCad

Needs **KiCad 10.x** — see the Requirements section in the top-level
`README.md`, including the `KICAD_APP` override if yours is installed
somewhere unusual. On this machine it sits in `~/Applications/KiCad`, not
`/Applications`, because the Homebrew cask install wanted a sudo password it
had no terminal to prompt for.

Open **`rmc-pizz-arco/rmc-pizz-arco.kicad_pro`**. Schematic and board both
open, cross-probing works (clicking a symbol highlights its footprint), and
*Update PCB from Schematic* reports no changes — the generated board carries
the schematic symbol paths that make all of that work.

> **`build.sh` regenerates the schematic and the board from scratch, so
> anything changed in the GUI is destroyed on the next build.** `design.py` is
> the source of truth. Use the editor to inspect, measure and try things out;
> changes that should survive belong in the generator.

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

## Questions for RMC — all answered

Four rounds of correspondence, 2026-07-30 to 2026-08-01. Nothing is
outstanding. The full text of every reply is kept verbatim in `STATE.md`,
because every paraphrase is an interpretation; this is the summary.

| Asked | Answered |
| --- | --- |
| **DIN-8 pinout, and is pin 8 used?** | Pins 1–6 are the six string signals, **pins 7 and 8 can carry bipolar power**, shell/shield is ground. They are spare preamp inputs as shipped and must be disconnected from the preamp first — which RMC do at assembly. |
| **Supply** | ±4.5 V from a 9 V battery in the PD2 through a transistor rail splitter. Power management stays in the PD2; the instrument electronics are slaved to it. No local supply. |
| **Element capacitance** | **1700 pF.** Against 3M3 that is a 28 Hz corner, well below the bottom string. |
| **The 220 pF ‖ 1.5 nF pair** | It was approximating that 1700 pF. Collapses to a single capacitor; **1.8 nF C0G**, matched across the six. |
| **Peak open-circuit output on hard pizzicato** | No single figure — it is instrument-specific. Arco cannot clip; pizz can, and it is inaudible. See "Headroom" above. |
| **Which way round is pizz and which arco?** | In-phase (switch closed) is for picking, out-of-phase for bowing. |
| **Does the DIN-8S socket switch?** | It does not — the contacts are fork-type and accept a pin. Moot now: there is no battery here to switch. |
| **Inverter resistor tolerance** | ±1%. |
| **Decoupling** | A pair of 4.7 µF/25 V at each end of the rails, replacing our eighteen local capacitors. |
| **Three CD4066 packages or two?** | Two. One side of every cell is grounded and the control lines are paralleled, so there is very little to route. |

### Advice we are deliberately not taking

Four of RMC's suggestions assume a self-built board, and this one is going to
a turnkey line. Recorded so they are not re-litigated:

- **"Select 1.8 nF capacitors with a 1.7 nF ±50 pF value."** Impossible on a
  turnkey line. Solved instead by ordering all six from one reel, so they track
  each other far more tightly than the tolerance band suggests.
- **"A multi-layer ceramic capacitor can be trimmed by abrading it."** A
  hand-selection method by another route. **Keep it as a field-service note** —
  it is genuinely useful if one of these ever needs adjusting after the fact —
  but the board is specified so it never has to be used.
- **"Through-hole jumpers (wire-wrap AWG #30) when a long jump is a pain."**
  Reintroduces manual operations to a board built in one pass. Solved with the
  1206 trick instead.
- **"Manual assembly isn't difficult with 0805 and SOIC."** True, and why the
  board started that way — but turnkey assembly is what freed the package
  choice, and the 1206 passives it allowed are what made the routing work.

### One query left open on RMC's side, not ours

RMC offered to fit a **USB socket in the Poly-Drive II enclosure**, so the
preamp can be phantom-powered and the battery kept charged. Charging is fine.
**Running permanently from USB may not be:** the battery's negative terminal
*is* the −4.5 V rail, because the splitter's midpoint is signal ground. If the
socket's ground is common with battery negative and it is fed from an earthed
source while the PD2's output reaches earth through a mixer, the −4.5 V rail is
tied to earth through the audio ground — a short across the lower half of the
splitter.

It only bites in the permanently-powered case; occasional charging can always
be done unplugged. It affects their enclosure, not this board, and they may
already isolate the charging circuit.

## Regenerating

```bash
cd electronics && ./build.sh
```

Everything is generated from `design.py`, which is the single source of truth
for the circuit. `gen_sch.py` draws the schematic from it, `gen_pcb.py` builds
the board from it, and `verify.py` checks the drawn schematic still matches.
