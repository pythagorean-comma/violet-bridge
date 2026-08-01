"""Run the autorouter over the placed board and bring the result back in.

NOT part of the build any more, and not needed: gen_pcb.py routes the board
completely and DRC-clean on its own, so there is nothing left for a router to
do. Kept because it is the working end of the freerouting route -- if a future
change makes some region genuinely awkward, running this over the DSN that
gen_pcb.py still writes is the escape hatch, and rediscovering how to drive
freerouting headlessly is a session's work.

Runs under KiCad's bundled interpreter, like gen_pcb.py. Everything already
laid down is exported as existing wiring, so freerouting works around it
rather than ripping it up. FREEROUTING_JAR overrides where the jar is found.
"""

import os
import pathlib
import subprocess
import sys

import pcbnew

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import design as circuit  # noqa: E402

HERE = pathlib.Path(__file__).parent
BOARD = HERE / circuit.PROJECT / f"{circuit.PROJECT}.kicad_pcb"
DSN = HERE / "build" / f"{circuit.PROJECT}.dsn"
SES = HERE / "build" / f"{circuit.PROJECT}.ses"

def _candidates():
    """Where the jar might be. Names carry a version, so glob rather than
    hard-code one -- dropping in a newer release should just work."""
    override = os.environ.get("FREEROUTING_JAR")
    if override:
        yield pathlib.Path(override)
    for directory in (HERE / "tools", pathlib.Path.home() / "Applications",
                      pathlib.Path.home() / "Downloads"):
        if directory.is_dir():
            yield from sorted(directory.glob("freerouting*.jar"), reverse=True)


def java_for(jar):
    """Find a JRE new enough for this jar.

    Freerouting ships class files ahead of most installed runtimes, and the
    failure is a LinkageError deep in the launcher rather than anything
    obvious. SDKMAN keeps its JDKs outside java_home, so look there too.
    """
    candidates = [os.environ.get("JAVA_HOME", "") + "/bin/java", "java"]
    sdkman = pathlib.Path.home() / ".sdkman" / "candidates" / "java"
    if sdkman.is_dir():
        candidates += [str(p / "bin" / "java") for p in
                       sorted(sdkman.iterdir(), reverse=True) if (p / "bin" / "java").is_file()]
    for candidate in candidates:
        if not candidate or (candidate != "java" and not pathlib.Path(candidate).is_file()):
            continue
        probe = subprocess.run([candidate, "-jar", str(jar), "--help"],
                               capture_output=True, text=True)
        if "UnsupportedClassVersionError" not in (probe.stdout + probe.stderr):
            return candidate
    return None


def find_jar():
    for candidate in _candidates():
        if candidate.is_file():
            return candidate
    return None


def autoroute(jar, java):
    SES.unlink(missing_ok=True)
    result = subprocess.run(
        [java, "-jar", str(jar), "-de", str(DSN), "-do", str(SES), "-mp", "100"],
        capture_output=True, text=True, timeout=3600)
    if not SES.exists():
        raise SystemExit("freerouting produced no session file:\n"
                         f"{result.stdout[-2000:]}\n{result.stderr[-2000:]}")
    return SES


def main():
    jar = find_jar()
    if jar is None:
        print("freerouting.jar not found -- board left unrouted.")
        print("  Put it in electronics/tools/freerouting.jar or set FREEROUTING_JAR.")
        print(f"  The design it needs is already written: {DSN}")
        return 0

    java = java_for(jar)
    if java is None:
        print(f"found {jar.name}, but no installed Java can run it.")
        print("  It needs a newer JRE than any on this machine.")
        print("  Install one (e.g. `sdk install java 25-tem`) or drop in an")
        print("  older freerouting release, then re-run.")
        return 0

    print(f"routing with {jar.name} under {java}")
    autoroute(jar, java)

    board = pcbnew.LoadBoard(str(BOARD))
    if not pcbnew.ImportSpecctraSES(board, str(SES)):
        raise SystemExit(f"Specctra SES import failed: {SES}")
    # The planes have to be re-filled: the router adds vias that need to
    # connect to them, and an unfilled zone reads as unconnected in DRC.
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(BOARD), board)

    tracks = len(list(board.GetTracks()))
    print(f"imported {SES.name}; board now carries {tracks} track/via items")
    return 0


if __name__ == "__main__":
    sys.exit(main())
