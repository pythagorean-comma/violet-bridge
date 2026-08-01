# RMC pizz/arco 6-channel board — fabrication order

Upload `rmc-pizz-arco-pcbway.zip`. It contains only the layers a fab needs.

Figures below are measured from the board `gen_pcb.py` produces, not estimated.
Regenerate with `./build.sh`, which refuses to write the zip while DRC has any
error outstanding — so a board with known faults cannot reach a fab by accident.

## Settings that are NOT in the gerbers — you must enter these

| Setting | Value |
| --- | --- |
| **Layers** | **4** — the default on most order forms is 2. In1 is a ground plane, In2 is the V+ plane; a 2-layer build would silently drop both. |
| Board size | 78.8 × 81.3 mm, single up |
| Thickness | 1.6 mm |
| Copper weight | 1 oz outer, 0.5 oz inner (standard) |
| Surface finish | ENIG preferred — flat pads suit the 1.27 mm-pitch SOIC-14s. HASL is acceptable and cheaper. |
| Solder mask / silkscreen | any colour |
| Via treatment | none — no tenting or filling required |

## Design rules used

All comfortably inside standard capability at PCBWay, JLCPCB and similar. No
advanced process, no extra charge.

| Parameter | This board | Typical standard limit |
| --- | --- | --- |
| Min track width | 0.25 mm | 0.09–0.127 mm |
| Min clearance | 0.20 mm | 0.09–0.127 mm |
| Min drill | 0.30 mm | 0.20–0.30 mm |
| Via pad / drill | 0.60 / 0.30 mm | — |
| Min annular ring | 0.15 mm | 0.10–0.13 mm |
| Board edge clearance | 0.30 mm | — |

Hole count: **148 vias at 0.30 mm** and **29 connector holes at 1.00 mm**, 177
plated holes in all.

## What is in the zip

Copper `F_Cu.gtl`, `In1_Cu.g1`, `In2_Cu.g2`, `B_Cu.gbl`; solder mask
`F_Mask.gts`, `B_Mask.gbs`; silkscreen `F_Silkscreen.gto`, `B_Silkscreen.gbo`;
outline `Edge_Cuts.gm1`; drill `.drl` (Excellon, single file, mixed
plated/non-plated); and `.gbrjob` describing the stackup.

`Edge_Cuts.gm1` is the **only** board profile. Nothing else in the zip
contains an outline.

## Ordering a stencil as well

Add `F_Paste.gtp` (and `B_Paste.gbp` if you ever populate the back — at
present nothing is mounted there). Regenerate with `F.Paste` added to the
`--layers` list in `build.sh`.

## Ordering assembly

**This board is designed for turnkey assembly, not for hand-building.** An
earlier revision was deliberately specified in 0805 and SOIC-8 so it could be
built by hand; that constraint is gone, and dropping it is what allowed the
1206 passives the routing now depends on. Do not read the part sizes as
evidence that hand assembly was intended.

Supply `../rmc-pizz-arco-bom.csv` and `../rmc-pizz-arco-pos.csv` (centroid).
The BOM will need reformatting into the assembler's own template, and needs
manufacturer part numbers filling in for the passives — only the actives
(OPA4191, CD4066B) carry an MPN at the moment.

**80 placements: 72 SMD and 8 through-hole connectors.** The connectors are
2.54 mm pin headers — six 1x03, one 1x09, one 1x02 — and are a hand-solder
line item on top of the SMT run, which PCBWay and similar quote routinely.
They were chosen over SMD headers on measured land area and on mechanical
retention: an SMD header has no anchor beyond its solder fillet, so a tugged
loom lifts pads.

### Requirements that are not visible in the gerbers or the BOM

These are electrical requirements. An assembler substituting on footprint and
nominal value alone gets all four of them wrong.

| Parts | Requirement | Why |
| --- | --- | --- |
| **C104, C204, C304, C404, C504, C604** — six 1.8 nF | **C0G/NP0, ±2%, 50 V, and all six ordered as ONE line item from a single reel.** | These set the balance between the two piezo elements on each string. What matters is that the six match *each other*, not that each matches 1.8 nF: a ±5% part permits a 10% spread between two channels, which is worse than the balance being asked for. Parts from one reel and date code track far tighter than the tolerance band. |
| **Every capacitor of 10 nF and below** — the 18 × 100 pF, the six 1.8 nF, C701 | **C0G/NP0. Not optional, not substitutable with X7R.** | X7R at these values drifts with temperature and with signal voltage, which would destroy exactly the string balance the matched capacitors exist to protect. |
| **The 18 × 47 k** — R104–R106 and their equivalents in every channel | **±1% tolerance.** | They set the all-pass inverter's gain at exactly −1. RMC specified ±1% explicitly. |
| **U1–U3** | **OPA4191**, ordered by that part number. | The project library carries the symbol under a borrowed body (`OPA4197xD`, renamed), which is a drawing convenience only. The part fitted must be OPA4191. |

The 1 M, 20 k, 3M3, 1 k and 4.7 µF parts have no special requirement; standard
±5% — ±10% or ±20% for the 4.7 µF — is fine.

### Polarity — the one thing that destroys the board

J7 pin 7 is **+4.5 V** and pin 8 is **−4.5 V**, with pin 9 the shell/ground.
There is deliberately no reverse-protection diode: a series Schottky per rail
would cost about 0.6 dB of headroom out of a 9 V total supply, and this design
has none to spare. A loom built backwards therefore puts 9 V backwards across
every op-amp and destroys the board.

The convention is printed on the silkscreen, and the build procedure should
include a continuity check from the DIN plug to J7 before first power-up.
