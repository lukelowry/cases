"""Convert Europe V2 CSVs to a consolidated GridKit JSON case file."""

import csv
import json
from pathlib import Path

here = Path(__file__).parent


def read_csv(name):
    with open(here / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_bool(val):
    return val.strip().lower() in ("true", "t", "1")


def opt_float(val):
    if val and val.strip():
        return float(val)
    return None


def opt_int(val):
    if val and val.strip():
        return int(val)
    return None


# ---------------------------------------------------------------------------
# Read sources
# ---------------------------------------------------------------------------

buses = read_csv("buses.csv")
lines = read_csv("lines.csv")
transformers = read_csv("transformers.csv")
links = read_csv("links.csv")
converters = read_csv("converters.csv")

# ---------------------------------------------------------------------------
# Build buses array
# ---------------------------------------------------------------------------

json_buses = []
for b in sorted(buses, key=lambda x: x["bus_id"]):
    entry = {
        "number": b["bus_id"],
        "class": "bus",
        "init": {"Vr": 1.0, "Vi": 0.0},
    }
    voltage = opt_float(b.get("voltage"))
    if voltage is not None:
        entry["v_base"] = voltage * 1e3

    ext = {
        "lon": float(b["x"]),
        "lat": float(b["y"]),
        "symbol": b.get("symbol") or None,
        "country": b.get("country") or None,
    }
    if to_bool(b.get("dc", "f")):
        ext["dc"] = True
    if to_bool(b.get("under_construction", "f")):
        ext["planned"] = True
    entry["extension"] = ext
    json_buses.append(entry)

# ---------------------------------------------------------------------------
# Build devices array
# ---------------------------------------------------------------------------

json_devices = []

# Lines — have R, X, B (no G in source data)
for ln in lines:
    device = {
        "class": "Branch",
        "ports": {"bus1": ln["bus0"], "bus2": ln["bus1"]},
        "id": ln["line_id"],
        "params": {
            "R": opt_float(ln.get("r")) or 0.0,
            "X": opt_float(ln.get("x")) or 0.0,
            "G": 0.0,
            "B": opt_float(ln.get("b")) or 0.0,
        },
    }
    ext = {
        "circuits": opt_int(ln.get("circuits")),
        "length_m": round(float(ln["length"])) if ln.get("length") else None,
        "underground": to_bool(ln.get("underground", "f")),
        "i_nom": opt_float(ln.get("i_nom")),
        "s_nom": opt_float(ln.get("s_nom")),
        "type": ln.get("type") or None,
    }
    voltage = opt_float(ln.get("voltage"))
    if voltage is not None:
        ext["v_base"] = voltage * 1e3
    if to_bool(ln.get("under_construction", "f")):
        ext["planned"] = True
    device["extension"] = ext
    json_devices.append(device)

# Transformers
for xf in transformers:
    device = {
        "class": "Branch",
        "ports": {"bus1": xf["bus0"], "bus2": xf["bus1"]},
        "id": xf["transformer_id"],
        "params": {"R": 0.0, "X": 0.0, "G": 0.0, "B": 0.0},
        "extension": {
            "xfmr": True,
            "voltage_bus0": opt_float(xf.get("voltage_bus0")),
            "voltage_bus1": opt_float(xf.get("voltage_bus1")),
            "s_nom": opt_float(xf.get("s_nom")),
        },
    }
    json_devices.append(device)

# Links (HVDC)
for lk in links:
    device = {
        "class": "Branch",
        "ports": {"bus1": lk["bus0"], "bus2": lk["bus1"]},
        "id": lk["link_id"],
        "params": {"R": 0.0, "X": 0.0, "G": 0.0, "B": 0.0},
    }
    ext = {
        "dc": True,
        "p_nom": opt_float(lk.get("p_nom")),
        "length_m": round(float(lk["length"])) if lk.get("length") else None,
        "underground": to_bool(lk.get("underground", "f")),
    }
    voltage = opt_float(lk.get("voltage"))
    if voltage is not None:
        ext["v_base"] = voltage * 1e3
    if to_bool(lk.get("under_construction", "f")):
        ext["planned"] = True
    device["extension"] = ext
    json_devices.append(device)

# Converters (AC/DC)
for cv in converters:
    device = {
        "class": "Branch",
        "ports": {"bus1": cv["bus0"], "bus2": cv["bus1"]},
        "id": cv["converter_id"],
        "params": {"R": 0.0, "X": 0.0, "G": 0.0, "B": 0.0},
    }
    ext = {
        "converter": True,
        "p_nom": opt_float(cv.get("p_nom")),
    }
    voltage = opt_float(cv.get("voltage"))
    if voltage is not None:
        ext["v_base"] = voltage * 1e3
    device["extension"] = ext
    json_devices.append(device)

# ---------------------------------------------------------------------------
# Assemble and write
# ---------------------------------------------------------------------------

case = {
    "header": {
        "format_version": 0,
        "format_revision": 1,
        "case_name": "Europe GridKit V2",
        "case_description": "European transmission network from GridKit open data (V2)",
        "case_comments": "Includes R/X/B for lines; transformer and link impedances not available",
        "freq_base": 50.0,
        "va_base": 100e6,
    },
    "buses": json_buses,
    "signals": [],
    "devices": json_devices,
}

outpath = here / "europe.json"
outpath.write_text(json.dumps(case, indent=2), encoding="utf-8")

print(f"Wrote {len(json_buses)} buses, {len(json_devices)} devices "
      f"({len(lines)} lines + {len(transformers)} xfmrs + {len(links)} links + {len(converters)} converters)")
print(f"  -> {outpath}")
