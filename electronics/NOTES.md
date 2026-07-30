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
  half supply by a 100k/100k divider buffered by U7A, so the amplifiers see
  half the supply either side of it: ±4.5 V on a 9 V pack, ±6 V on
  12 V. Because the supply floats this costs nothing and **no coupling
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

> **Intended arrangement: a 9 V onboard rechargeable pack, inside the
> instrument** — provisionally, pending the headroom check below, and it must
> be a pack that genuinely holds 9 V under load. RMC's drawing specifies a
> 12 V wallwart; the board accepts anything in 9–15 V, so this is reversible
> after building.

**9–15 V DC, and it must float** (no connection to mains earth). Floating is
the constraint that actually matters: the mid-rail buffer makes signal ground
half the supply, so an earth-referenced source would short it. A battery is
inherently isolated, so an onboard pack satisfies this for free — it is a
better source here than a wallwart, not a worse one.

No *component* on the board requires 12 V:

| Part | Range |
| --- | --- |
| OPA2191 ×7 | 4.5–36 V |
| CD4066B ×3 | 3–18 V |
| C701 bulk | 25 V rated |
| D702 SMAJ15A | 15 V standoff, never conducts in range |

But that is not the same as 12 V being arbitrary, and it should not be read
that way. **RMC specified 12 V over the far more convenient 9 V, and they know
their own elements.** Headroom is the obvious reason, so their choice is
evidence that the elements produce peaks worth leaving room for.

Running at 9 V costs about **2.5 dB** of headroom (±4.5 V rails rather than
±6 V). Two things limit the exposure: there is no gain anywhere in the signal
path — the buffer is unity, the all-pass is ±1 — so what is needed is the
white element's own peak, not a multiple of it; and **PZT 1 never passes
through an op-amp**, running straight to the DIN, so it cannot clip whatever
the rails do. Only the PZT 2 contribution is at risk, and it is attenuated at
the summing node relative to the op-amp output. Clipping would therefore be
transient distortion on the hardest attacks, not gross breakup.

### Checking the headroom

The deciding number is the white element's **peak open-circuit output on the
hardest pizzicato**. It is worth measuring rather than asking: it depends on
this instrument, these strings and this player, so a figure from RMC is only a
cross-check.

| Supply | Rails | Usable swing (OPA2191 is rail-to-rail) |
| --- | --- | --- |
| 12 V | ±6 V | ~±5.9 V |
| 9 V | ±4.5 V | ~±4.4 V |

To measure: wire one white element to a **3M3 resistor to ground with 100 pF
across it** — that replicates exactly what the buffer input sees — and probe
that node with a **×10 scope probe** (10 MΩ, ~12 pF, light enough not to
disturb it). Single-shot trigger, hardest pizzicato you would ever play, on
the lowest and the highest strings; the worst case governs. A multimeter is no
use here — it averages, and the transient peak is the whole question.

The buffer sees very nearly the open-circuit voltage, so element peak ≈ op-amp
peak: the 100 pF is only a mild divider against the element's own capacitance
(×0.91 for a 1 nF element, ×0.99 for 10 nF).

> **A "9 V rechargeable" is not necessarily 9 V.** NiMH types sit near
> **8.4 V** fully charged and sag under load, which gives ±4.2 V rails or
> worse and quietly invalidates the sums above. Use a **regulated Li-ion type
> that holds ~9 V** (Fishman's Universal Rechargeable Battery Pack is that
> sort of product), and **measure the pack loaded** rather than trusting the
> label.

**This need not be settled before building** — the board accepts 9–15 V with
no component change. Fit a pack, play it, and if the loudest attacks distort,
the options in order of practicality are:

1. **Stay at 9 V** if the measurement allows, with a pack that genuinely holds
   9 V under load.
2. **RMC's 12 V wallwart**, if the instrument need not be self-contained.
   +2.5 dB.
3. **A 12 V pack in 9 V form factor.** These exist — the "12 Volt Mod" is
   smaller than a PP3 — but confirm it is *rechargeable* and how it charges
   before relying on it. Hobby 3S Li-ion packs are not a sensible answer here:
   they generally need a balance charger and are frequently unprotected cells,
   which is not something to fit inside a wooden instrument.
4. **A ±9 V charge-pump respin** (ICL7660 / TC1044S / LT1054). Best headroom
   of the lot at **+6.1 dB**, keeps the convenient 9 V pack, and makes audio
   ground the battery negative — which would remove the grounding hazard
   described under "Installing it". This is a board change, not a swap.

**Do not run two packs in series at 18 V.** That is the CD4066B's absolute
maximum with no margin, and D702 would sit in conduction. It needs a
higher-voltage switch or an LDO down to 12 V — a respin, not a relabel.

**Do not boost 9 V to 12 V.** A switching converter beside a 3M3-loaded piezo
front end puts noise in the worst possible place to buy 2.5 dB.

That is an argument about the return, not about switchers in general. An
*inverter* to **±9 V** is a different proposition — about **6.1 dB**, roughly
2.4× the swing — and is the standard way guitar pedals win headroom from a 9 V
supply. See "Checking the headroom".

Total draw is about **2.1 mA** — fourteen OPA2191 halves at 140 µA each, plus
45 µA for the mid-rail divider and a negligible amount for the switches. On a
9 V pack that is a very long time between charges. R702/R703 are 100k rather
than the more usual 10k specifically to keep that figure down; the trade is
that the mid-rail reference takes about 2 s to settle at switch-on.

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
        +-- white -> 3M3 bias -> 1k/100p -> buffer -> +-1 --+ via 1.72 nF
                                     (polarity from J8)     v
                                                        OUT (1 of 6)

   6 x OUT + audio ground
        v
   J7, 8-way --> instrument DIN-8 socket --> RMC cable --> Poly-Drive II
```

Two things follow from this that are easy to get wrong:

- **The red element never passes through the electronics.** It runs straight
  from the saddle to the DIN. Only the white one is buffered and
  polarity-switched, then summed back into the red through 1.72 nF.
- **The board applies no gain, and its output is still piezo-like** -- high
  impedance, with no load resistor on board. That is deliberate: it is what
  the Poly-Drive II expects to see, and the Poly-Drive supplies the load.
  The board exists to do the two-element mix, which the Poly-Drive cannot,
  because it has only one input per string.

### Connectors

| | Pin 1 | Pin 2 | Pin 3 | |
| --- | --- | --- | --- | --- |
| **J1–J6** saddle 1–6 | shield | white | red | |
| **J7** to DIN-8 | pins 1–6 = channels 1–6 | 7 = audio ground | 8 = reserved | see the DIN pin 8 question |
| **J8** pizz/arco toggle | switch | + rail | | DC only, no audio |
| **J9** battery | + | − | | 9–15 V, floating |

Switch **closed** grounds the all-pass and inverts PZT 2 relative to PZT 1.
Which of those is "pizz" and which "arco" is an open question for RMC.

### Grounding — read before wiring

> **The audio ground is the mid-rail, not the battery negative.**
>
> The saddle shields (J1–J6 pin 1) and DIN pin 7 sit at *half the supply* —
> about +4.5 V above the battery's negative terminal on a 9 V pack.
>
> **Do not bond battery negative to the shields, to DIN ground, or to any
> instrument earth.** That shorts U7A's output through R704 (10 Ω), demanding
> roughly 450 mA. The mid-rail collapses and the board stops working
> correctly — a baffling fault if you are not expecting it.

Put positively: the Poly-Drive's ground, arriving over the DIN cable, is what
anchors the board's audio ground, and the battery floats on top of it. That is
the whole reason the supply has to be isolated — and why a battery suits this
better than a wallwart, being isolated by construction.

The toggle on J8 carries DC only, so its wiring is uncritical; just keep its
terminals clear of anything grounded.

### Switching it off

**There is no power switch on the board.** J9 runs straight through F701 and
D701 to the rails, so the board is live whenever a battery is connected —
played or not.

At about **2.1 mA**, a typical 500 mAh 9 V pack is flat in roughly **ten
days** of being left connected. Something has to break that circuit:

- a switch in the battery lead — simplest, and it can be anywhere convenient;
- a switched socket, if RMC offer one for the DIN-8 (worth asking alongside
  the pinout question);
- or unplugging the pack, which works but relies on remembering.

Guitars normally get this for free from a TRS output jack whose ring contact
breaks the battery when the lead is pulled. A DIN socket does not do that, so
it is a decision to make while the instrument is open. No board change is
involved either way.

### If the battery goes flat

The instrument does **not** go silent. The red element of each saddle reaches
the DIN through copper alone — no op-amp, no analog switch, nothing in series
— and its return runs shield → J pin 1 → ground plane → DIN pin 7, equally
passive. That loop survives a dead battery intact.

What is lost:

- **The white element entirely**, since its buffer is dead. You hear the red
  element alone, and the pizz/arco switch does nothing.
- **Some level on the red element too.** With the op-amp unpowered its output
  no longer drives `C04 ‖ C05`; those 1.72 nF stop being a source and become a
  shunt load across the output. The red element then works into that extra
  capacitance and loses level by the divider against its own — how much
  depends on the element capacitance, which is an open question for RMC.

So the signature to recognise is **suddenly thinner and quieter, with the
pizz/arco switch having no effect**.

The brown-out on the way down is less pleasant than the flat state. The
OPA2191 needs 4.5 V and is undefined below it, so expect noise and distortion
rather than a clean fade — a protected pack that cuts off abruptly is kinder
here than an alkaline sagging through a concert.

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
  depends on the element's own capacitance, still an open question — and twelve
  high-impedance lines sharing a multicore risk crosstalk, which attacks
  precisely the per-string separation a hex system exists to provide. Roland
  GK cables work because the GK pickup buffers *at the instrument*, for this
  reason.
- **Pedal power is not automatically isolated.** Daisy-chain supplies share a
  sleeve usually tied to audio ground, which would short the mid-rail buffer.
  A battery or a genuinely isolated output only — or a charge-pump respin for
  a true ±9 V ground, which would also recover the headroom lost at 9 V.

## Status

- Schematic: **ERC clean.** The 18 remaining warnings are all one benign case
  (a 4066 signal pin tied to ground, which is intended).
- The generated schematic is read back through KiCad and compared against
  `design.py` net by net — 58 nets, 330 pin connections, exact match. See
  `verify.py`.
- Board: **fully routed, 0 unconnected items, DRC clean.**

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

## Questions for RMC

**The wording to send is in [`RMC-QUESTIONS.md`](RMC-QUESTIONS.md)** — kept
separate so the questions exist in one place only. This section is the *why*:
what each answer changes for us. Numbering matches.

1. **Can it run on 9 V.** The pivotal one, and why it leads. Peak element
   output decides the supply — see "Checking the headroom" above for the
   ±4.4 V / ±5.9 V thresholds and the measurement we intend to make ourselves.
   Their figure is a cross-check, not a substitute: the governing number
   depends on the strings and the player. The sub-questions matter as much as
   the number — *why* they specified 12 V, and whether they were assuming an
   outboard mains-powered box rather than an installation inside the
   instrument. If the latter, their 12 V was free to them and carries no
   information about headroom at all, and we may have taken the design
   somewhere they did not intend.

   A wrong answer here changes the battery, the compartment, the switch
   arrangement and whether the instrument can be self-contained — decisions
   wanted before anything is bought or any cavity is cut.
2. **DIN-8 pinout.** Blocking for the wiring loom, not for the board. Our
   assignment — pins 1–6 = channels, 7 = ground, 8 = unassigned — is an
   assumption. If theirs differs it is a rewiring job at the socket, cheap now
   and tedious later.
3. **DIN pin 8.** If it is ground or shield, JP1 (fitted unpopulated) ties it
   there with no cutting. If it is a **supply**, we can only use it when
   isolated from DIN ground: our audio ground is the mid-rail, so a rail
   referenced to pin 7 gives a positive supply with no negative side for
   signals to swing into. Using it would mean a negative-rail generator and a
   re-bias — a respin, not a wiring change. Worth knowing before assuming the
   battery is the only option.
4. **Element capacitance.** Sets the input high-pass corner against the 3M3;
   under about 1 nF and the bottom string (D2, 73 Hz) starts to suffer. A
   separate concern from peak output, despite coming from the same part.
5. **Pizz or arco.** Purely a labelling question — the circuit is symmetric,
   so this decides which way round the legend on the toggle reads, nothing
   more.
6. **220 pF ‖ 1.5 nF.** If the pair is just how 1.72 nF was made up, it
   collapses to one capacitor and removes six components. If it is
   select-on-test, both pads stay.
7. **Switched DIN socket.** Decides whether the battery isolation is free at
   the socket or needs a switch in the battery lead. Either works; it is an
   installation choice, and the ten-day standby drain is why it matters.

## Regenerating

```bash
cd electronics && ./build.sh
```

Everything is generated from `design.py`, which is the single source of truth
for the circuit. `gen_sch.py` draws the schematic from it, `gen_pcb.py` builds
the board from it, and `verify.py` checks the drawn schematic still matches.
