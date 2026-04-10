# Power System Case Repository

A collection of power system simulation cases for use with PowerWorld Simulator, PSS/E, PSLF, and MATPOWER.

## Contents

- **IEEE/** — Standard IEEE test cases (e.g., New England 39-Bus)
- **Synthetic/** — Synthetic grid models (ACTIVSg, Texas, Hawaii, Memphis, Midwest, Poland, USA, EastWest)
- **Other/** — Additional test cases (GIC 20-Bus, Two Area, UIUC 150, WECC 240)

## File Formats

| Extension | Description |
|-----------|-------------|
| `.raw` | PSS/E power flow data |
| `.epc` | PSLF powerflow case |
| `.pwb` | PowerWorld binary case |
| `.pwd` | PowerWorld oneline display |
| `.dyr` | PSS/E dynamic model data |
| `.dyd` | PSLF dynamic model data |
| `.aux` | PowerWorld auxiliary file |
| `.m` | MATPOWER / MATLAB case |
| `.gic` | GIC (geomagnetically induced current) data |

## File Index

See [INDEX.md](INDEX.md) for a complete listing of all files organized by type.

To regenerate the index after adding or removing files:

```
python scripts/generate_index.py
```
