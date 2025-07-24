# Brain Tissue Analysis Pipeline

Complete workflow to process large cerebellum microscopy data: from original scan → individual tiles → reconstructed regions for analysis.

*Built in collaboration for Morgane Marie and Baptiste Philippot.*

## What this pipeline does

Converts your large brain microscopy file (`.czi` format) into manageable pieces, then lets you reconstruct specific regions for analysis:

1. **Convert** large CZI microscopy file → accessible OME-Zarr format 
2. **Extract** 1,246 individual brain tissue tiles (1024×1024 pixels each)
3. **Reconstruct** any region you choose → single image file ready for ImageJ/napari

**Perfect for researchers who need specific brain regions without loading 126GB+ files.**

## Complete Workflow Overview

**You'll need**: Your original `Morgane_BP_Cerebellum_Stitch.czi` microscopy file (~126GB) and a computer with 8GB+ RAM.

**The process**: 3 main steps that you run once, then reconstruct regions as needed.

| Step | What it does | Time | Output |
|------|-------------|------|---------|
| 1. **Convert** | CZI → OME-Zarr format | ~2 hours | `.ome.zarr` file |
| 2. **Extract** | OME-Zarr → 1,246 tiles | ~30 min | `tiles/` folder |
| 3. **Reconstruct** | Select tiles → analysis image | ~1 min | `.tif` file |

*Steps 1-2 are one-time setup. Step 3 you'll use repeatedly for different brain regions.*

## Setup (First Time Only)

### Get the Code
```bash
# Clone to your local machine  
git clone https://github.com/serg-bg/cerebellum-brain-tile-reconstructor.git
cd cerebellum-brain-tile-reconstructor
```

### Install Requirements
1. **Install uv package manager**: https://docs.astral.sh/uv/#installation  
2. **Python 3.9+** (usually already installed)

### Setup Environment
```bash
# Create virtual environment and install everything
uv venv
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate.bat  # Windows

uv sync
uv pip install -e .
```

### Test It Works
```bash
tile-stitcher --help
```
✅ You should see help text. If errors, see [troubleshooting](#common-issues).

## The 3-Step Process

### Step 1: Convert CZI → OME-Zarr (~2 hours)
```bash
# Put your CZI file in the project folder, then:
python convert_czi_to_ome_zarr_optimized.py
```
**What this does**: Converts your large CZI microscopy file to OME-Zarr format that Python can work with efficiently.  
**Output**: `Morgane_BP_Cerebellum_Stitch.ome.zarr/` folder  
**Progress**: You'll see CPU usage, memory stats, and processing updates.

### Step 2: Extract Individual Tiles (~30 minutes)  
```bash
# Extract 1,246 brain tissue tiles from the converted file
python scripts/napari_roi_extractor.py Morgane_BP_Cerebellum_Stitch.ome.zarr --tiles --output tiles/
```
**What this does**: Scans the brain image and saves only regions with actual tissue as individual 1024×1024 tiles.  
**Output**: `tiles/` folder with 1,246 tile folders  
**Progress**: Shows tile extraction progress and skips empty regions.

### Step 3: Reconstruct Brain Regions (~ 1 minute each)
```bash
# See what regions are available
tile-stitcher explore --grid

# Create your first brain reconstruction (3x3 tiles)
tile-stitcher stitch --region y015:018,x010:013 --output my_brain_region.tif --force
```
**What this does**: Combines specific tiles back into a single image file ready for analysis.  
**Output**: TIFF file compatible with ImageJ, Fiji, napari, etc.  
**Result**: ~200MB file with 19 depth layers of brain tissue.

## Quick Examples After Setup

```bash
# Small test region (good for first try)
tile-stitcher stitch --region y005:008,x008:011 --output test_region.tif --force

# Medium analysis region  
tile-stitcher stitch --region y010:015,x008:013 --output analysis_region.tif --force

# Compare different channels from same region
tile-stitcher stitch --region y012:017,x010:015 --channel 0 --output region_c0.tif --force
tile-stitcher stitch --region y012:017,x010:015 --channel 1 --output region_c1.tif --force
```

## What You Get

**Final result**: Individual TIFF files with your chosen brain regions, ready for:
- **ImageJ/Fiji**: Double-click to open, all 19 z-slices included
- **napari**: `napari my_brain_region.tif` for 3D visualization  
- **Analysis software**: Standard TIFF format works everywhere

**Data specs**: 32×25 tile grid, 2 channels, 19 z-slices per tile, 1024×1024 pixels each.

---

## Common Issues

### "No such file: Morgane_BP_Cerebellum_Stitch.czi"
```bash
# Make sure your CZI file is in the project folder with exact name:
ls -la Morgane_BP_Cerebellum_Stitch.czi
```

### "ModuleNotFoundError: No module named 'distributed'"  
```bash
# Fix missing dependency:
uv pip install "dask[distributed]" --upgrade
```

### "Out of memory" during conversion
```bash  
# Close other programs and try again, or contact Sergio for tips
```

### Need Help?
- **Complete guide**: [`docs/getting-started.md`](docs/getting-started.md)
- **Contact**: Sergio Bernal-Garcia <smb2318@columbia.edu>

---

*Built for Morgane Marie and Baptiste Philippot - Sergio Bernal-Garcia <smb2318@columbia.edu>*
