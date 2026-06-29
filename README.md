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

- Two or more jointed components that can still be dragged are not detected (will fix)
- Cannot detect warnings/errors in timeline (works as intended)

## Installation Instructions

First, download all code in this repository as a ZIP file. After extraction, open any Fusion 360 design file, select the Utilities tab, then click "Scripts and Add-Ins." Ensure the name of the folder is "AlphaScan," then click the plus sign and select the script folder. After selecting "Open" or "Select Folder" in the popup file browser, AlphaScan is ready to run in the plugin dialog.

## Release History

### Release Alpha 1.0 (6/29/2026)

First release!
