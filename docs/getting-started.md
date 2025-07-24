# Complete Brain Tissue Analysis Guide

Step-by-step instructions to go from your original microscopy file to reconstructed brain regions, designed for researchers new to command-line tools.

## What This Complete Pipeline Does

Starting with your large `Morgane_BP_Cerebellum_Stitch.czi` microscopy file, this pipeline will:

1. **Convert** - Transform CZI format into accessible OME-Zarr format
2. **Extract** - Create 1,246 individual brain tissue tiles from the large image  
3. **Explore** - See what regions are available and where tissue is located
4. **Select** - Choose specific brain regions you want to analyze
5. **Reconstruct** - Combine tiles into single images ready for ImageJ/napari

## Before You Start

### What You Need
- **Your CZI file**: `Morgane_BP_Cerebellum_Stitch.czi` (~126GB)
- **Computer**: macOS, Linux, or Windows with 8GB+ RAM and 200GB+ free space
- **Time**: ~3 hours for first-time setup, then <1 minute per brain region
- **Software**: Python 3.9+ and uv package manager (we'll install these)

### Understanding the Process
This isn't a quick click-and-done tool. You'll run 3 commands that do heavy computational work:
1. **Step 1** (~2 hours): Convert CZI → OME-Zarr format
2. **Step 2** (~30 min): Extract brain tiles from OME-Zarr  
3. **Step 3** (~1 min each): Reconstruct specific regions as needed

*Steps 1-2 are one-time setup. Step 3 you'll use repeatedly.*

## First-Time Setup

### Open Your Terminal/Command Prompt
- **Mac**: Press `Cmd + Space`, type "Terminal", press Enter
- **Windows**: Press `Win + R`, type "cmd", press Enter  
- **Linux**: Press `Ctrl + Alt + T`

You'll see a window with text and a blinking cursor - this is where you'll type commands.

### Get the Code and Software
```bash
# Download the pipeline code
git clone https://github.com/serg-bg/cerebellum-brain-tile-reconstructor.git
cd cerebellum-brain-tile-reconstructor

# Install uv package manager (if you don't have it)
# Visit: https://docs.astral.sh/uv/#installation for instructions

# Create isolated environment and install everything
uv venv
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate.bat  # Windows

uv sync
uv pip install -e .
```

### Test Everything Works
```bash
tile-stitcher --help
python convert_czi_to_ome_zarr_optimized.py --help
```
✅ Both should show help text. If you get errors, see [troubleshooting](#troubleshooting).

## The Complete 3-Step Pipeline

**Important**: Make sure your `Morgane_BP_Cerebellum_Stitch.czi` file is in your project folder before starting.

### Step 1: Convert CZI to OME-Zarr (~2 hours)

```bash
# Make sure your CZI file is in the project folder
ls -la Morgane_BP_Cerebellum_Stitch.czi

# Start the conversion (this will take ~2 hours)
python convert_czi_to_ome_zarr_optimized.py
```

**What you'll see**:
- System info (CPU cores, memory)
- Processing progress with time estimates
- Memory usage statistics
- "Conversion complete!" when done

**Output**: A new folder called `Morgane_BP_Cerebellum_Stitch.ome.zarr/`

**What this does**: Converts your proprietary CZI microscopy file into an open OME-Zarr format that Python can efficiently process. The conversion creates multiple resolution levels for faster access.

### Step 2: Extract Brain Tissue Tiles (~30 minutes)

```bash
# Extract individual tiles from the converted file
python scripts/napari_roi_extractor.py Morgane_BP_Cerebellum_Stitch.ome.zarr --tiles --output tiles/
```

**What you'll see**:
- "Scanning image for tissue regions..."
- Progress bar showing tile extraction
- "Skipping empty regions" for areas without brain tissue
- "Extracted 1,246 tiles" when complete

**Output**: A new `tiles/` folder with 1,246 subfolders like `tile_y015_x010_c0/`

**What this does**: Scans your brain image in a 32×25 grid and saves only the 1024×1024 pixel regions that contain actual brain tissue. Skips empty space to save storage.

### Step 3: Your First Brain Reconstruction (~1 minute)

```bash
# See what brain regions are available  
tile-stitcher explore --grid

# Create a small test reconstruction (3x3 tiles)
tile-stitcher stitch --region y015:018,x010:013 --output my_first_brain_region.tif --force
```

**What you'll see**:
- Grid visualization showing available tiles
- "Reconstructing region: 3x3 tiles"
- Progress bar: "Stitching tiles"
- "Reconstruction complete: my_first_brain_region.tif"

**Output**: `my_first_brain_region.tif` (~200MB file)

**What this does**: Combines 9 individual tiles back into a single brain region image with all 19 depth layers, ready for ImageJ or napari analysis.

## Understanding What You Created

### Your Files After Setup
```
cerebellum-brain-tile-reconstructor/
├── Morgane_BP_Cerebellum_Stitch.czi           # Original microscopy file
├── Morgane_BP_Cerebellum_Stitch.ome.zarr/    # Converted format (Step 1)
├── tiles/                                     # 1,246 individual brain tiles (Step 2)
│   ├── tile_y000_x006_c0/
│   ├── tile_y000_x006_c1/
│   └── ... (1,244 more)
└── my_first_brain_region.tif                  # Your reconstruction (Step 3)
```

### Your Brain Region File
**`my_first_brain_region.tif`** contains:
- **Size**: 3072×3072 pixels (3×3 tiles of 1024 pixels each)
- **Depth**: 19 z-slices (layers through the tissue thickness)  
- **File size**: ~200MB
- **Compatible with**: ImageJ, Fiji, napari, MATLAB, Python, etc.

### How to View Your Results
- **Quick view**: Double-click the TIFF file (opens in system image viewer)
- **Scientific analysis**: 
  - **ImageJ**: File → Open → select your TIFF
  - **napari**: `napari my_first_brain_region.tif` 
  - **Python**: `tifffile.imread('my_first_brain_region.tif')`

## After Setup: Creating More Brain Regions

Once you've completed the 3-step setup, you can create brain regions quickly:

### Explore What's Available
```bash
# See the brain tissue grid (shows where tissue is present)
tile-stitcher explore --grid

# Get suggestions for good regions to reconstruct
tile-stitcher explore --suggest
```

### Small Test Regions (Good for Learning)
```bash
# 2x2 region (~120MB, 30 seconds)
tile-stitcher stitch --region y015:017,x010:012 --output small_region.tif --force

# 3x3 region (~200MB, 45 seconds)
tile-stitcher stitch --region y010:013,x008:011 --output test_region.tif --force
```

### Medium Analysis Regions (Good for Research)
```bash
# 5x5 region (~380MB, 2 minutes)
tile-stitcher stitch --region y012:017,x010:015 --output analysis_region.tif --force

# Save region selection for reuse
tile-stitcher select --region y020:025,x005:010 --save my_study_region.json
tile-stitcher stitch --load my_study_region.json --output study_data.tif --force
```

### Compare Different Channels
```bash
# Same region, different imaging conditions
tile-stitcher stitch --region y015:020,x010:015 --channel 0 --output region_channel0.tif --force
tile-stitcher stitch --region y015:020,x010:015 --channel 1 --output region_channel1.tif --force
```

## Understanding Brain Coordinates

Your brain tissue is organized in a **32×25 grid** (32 rows, 25 columns):

### Coordinate System
- **y-coordinates**: 0-31 (rows, top to bottom)
- **x-coordinates**: 0-24 (columns, left to right)  
- **Channels**: 0 and 1 (different imaging conditions)

### Region Format: `y[start]:[end],x[start]:[end]`
```bash
--region y015:018,x010:013
```
This means:
- **y015:018** = rows 15, 16, 17 (3 rows)
- **x010:013** = columns 10, 11, 12 (3 columns)  
- **Result**: 3×3 grid = 9 tiles total

### Quick Size Reference
| Region | Tiles | Pixels | File Size | Time |
|--------|-------|--------|-----------|------|
| 2×2 | 4 tiles | 2048×2048 | ~120MB | 30s |
| 3×3 | 9 tiles | 3072×3072 | ~200MB | 45s |
| 5×5 | 25 tiles | 5120×5120 | ~380MB | 2min |

### Channel Selection
- **Channel 0** (`--channel 0`): Default imaging condition
- **Channel 1** (`--channel 1`): Alternative imaging condition
- Most analyses start with channel 0

## File Management Tips

### Naming Your Output Files
Use descriptive names that include region info:
```bash
--output cerebellum_y010-015_x005-010_c0.tif
--output purkinje_layer_medium_region.tif
--output analysis_region_channel1.tif
```

### Saving and Sharing Selections
```bash
# Save a selection for later
tile-stitcher select --region y020:025,x010:015 --save purkinje_cells.json

# Share with colleague - they can use:
tile-stitcher stitch --load purkinje_cells.json --output colleague_analysis.tif --force
```

## Memory and Size Guidelines

### Region Size vs Resources Needed

| Region Size | Tiles | Memory Needed | Output Size | Time |
|-------------|-------|---------------|-------------|------|
| 2x2 tiles   | 4     | ~150MB        | ~120MB      | 30s  |
| 3x3 tiles   | 9     | ~300MB        | ~200MB      | 45s  |
| 5x5 tiles   | 25    | ~600MB        | ~380MB      | 2min |
| 8x8 tiles   | 64    | ~1.5GB        | ~950MB      | 5min |

Start small (2x2 or 3x3) for testing, then scale up.

## Troubleshooting by Step

### Setup Issues

**"Command not found: tile-stitcher"**
```bash
# Make sure you activated the environment
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate.bat  # Windows

# You should see (.venv) at the start of your command line
# If not, the environment isn't active
```

**"uv not found" or "git not found"**
- Install uv: https://docs.astral.sh/uv/#installation
- Install git: https://git-scm.com/downloads

### Step 1: CZI Conversion Issues

**"No such file: Morgane_BP_Cerebellum_Stitch.czi"**
```bash
# Check file is in project folder with exact name
ls -la *.czi
# Should show: Morgane_BP_Cerebellum_Stitch.czi

# If not, copy your CZI file to the project folder
```

**"ModuleNotFoundError: No module named 'distributed'"**
```bash
# Install missing dependency
uv pip install "dask[distributed]" --upgrade
```

**"Out of memory" during conversion**
- Close other applications
- Use a machine with more RAM (16GB+ recommended)
- Contact Sergio for workstation access

### Step 2: Tile Extraction Issues

**"Cannot find OME-Zarr file"**
```bash
# Check Step 1 completed successfully
ls -la Morgane_BP_Cerebellum_Stitch.ome.zarr/
# Should show zarr folder structure
```

**"No tissue found" or "Extracted 0 tiles"**
- Your OME-Zarr file might be corrupted
- Re-run Step 1 (CZI conversion)

### Step 3: Reconstruction Issues

**"No tiles found in region"**
```bash
# Check tiles folder exists
ls tiles/ | head
# Should show tile directories like tile_y000_x006_c0/

# Check your coordinates are valid
tile-stitcher explore --grid
```

**"Region outside bounds"**
```bash
# Check valid coordinate ranges
tile-stitcher explore
# Shows valid ranges: y0:32, x0:25

# Use coordinates within bounds
tile-stitcher stitch --region y005:008,x008:011 --output test.tif --force
```

**"Out of memory" during reconstruction**
```bash
# Try smaller regions first  
tile-stitcher stitch --region y015:017,x010:012 --output small.tif --force

# Or limit memory usage
tile-stitcher stitch --region y010:015,x010:015 --max-memory 4096 --output limited.tif --force
```

## Getting Help

### Built-in Commands
```bash
# General help for each tool
tile-stitcher --help
python convert_czi_to_ome_zarr_optimized.py --help
python scripts/napari_roi_extractor.py --help

# Specific command help
tile-stitcher explore --help      # Exploration options
tile-stitcher select --help       # Selection options  
tile-stitcher stitch --help       # Reconstruction options
```

### Check Your Setup
```bash
# See dataset overview (after Step 2)
tile-stitcher explore --grid      # Visual tissue map
tile-stitcher explore --suggest   # Get good region suggestions

# Check what files you have
ls -la *.czi *.ome.zarr tiles/     # Should show all your files
```

### If You Get Stuck
1. **Re-read the error message** - they usually tell you exactly what's wrong
2. **Check the troubleshooting section** above for your specific step
3. **Start over with smaller regions** if memory issues occur
4. **Contact Sergio** with the exact error message and what step failed

## Summary: Complete Workflow

```bash
# ONE TIME SETUP (do once)
git clone https://github.com/serg-bg/cerebellum-brain-tile-reconstructor.git
cd cerebellum-brain-tile-reconstructor
uv venv && source .venv/bin/activate
uv sync && uv pip install -e .

# STEP 1: Convert CZI (do once, ~2 hours)  
python convert_czi_to_ome_zarr_optimized.py

# STEP 2: Extract tiles (do once, ~30 min)
python scripts/napari_roi_extractor.py Morgane_BP_Cerebellum_Stitch.ome.zarr --tiles --output tiles/

# STEP 3: Create brain regions (repeat as needed, ~1 min each)
tile-stitcher explore --grid                                    # See what's available
tile-stitcher stitch --region y015:018,x010:013 --output my_region.tif --force   # Get your data
```

**Remember**: Steps 1-2 are one-time setup. Step 3 is what you'll use repeatedly for your research.

---

**Questions?** Contact Sergio Bernal-Garcia <smb2318@columbia.edu>