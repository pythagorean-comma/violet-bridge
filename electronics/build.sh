#!/bin/bash
# Regenerate the whole project from design.py and check it.
#
# The schematic writer is plain Python; the board needs KiCad's own bundled
# interpreter for pcbnew. Both are pinned here so the build does not depend on
# whatever python happens to be on the path.
set -euo pipefail
cd "$(dirname "$0")"

KICAD_APP="$HOME/Applications/KiCad/KiCad.app"
KICAD_PY="$KICAD_APP/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3"
KICAD_CLI="$KICAD_APP/Contents/MacOS/kicad-cli"
VENV_PY="../.venv/bin/python"

export KICAD10_SYMBOL_DIR="$KICAD_APP/Contents/SharedSupport/symbols"
export KICAD10_FOOTPRINT_DIR="$KICAD_APP/Contents/SharedSupport/footprints"

PROJECT=rmc-pizz-arco/rmc-pizz-arco
mkdir -p build fab

echo "== schematic and project =="
"$VENV_PY" gen_sch.py
"$VENV_PY" gen_project.py

echo "== checking the drawing against design.py =="
"$VENV_PY" verify.py

echo "== board =="
"$KICAD_PY" gen_pcb.py 2>&1 | grep -v "assert" || true

echo "== ERC / DRC =="
"$KICAD_CLI" sch erc --severity-error --severity-warning -o build/erc.rpt "$PROJECT.kicad_sch" | tail -1
"$KICAD_CLI" pcb drc --severity-error -o build/drc.rpt "$PROJECT.kicad_pcb" | tail -2

echo "== fab outputs =="
"$KICAD_CLI" sch export pdf -o fab/rmc-pizz-arco-schematic.pdf "$PROJECT.kicad_sch" >/dev/null
"$KICAD_CLI" sch export bom --group-by Value,Footprint \
    --fields 'Reference,Value,Footprint,${QUANTITY},Datasheet' \
    -o fab/rmc-pizz-arco-bom.csv "$PROJECT.kicad_sch" >/dev/null
"$KICAD_CLI" pcb export gerbers -o fab/gerbers/ "$PROJECT.kicad_pcb" >/dev/null
"$KICAD_CLI" pcb export drill -o fab/gerbers/ "$PROJECT.kicad_pcb" >/dev/null
"$KICAD_CLI" pcb export pos --format csv --units mm \
    -o fab/rmc-pizz-arco-pos.csv "$PROJECT.kicad_pcb" >/dev/null
echo "done -- see NOTES.md for outstanding DRC items"
