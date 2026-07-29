"""Write the KiCad project scaffolding around the generated schematic.

Produces the .kicad_pro (design rules and net classes), the symbol and
footprint library tables, and the one-symbol project library that holds
OPA2191 -- which KiCad does not ship.

Library paths go through KiCad's own ${KICAD10_*_DIR} variables rather than
absolute paths, so the project opens on any machine with KiCad 10 installed.
"""

import json
import pathlib

import design as circuit
import symlib
from kisch import Schematic, _uuid
from sexp import Sym, dumps

PROJECT = "rmc-pizz-arco"

# 2-layer, 1 oz copper, comfortably inside every low-cost fab's capability
# (JLCPCB and PCBWay both accept 0.127 mm; this leaves a wide margin).
TRACK_WIDTH = 0.25
POWER_TRACK_WIDTH = 0.5
CLEARANCE = 0.2
VIA_DIAMETER = 0.6
VIA_DRILL = 0.3


def net_classes():
    default = {
        "bus_width": 12, "clearance": CLEARANCE, "diff_pair_gap": 0.25,
        "diff_pair_via_gap": 0.25, "diff_pair_width": 0.2, "line_style": 0,
        "microvia_diameter": 0.3, "microvia_drill": 0.1, "name": "Default",
        "pcb_color": "rgba(0, 0, 0, 0.000)", "priority": 2147483647,
        "schematic_color": "rgba(0, 0, 0, 0.000)", "track_width": TRACK_WIDTH,
        "via_diameter": VIA_DIAMETER, "via_drill": VIA_DRILL, "wire_width": 6,
    }
    power = dict(default, name="Power", track_width=POWER_TRACK_WIDTH,
                 priority=1, pcb_color="rgba(200, 52, 52, 0.800)")
    return [default, power]


def project_file(path, root_uuid):
    document = {
        "board": {
            "design_settings": {
                "defaults": {
                    "board_outline_line_width": 0.1,
                    "copper_line_width": 0.2,
                    "copper_text_size_h": 1.5, "copper_text_size_v": 1.5,
                    "copper_text_thickness": 0.3,
                    "courtyard_line_width": 0.05,
                    "other_line_width": 0.15,
                    "silk_line_width": 0.12,
                    "silk_text_size_h": 0.8, "silk_text_size_v": 0.8,
                    "silk_text_thickness": 0.12,
                },
                "diff_pair_dimensions": [],
                "drc_exclusions": [],
                "rules": {
                    "allow_blind_buried_vias": False,
                    "allow_microvias": False,
                    "max_error": 0.005,
                    "min_clearance": 0.0,
                    "min_connection": 0.0,
                    "min_copper_edge_clearance": 0.3,
                    "min_hole_clearance": 0.25,
                    "min_hole_to_hole": 0.25,
                    "min_microvia_diameter": 0.2,
                    "min_microvia_drill": 0.1,
                    "min_resolved_spokes": 2,
                    "min_silk_clearance": 0.0,
                    "min_text_height": 0.8,
                    "min_text_thickness": 0.08,
                    "min_through_hole_diameter": 0.3,
                    "min_track_width": 0.15,
                    "min_via_annular_width": 0.13,
                    "min_via_diameter": 0.45,
                    "solder_mask_to_copper_clearance": 0.0,
                    "use_height_for_length_calcs": True,
                },
                "track_widths": [0.0, TRACK_WIDTH, POWER_TRACK_WIDTH, 1.0],
                "via_dimensions": [{"diameter": 0.0, "drill": 0.0},
                                   {"diameter": VIA_DIAMETER, "drill": VIA_DRILL}],
                "zones_allow_external_fillets": False,
            },
        },
        "boards": [],
        "cvpcb": {"equivalence_files": []},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": f"{PROJECT}.kicad_pro", "version": 3},
        "net_settings": {
            "classes": net_classes(),
            "meta": {"version": 4},
            # The rails and the audio ground get the wider track class.
            "netclass_patterns": [
                {"netclass": "Power", "pattern": "V+"},
                {"netclass": "Power", "pattern": "V-"},
                {"netclass": "Power", "pattern": "AGND"},
                {"netclass": "Power", "pattern": "VIN"},
                {"netclass": "Power", "pattern": "VFUSED"},
            ],
        },
        "pcbnew": {"last_paths": {}, "page_layout_descr_file": ""},
        "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
        "sheets": [[root_uuid, "Root"]],
        "text_variables": {},
    }
    path.write_text(json.dumps(document, indent=2) + "\n")


def library_tables(directory):
    """Point at KiCad's stock libraries plus the project's own."""
    used_symbol_libs = sorted({nick for nick, _, _, _ in circuit.LIBS.values()
                               if nick != "rmc"})
    rows = [f'  (lib (name "{nick}")(type "KiCad")(uri '
            f'"${{KICAD10_SYMBOL_DIR}}/{nick}.kicad_sym")(options "")(descr ""))'
            for nick in used_symbol_libs]
    rows.append('  (lib (name "rmc")(type "KiCad")(uri '
                '"${KIPRJMOD}/rmc.kicad_sym")(options "")(descr '
                '"Parts not in the stock libraries"))')
    (directory / "sym-lib-table").write_text(
        "(sym_lib_table\n  (version 7)\n" + "\n".join(rows) + "\n)\n")

    footprint_libs = sorted({part.footprint.split(":", 1)[0]
                             for part in circuit.PARTS.values() if part.footprint})
    rows = [f'  (lib (name "{nick}")(type "KiCad")(uri '
            f'"${{KICAD10_FOOTPRINT_DIR}}/{nick}.pretty")(options "")(descr ""))'
            for nick in footprint_libs]
    (directory / "fp-lib-table").write_text(
        "(fp_lib_table\n  (version 7)\n" + "\n".join(rows) + "\n)\n")


def symbol_library(path):
    """The project library: OPA2191, bodied on TI's OPA2197 dual."""
    symbol = symlib.flatten("Amplifier_Operational", "OPA2197xD", rename="OPA2191")
    symbol = circuit.patch_symbol("rmc:OPA2191", symbol)
    library = [Sym("kicad_symbol_lib"),
               [Sym("version"), 20251024],
               [Sym("generator"), "violet-bridge"],
               [Sym("generator_version"), "10.0"],
               symbol]
    path.write_text(dumps(library) + "\n")


def main():
    directory = pathlib.Path(__file__).parent / PROJECT
    directory.mkdir(parents=True, exist_ok=True)
    root_uuid = Schematic(PROJECT).uuid
    project_file(directory / f"{PROJECT}.kicad_pro", root_uuid)
    library_tables(directory)
    symbol_library(directory / "rmc.kicad_sym")
    print(f"wrote project scaffolding in {directory}")


if __name__ == "__main__":
    main()
