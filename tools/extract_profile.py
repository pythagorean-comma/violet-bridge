"""One-off extractor: docs/JEN-VDG.pdf -> profile_data.py

The drawing is an AutoCAD 2000 plot with an *uncompressed* content stream made
entirely of stroked polylines (`m`/`l`/`S` only). There are no fonts and no text
objects -- every dimension number is drawn as line segments -- so nothing useful
comes out of a text extractor. The line work itself is exact, and that is what we
recover here.

Run this by hand when the drawing or the calibration changes:

    python tools/extract_profile.py

It rewrites profile_data.py, which is committed so that bridge.py never has to
parse a PDF.
"""

import math
import os
import re
from datetime import date

PDF_PATH = "docs/JEN-VDG.pdf"
OUTPUT_PATH = "profile_data.py"

# --- calibration --------------------------------------------------------
# Solved from the drawing's own dimension leaders; residual under 0.001".
# The page carries /Rotate 270, hence the axis swap in to_model_mm().
SCALE_PT_PER_INCH = 64.48
DATUM_X_PT = -316.32        # X zero: midpoint between strings 3 & 4
DATUM_Y_PT = 421.56         # Y zero: the foot baseline
MM_PER_INCH = 25.4

# --- classification thresholds ------------------------------------------
# Anything crossing this box is annotation. The crown reaches y = 36.9 and the
# dimension leaders run out to y = 47.7, so 40 separates them cleanly.
SHAPE_BOX = (-54.0, 54.0, -1.5, 40.0)
STRING_MARKER_COLOUR = (0.0, 1.0, 0.0)
HOLE_MIN_POINTS = 15                     # hole circles come through as 21 points
SLOT_SIDE_LENGTH = (10.0, 12.5)          # the 12 radial slot sides
DATUM_LINE_LENGTH = 30.0                 # the 0.0000 extension line spans the arch
CHAIN_TOL = 0.05                         # exact endpoint matches
RING_CLOSE_TOL = 1.2                     # the ring's own cusp at the left crown end
CURL_MAX_LENGTH = 2.0                    # arm-base curls; anything bigger is a real orphan
LINK_TOL = 1.2                           # used to spot isolated dimension leaders


def read_content_stream(pdf_path):
    """Return the page's content stream as text. It is stored uncompressed."""
    raw = open(pdf_path, "rb").read()
    start = raw.index(b"stream") + len(b"stream")
    end = raw.index(b"endstream")
    return raw[start:end].decode("latin-1")


def parse_subpaths(stream):
    """Split the content stream into (colour, points) subpaths.

    Only `m`, `l`, `RG` and the path-ending `S`/`Q` operators appear, so the
    interpreter can stay this small.
    """
    subpaths = []
    current = []
    colour = (0.0, 0.0, 0.0)
    numbers = []

    for token in stream.split():
        if re.fullmatch(r"-?\d+(\.\d+)?", token):
            numbers.append(float(token))
            continue
        if token == "m":
            if current:
                subpaths.append((colour, current))
            current = [(numbers[-2], numbers[-1])]
        elif token == "l":
            current.append((numbers[-2], numbers[-1]))
        elif token == "RG":
            colour = tuple(numbers[-3:])
        elif token in ("S", "Q") and current:
            subpaths.append((colour, current))
            current = []
        numbers = []

    if current:
        subpaths.append((colour, current))
    return subpaths


def to_model_mm(subpaths):
    """Map PDF points to model millimetres about the drawing's own datum."""
    def convert(point):
        x_pdf, y_pdf = point
        x_mm = (-y_pdf - DATUM_X_PT) / SCALE_PT_PER_INCH * MM_PER_INCH
        y_mm = (x_pdf - DATUM_Y_PT) / SCALE_PT_PER_INCH * MM_PER_INCH
        return (x_mm, y_mm)

    return [(colour, [convert(p) for p in pts]) for colour, pts in subpaths]


def dedupe(subpaths):
    """Drop repeated strokes.

    The plot draws a handful of paths twice. Left in, the chainer walks such a
    path out and straight back again, which puts a doubled-back spur in the ring
    and two self-intersections with it.
    """
    seen = set()
    unique = []
    for colour, points in subpaths:
        key = tuple((round(x, 6), round(y, 6)) for x, y in points)
        if key in seen or tuple(reversed(key)) in seen:
            continue
        seen.add(key)
        unique.append((colour, points))
    return unique


def inside_shape_box(points):
    x_lo, x_hi, y_lo, y_hi = SHAPE_BOX
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    return x_lo <= min(xs) and max(xs) <= x_hi and y_lo <= min(ys) and max(ys) <= y_hi


def path_length(points):
    return sum(math.dist(points[i], points[i + 1]) for i in range(len(points) - 1))


def circle_of(points):
    """Centre and radius of a closed polygon approximating a circle."""
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    r = ((max(xs) - min(xs)) + (max(ys) - min(ys))) / 4
    return cx, cy, r


def classify(subpaths):
    """Sort the drawing's line work into the pieces we care about.

    Rules are applied in order and were each checked against the plot:
      - green stroke .............. the drawing's string-position markers
      - leaves the shape box ...... a dimension leader, discarded
      - closed and many-pointed ... one of the 7 drilled holes
      - 2-point, 10.0-12.5 mm ..... one of the 12 radial slot sides (parked)
      - 2-point, over 30 mm ....... the 0.0000 datum extension line, discarded
      - anything else ............. a candidate profile edge
    """
    markers, holes, slot_sides, edges = [], [], [], []

    for colour, points in subpaths:
        if not inside_shape_box(points):
            continue
        if colour == STRING_MARKER_COLOUR:
            markers.append(circle_of(points))
            continue
        closed = math.dist(points[0], points[-1]) < 1e-9
        if closed and len(points) >= HOLE_MIN_POINTS:
            holes.append(circle_of(points))
            continue
        if len(points) == 2:
            length = math.dist(points[0], points[1])
            if SLOT_SIDE_LENGTH[0] < length < SLOT_SIDE_LENGTH[1]:
                slot_sides.append(points)
                continue
            if length > DATUM_LINE_LENGTH:
                continue
        edges.append(points)

    return markers, holes, slot_sides, edges


def split_isolated(edges, tol=LINK_TOL):
    """Separate the radial dimension leaders from the real profile edges.

    Those leaders are 2-point segments the same length as the real arm-side
    edges, so length alone cannot tell them apart. What does: the silhouette is
    a closed ring, so every real edge meets a neighbour at both ends, while a
    leader floats free in the middle of a notch.

    Returns (edges, leaders). The leaders are not waste -- the lower end of each
    is the drawing's own radial dimension target, i.e. the top of a slot.
    """
    kept = list(edges)
    leaders = []
    changed = True
    while changed:
        changed = False
        for candidate in list(kept):
            others = [e for e in kept if e is not candidate]
            linked = [
                any(math.dist(end, other[0]) < tol or math.dist(end, other[-1]) < tol
                    for other in others)
                for end in (candidate[0], candidate[-1])
            ]
            if not all(linked):
                kept.remove(candidate)
                leaders.append(candidate)
                changed = True
    return kept, leaders


def chain_edges(edges, tol):
    """Join edges end-to-end into the longest runs a given tolerance allows."""
    pending = [list(e) for e in edges]
    chains = []
    while pending:
        chain = pending.pop(0)
        grew = True
        while grew:
            grew = False
            for i, other in enumerate(pending):
                if math.dist(chain[-1], other[0]) < tol:
                    chain += pending.pop(i)[1:]
                elif math.dist(chain[-1], other[-1]) < tol:
                    chain += list(reversed(pending.pop(i)))[1:]
                elif math.dist(chain[0], other[-1]) < tol:
                    chain = pending.pop(i)[:-1] + chain
                elif math.dist(chain[0], other[0]) < tol:
                    chain = list(reversed(pending.pop(i)))[:-1] + chain
                else:
                    continue
                grew = True
                break
        chains.append(chain)
    return chains


def close_ring(chains):
    """Pick the silhouette out of the chains and check that it really closes.

    The profile edges chain into one long run plus twelve ~1.4 mm curls, which
    are small relief loops sitting tangent to the outline at the arm bases. The
    long run closes on itself across a 0.9 mm cusp at the left end of the crown,
    which is genuinely all the plot draws there.

    Anything left over that is not curl-sized means the classification has gone
    wrong, so say so rather than quietly producing a mangled profile.
    """
    ring = max(chains, key=len)
    leftovers = [c for c in chains if c is not ring]

    gap = math.dist(ring[0], ring[-1])
    if gap > RING_CLOSE_TOL:
        raise ValueError(
            f"outline does not close: {len(ring)} points, end gap {gap:.3f} mm "
            f"exceeds {RING_CLOSE_TOL} mm"
        )

    oversized = [c for c in leftovers if path_length(c) > CURL_MAX_LENGTH]
    if oversized:
        raise ValueError(
            f"{len(oversized)} orphaned chains longer than {CURL_MAX_LENGTH} mm; "
            f"largest is {max(path_length(c) for c in oversized):.2f} mm"
        )

    if gap < CHAIN_TOL:
        ring = ring[:-1]
    return list(ring), leftovers


def signed_area(ring):
    total = 0.0
    for i in range(len(ring)):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % len(ring)]
        total += x0 * y1 - x1 * y0
    return total / 2


def sort_by_angle(circles, centre):
    cx, cy = centre
    return sorted(circles, key=lambda c: math.atan2(c[1] - cy, c[0] - cx), reverse=True)


def fit_circle(points):
    """Least-squares centre and radius through a set of points."""
    n = len(points)
    sx = sum(x for x, _ in points)
    sy = sum(y for _, y in points)
    sxx = sum(x * x for x, _ in points)
    syy = sum(y * y for _, y in points)
    sxy = sum(x * y for x, y in points)
    sxxx = sum(x * (x * x + y * y) for x, y in points)
    syyy = sum(y * (x * x + y * y) for x, y in points)
    ssq = sum(x * x + y * y for x, y in points)

    # Normal equations for  x^2 + y^2 + D x + E y + F = 0
    a = [[sxx, sxy, sx], [sxy, syy, sy], [sx, sy, float(n)]]
    rhs = [-sxxx, -syyy, -ssq]

    for col in range(3):
        pivot = max(range(col, 3), key=lambda r: abs(a[r][col]))
        a[col], a[pivot] = a[pivot], a[col]
        rhs[col], rhs[pivot] = rhs[pivot], rhs[col]
        for row in range(col + 1, 3):
            factor = a[row][col] / a[col][col]
            for k in range(col, 3):
                a[row][k] -= factor * a[col][k]
            rhs[row] -= factor * rhs[col]
    sol = [0.0, 0.0, 0.0]
    for row in (2, 1, 0):
        sol[row] = (rhs[row] - sum(a[row][k] * sol[k] for k in range(row + 1, 3))) / a[row][row]

    d, e, f = sol
    cx, cy = -d / 2, -e / 2
    return cx, cy, math.sqrt(cx * cx + cy * cy - f)


def format_points(points, indent=4):
    pad = " " * indent
    return "\n".join(f"{pad}({x:.4f}, {y:.4f})," for x, y in points)


def write_profile_data(path, ring, holes, slot_sides, slot_tops, curls, crown):
    cx, cy, radius = crown
    hole_diameter = sum(2 * r for _, _, r in holes) / len(holes)
    xs = [x for x, _ in ring]
    ys = [y for _, y in ring]

    lines = [
        '"""Front-view profile of the JEN-VDG bridge, in millimetres.',
        "",
        f"Generated by tools/extract_profile.py on {date.today().isoformat()}.",
        "Do not edit by hand -- rerun the extractor instead.",
        "",
        f"Source:  {PDF_PATH} (AutoCAD 2000 plot, 'JEN-VDG interior view')",
        f"Scale:   {SCALE_PT_PER_INCH} PDF points per inch",
        "Datum:   X zero at the midpoint between strings 3 & 4,",
        "         Y zero at the foot baseline.",
        "",
        "The drawn part is a 6-string viola d'amore bridge. The profile is",
        "mildly asymmetric because it was traced from a real bridge; that is",
        "faithful to the source and is deliberately not corrected.",
        '"""',
        "",
        f"SCALE_PT_PER_INCH = {SCALE_PT_PER_INCH}",
        "",
        f"# Circle through the 7 hole centres.",
        f"CROWN_CENTRE = ({cx:.4f}, {cy:.4f})",
        f"HOLE_CIRCLE_R = {radius:.4f}",
        f"HOLE_DIAMETER = {hole_diameter:.4f}",
        "",
        f"# Closed silhouette, {len(ring)} points, counter-clockwise.",
        f"# Extent: {max(xs) - min(xs):.3f} x {max(ys) - min(ys):.3f} mm.",
        "OUTLINE = [",
        format_points(ring),
        "]",
        "",
        "# Drilled through-holes as (x, y, radius).",
        "HOLES = [",
        "\n".join(f"    ({x:.4f}, {y:.4f}, {r:.4f})," for x, y, r in holes),
        "]",
        "",
        "# Targets of the drawing's six radial notes (2.820-2.860\"R at 59-125deg).",
        "# Each lands on the top centre of one slot, to better than 0.05 mm.",
        "SLOT_TOPS = [",
        format_points(slot_tops),
        "]",
        "",
        "# The 6 radial pairs running from the arch crown up to the arm shoulders.",
        "# Parked, not cut: a front view cannot tell pierced slots from carving",
        "# lines on the interior face. Decide against the real bridge.",
        "SLOT_SIDES = [",
        "\n".join(
            "    [" + ", ".join(f"({x:.4f}, {y:.4f})" for x, y in side) + "],"
            for side in slot_sides
        ),
        "]",
        "",
        "# Twelve ~1.4 mm relief loops sitting tangent to the outline at the arm",
        "# bases, two per notch. Too small to matter to the blank and they overlap",
        "# the outline rather than joining it, so they are parked as well.",
        "ARM_BASE_CURLS = [",
        "\n".join(
            "    [" + ", ".join(f"({x:.4f}, {y:.4f})" for x, y in curl) + "],"
            for curl in curls
        ),
        "]",
        "",
    ]
    open(path, "w").write("\n".join(lines))


def main():
    subpaths = parse_subpaths(read_content_stream(PDF_PATH))
    subpaths = dedupe(to_model_mm(subpaths))
    markers, holes, slot_sides, edges = classify(subpaths)

    edges, leaders = split_isolated(edges)
    ring, curls = close_ring(chain_edges(edges, CHAIN_TOL))
    if signed_area(ring) < 0:
        ring.reverse()

    holes.sort()
    crown = fit_circle([(x, y) for x, y, _ in holes])

    # A radial leader runs from its label down onto its target, so the lower
    # end of each is the point the dimension actually calls out.
    slot_tops = sorted(min(leader, key=lambda p: p[1]) for leader in leaders)

    write_profile_data(OUTPUT_PATH, ring, holes, slot_sides, slot_tops, curls, crown)

    xs = [x for x, _ in ring]
    ys = [y for _, y in ring]
    print(f"outline    : {len(ring)} points, closed, "
          f"{max(xs) - min(xs):.3f} x {max(ys) - min(ys):.3f} mm")
    print(f"holes      : {len(holes)} on R {crown[2]:.4f} mm")
    print(f"slot tops  : {len(slot_tops)}")
    print(f"slot sides : {len(slot_sides)} (parked)")
    print(f"arm curls  : {len(curls)} (parked)")
    print(f"markers    : {len(markers)} (reference only)")
    print(f"wrote      : {OUTPUT_PATH}")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
