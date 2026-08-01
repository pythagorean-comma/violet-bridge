# External enclosure — the board at the tail

The board lives in a housing on the outside of the instrument, at the tail,
screened from view by the tailpiece. This supersedes the onboard installation
assumed throughout [`NOTES.md`](NOTES.md), and it is a different proposal from
the outboard pedal that `NOTES.md` considered and rejected.

> **Updated 2026-08-01.** This document was written when the board carried its
> own battery. **It no longer does** — the Poly-Drive II supplies ±4.5 V down
> DIN pins 7 and 8 and there is no pack, no power section and no charging
> circuit anywhere on this instrument. Everything about the battery bay, the
> hatch and the charging hazard has been cut; the mounting analysis and the
> loom problem, which is still the least resolved part of this, stand
> unchanged. The board itself is finished and measures **78.8 × 81.3 mm**.

## Why this is not the pedal that was rejected

[`NOTES.md`](NOTES.md) turns down an outboard enclosure on three grounds. Two
of them are properties of the *cable*, not of being outboard, and they do not
survive a 60 mm run:

| Objection | At a pedal | At the tail |
| --- | --- | --- |
| Conductor count | 12 raw elements + ground, needs a 13-pin GK connector | 18-wire loom stays on the instrument; the box still emits 6 + ground into a DIN-8 |
| Relocating the high-impedance node | metres of multicore dividing against the element, crosstalk across twelve high-Z lines | a few pF against 3M3; the lanes stay separated |
| Supply isolation | daisy-chain supplies share a sleeve tied to audio ground | **gone.** The board has no supply to isolate — it takes ±4.5 V from the Poly-Drive II down the same DIN-8 |

**All three objections are now answered**, the third by the supply change
rather than by the mounting position. When this document was written the third
one still applied and got worse at the tail, because the pack was going to live
in the box and be charged there; with the pack gone, so is the fault.

## What the instrument stops needing

This is the real gain, and it is larger than the convenience:

- **No DIN-8 socket cavity.** J7 becomes a panel socket on the box. RMC's
  cable plugs into the box, not the instrument.
- **No battery compartment and no hatch.** There is no battery. It lives in
  the Poly-Drive II, which is where RMC want all the power management, and it
  is charged over USB there.
- **No power switch let into the ribs.** Nothing on this instrument draws
  power unless the Poly-Drive II is on.

Against that, the instrument still needs a route for the loom from the bridge.
See "The loom", which is the least resolved part of this.

## The board, as built

**78.8 × 81.3 mm, and finished.** The respin this document called for has
happened — for reasons that had nothing to do with the enclosure — and the
board is placed, routed and DRC-clean. See `STATE.md`.

**The 55 × 95 mm target recorded here no longer governs, and was not reachable
anyway.** It was estimated by adding up part footprints and doubling for
routing, which is exactly the method that has now missed three times on this
project. What actually sets the size is lane counting: a two-channel block is
a 9.25 mm quad plus a row and a sub-row on each side, and the twelve corridor
lanes leaving those blocks end up occupying two different layers over the full
height of the board. The finished board is 14% land — *less* dense than either
earlier revision — because room for lanes, not area for parts, is the binding
constraint.

**So the enclosure has to be designed around 78.8 × 81.3, not the other way
round.** That is 23.8 mm wider and 13.7 mm shorter than the target above. The
tailpiece is 100 mm, so length is comfortable; **width is now the problem this
document has to solve**, and the six parallel lanes running away from the
bridge that were sketched here are not what got built.

Two things the built board does give the enclosure:

- **J1–J6 are all on one edge**, in three blocks of two, so the loom still
  arrives at a single face.
- **J7 and J8 are together on the opposite edge**, laid flat. Cable and toggle
  both come out at the mounted end, away from the bow and the player.

**Nothing on the board is tall.** The only through-hole parts are 2.54 mm pin
headers; the electrolytics that used to drive the wedge's deep end went with
the power section. Whatever the shell becomes, component height is no longer a
constraint on it.

## Power — nothing to house

**There is no battery and no power section.** ±4.5 V arrives from the
Poly-Drive II on DIN pins 7 and 8, with the shell as ground, and RMC wire
those pins to their rails when they assemble our unit. The box carries the
board and a panel socket, and that is all.

This deletes four things this document previously had to solve: the pack, the
bay, the hatch, and the in-situ charging hazard.

> **The one thing to carry forward: polarity.** J7 pin 7 is **+4.5 V** and pin
> 8 is **−4.5 V**. There is deliberately no reverse-protection diode — a series
> Schottky per rail would cost about 0.6 dB of headroom out of a 9 V total
> supply — so a loom built backwards destroys the board. **Continuity-check
> from the DIN plug to J7 before first power-up.**

### The charging hazard did not vanish, it moved

Worth recording, because the analysis was right and it still applies — just to
someone else's enclosure.

RMC have offered to fit a **USB socket in the Poly-Drive II**, so the preamp
can be phantom-powered and the battery kept topped up. The battery's negative
terminal *is* the −4.5 V rail, because the splitter's midpoint is signal
ground. If that socket's ground is common with battery negative, and it is fed
from an earthed source while the PD2's output reaches earth through a mixer,
the −4.5 V rail is tied to earth through the audio ground — a short across the
lower half of the splitter.

This is exactly the fault this document identified when the pack was going to
live in our box, relocated into theirs. It only bites in the permanently
powered case; occasional charging can always be done unplugged. Raised with
RMC; it affects their enclosure, not this one.

### The former fallback, and why it is no longer needed here

This document used to carry the working for a Fishman Universal Rechargeable
Battery Pack and an inline 9 → 12 V converter, kept against the possibility
that ±4.5 V would not give enough headroom.

**That question was answered on 2026-08-01 and the answer needs no supply
change** — arco cannot clip, pizz can and is inaudible when it does, and the
OPA4191's datasheet confirms the amplifier does not latch up on overdrive. See
"The headroom answer" in `STATE.md`, which also records what would falsify it.

The fallback still exists but has nothing to do with this enclosure: it is the
`supply-charge-pump` branch, complete and internally consistent, with the
Fishman pack specification and the charge-pump-versus-boost comparison in its
own copy of this file. RMC have discouraged a local supply twice. If it is ever
revived, the enclosure gains a pack, a bay and a hatch, and the charging
analysis above comes back to this document from theirs.

## Mass, and where it is carried

Estimated: board ~25 g as built (78.8 × 81.3 × 1.6 mm of 4-layer FR4 is about
19 g of laminate, plus copper and 80 small parts), shell ~25 g, wiring and
fixings ~10 g. **Call it 60 g** — the 45 g pack that used to dominate this
budget is gone.

**The conclusion does not change, and it is worth keeping the reasoning.** A
bass viol tailpiece in ebony is 30–40 g. Even 60 g clamped to it would roughly
double the mass of a freely-suspended component whose mass and afterlength are
part of how the instrument responds — a real acoustic intervention with an
unpredictable direction. So the box still does **not** hang on the tailpiece.

**It mounts to the tail block and cantilevers forward under the tailpiece.**
Visually identical; the tailpiece screens it and stays free to move. The tail
block is the most mechanically inert point on the instrument, so mass there is
close to free. A 60 g load on an ~80 mm cantilever is structurally trivial.

## Form

A **wedge, deepest at the tail**, following the space that is actually
available:

- **Tail section** — hangs below and behind the saddle, past the bottom edge
  of the instrument, where belly clearance stops applying. Carries the DIN-8
  socket and the pizz/arco toggle on its rear face, which is the edge those
  two connectors are on. This is also the mounting point, so the mass sits
  over the fixing.
- **Forward nose** — thin, runs under the tailpiece over the belly, never
  touching it. Carries the three channel blocks and the J1–J6 headers at its
  leading edge.

**The wedge may not survive the board's width.** It was drawn around a 55 mm
board and the built one is 78.8 mm. Whether that fits under the tailpiece at
all is one of the measurements below, and it is now the first of them.

The board lies flat and parallel to the belly through both sections; only the
lid follows the taper. Cork or suede lining anywhere the shell approaches
varnish. Nothing fastens into the tailpiece, and nothing rests on the belly.

The model will be parametric CadQuery at the repository root, in the style of
`bridge.py` — lofted between profiles rather than assembled from booleans.

## The loom

Eighteen wires from the bridge feet to the nose of the box. This is the
weakest part of the proposal and it is not yet solved.

Running them along the belly is out: they buzz, they damp the top, and they
look wrong on a good instrument.

**Preferred: send them inside.** One small hole beside a bridge foot — which
the onboard installation needed regardless — through the body to a feedthrough
at the tail block, where the box already is. Nothing visible between bridge
and box. Net cutting is *less* than the onboard plan required, since the
socket cavity and battery compartment are gone.

Whether any hole is acceptable is the owner's and the luthier's call, not a
question this document can close.

## What has to be measured

The box cannot be modelled without these. All from the instrument itself:

1. **Tailpiece width** at the bridge end and at the saddle end.
2. **Tailpiece underside height above the belly**, at both ends — this sets
   the wedge angle and the nose thickness.
3. **Tailpiece length confirmed at 100 mm**, and its distance from the bridge.
4. **Endpin: present or not?** If present, its diameter and projection — an
   endpin mount is the cleanest fixing. If absent, the box has to grip the
   saddle or the lower ribs instead, which is a different bracket and a more
   delicate one.
5. **Saddle height and width**, and the bottom rib depth at the tail.
6. **Clearance to the player.** Held between the calves, the tail points down
   toward the floor. How much can protrude below the bottom edge before it
   fouls? This caps the tail section's depth and no drawing will answer it.

## Status

*Updated 2026-08-01.*

- Concept agreed: external, tail-block mounted. **No battery, no hatch.**
- Board: **finished at 78.8 × 81.3 mm and DRC-clean.** The respin this document
  asked for happened; the 55 × 95 target it set did not survive and was not
  reachable. The enclosure now has to be designed around the board.
- Supply: **settled.** ±4.5 V from the Poly-Drive II. The charge-pump and
  inline-boost alternatives are closed — see "The former fallback".
- **Width is the new open question.** 78.8 mm under a 100 mm tailpiece, against
  a design drawn for 55 mm.
- Instrument measurements: **outstanding.** Still blocks the model.
- Loom routing: **open**, pending a view on drilling the belly. Unchanged, and
  still the least resolved part of this.
