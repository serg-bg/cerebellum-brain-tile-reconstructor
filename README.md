# Brain Tile Reconstructor

Stitch together brain tissue regions from our 1,246 individual microscopy tiles.

*Built in collaboration for Morgane Marie and Baptiste Philippot.*

## What it does

Takes specific regions from the cerebellum tile dataset and combines them into single images ready for analysis. Works with the 32×25 grid of tiles we extracted, handling both channels and all 19 z-slices.

## For Collaborators - Getting Started

### Step 1: Clone the Repository
```bash
# Clone to your local machine
git clone https://github.com/[your-username]/cerebellum-brain-tile-reconstructor.git
cd cerebellum-brain-tile-reconstructor
```

### Step 2: Install Prerequisites
- **Install uv package manager**: https://docs.astral.sh/uv/#installation
- **Python 3.9+** (usually already installed)

### Step 3: Set Up Environment
```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate  # Mac/Linux
# OR
.venv\Scripts\activate.bat  # Windows cmd
# OR  
.venv\Scripts\Activate.ps1  # Windows PowerShell

# Install dependencies and the tool
uv sync
uv pip install -e .
```

### Step 4: Test Installation
```bash
tile-stitcher --help
```
You should see help text. If you get errors, check the [troubleshooting guide](docs/getting-started.md#troubleshooting).

## Basic usage

```bash
# See what's available
tile-stitcher explore --grid

# Make a small test region (3x3 tiles)
tile-stitcher stitch --region y005:008,x008:011 --output test_region.tif --force
```

That creates a ~200MB TIFF file ready for ImageJ or napari.

## Documentation

Everything else is in [`docs/getting-started.md`](docs/getting-started.md):
- Step-by-step installation help
- Detailed examples with working coordinates  
- Troubleshooting common issues
- Memory management tips
- Sharing regions between collaborators

## Dataset structure

- **1,246 tiles** in 32×25 grid (y:0-31, x:0-24)
- **2 channels** per location with different imaging conditions
- **19 z-slices** per tile, 1024×1024 pixels each
- **~45MB per tile**, both TIFF and OME-Zarr formats available

## Quick examples

```bash
# Medium region for analysis (5x5 tiles, ~400MB)
tile-stitcher stitch --region y010:015,x008:013 --output analysis.tif --force

# Compare channels from same region
tile-stitcher stitch --region y012:017,x010:015 --channel 0 --output region_c0.tif --force
tile-stitcher stitch --region y012:017,x010:015 --channel 1 --output region_c1.tif --force
```

For anything beyond basic usage, see the [complete guide](docs/getting-started.md).

## Common Issues

### "ModuleNotFoundError: No module named 'distributed'"
If you get this error when running conversion scripts:
```bash
# Fix with:
uv pip install "dask[distributed]" --upgrade
# or
pip install "dask[distributed]" --upgrade
```

### "ModuleNotFoundError: No module named 'termios'" (Windows)
This is now fixed in the latest version. Update with:
```bash
git pull origin main
uv pip install -e . --force-reinstall
```

### Need Help?
- Check the [detailed troubleshooting guide](docs/getting-started.md#troubleshooting)
- Contact: Sergio Bernal-Garcia <smb2318@columbia.edu>

---

Sergio Bernal-Garcia <smb2318@columbia.edu>
