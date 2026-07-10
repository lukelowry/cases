"""
Convert Europe V1 CSVs to an enriched GridKit JSON case file.

The .lat file remains the topology source of truth. This script merges CSV
metadata onto that topology so bus numbering, branch order, and polylines stay
aligned with Europe.lat.
"""

import csv
import json
import re
from pathlib import Path

here = Path(__file__).parent


def read_csv(name):
    with open(here / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, quotechar="'", skipinitialspace=True))


def read_lat(name):
    vertices = []
    edges = []
    section = None
    with open(here / name, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line == "[vertices]":
                section = "vertices"
                continue
            if line == "[edges]":
                section = "edges"
                continue

            parts = line.split()
            if section == "vertices":
                if len(parts) != 3:
                    raise ValueError(f"Invalid vertex row in {name}: {line}")
                vertices.append({
                    "number": int(parts[0]),
                    "longitude": float(parts[1]),
                    "latitude": float(parts[2]),
                })
            elif section == "edges":
                if len(parts) < 2:
                    raise ValueError(f"Invalid edge row in {name}: {line}")
                coords = [float(value) for value in parts[2:]]
                if len(coords) % 2:
                    raise ValueError(f"Odd polyline coordinate count in {name}: {line}")
                polyline = [
                    [coords[i], coords[i + 1]]
                    for i in range(0, len(coords), 2)
                ]
                edges.append({
                    "bus1": int(parts[0]),
                    "bus2": int(parts[1]),
                    "polyline": polyline,
                })
            else:
                raise ValueError(f"Row before section header in {name}: {line}")
    return vertices, edges


def to_bool(value):
    return str(value or "").strip().lower() in ("true", "t", "1")


def opt_float(value):
    text = str(value or "").strip()
    if not text:
        return None
    return float(text)


def opt_int(value):
    text = str(value or "").strip()
    if not text:
        return None
    return int(text)


def length_m(value):
    parsed = opt_float(value)
    return round(parsed) if parsed is not None else None


def country_from_tags(tags):
    match = re.search(r'"country"=>"([^"]*)"', tags or "")
    if not match:
        return None
    country = match.group(1).strip()
    return country or None


def clean(values):
    return {key: value for key, value in values.items() if value is not None and value != ""}


def branch_params():
    return {"R": 0.0, "X": 0.0, "G": 0.0, "B": 0.0}


def validate_edge(index, source_bus0, source_bus1, source_id):
    expected = (id_map[int(source_bus0)], id_map[int(source_bus1)])
    actual = (lat_edges[index]["bus1"], lat_edges[index]["bus2"])
    if actual != expected:
        raise ValueError(
            f"Edge {index} ({source_id}) maps to {expected}, "
            f"but Europe.lat has {actual}"
        )


def branch_device(index, source_kind, source_id, extension, params=None):
    edge = lat_edges[index]
    ext = {
        "source_kind": source_kind,
        "source_id": str(source_id),
    }
    if edge["polyline"]:
        ext["polyline"] = edge["polyline"]
    ext.update(clean(extension))
    return {
        "class": "Branch",
        "id": f"BR_{index}",
        "ports": {"bus1": edge["bus1"], "bus2": edge["bus2"]},
        "params": params or branch_params(),
        "extension": ext,
    }


lat_vertices, lat_edges = read_lat("europe.lat")
buses = read_csv("buses.csv")
lines = read_csv("lines.csv")
transformers = read_csv("transformers.csv")
links = read_csv("links.csv")

bus_rows = {int(row["bus_id"]): row for row in buses}
bus_ids = sorted(bus_rows)
id_map = {bus_id: index for index, bus_id in enumerate(bus_ids, 1)}

if len(lat_vertices) != len(bus_ids):
    raise ValueError(f"Europe.lat has {len(lat_vertices)} buses, CSV has {len(bus_ids)}")

expected_edges = len(lines) + len(transformers) + len(links)
if len(lat_edges) != expected_edges:
    raise ValueError(f"Europe.lat has {len(lat_edges)} edges, CSV has {expected_edges}")


json_buses = []
for index, source_bus_id in enumerate(bus_ids):
    vertex = lat_vertices[index]
    if vertex["number"] != id_map[source_bus_id]:
        raise ValueError(
            f"Vertex {index} is numbered {vertex['number']}, "
            f"expected {id_map[source_bus_id]} for source bus {source_bus_id}"
        )

    row = bus_rows[source_bus_id]
    voltage_kv = opt_float(row.get("voltage"))
    extension = clean({
        "longitude": vertex["longitude"],
        "latitude": vertex["latitude"],
        "station_id": opt_int(row.get("station_id")),
        "voltage_kv": voltage_kv,
        "dc": to_bool(row.get("dc")),
        "symbol": row.get("symbol"),
        "country": country_from_tags(row.get("tags")),
        "under_construction": to_bool(row.get("under_construction")),
    })
    bus = {
        "number": vertex["number"],
        "class": "bus",
        "name": str(source_bus_id),
        "init": {},
        "extension": extension,
    }
    if voltage_kv is not None:
        bus["v_base"] = voltage_kv * 1e3
    json_buses.append(bus)


json_devices = []
edge_index = 0

for row in lines:
    validate_edge(edge_index, row["bus0"], row["bus1"], row["line_id"])
    voltage_kv = opt_float(row.get("voltage"))
    json_devices.append(branch_device(
        edge_index,
        "line",
        row["line_id"],
        {
            "voltage_kv": voltage_kv,
            "circuits": opt_int(row.get("circuits")),
            "length_m": length_m(row.get("length")),
            "underground": to_bool(row.get("underground")),
            "under_construction": to_bool(row.get("under_construction")),
        },
    ))
    edge_index += 1

for row in transformers:
    validate_edge(edge_index, row["bus0"], row["bus1"], row["transformer_id"])
    json_devices.append(branch_device(
        edge_index,
        "transformer",
        row["transformer_id"],
        {
            "xfmr": True,
        },
    ))
    edge_index += 1

for row in links:
    validate_edge(edge_index, row["bus0"], row["bus1"], row["link_id"])
    json_devices.append(branch_device(
        edge_index,
        "link",
        row["link_id"],
        {
            "dc": True,
            "length_m": length_m(row.get("length")),
            "underground": to_bool(row.get("underground")),
            "under_construction": to_bool(row.get("under_construction")),
        },
    ))
    edge_index += 1


case = {
    "header": {
        "format_version": 0,
        "format_revision": 1,
        "case_name": "Europe",
        "case_description": "European transmission network from GridKit open data (Europe V1).",
        "case_comments": (
            "Merged from Europe V1 CSV metadata and Europe.lat topology. "
            "V1 source data does not include real branch impedances, so R/X/G/B are zeroed."
        ),
        "freq_base": 50.0,
        "va_base": 100e6,
    },
    "buses": json_buses,
    "signals": [],
    "devices": json_devices,
}

outpath = here / "europe.case.json"
with outpath.open("w", encoding="utf-8", newline="\n") as f:
    json.dump(case, f, indent=2)
    f.write("\n")

print(f"Wrote {len(json_buses)} buses, {len(json_devices)} devices -> {outpath}")
print(f"  devices: {len(lines)} lines + {len(transformers)} transformers + {len(links)} links")
