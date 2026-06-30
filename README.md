# AlphaScan

AlphaScan is a Fusion 360 script that scans your CAD for mistakes.

## Features

- Detects sketches that are not fully constrained
- Detects invalid components
- Detects bodies without edges or volume
- Detects components that are not secured
- Detects empty components (no bodies)
- Detects M4 and 14mm bearing holes that have insufficient clearance (0.2 mm diametrical)
- Detects out-of-date references

## Known Issues

- Two or more jointed components that are still floating as an "island" are not detected (created Alpha 1.0, will not fix as of Alpha 1.2)
- Cannot detect warnings/errors in timeline (created Alpha 1.0, works as intended as of Alpha 1.0)

## Installation Instructions

First, download all code in this repository as a ZIP file. After extraction, open any Fusion 360 design file, select the Utilities tab, then click "Scripts and Add-Ins." Ensure the name of the folder is "AlphaScan," then click the plus sign and select the script folder. After selecting "Open" or "Select Folder" in the popup file browser, AlphaScan is ready to run in the plugin dialog.

## Release History

### Patch Alpha 1.2 (6/29/2026)

Converted to Add-In with custom button. \
Added forced updates. \
Clarified which references are out of date. \
Fixed bearing hole name in config. \
Fixed 'No hole issues' showing with hole issues.

### Hotfix Alpha 1.1 (6/29/2026)

Fixed issue where edge.radius reports size in centimeters. \
Added config.json and organized assets.

### Release Alpha 1.0 (6/29/2026)

First release!
