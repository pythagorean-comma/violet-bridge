# violet-bridge
CadQuery based python scripts to generate STEP and SVG renderings of components of a viola da gamba bridge.
The bridge saddles can be moved fore and aft to allow fine intonation adjustments
The saddles have recesses such that RMC pizz/arco pickups can be installed.


![image](docs/violet-bridge-disassembled.png)
![image](docs/violet-bridge-assembled.png)

## Pickup electronics

`electronics/` holds the phase-switching preamp for the RMC pizz/arco pickups
that sit in the saddles — six channels of RMC's schematic
(`docs/Pizz-Arco-Switching-260729.png`), plus the supply splitting and
switching that drawing leaves open. See [electronics/NOTES.md](electronics/NOTES.md)
for the circuit analysis, the design decisions, and the open questions for RMC.
