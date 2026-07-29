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
import sexp

KICAD_CLI = pathlib.Path.home() / "Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"


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
    return 0


if __name__ == "__main__":
    sys.exit(main())
