# Where the redesign has got to

Written 2026-07-30, mid-rework, as a hand-off. Read this before running
anything in `electronics/`.

## Status in one line

**Everything is settled and the board is built. Nothing is outstanding.**

*Updated 2026-08-01. The sections below were written 2026-07-30, while the
headroom question was still open and no rework had started; both of those are
now false, and where a later section contradicts an earlier one, the later one
is right. Round four's answer is under "The headroom answer" below.*

After four rounds, the arrangement is fixed: **the Poly-Drive II supplies
±4.5 V** down DIN pins 7 and 8, shell as ground, and **RMC perform the
modification themselves when they assemble our unit.** Power management stays
entirely in the PD2, with the instrument electronics slaved to it, on their
explicit recommendation.

**This board carries no battery, no power section and no protection.** Stated
plainly because it was previously implied across three sections and asserted in
none. Total draw is under 6 mA — 3.5 mA for the PD2, ~2 mA for us — from a
1350 mAh USB-rechargeable 9 V, giving ~70 hours between charges.

**Headroom is answered and it does not change the circuit.** Arco cannot clip;
pizz can, and RMC's position is that this is inaudible provided the electronics
do not latch up, which the OPA4191's datasheet confirms they do not. Full
reasoning under "The headroom answer".

### Where the board is

**Branch `pd2-slaved-board`. The board is complete and DRC-clean.** `./build.sh`
regenerates schematic and board from `design.py`, checks both against it, runs
ERC and DRC and writes the fab package:

| | |
| --- | --- |
| Outline | **78.8 × 81.3 mm = 6406 mm²** — measured, not projected |
| Parts | 80 placements: 72 SMD, 8 through-hole connectors |
| Nets | 53 nets, 233 pin connections, matched to `design.py` exactly |
| DRC | **0 violations, 0 unconnected items** |
| ERC | 0 errors; 10 warnings, all of them a CD4066 bidirectional pin meeting a power flag, which is what those pins are |
| Routing | entirely in `gen_pcb.py`. No autorouter is involved and none is needed |

The size number above replaces the ~60 × 70 mm projection that used to sit at
the bottom of this document; see "The size lesson, measured".

**The remaining checks are the three `build.sh` cannot do** — open the project
in KiCad once and confirm no symbol shows a broken library link, re-audit AGND
by hand against the table below, and confirm `NO_CONNECT` is empty. The last
two are properties of `design.py` and have not changed since the schematic was
verified.

---

## Where the code is

**`pd2-slaved-board` is the current board** and implements everything in this
document. Work through it, not through `main`.

**`main` is the original 88 × 112 mm hand-buildable board** (`8c425fb`), plus
this document and `RMC-QUESTIONS-2.md`. Nothing on `main` implements the
redesign, and the generators and `fab/` outputs there are self-consistent —
they are simply the old board.

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
| `ENCLOSURE.md` | Tail-block enclosure study. The mounting analysis and the 18-wire loom problem stand. The battery bay, charging hatch and mass budget are dead — there is no battery in the instrument. Keep the Fishman specification and the charge-pump-vs-boost comparison until the headroom answer lands; they are the fallback's working, and only then are they safe to cut. |
| `design.py`, `gen_pcb.py` | The channel circuit and the measured layout findings below. The supply sections are dead. |

`NOTES.md` on `main` describes the original board accurately, but its supply
reasoning — the whole 9 V vs 12 V argument and the grounding warnings that
follow from a mid-rail — is now known to be answering a question that did not
exist. See below.

---

## What RMC's first reply changed

Their first answer of 2026-07-30 settled five of the seven original questions
and corrected two of our own decisions. **Read this together with "What the
second reply changed" below** — the second reply revises the power picture
here in one important respect.

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

## What the second reply changed

Their answer to the four questions, later on 2026-07-30. Verbatim text is at
the end of this document. Three answers settle things; one does not.

### Answer 4 — switch labelling. Settled.

> "In-phase is for picking (maximum vertical sensitivity) and out-of-phase is
> for bowing (maximum horizontal sensitivity)."

Chains cleanly with what was already known — the elements are out of phase on
the plate, so closing the CD4066 grounds the all-pass non-inverting input,
gives −1, and brings them electrically **into** phase:

| Toggle | Control line | CD4066 | All-pass | Elements | Mode |
| --- | --- | --- | --- | --- | --- |
| closed | Vdd via 20 kΩ | ON | −1 | in phase | **PIZZ** (picking) |
| open | Vss via 1 MΩ | OFF | +1 | out of phase | **ARCO** (bowing) |

Silkscreen J8 **closed = PIZZ**. Note the rest state — control pulled to Vss —
is **arco**, so that is what the instrument does with the toggle disconnected
or the loom broken. Worth stating in `NOTES.md`. No circuit change.

### Answer 3 — summing capacitor. Settled, looser than we proposed.

RMC accept 1.8 nF NPO **±5%**; we had proposed ±2%. Take **1.8 nF C0G/NP0 ±2%,
50 V, 1206** — tighter than asked, costs nothing at this value, and 1206 is the
size wanted for lane crossings anyway. C0G remains non-negotiable.

One thing their answer implies but does not say: the requirement is
*channel-to-channel* matching ("they should all be about the same value"), not
absolute accuracy against 1700 pF. A ±5% tolerance permits a 10% spread between
two channels, which is worse than the balance they are asking for. **Order all
six plus spares as a single line item**, so they come from one reel and date
code — parts from one reel track far tighter than the tolerance band. This is a
purchasing note for `fab/ORDER.md`, not a design change.

The abrasive-trimming technique is a hand-build method. It joins the "advice we
are deliberately not taking" list, but is worth keeping as a field-service note.

### Answer 2 — grounding. Confirms the model, and hardens it.

Confirms pins 7 & 8 are power and shell/shield is both audio and DC ground.
Then the operative sentence: **"the current flowing in the Ground terminal is
only related to the Audio signals."** With answer 1's *"make sure that the
current drain on the power rails is symmetrical"* and *"take into account any
and all DC-carrying networks referenced to Ground"*, that is a firm design rule:

> **No DC path from either rail to AGND anywhere on the board.**

The reason is structural. The PD2's "ground" is the midpoint of a transistor
rail splitter, and it reaches this board down the DIN shell — the same single
conductor carrying six string returns. Any DC imbalance flows in that conductor.

Audited against the target design, **the rule is already satisfied.** The audit
matters more than the conclusion, because it is what must not be broken later:

| Connection to AGND | DC it carries |
| --- | --- |
| J1–J6 pin 1, six saddle shields | audio return only |
| R02 3M3 ×6, piezo bias | op-amp bias current, ~20 pA |
| C01, C03 100p ×6; C701 10 n debounce | none — capacitive |
| CD4066 cell, grounded side ×6 | audio only, and only when ON |
| 4 × 4.7 µF rail bypass | leakage only |

Everything else runs rail-to-rail with no ground reference. The OPA4191s draw
V+ → V− through the die. The CD4066 has **no ground pin at all** — which is
what *"needs no Grounding… the logic Vss is connected to −4.5VDC"* means: pin 7
= Vss = −4.5 V, pin 14 = Vdd = +4.5 V, already correct in `design.py`. And the
control network runs Vdd → 20 kΩ → control → 1 MΩ → Vss, about 8.8 µA, with no
ground path.

What made this true is a deletion, not an addition: **the mid-rail buffer was
the one real ground-current source** (U7A driving AGND through R704 10 Ω), and
it goes with the power section.

So the constraint costs nothing today. What it forbids: no power LED, no
rail-to-ground divider, no single-ended pull-up, no asymmetric bypass. Write it
into `design.py` as a comment on the AGND net and re-check it at review.

*(Their "the switches are floating" is about the package having no ground pin,
not about the circuit. Grounding one side of each cell is still correct — it is
what grounds the all-pass input.)*

### Answer 1 — the rails. Two changes, one of them new scope.

**a) ±4.5 V, from a 9 V battery in the PD2.** This is the flag; see the next
section.

**b) Pins 7 & 8 currently feed preamp inputs, and must be disconnected.**

> "Once the DIN-8 pins 7 & 8 are disconnected from the preamp, you can do
> whatever you like with them."

**The first reply said this too** — *"DIN-8 Purple #7 and Grey #8 wires must be
disconnected from the preamp inputs in order to be carrying power"* — and this
document missed it, paraphrasing the power paragraph without that sentence and
planning as though the rails were simply present on the DIN. Worth naming as a
reading error rather than a new fact, because it is the same class of mistake
that produced the two previous redos: taking the convenient half of a paragraph.

They are not simply present. The PD2 is 8-channel-capable; on a 6-string
instrument pins 7 & 8 are **spare preamp inputs**, and freeing them means
opening the Poly-Drive II. That looked at the time like new scope on someone
else's hardware; the third reply removed it entirely.

It also means the polarity is **ours to define**, not the PD2's — RMC call
pin 7 = + and pin 8 = − "arbitrary… just my knee-jerk response". The board sets
the convention and the modification follows it.

---

## What the third reply settled

Round two asked one question: does this require the PD2 to be modified, and
could a battery instead sit on pins 7 & 8? The answer closed more than it was
asked (verbatim at the end of this document).

- **RMC perform the modification**, when they assemble our Poly-Drive II. It
  was never an aftermarket job on someone else's hardware, so reversibility,
  warranty and who-does-it all evaporate at once.
- **The PD2 supplies the rails.** *"Power management performed only in the
  Poly-Drive II preamp, keeping the instrument electronics slaved to the
  preamp."*
- **A local supply is discouraged**, for the second time. `supply-charge-pump`
  stays a fallback against a bad headroom answer, nothing more.
- **Current: 3.5 mA for the PD2, ~2 mA for us, under 6 mA total.** Their figure
  for our board matches the 1.7 mA computed here, which is a useful independent
  check on the part count.
- **~70 hours between charges** from a 1350 mAh USB-rechargeable 9 V.

Their derating is worth recording as sound rather than cautious, because it
looks arbitrary and is not: a 1350 mAh cell at 3.7 V is 5.0 Wh, and delivering
that at 9 V through a boost converter at 75–85% efficiency gives 420–470 mAh.
Their "1/3 of capacity" *is* the conversion loss, not a safety margin.

**Our own drain has stopped mattering.** 2 mA of an under-6 mA total, on a
battery recharged weekly. Earlier drafts treated it as a cost to justify; it is
not one.

## Open query: the proposed USB socket

RMC offer to fit a USB socket in the PD2 enclosure, so *"the preamp can be
phantom-powered if desired, keeping the battery fully charged."*

Charging is fine. **Running permanently from USB may not be**, and it is worth
resolving before they build the unit:

The battery's negative terminal **is the −4.5 V rail**, because the splitter's
midpoint is signal ground. So if the socket's ground is common with the battery
negative, and it is fed from an earthed source — a computer, a class-I supply —
while the PD2's output reaches earth through a mixer, the −4.5 V rail is tied
to earth through the audio ground. That is a short across the lower half of the
splitter.

This is the same fault `ENCLOSURE.md` identified when the pack was going to
live on our board, relocated into theirs. Occasional charging can always be
done unplugged, so it only bites in the permanently-powered case. **Asked, not
asserted** — they designed the unit and may already isolate the charging
circuit.

**Decision: no series reverse protection.** A Schottky per rail costs ~0.6 V of
a 9 V total supply, about 0.6 dB of headroom this design does not have. A
reversed loom puts 9 V backwards across every op-amp and destroys the board, so
the mitigation is procedural instead: pin 7 = +4.5 V and pin 8 = −4.5 V on the
silkscreen, in `NOTES.md`, in `ENCLOSURE.md`'s loom section and in
`fab/ORDER.md`, with a continuity check in the build procedure. A deliberate
trade, recorded as one.

**JP1 must still be deleted, not left unfitted** — and now doubly so: it would
short a −4.5 V rail to ground.

---

## The headroom answer — round four, 2026-08-01. Settled.

This was the last open question and the only one that could have changed the
circuit rather than the layout. **It is answered, and the answer is that no
change is needed.** The section that follows this one is the case as it stood
before the answer; it is kept because the reasoning in it is what the answer
had to address, and because the fallback it describes is still the fallback.

**There is no single peak figure, and that is why one was never given.** Output
is proportional to excitation, to string tension and to the sine of the break
angle, so it is instrument-specific. RMC answered the consequence instead:

- **Arco is not at risk.** A bowed attack is "a short noisy fade-in without any
  large initial percussive transient", and out of phase the two elements cancel
  vertical force variations at the summing node.
- **Pizz can clip, and that is acceptable.** In phase, vertical sensitivity is
  maximised and a picking transient may saturate the buffer. RMC's position is
  that this is inaudible **provided the electronics do not latch up**.
- **The concern recorded below was right about the mechanism and wrong about
  the severity.** If the white element clips, the two do stop summing at equal
  weight — but the red element bypasses the electronics entirely and dominates
  for those milliseconds, giving "an extremely short change in polar pattern,
  not an audible click or buzz".

### The load-bearing fact, confirmed from the datasheet

Everything above rests on the amplifier not latching up, so this was checked
rather than assumed. **OPA191/OPA2191/OPA4191 datasheet SBOS701D (December
2015, revised August 2021), §8.3.3 "Phase Reversal Protection":**

> "The OPAx191 family has internal phase-reversal protection... Input signals
> beyond the rails do not cause phase reversal; instead, the output limits into
> the appropriate rail."

Two numbers from the same datasheet complete the picture:

- **Absolute maximum on a signal input pin is only (V−) − 0.5 V to (V+) + 0.5 V,
  with an input current limit of ±10 mA.** So the protection is a clamp, and
  what keeps the clamp inside its rating is the series resistance in front of
  it. R01, the 1 kΩ stopper, is that resistance: even 5 V of overdrive past the
  rail draws 5 mA, half the limit. **R01 is therefore doing two jobs and must
  not be reduced** — it was placed as a stopper, and it is also what makes
  accepting clipping safe.
- **Absolute maximum supply is ±20 V (40 V single-supply)**, so RMC's "safe to
  ±15 V" is conservative rather than a limit. The `supply-charge-pump`
  fallback's ±9 V sits a long way inside it.

### What would falsify this

Recorded because "settled" here means "settled on RMC's judgement plus one
datasheet paragraph", not "measured on this instrument":

- **Audible artefacts on hard pizzicato** — a click, a buzz, or a change in
  timbre that comes and goes with playing strength rather than smoothly with
  it. That is the failure this reasoning predicts will not happen.
- **Anything worse than a momentary change in polar pattern**, which is what
  RMC predict the clipping will sound like.

**If it is falsified, the fix needs no layout change.** RMC gave a mitigation
that is component values only, applicable after assembly without a respin: a
capacitor in parallel with R02 (3M3) divides against the element's own 1700 pF
and attenuates the white signal into the buffer, and increasing C04 loads the
red element correspondingly to restore the balance. The `supply-charge-pump`
branch remains the second fallback, and RMC have now discouraged it twice.

**Consequence for the board: none.** No netlist change, no layout change.

## The case before the answer — how it stood, and what the fallback is

*Kept as the reasoning the answer had to address. The conclusion of this
section — that the number decides the concept — is superseded by the section
above; the fallback comparison at the end of it is still current.*

### The rails are ±4.5 V

> "CD4066 will work just fine on the available power provided in the PD2 by a
> 9V battery going through a pair of transistors to create ±4.5VDC."

That answer addresses the **CD4066's supply range** (3–18 V — never in doubt).
It does not address **op-amp signal headroom**, which is the question this
project has now been round twice.

| Supply | Rails | OPA4191 swing | vs RMC's own drawing |
| --- | --- | --- | --- |
| RMC's 12 V drawing | ±6 V | ~±5.85 V | — |
| **PD2, 9 V regulated** | **±4.5 V** | **~±4.35 V** | **−2.6 dB** |

One row, because RMC recommend a regulated USB-rechargeable pack: the rails
hold ±4.5 V for the whole ~70-hour cycle rather than sagging. Earlier drafts of
this document carried end-of-life rows for an alkaline; they no longer apply.

The one consequence of regulation worth writing into `NOTES.md`: **there is no
low-battery warning.** A regulated pack holds 9 V and then falls off a cliff,
so a preamp watching battery voltage cannot warn. RMC's answer to that is a
habit rather than a circuit — *"just charge the thing once a week"* — and at
~70 hours a weekly habit covers a weekly runtime comfortably. It is worth
stating for whoever plays the instrument, not designing around.

### Why the number decides the concept

There is no gain on the board — the buffer is unity, the all-pass is ±1 — so
the requirement is simply **the white element's own open-circuit peak into the
3M3**.

What happens when it is exceeded is worse than ordinary clipping. At the
summing node,

```
OUT = (V_red · C_red + V_white · C04) / (C_red + C04 + C_stray)
```

with C_red ≈ 1700 pF and C04 = 1800 pF, so the two elements contribute at
roughly equal weight — exactly the string balance RMC asked for. But **the red
element never passes through an op-amp** and the white one does. So on a hard
pizzicato the white contribution clips while the red does not: the mix shifts
with playing level, differently on each string. That attacks the balance the
capacitor matching exists to protect.

### Nothing on the board fixes it — but the lever is a branch we already built

Within RMC's proposal there is no adjustment available. Attenuating the white
channel breaks the equal-weight summing that matching C04 to 1700 pF exists to
achieve; a charge pump fed from the DIN rails would double the drain on *the
PD2's* battery and put a switcher's noise into their own rails next to a 3M3
piezo node; and a separate onboard battery is what they are steering away from
("drawing power from the preamp rails eliminates power management circuitry").

**But `supply-charge-pump` is exactly that alternative, and it is finished.**
`ENCLOSURE.md` on that branch reads *"Fishman Universal Rechargeable Battery
Pack, decided already"* — 38.1 × 44.3 × 10.9 mm, 45 g, 9 V regulated Li-ion,
micro-USB, *"at the board's 2.1 mA this runs for weeks."* The ±9 V board was
designed around that pack.

**It is a fallback, and RMC have now discouraged it twice** — most recently
*"power management performed only in the Poly-Drive II preamp."* Reach for it
only if the elements turn out to exceed ~4 V peak, and expect to have to argue
for it.

| | **A — RMC's proposal** | **B — `supply-charge-pump`** |
| --- | --- | --- |
| Supply | ±4.5 V from PD2 over DIN 7/8 | Fishman pack + charge pump, ±9 V |
| Swing | ~±4.35 V | ~±8.85 V (**+6.2 dB**, beyond RMC's own 12 V) |
| PD2 modification | **RMC do it at assembly** | none — pins 7/8 untouched |
| Drain on PD2 battery | ~2 mA of under 6 mA | none |
| Board | **78.8 × 81.3 mm measured** | 56 × 94 mm measured |
| Battery to charge | one, in the PD2 | one, in the instrument, plus hatch |
| RMC's view | recommended | discouraged twice |
| Status | **built, verified, DRC clean** | built, verified, DRC nearly clean |

Path B's grounding is the part worth checking rather than assuming, and it is
clean: the pump makes AGND the pack's negative terminal, so bonding AGND to the
DIN shell puts pack-negative, USB ground and PD2 ground all on one node. That
is why `ENCLOSURE.md` says the charging hazard disappears under the charge pump
but not under the mid-rail.

Two earlier arguments for B are now dead and are recorded as such so they are
not re-run: the modification is no longer a burden on anyone (RMC do it), and
the headroom no longer depends on an unspecified battery in a box we do not own
(RMC specify the pack and assemble the unit).

So the element-peak answer does not change what gets built *within* A. It
decides whether A holds at all — and the bar for leaving it has risen, because
A is now RMC's considered recommendation rather than a convenience.

### Asked once, unanswered in three replies — then answered in the fourth

It was **question 1 of the seven** sent in round one (`RMC-QUESTIONS.md` on
`supply-charge-pump`), in the subject line, phrased as a threshold rather than
an open request: *"Do the elements ever exceed about 4 V peak on a hard
pizzicato?"* None of the three replies addresses it. It then dropped out of the
four-question set, which asked about rail *voltage and current* but not element
peak output, and was deliberately held out of round two so as not to presuppose
the supply answer.

**It is now released, on its own, in round three** — and says outright that it
is a repeat. There is nothing else left to ask it behind.

---

## The agreed target design

### Per channel (×6) — 10 passives, down from 13

R01 1k · R02 3M3 · C01 100p · R03 1k · R04/R05/R06 47k **±1%** ·
C02/C03 100p · **C04 1n8 C0G/NP0 ±2% 50 V, all six from one reel**

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

**~79 placements against 120.** Draw falls to ~1.7 mA (12 halves × 140 µA),
drawn symmetrically from ±4.5 V with nothing in the ground return but audio.

### Supply, connectors and labelling

- **Supply: ±4.5 V from the Poly-Drive II**, down DIN-8 **pin 7 = +4.5 V,
  pin 8 = −4.5 V**, shell/shield = ground. Regulated, from a 1350 mAh
  USB-rechargeable 9 V in the PD2; RMC wire pins 7 & 8 to the rails at
  assembly. No power section, no battery of our own, no protection diodes —
  see the reverse-protection decision above.
- **Draw: ~2 mA**, of an under-6 mA total shared with the PD2's own 3.5 mA.
- **`JP1` is deleted**, not left unfitted.
- **J8 toggle: closed = PIZZ, open = ARCO.** Rest state is arco.
- **AGND carries no DC.** Standing rule; audit table above.

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

### Size after the redesign — MEASURED, 2026-08-01

**78.8 × 81.3 mm = 6406 mm², from a board that is placed, routed and
DRC-clean.** This replaces a projection of ~60 × 70 ≈ 4200 mm² that stood here.

| | Area | vs original |
| --- | --- | --- |
| Original (`main`) | 88 × 112 = 9856 mm² | — |
| Abandoned `supply-charge-pump` | 56 × 94 = 5264 mm² | 1.87× |
| **This board** | **78.8 × 81.3 = 6406 mm²** | **1.54×** |

**The projection missed, and it missed the way the last one did.** 4200 against
6406 is 34% low, and the error is the same both previous times: counting parts
rather than counting lanes. What actually set the two dimensions:

- **Height came out near the prediction** — ~70 projected against 81.3. Most of
  the excess is the fan-in above the tail connector: six OUT lanes have to
  reach a header whose pins run the same way round as the channels, and that
  needs six approach rows plus clearance to the last sub-row.
- **Width was badly under** — ~60 projected against 78.8. Twelve corridor lanes
  was the right count. What was missed is that OUT and SWN pull in opposite
  directions and end up occupying **different layers over the whole height of
  the board**, which leaves V−, SW_CTL and SW_TOG no route through the corridor
  at all. They need a column of their own east of the switches, and that column
  plus the bypass caps beyond it is most of the width the projection lacked.

**Two dimensions were spent deliberately, on routability rather than on parts.**
The right-hand column sits 2 mm further out than the parts need and the tail
connector 0.5 mm lower, both because a measured crossing demanded it. That is
the rule this project keeps relearning: **a number from an unroutable placement
is not a smaller board, it is a board that does not exist.**

**Land utilisation is about 14%**, against 17% on the original and ~20% on the
abandoned branch. This board is *less* dense than either, which is the clearest
statement of what constrains it: not area for parts, but room for lanes. The
eight connectors remain the largest single consumer of land.

#### Figures quoted during the work that were wrong

Recorded because the same mistake was made twice in one session:

- **91 × 75** — measured before the courtyard overlaps were found, so not a
  legal placement at all.
- **5302 mm² (74 × 71)** — a legal placement with 0.7 mm of lane clearance.
  Legal but not routable: making room for the routing took it to 5971, the 3 mm
  border took it to 6044, and actually routing it took it to 6406.

---

## Questions sent to RMC — round one of 2026-07-30. All four answered.

1. **Rail voltage, polarity and current on pins 7 and 8.** → ±4.5 V, polarity
   ours to choose, from a 9 V battery in the PD2 via a transistor rail
   splitter. **Partially answered:** the headroom consequence was not addressed,
   and the pins turn out to need a modification inside the PD2 first.
2. **Ground return.** → Confirmed, and hardened into the symmetry rule.
3. **Summing capacitor tolerance.** → ±5% accepted; we are taking ±2%.
4. **Switch labelling.** → Closed = in phase = pizz.

The concern recorded here before they replied was right, and is worth keeping
for the next person: *"If the Poly-Drive supplies ±4.5 V, that is the headroom
position this whole exercise was trying to escape — and with no battery there
is no longer any lever to pull."* That is exactly what happened.

## Questions sent to RMC — round two, answered

One question: does freeing pins 7 & 8 require the Poly-Drive II to be modified,
and could a battery pack instead be connected to those pins? **Answered in
full** — RMC do the modification at assembly, the PD2 supplies the rails, power
management stays there.

Asking one question rather than five worked, and the reason is worth keeping:
the four held questions were each downstream of it, and three dissolved on the
answer without ever being sent.

## Questions sent to RMC — round three, answered

Full text in **`RMC-QUESTIONS-2.md`**. Three items, one of them the blocker:

1. **The proposed USB socket.** Time-critical rather than important — they were
   about to build the unit, and fitting it was a decision being made then. See
   "Open query" above; the hazard identified there stands, and only bites in
   the permanently-powered case.
2. **The element peak output.** The blocker. **Answered** — see "The headroom
   answer" above. No circuit or layout change.
3. **Polarity**, stated rather than asked: we print pin 7 = +4.5 V and build
   the loom to match; they say if they would rather it were reversed. No
   objection raised, so that is the convention, and it is now on the
   silkscreen, in `NOTES.md`, in `ENCLOSURE.md` and in `fab/ORDER.md`.

**Nothing is outstanding with RMC.** The next thing they need from us is the
design itself, for review.

## RMC advice we are deliberately not taking

Four of their suggestions assume a self-built board:

- **"A multi-layer ceramic capacitor can be trimmed… by abrading it."** A
  hand-selection method by another route, and no more compatible with a turnkey
  line than the first. Keep it as a field-service note — it is genuinely useful
  if one of these ever needs adjusting after the fact — but the board is
  specified so it never has to be used.

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

The circuit-specific functions only. This is the *rationale*; the order of
operations is under "Next steps" at the end.

- **`design.py`** — keep `Part`, `Design`, `_resistor`, `_capacitor`,
  `patch_symbol`, `build_footprint`. Rewrite `channel()`, `switch_bank()`,
  `output()`; `power()` deletes entirely. The constants block survives as a
  structure but not as values — footprints, `LIBS` and the supply strings all
  change.
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

## RMC's first reply, 2026-07-30 — verbatim

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

## RMC's second reply, 2026-07-30 — verbatim

Answering the four questions above. Numbering is theirs.

> Once the DIN-8 pins 7 & 8 are disconnected from the preamp, you can do
> whatever you like with them. Arbitrarily, pin 7 can be +4.5VDC and pin 8 can
> be -4.5VDC, but that's just my knee-jerk response.
>
> CD4066 will work just fine on the available power provided in the PD2 by a 9V
> battery going through a pair of transistors to create ±4.5VDC.
>
> Ultimately, the power rails need to remain symmetrical : +4.5VDc and -4.5VDC
> from 9V battery voltage, so make sure that the current drain on the power
> rails is symmetrical in the new board.
>
> Take into account any and all DC-carrying networks referenced to Ground. Note
> that the CD4066 needs no Grounding since the switches are floating and the
> logic Vss is connected to -4.5VDC.
>
> 2) Correct. Pins 7 & 8 are for power and shell/shield is both Audio & DC
> Ground. That being said, the current flowing in the Ground terminal is only
> related to the Audio signals.
>
> 3) Yes a 1.8nF NPO cap with ±5% tolerance should work pretty well. Murata is a
> good manufacturer and both Digi-Key & Mouser stock them.
>
> *** Please note that a multi-layer ceramic capacitor can be trimmed to a
> lesser capacitance value by abrading it with a rubber abrasive such as the
> small Cratex-type tips jewelers use for polishing metal. Capacitor
> construction includes capacitive layers sandwiched between top & bottom
> Insulating layers and capped with metal terminals. Abrade the region between
> the terminals. Just so you know.....
>
> 4) In-phase is for picking (maximum vertical sensitivity) and out-of-phase is
> for bowing (maximum horizontal sensitivity).

---

## RMC's third reply, 2026-07-31 — verbatim

Answering round two's single question. It settled considerably more than was
asked.

> Yes, disconnecting wires 7 & 8 from the input pads, and connecting them to
> the power rails will be performed when I assemble your Poly-Drive II preamp.
>
> I recommend having power management performed only in the Poly-Drive II
> preamp and keeping the instrument electronics slaved to the preamp.
>
> High-capacity 9V batteries with a USB charging socket are ubiquitous these
> days, so just charge the ting once a week and keep things simple & reliable.
> Based on a current drain of about 3.5 mA for the Poly-Drive II and about 2 mA
> for the new board (under 6 mA total), a 1350mA/H battery can provide at least
> 70 hours of play (420mA/Hr equivalent to 1/3 of the battery's capacity)
> before needing a recharge. At 10 hours a day, that's a bout a week of
> operation or 2 weeks at 5 hours a day. Charging usually takes less than an
> hour.
>
> [link to a 1350 mAh USB-rechargeable 9 V battery]
>
> It is possible to have a USB socket installed in the Poly-Drive II enclosure
> to avoid having to remove the lid to access the battery. This way the preamp
> can be phantom-powered if desired, keeping the battery fully charged.

---

## What is done, and what is left

Everything the rework called for is done. This section replaces the ordered
plan that used to stand here; the plan itself, with the reasoning for each
step, is in `.claude/plans/read-electronics-state-md-before-doing-stateful-bonbon.md`.

### Done

| | |
| --- | --- |
| **The gate** | RMC answered the element peak output on 2026-08-01. See "The headroom answer". |
| **`design.py`** | `power()` deleted outright; `channel_pair()` around one OPA4191 per two channels; `switch_bank()` for two CD4066B on RMC's control network; `output()` with DIN 7/8 as the rails and JP1 gone; `bypass()` added. `NO_CONNECT` is empty, as it should be. |
| **`gen_project.py`** | `symbol_library()` driven off `circuit.LIBS`, so a borrowed part can no longer be added to the design and left out of the written library. `VIN`/`VFUSED` dropped from the netclass patterns. |
| **`gen_sch.py`** | Two-channel blocks, switch and output sections rewritten, `power_section()` deleted, the backwards sheet note about a floating supply replaced. |
| **`gen_pcb.py`** | Placed, routed and DRC-clean at 78.8 × 81.3 mm. Routing entirely by hand in code; no autorouter. |
| **The documents** | `STATE.md` (this file), `NOTES.md`, `ENCLOSURE.md` and `fab/ORDER.md` all brought up to the built board. |

### Left

**Nothing is blocking.** Three checks the build cannot perform, and one
external step:

1. **Open the project in KiCad once** and confirm no symbol shows a broken
   library link. This is the only check that catches the `symbol_library()`
   class of bug, because the schematic embeds its own copy of every symbol and
   both ERC and `verify.py` pass regardless.
2. **Re-audit AGND by hand** against the table under "Answer 2 — grounding".
   The only things on it should be six saddle shields, six 3M3 bias resistors,
   the RF and all-pass capacitors, the grounded side of each 4066 cell, C701
   and the four bypass caps. Total DC into AGND should be leakage only.
3. **Read the layout PDF** — `fab/rmc-pizz-arco-layout.pdf`, which plots the
   four copper layers with reference designators. It is the artefact a reviewer
   can actually comment on.
4. **Send the design to RMC for review.** They designed the circuit and asked
   to see it. That is the next thing that should happen.

### Then, after review

Order from `fab/rmc-pizz-arco-pcbway.zip`, following `fab/ORDER.md` — which
carries the four requirements that are invisible in the gerbers and the BOM
(matched capacitors from one reel, C0G, ±1% inverter resistors, OPA4191 by
part number) and the polarity convention that destroys the board if a loom is
built backwards.
