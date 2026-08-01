# External enclosure — board and battery at the tail

The board and pack live in a housing on the outside of the instrument, at the
tail, screened from view by the tailpiece. This supersedes the onboard
installation assumed throughout [`NOTES.md`](NOTES.md), and it is a different
proposal from the outboard pedal that `NOTES.md` considered and rejected.

## Why this is not the pedal that was rejected

[`NOTES.md`](NOTES.md) turns down an outboard enclosure on three grounds. Two
of them are properties of the *cable*, not of being outboard, and they do not
survive a 60 mm run:

| Objection | At a pedal | At the tail |
| --- | --- | --- |
| Conductor count | 12 raw elements + ground, needs a 13-pin GK connector | 18-wire loom stays on the instrument; the box still emits 6 + ground into a DIN-8 |
| Relocating the high-impedance node | metres of multicore dividing against the element, crosstalk across twelve high-Z lines | a few pF against 3M3; the lanes stay separated |
| Supply isolation | daisy-chain supplies share a sleeve tied to audio ground | **unchanged — still applies.** See "Charging" below |

The third objection stands and gets worse in one specific way that is new
here.

## What the instrument stops needing

This is the real gain, and it is larger than the convenience:

- **No DIN-8 socket cavity.** J7 becomes a panel socket on the box. RMC's
  cable plugs into the box, not the instrument.
- **No battery compartment and no hatch.** The pack is in the box.
- **No power switch let into the ribs.** Removing the pack breaks the circuit
  — see "Charging".

Against that, the instrument still needs a route for the loom from the bridge.
See "The loom", which is the least resolved part of this.

## The board must be respun

The board is 88 × 112 mm ([`gen_pcb.py`](gen_pcb.py) line 586). The tailpiece
is 100 mm. There is no housing to design until this changes.

**Target envelope: 55 × 95 mm**, long axis running from bridge to tail.

### Why that is achievable

The present board is spacious rather than dense — it was laid out for
hand-soldering, not for area. Estimating part footprints with routing
overhead at 2×:

| Block | 0805 | 0402 |
| --- | --- | --- |
| Six channels | ~2150 mm² | ~1200 mm² |
| Switch bank, DIN, toggle | ~1000 mm² | ~700 mm² |
| Power section | ~700 mm² | ~500 mm² |
| **Total** | **~3850 mm²** | **~2400 mm²** |

Against 55 × 95 = 5225 mm² that is 74% utilisation at 0805 and 46% at 0402.
**Try it at 0805 first** — hand-solderability is worth keeping, and the
numbers say it probably survives. 0402 is the reserve, not the plan.

### The layout this wants

Not six stacked tiles. Six tiles at 14 mm pitch is 84 mm of *width*, which
does not fit. Instead: **six parallel lanes, ~9 mm wide, running away from the
bridge**, one per string, with the switch bank, DIN and power in a transverse
block across the tail end. Six lanes is 54 mm. Each lane is then ~65 mm long
against ~360 mm² of parts, which is comfortable.

That layout is better for the circuit as well as for the box — it is the
maximum channel separation available, and the high-Z runs are as short as they
can be made.

### Constraints the respin must honour

- **J1–J6 on the nose edge** (the bridge end). Six 1x03 headers at 7.6 mm each
  is 45.6 mm across a 55 mm edge — it fits, but only just, so this drives the
  edge assignment rather than falling out of it.
- **J7 and J9 on the tail edge.** Cable and pack both belong at the mounted
  end, away from the bow and the player.
- **Tall parts at the tail.** C701 (`CP_Elec_6.3x5.4`) and anything else over
  ~4 mm must sit in the deep end of the wedge — see "Form".
- **Revisit the A/B cell restriction.** [`NOTES.md`](NOTES.md) uses only the A
  and B cells of each CD4066B because channels arrive from the left and the
  control line comes down the right. A transverse switch block changes that
  geometry, and the reasoning has to be redone rather than carried over.

## Power

**Fishman Universal Rechargeable Battery Pack**, decided already:

| | |
| --- | --- |
| Dimensions | 38.1 × 44.3 × 10.9 mm |
| Mass | 45 g |
| Output | 9 V regulated, Li-ion |
| Charging | micro-USB, ≤3 h from empty |

At the board's 2.1 mA this runs for weeks. The regulated output is what
[`NOTES.md`](NOTES.md) asks for — it holds 9 V rather than sagging like NiMH —
so the pack itself is settled. **Measure it loaded anyway**; that instruction
has not changed.

### Charging — a new hazard, same fault as before

> **Do not charge the pack with the DIN cable connected.**

The pack is almost certainly a non-isolated boost converter, so its USB ground
is common with its 9 V negative — which is `V-` on the board. Meanwhile `AGND`
is the mid-rail, anchored near earth through DIN pin 7 and the Poly-Drive.
Plug in a charger whose USB ground reaches earth (an earthed computer, a
class-I supply) and `V-` is pulled to earth too. That shorts `AGND` to `V-`
across R704, demanding ~450 mA from U7A.

It is exactly the fault [`NOTES.md`](NOTES.md) describes under "Grounding",
arriving by a route that did not exist when the pack was inside the
instrument.

**The design answer is a removable pack**, not a warning label: a hatch, a
standard 9 V snap, charge it off the instrument. That also solves the
ten-day standby drain that `NOTES.md` leaves open, because removing the pack
*is* the power switch. One decision, three problems.

A DPDT switch breaking both leads would allow in-situ charging, but it is a
part that can be left in the wrong position, and it does not solve standby
drain as cleanly. Fit the hatch; add the switch only if the friction proves
real.

### On the inline 9 → 12 V converter

Noted as the fallback if the headroom measurement demands 12 V. Two things to
weigh before fitting one:

[`NOTES.md`](NOTES.md) rules this out directly — "a switching converter beside
a 3M3-loaded piezo front end puts noise in the worst possible place to buy
2.5 dB." That reasoning has not changed, and an inline module at the tail is
if anything closer to the front end than a wallwart would have been.

More usefully: **if a converter is going in anyway, the ±9 V charge pump is
the better one.** Same class of part, same board area, and it is already
written up as option 4 in `NOTES.md`:

| | Headroom | Grounding |
| --- | --- | --- |
| 9 V as-is | reference | mid-rail; charging hazard above applies |
| Inline boost to 12 V | +2.5 dB | mid-rail; hazard unchanged |
| ±9 V charge pump | **+6.1 dB** | **audio ground becomes battery negative — hazard disappears** |

The charge pump makes `AGND` the pack's negative terminal, so tying it to
earth through a charger does nothing at all. It removes the grounding warning
from `NOTES.md`, removes the charging hazard above, and yields 2.4× the swing
instead of 1.3×.

It is a board change — but **the board is being respun anyway**, which is the
only reason this is worth raising now rather than filing as a someday item.
Decide it before the respin, not after.

## Mass, and where it is carried

Estimated: board ~20 g after the respin, shell ~25 g, pack 45 g, wiring and
fixings ~10 g. **Call it 100 g.**

A bass viol tailpiece in ebony is 30–40 g. Clamping 100 g to it triples the
mass of a freely-suspended component whose mass and afterlength are part of
how the instrument responds. That is a real acoustic intervention with an
unpredictable direction, and it is the reason the box does **not** hang on the
tailpiece.

**It mounts to the tail block and cantilevers forward under the tailpiece.**
Visually identical; the tailpiece screens it and stays free to move. The tail
block is the most mechanically inert point on the instrument, so mass there is
close to free. A 100 g load on an ~80 mm cantilever is structurally trivial.

## Form

A **wedge, deepest at the tail**, following the space that is actually
available:

- **Tail section** — hangs below and behind the saddle, past the bottom edge
  of the instrument, where belly clearance stops applying. Carries the DIN-8
  socket on its rear face, the battery hatch, the pack, and the tall parts.
  This is also the mounting point, so the mass sits over the fixing.
- **Forward nose** — thin, runs under the tailpiece over the belly, never
  touching it. Carries the six channel lanes and the J1–J6 headers at its
  leading edge.

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

- Concept agreed: external, tail-block mounted, Fishman pack.
- Board respin to 55 × 95: **agreed, not started.**
- ±9 V charge pump vs 9 V as-is vs inline boost: **open, decide before the
  respin.**
- Instrument measurements: **outstanding.** Blocks the model.
- Loom routing: **open**, pending a view on drilling the belly.
