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
DRC_ERRORS=$(grep -cE '^\[' build/drc.rpt || true)

echo "== documentation outputs =="
"$KICAD_CLI" sch export pdf -o fab/rmc-pizz-arco-schematic.pdf "$PROJECT.kicad_sch" >/dev/null
"$KICAD_CLI" sch export bom --group-by Value,Footprint \
    --fields 'Reference,Value,Footprint,${QUANTITY},Datasheet' \
    -o fab/rmc-pizz-arco-bom.csv "$PROJECT.kicad_sch" >/dev/null
"$KICAD_CLI" pcb export pos --format csv --units mm \
    -o fab/rmc-pizz-arco-pos.csv "$PROJECT.kicad_pcb" >/dev/null

# The set a fab actually gets: copper, mask, silk, outline, drill -- and
# nothing else. A blanket export also writes Fab, Courtyard and User layers,
# and F.Fab carries a second closed board outline; if CAM picks that one up
# instead of Edge.Cuts the board comes back the wrong shape.
echo "== fab package =="
if [ "$DRC_ERRORS" -ne 0 ]; then
    rm -f fab/rmc-pizz-arco-pcbway.zip
    echo "SKIPPED: $DRC_ERRORS DRC error(s) outstanding -- see build/drc.rpt."
    echo "No fabrication package is written while the board has known errors."
    exit 0
fi
rm -rf fab/pcbway
"$KICAD_CLI" pcb export gerbers \
    --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts \
    -o fab/pcbway/ "$PROJECT.kicad_pcb" >/dev/null
# Omitting --excellon-separate-th gives one combined PTH/NPTH file, which is
# what fabs expect; it is a bare flag, not a key=value.
"$KICAD_CLI" pcb export drill --format excellon \
    -o fab/pcbway/ "$PROJECT.kicad_pcb" >/dev/null
cp fab/ORDER.md fab/pcbway/
(cd fab/pcbway && zip -q -r ../rmc-pizz-arco-pcbway.zip .)
echo "wrote fab/rmc-pizz-arco-pcbway.zip -- upload this, and see fab/ORDER.md"
