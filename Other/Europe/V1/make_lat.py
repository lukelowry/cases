"""Convert Europe V1 CSVs (buses, lines, transformers, links) to a .lat file."""

import csv
import re
from pathlib import Path

here = Path(__file__).parent


def read_csv(name):
    with open(here / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_buses():
    """Parse buses.csv manually — the tags column contains commas inside
    single quotes which breaks the standard csv reader."""
    buses = {}
    with open(here / "buses.csv", encoding="utf-8") as f:
        next(f)  # skip header
        for line in f:
            parts = line.strip().rsplit(",", 2)
            bus_id = int(parts[0].split(",", 1)[0])
            lon, lat = parts[1], parts[2]
            buses[bus_id] = (lon, lat)
    return buses


def parse_waypoints(raw_line, bus0_pos, bus1_pos):
    """Extract intermediate waypoints from a LINESTRING in the raw CSV line.
    Returns coordinate string (lon lat pairs) with first and last points
    stripped, since those match the bus vertices.
    Reverses interior points when the LINESTRING runs bus1->bus0."""
    m = re.search(r"LINESTRING\(([^)]+)\)", raw_line)
    if not m:
        return ""
    pairs = []
    for p in m.group(1).split(","):
        parts = p.strip().split()
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


def read_branches_with_geometry(filename):
    """Read a CSV file raw to get bus0, bus1, and geometry from each row."""
    branches = []
    with open(here / filename, encoding="utf-8") as f:
        next(f)  # skip header
        for line in f:
            fields = line.split(",", 3)
            # fields[0] = id, fields[1] = bus0, fields[2] = bus1
            bus0 = int(fields[1])
            bus1 = int(fields[2])
            b0_pos = bus_coords.get(bus0)
            b1_pos = bus_coords.get(bus1)
            b0_xy = (float(b0_pos[0]), float(b0_pos[1])) if b0_pos else None
            b1_xy = (float(b1_pos[0]), float(b1_pos[1])) if b1_pos else None
            waypoints = parse_waypoints(line, b0_xy, b1_xy)
            branches.append((bus0, bus1, waypoints))
    return branches


bus_coords = read_buses()
lines_raw = read_branches_with_geometry("lines.csv")
links_raw = read_branches_with_geometry("links.csv")
transformers = read_csv("transformers.csv")

# Sequential 1-indexed mapping
bus_ids = sorted(bus_coords)
id_map = {bid: idx for idx, bid in enumerate(bus_ids, 1)}

vertices = []
for bid in bus_ids:
    lon, lat = bus_coords[bid]
    vertices.append(f"{id_map[bid]} {round(float(lon), 6)} {round(float(lat), 6)}")

# Consolidate all branches
edges = []
for bus0, bus1, waypoints in lines_raw:
    edges.append(f"{id_map[bus0]} {id_map[bus1]}{waypoints}")
for xf in transformers:
    edges.append(f"{id_map[int(xf['bus0'])]} {id_map[int(xf['bus1'])]}")
for bus0, bus1, waypoints in links_raw:
    edges.append(f"{id_map[bus0]} {id_map[bus1]}{waypoints}")

out = "[vertices]\n" + "\n".join(vertices) + "\n\n[edges]\n" + "\n".join(edges) + "\n"

outpath = here / "europe.lat"
outpath.write_text(out, encoding="utf-8")
print(f"Wrote {len(vertices)} vertices, {len(edges)} edges -> {outpath}")
