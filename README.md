# violet-bridge
CadQuery based python scripts to generate STEP and SVG renderings of components of a viola da gamba bridge.
The bridge saddles can be moved fore and aft to allow fine intonation adjustments
The saddles have recesses such that RMC pizz/arco pickups can be installed.


![image](docs/violet-bridge-disassembled.png)
![image](docs/violet-bridge-assembled.png)

## Requirements

The two halves of this repository have separate prerequisites.

**Bridge geometry** — `bridge.py`, `bridge_body.py`, `assembly.py`:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python assembly.py
```

Python 3.10–3.12. Use `.venv/bin/python` rather than a bare `python`.

**Electronics** — `electronics/build.sh`:

- **KiCad 10.x** (`brew install --cask kicad`, or
  <https://www.kicad.org/download/>). Not a pip package, so
  `requirements.txt` cannot supply it. The file formats written are version
  specific — KiCad 9 will not open the generated schematic.
- No additional Python packages. The generators are pure standard library
  apart from `pcbnew`, which ships inside KiCad; `build.sh` therefore runs
  `gen_pcb.py` under KiCad's own bundled interpreter and everything else
  under the venv above.

`electronics/kicad.py` finds the installation — it checks `$KICAD_APP`, then
`/Applications/KiCad/KiCad.app`, then `~/Applications/KiCad/KiCad.app`, then
`kicad-cli` on `PATH`. If yours lives somewhere else:

```bash
export KICAD_APP=/path/to/KiCad.app
```

Run `.venv/bin/python electronics/kicad.py` to see what it found.

## Pickup electronics

`electronics/` holds the phase-switching preamp for the RMC pizz/arco pickups
that sit in the saddles — six channels of RMC's schematic
(`docs/Pizz-Arco-Switching-260729.png`), plus the supply splitting and
switching that drawing leaves open. See [electronics/NOTES.md](electronics/NOTES.md)
for the circuit analysis, the design decisions, and the open questions for RMC.
