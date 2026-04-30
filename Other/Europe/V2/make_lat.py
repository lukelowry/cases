"""Convert Europe V2 CSVs (buses, lines, transformers, links, converters) to a .lat file."""

import csv
import re
from pathlib import Path

here = Path(__file__).parent


def read_csv(name):
    with open(here / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def strip_prefix(bus_id):
    """Strip OSM prefixes (way/, relation/) for readable .lat labels."""
    for prefix in ("way/", "relation/", "merged_"):
        if bus_id.startswith(prefix):
            bus_id = bus_id[len(prefix):]
    return bus_id


def parse_waypoints(raw_line, bus0_pos, bus1_pos):
    """Extract intermediate waypoints from a LINESTRING in the raw CSV line.
    Strips first and last points (bus endpoints known from vertices).
    Reverses interior points when the LINESTRING runs bus1->bus0."""
    m = re.search(r"LINESTRING\s*\(([^)]+)\)", raw_line)
    if not m:
        return ""
    pairs = []
    for pair in m.group(1).split(","):
        parts = pair.strip().split()
        if len(parts) == 2:
            pairs.append((float(parts[0]), float(parts[1])))
    interior = pairs[1:-1]
    if not interior:
        return ""
    # Check if LINESTRING runs opposite to bus0->bus1 direction
    if len(pairs) >= 2 and bus0_pos and bus1_pos:
        ls_start = pairs[0]
        d_start_b0 = (ls_start[0] - bus0_pos[0])**2 + (ls_start[1] - bus0_pos[1])**2
        d_start_b1 = (ls_start[0] - bus1_pos[0])**2 + (ls_start[1] - bus1_pos[1])**2
        if d_start_b1 < d_start_b0:
            interior = interior[::-1]
    flat = []
    for lon, lat in interior:
        flat.append(f"{round(lon, 6)}")
        flat.append(f"{round(lat, 6)}")
    return " " + " ".join(flat)


# ---------------------------------------------------------------------------
# Read buses
# ---------------------------------------------------------------------------

buses = read_csv("buses.csv")
bus_ids = sorted(set(b["bus_id"] for b in buses))
id_map = {bid: idx for idx, bid in enumerate(bus_ids, 1)}
bus_coords = {}
for b in buses:
    bus_coords[b["bus_id"]] = (b["x"], b["y"])

# ---------------------------------------------------------------------------
# Read branches with geometry from raw lines
# ---------------------------------------------------------------------------

def read_branches_raw(filename, bus0_idx=1, bus1_idx=2):
    """Read CSV raw to get bus0, bus1 and geometry."""
    branches = []
    with open(here / filename, encoding="utf-8") as f:
        header = next(f)
        for line in f:
            fields = line.split(",", max(bus0_idx, bus1_idx) + 1)
            bus0 = fields[bus0_idx]
            bus1 = fields[bus1_idx]
            b0_pos = bus_coords.get(bus0)
            b1_pos = bus_coords.get(bus1)
            b0_xy = (float(b0_pos[0]), float(b0_pos[1])) if b0_pos else None
            b1_xy = (float(b1_pos[0]), float(b1_pos[1])) if b1_pos else None
            waypoints = parse_waypoints(line, b0_xy, b1_xy)
            branches.append((bus0, bus1, waypoints))
    return branches


lines_raw = read_branches_raw("lines.csv")
links_raw = read_branches_raw("links.csv")
converters_raw = read_branches_raw("converters.csv")
transformers = read_csv("transformers.csv")

# ---------------------------------------------------------------------------
# Build .lat
# ---------------------------------------------------------------------------

vertices = []
for bid in bus_ids:
    lon, lat = bus_coords[bid]
    vertices.append(f"{id_map[bid]} {round(float(lon), 6)} {round(float(lat), 6)}")

# Edges
edges = []
for bus0, bus1, waypoints in lines_raw:
    edges.append(f"{id_map[bus0]} {id_map[bus1]}{waypoints}")

for xf in transformers:
    edges.append(f"{id_map[xf['bus0']]} {id_map[xf['bus1']]}")

for bus0, bus1, waypoints in links_raw:
    edges.append(f"{id_map[bus0]} {id_map[bus1]}{waypoints}")

for bus0, bus1, waypoints in converters_raw:
    edges.append(f"{id_map[bus0]} {id_map[bus1]}{waypoints}")

out = "[vertices]\n" + "\n".join(vertices) + "\n\n[edges]\n" + "\n".join(edges) + "\n"

outpath = here / "europe.lat"
outpath.write_text(out, encoding="utf-8")
print(f"Wrote {len(vertices)} vertices, {len(edges)} edges -> {outpath}")
