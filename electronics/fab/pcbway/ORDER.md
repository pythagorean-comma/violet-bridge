# RMC pizz/arco 6-channel board — fabrication order

Upload `rmc-pizz-arco-pcbway.zip`. It contains only the layers a fab needs.

## Settings that are NOT in the gerbers — you must enter these

| Setting | Value |
| --- | --- |
| **Layers** | **4** — the default on most order forms is 2. In1 is a ground plane, In2 is the V+ plane; a 2-layer build would silently drop both. |
| Board size | 88 × 112 mm, single up |
| Thickness | 1.6 mm |
| Copper weight | 1 oz outer, 0.5 oz inner (standard) |
| Surface finish | ENIG preferred — flat pads suit the SOIC-8s. HASL is acceptable and cheaper. |
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

## Ordering assembly rather than a bare board

Supply `../rmc-pizz-arco-bom.csv` and `../rmc-pizz-arco-pos.csv` (centroid).
The BOM will need reformatting into the assembler's own template, and needs
manufacturer part numbers filling in for the passives — only the actives
(OPA2191, CD4066B) carry an MPN at the moment.

Bear in mind the board was chosen as 0805 and SOIC specifically so it can be
hand-built; assembly is optional.
