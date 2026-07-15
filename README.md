# Power System Case Repository

A collection of power system simulation cases for PowerWorld Simulator, PSS/E, PSLF, and MATPOWER. Large files are stored with Git LFS.

## Contents

- [IEEE/](IEEE/): standard IEEE test cases (IEEE39)
- [Synthetic/](Synthetic/): synthetic grid models (ACTIVSg200 through ACTIVSg70k, Texas2k, Texas7k, Hawaii40, Memphis, Midwest24k, Poland2746, EastWest, USA)
- [Other/](Other/): additional cases (EuropeV1, EuropeV2, GIC20, TwoArea, UIUC150, WECC240)

## Conventions

Each case lives in its own folder, and the folder name is the base name of every file in it. For example:

```
Synthetic/USA/
    README.md          case notes: description, vintage, provenance
    USA.pwb            PowerWorld case
    USA.pwd            PowerWorld oneline
    USA.raw            PSS/E
    USA.epc            PSLF
    USA.lat            Lattice
    USA.case.json      GridKit
    upstream/          original distribution files, kept as received
```

Rules:

1. Primary files are named Base.ext with lowercase extensions.
2. Secondary files are named Base.qualifier.ext, for example Texas7k.gnet.idv and ACTIVSg2000.contingencies.aux.
3. Paths contain no spaces or brackets. Dates and versions are recorded in each case README, not in filenames.
4. variants/ holds alternate builds named Base.VariantName.ext, for example WECC240.SimpleDynamics.pwb, so files identify their grid out of context.
5. upstream/ holds original distribution files. MATPOWER .m files keep their original names so MATLAB function names still match.
6. tools/ holds case-specific build scripts. Shared scripts live in [scripts/](scripts/).

## File Formats

| Extension | Description |
|-----------|-------------|
| .raw | PSS/E power flow data |
| .epc | PSLF powerflow case |
| .pwb | PowerWorld binary case |
| .pwd | PowerWorld oneline display |
| .lat | Lattice case |
| .case.json | GridKit-format case data (graph schema) |
| .dyr | PSS/E dynamic model data |
| .dyd | PSLF dynamic model data |
| .aux | PowerWorld auxiliary file |
| .m | MATPOWER / MATLAB case |
| .gic | GIC (geomagnetically induced current) data |
| .con | Contingency data |
| .idv | PowerWorld script file |
| .bsg | PowerWorld base generation |
| .tsb | PowerWorld transient stability |

## File Index

See [INDEX.md](INDEX.md) for a complete listing of all files organized by type. To regenerate it after adding or removing files:

```
python scripts/generate_index.py
```
