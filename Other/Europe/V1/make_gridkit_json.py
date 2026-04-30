"""
Convert Europe V1 GridKit CSVs to a consolidated GridKit JSON case file.

Produces a JSON following the Grid Dynamics case format with:
  - header: case metadata
  - buses: one entry per bus with coordinates and voltage base
  - devices: consolidated Branch devices from lines, transformers, and links
"""

import csv
import json
import re
from pathlib import Path

here = Path(__file__).parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_csv(name):
    with open(here / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_buses():
    """Parse buses.csv with manual handling for the tags column
    (contains commas inside single quotes)."""
    buses = {}
    with open(here / "buses.csv", encoding="utf-8") as f:
        next(f)  # skip header
        for line in f:
            # x,y are always the last two fields
            rest, lon, lat = line.strip().rsplit(",", 2)
            fields = rest.split(",", 6)  # bus_id, station_id, voltage, dc, symbol, under_construction, tags...
            bus_id = int(fields[0])
            station_id = int(fields[1]) if fields[1] else None
            voltage = float(fields[2]) if fields[2] else None
            dc = fields[3].strip() == "t"
            symbol = fields[4].strip() if len(fields) > 4 else ""
            under_construction = fields[5].strip() == "t" if len(fields) > 5 else False
            # Extract country from tags
            country_match = re.search(r'"country"=>"([^"]*)"', rest)
            country = country_match.group(1) if country_match else None
            buses[bus_id] = {
                "lon": float(lon),
                "lat": float(lat),
                "voltage_kv": voltage,
                "dc": dc,
                "substation": station_id,
                "symbol": symbol,
                "under_construction": under_construction,
                "country": country,
            }
    return buses


def to_bool(val):
    return val.strip().lower() in ("true", "t", "1")


# ---------------------------------------------------------------------------
# Read sources
# ---------------------------------------------------------------------------

bus_data = read_buses()
lines = read_csv("lines.csv")
transformers = read_csv("transformers.csv")
links = read_csv("links.csv")

# ---------------------------------------------------------------------------
# Build buses array
# ---------------------------------------------------------------------------

json_buses = []
for bus_id in sorted(bus_data):
    b = bus_data[bus_id]
    entry = {
        "number": bus_id,
        "class": "bus",
        "init": {"Vr": 1.0, "Vi": 0.0},
    }
    if b["voltage_kv"] is not None:
        entry["v_base"] = b["voltage_kv"] * 1e3  # kV -> V
    ext = {
        "lon": b["lon"],
        "lat": b["lat"],
        "substation": b["substation"],
        "symbol": b["symbol"] or None,
        "country": b["country"],
    }
    if b["dc"]:
        ext["dc"] = True
    if b["under_construction"]:
        ext["planned"] = True
    entry["extension"] = ext
    json_buses.append(entry)

# ---------------------------------------------------------------------------
# Build devices array — all branches consolidated
# ---------------------------------------------------------------------------

json_devices = []

for ln in lines:
    device = {
        "class": "Branch",
        "ports": {"bus1": int(ln["bus0"]), "bus2": int(ln["bus1"])},
        "id": str(ln["line_id"]),
        "params": {"R": 0.0, "X": 0.0, "G": 0.0, "B": 0.0},
    }
    ext = {
        "circuits": int(ln["circuits"]) if ln["circuits"] else None,
        "length_m": round(float(ln["length"])) if ln["length"] else None,
        "underground": to_bool(ln["underground"]),
    }
    if ln["voltage"]:
        ext["v_base"] = float(ln["voltage"]) * 1e3
    if to_bool(ln["under_construction"]):
        ext["planned"] = True
    device["extension"] = ext
    json_devices.append(device)

for xf in transformers:
    device = {
        "class": "Branch",
        "ports": {"bus1": int(xf["bus0"]), "bus2": int(xf["bus1"])},
        "id": str(xf["transformer_id"]),
        "params": {"R": 0.0, "X": 0.0, "G": 0.0, "B": 0.0},
        "extension": {"xfmr": True},
    }
    json_devices.append(device)

for lk in links:
    device = {
        "class": "Branch",
        "ports": {"bus1": int(lk["bus0"]), "bus2": int(lk["bus1"])},
        "id": str(lk["link_id"]),
        "params": {"R": 0.0, "X": 0.0, "G": 0.0, "B": 0.0},
    }
    ext = {
        "dc": True,
        "length_m": round(float(lk["length"])) if lk["length"] else None,
        "underground": to_bool(lk["underground"]),
    }
    if to_bool(lk["under_construction"]):
        ext["planned"] = True
    device["extension"] = ext
    json_devices.append(device)

# ---------------------------------------------------------------------------
# Assemble and write
# ---------------------------------------------------------------------------

case = {
    "header": {
        "format_version": 0,
        "format_revision": 1,
        "case_name": "Europe GridKit V1",
        "case_description": "European transmission network from GridKit open data",
        "case_comments": "Topology only — R/X/G/B parameters are zeroed (not available in source data)",
        "freq_base": 50.0,
        "va_base": 100e6,
    },
    "buses": json_buses,
    "signals": [],
    "devices": json_devices,
}

outpath = here / "europe.case.json"
outpath.write_text(json.dumps(case, indent=2), encoding="utf-8")

print(f"Wrote {len(json_buses)} buses, {len(json_devices)} devices "
      f"({len(lines)} lines + {len(transformers)} xfmrs + {len(links)} links)")
print(f"  -> {outpath}")
