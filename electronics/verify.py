"""Read the generated schematic back through KiCad and compare it to design.py.

The schematic is drawn from geometry -- wires meeting at coordinates -- so a
misplaced endpoint would silently produce a different circuit. This exports
KiCad's own netlist and checks that the connectivity it found is exactly the
connectivity design.py asked for, net by net.
"""

import pathlib
import subprocess
import sys

import design as circuit
import kicad
import sexp

KICAD_CLI = kicad.KICAD_CLI


def export_netlist(schematic, destination):
    result = subprocess.run(
        [str(KICAD_CLI), "sch", "export", "netlist", "--format", "kicadsexpr",
         "-o", str(destination), str(schematic)],
        capture_output=True, text=True)
    if result.returncode != 0 or not destination.exists():
        raise SystemExit(f"netlist export failed:\n{result.stdout}\n{result.stderr}")
    return destination


def read_netlist(path):
    """net name -> set of (ref, pin), ignoring drawing-only power symbols."""
    tree = sexp.parse(path.read_text())
    found = {}
    for net in sexp.find_all(sexp.find(tree, "nets"), "net"):
        name = sexp.find(net, "name")[1]
        nodes = set()
        for node in sexp.find_all(net, "node"):
            ref = sexp.find(node, "ref")[1]
            pin = sexp.find(node, "pin")[1]
            if ref.startswith("#"):
                continue        # power symbols and flags name nets, they are not parts
            nodes.add((ref, str(pin)))
        found[name] = nodes
    return found


def compare(actual, expected):
    """Compare as partitions; report differences in both directions."""
    problems = []

    actual_by_nodes = {frozenset(nodes): name for name, nodes in actual.items() if nodes}
    expected_by_nodes = {frozenset(nodes): name for name, nodes in expected.items()}

    for nodes, name in expected_by_nodes.items():
        if nodes not in actual_by_nodes:
            # Find whatever the schematic did with these pins instead.
            landed = {}
            for pin in sorted(nodes):
                for actual_name, actual_nodes in actual.items():
                    if pin in actual_nodes:
                        landed.setdefault(actual_name, []).append(pin)
                        break
                else:
                    landed.setdefault("<nowhere>", []).append(pin)
            detail = "; ".join(f"{k}: {sorted(v)}" for k, v in landed.items())
            problems.append(f"net {name} not formed as drawn -> {detail}")

    for nodes, name in actual_by_nodes.items():
        if nodes not in expected_by_nodes and not name.startswith("unconnected-"):
            problems.append(f"unexpected net {name} = {sorted(nodes)}")

    for name in sorted(actual):
        if name.startswith("unconnected-"):
            problems.append(f"unconnected pin: {name}")

    # Names should line up too, for the nets the design names explicitly.
    for nodes, name in expected_by_nodes.items():
        actual_name = actual_by_nodes.get(nodes)
        if actual_name and actual_name != name and not actual_name.startswith("Net-"):
            problems.append(f"net {name} is called {actual_name} in the schematic")

    return problems


def _reference(node):
    for prop in sexp.find_all(node, "property"):
        if prop[1] == "Reference":
            return prop[2]
    return None


def _property(node, name):
    for prop in sexp.find_all(node, "property"):
        if prop[1] == name:
            return prop[2]
    return None


def read_schematic_symbols(path):
    """reference -> (uuid, value), for the first unit of each placed symbol.

    Only direct children of the sheet are instances; the definitions inside
    lib_symbols are nested one level deeper and are skipped for free.
    """
    tree = sexp.parse(path.read_text())
    found = {}
    for symbol in sexp.find_all(tree, "symbol"):
        unit = sexp.find(symbol, "unit")
        uuid_node = sexp.find(symbol, "uuid")
        reference = _reference(symbol)
        if unit is None or uuid_node is None or reference is None:
            continue
        if int(str(unit[1])) == 1 and not reference.startswith("#"):
            found[reference] = (uuid_node[1], _property(symbol, "Value"))
    return found


def read_board_footprints(path):
    """reference -> (schematic path, footprint identifier)."""
    tree = sexp.parse(path.read_text())
    found = {}
    for footprint in sexp.find_all(tree, "footprint"):
        reference = _reference(footprint)
        if reference is None:
            continue
        path_node = sexp.find(footprint, "path")
        found[reference] = (path_node[1] if path_node else None,
                            str(footprint[1]))
    return found


def check_board_linkage(schematic, board):
    """Every footprint must point at its schematic symbol and name its library.

    Without the path KiCad cannot associate the two, so cross-probing dies and
    'Update PCB from Schematic' offers to add every footprint again as a new
    part. Without the library prefix it cannot update a footprint from its
    library. Both are silent -- nothing else in the build would notice.
    """
    symbols = read_schematic_symbols(schematic)
    footprints = read_board_footprints(board)
    problems = []

    # Values are set in three places -- design.py, the schematic and the BOM
    # that KiCad derives from it -- so check the drawing still agrees with the
    # design. A stale literal here is invisible until it reaches a BOM.
    for reference, (_, value) in sorted(symbols.items()):
        wanted = circuit.PARTS[reference].value
        if value != wanted:
            problems.append(f"{reference}: schematic says {value!r}, "
                            f"design.py says {wanted!r}")

    for reference, (path, identifier) in sorted(footprints.items()):
        expected = symbols.get(reference)
        if expected is None:
            problems.append(f"{reference}: on the board but not the schematic")
        elif path != f"/{expected[0]}":
            problems.append(f"{reference}: path {path} does not match "
                            f"schematic symbol /{expected[0]}")
        if ":" not in identifier:
            problems.append(f"{reference}: footprint {identifier!r} has no library")

    for reference in sorted(set(symbols) - set(footprints)):
        if not circuit.PARTS[reference].footprint:
            continue        # power flags are schematic-only, by design
        problems.append(f"{reference}: in the schematic but not on the board")

    return problems, len(footprints)


def main():
    here = pathlib.Path(__file__).parent
    schematic = here / "rmc-pizz-arco" / "rmc-pizz-arco.kicad_sch"
    netlist = here / "build" / "verify.net"
    netlist.parent.mkdir(parents=True, exist_ok=True)

    export_netlist(schematic, netlist)
    actual = read_netlist(netlist)
    expected = {name: {n for n in nodes if not n[0].startswith("#")}
                for name, nodes in circuit.NETS.items()}

    problems = compare(actual, expected)
    if problems:
        print(f"{len(problems)} problem(s):")
        for problem in problems[:60]:
            print(f"  - {problem}")
        if len(problems) > 60:
            print(f"  ... and {len(problems) - 60} more")
        return 1

    print(f"schematic matches design.py: {len(expected)} nets, "
          f"{sum(len(v) for v in expected.values())} pin connections")

    board = here / circuit.PROJECT / f"{circuit.PROJECT}.kicad_pcb"
    if not board.exists():
        print("board not generated yet; skipping linkage check")
        return 0
    problems, count = check_board_linkage(schematic, board)
    if problems:
        print(f"{len(problems)} board linkage problem(s):")
        for problem in problems[:20]:
            print(f"  - {problem}")
        return 1
    print(f"board linked to schematic: {count} footprints")
    return 0


if __name__ == "__main__":
    sys.exit(main())
