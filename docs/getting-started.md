# Getting Started with Brain Tissue Tile Reconstruction

This guide helps you reconstruct brain tissue regions from individual microscopy tiles, designed specifically for researchers new to command-line tools.

## What This Tool Does

You have 1,246 individual brain tissue images (tiles) that were extracted from a large microscopy scan. This tool helps you:

1. **Explore** - See what tiles are available and where tissue is located
2. **Select** - Choose which region you want to reconstruct  
3. **Stitch** - Combine tiles into a single, large image for analysis

## Before You Start

### Prerequisites
- macOS, Linux, or Windows computer
- At least 4GB free RAM  
- Python 3.9 or newer (most modern systems have this)
- **uv package manager** - install from https://docs.astral.sh/uv/#installation

### One-Time Setup

1. **Open Terminal/Command Prompt**
   - **Mac**: Press `Cmd + Space`, type "Terminal", press Enter
   - **Windows**: Press `Win + R`, type "cmd", press Enter
   - **Linux**: Press `Ctrl + Alt + T`
   
   You'll see a window with text and a blinking cursor.

2. **Navigate to Your Project Directory**
   ```bash
   cd path/to/your/project/directory
   ```
   Replace `path/to/your/project/directory` with wherever you placed the project files.
   
3. **Activate the Virtual Environment**
   ```bash
   # Mac/Linux:
   source .venv/bin/activate
   
   # Windows cmd:
   .venv\Scripts\activate.bat
   
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   ```
   You should see `(.venv)` appear at the start of your command line.

4. **Install the Tool**
   ```bash
   pip install -e .
   ```
   Wait for installation to complete (1-2 minutes).

5. **Test Installation**
   ```bash
   tile-stitcher --help
   ```
   You should see help text. If you get an error, something went wrong.

## Your First Reconstruction (5 Minutes)

Let's create your first brain tissue reconstruction with a proven working example:

### Step 1: See What's Available
```bash
tile-stitcher explore --grid
```

This shows you:
- Total number of tiles (should be 1,246)
- A visual map where `██` means tissue is present
- Suggested regions that work well

### Step 2: Select a Small Region
```bash
tile-stitcher select --preset small --center-y 5 --center-x 10 --save my_first_region.json
```

This creates a 3x3 tile selection and saves it to a file you can reuse.

### Step 3: Create the Reconstruction
```bash
tile-stitcher stitch --load my_first_region.json --output my_first_brain_section.tif --force
```

Wait 30-60 seconds. You'll see a progress bar. When complete, you'll have a file called `my_first_brain_section.tif`.

### Step 4: View Your Result
- **On Mac**: Double-click `my_first_brain_section.tif` to open in Preview
- **For Analysis**: Open in ImageJ, Fiji, or napari for scientific analysis

The file contains all 19 depth layers (z-slices) of your brain tissue region.

## Understanding the Output

Your reconstructed image contains:
- **Width/Height**: 3072x3072 pixels (3x 1024-pixel tiles)  
- **Depth**: 19 z-slices (depth layers through tissue)
- **File Size**: ~200MB for a 3x3 region
- **Format**: Standard TIFF (compatible with all imaging software)

## Common Working Examples

### Small Region (3x3 tiles) - Good for Testing
```bash
# Explore and find good spots
tile-stitcher explore --suggest

# Create reconstruction  
tile-stitcher stitch --region y003:006,x008:011 --channel 0 --output small_test.tif --force
```

### Medium Region (5x5 tiles) - Good for Analysis
```bash
# Select larger region
tile-stitcher select --preset medium --center-y 15 --center-x 12 --save analysis_region.json

# Reconstruct
tile-stitcher stitch --load analysis_region.json --output brain_analysis.tif --force
```

### Specific Coordinates - When You Know Exactly What You Want
```bash
tile-stitcher stitch --region y010:015,x005:010 --channel 0 --output specific_region.tif --force
```

## Understanding Coordinates

The brain tissue is organized in a grid:
- **y**: Row number (0-31, top to bottom)
- **x**: Column number (0-24, left to right)
- **Format**: `y010:015,x005:010` means rows 10-14 and columns 5-9

To specify a region:
- `y010:015` = rows 10, 11, 12, 13, 14 (5 rows total)
- `x005:010` = columns 5, 6, 7, 8, 9 (5 columns total)
- Result: 5x5 grid of tiles

## Channel Selection

Your data has 2 imaging channels:
- **Channel 0** (`--channel 0`): One imaging condition
- **Channel 1** (`--channel 1`): Different imaging condition  
- **Default**: Channel 0 if not specified

Most users start with channel 0.

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

## Troubleshooting

### "Command not found: tile-stitcher"
```bash
# Make sure you activated the environment
# Mac/Linux:
source .venv/bin/activate
# Windows cmd:
.venv\Scripts\activate.bat
# Windows PowerShell:
.venv\Scripts\Activate.ps1

# Check if you see (.venv) at the start of your command line
# If not, the environment isn't active
```

### "No tiles found"
```bash
# Check you're in the right directory
pwd
# Should show: /Volumes/OWC__1M2_4TB/SBG_Baptiste_Morgane

# Check tiles exist
ls tiles/ | head
# Should show tile directories
```

### "Region outside bounds"
```bash
# Check valid ranges
tile-stitcher explore
# Shows valid ranges: y0:32, x0:25

# Use coordinates within these bounds
tile-stitcher stitch --region y000:005,x000:005 --output test.tif --force
```

### "Out of memory" 
```bash
# Try smaller regions first
tile-stitcher stitch --region y010:012,x010:012 --output small.tif --force

# Or limit memory usage
tile-stitcher stitch --region y010:015,x010:015 --max-memory 4096 --output limited.tif --force
```

### Files Are Too Large
```bash
# Use compression
tile-stitcher stitch --region y010:015,x010:015 --compression lzw --output compressed.tif --force

# Or select fewer z-slices
tile-stitcher stitch --region y010:015,x010:015 --z-range 5:15 --output fewer_slices.tif --force
```

## Getting Help

### Built-in Help
```bash
tile-stitcher --help              # General help
tile-stitcher explore --help      # Exploration options
tile-stitcher select --help       # Selection options
tile-stitcher stitch --help       # Reconstruction options
```

### Check What You Have
```bash
tile-stitcher explore             # See dataset overview
tile-stitcher explore --grid      # Visual grid map
tile-stitcher explore --suggest   # Get working region suggestions
```

## Next Steps

Once you're comfortable with basic reconstructions:

1. **Explore different regions** using the grid visualization
2. **Try both channels** to see different tissue features
3. **Save useful selections** as JSON files for reuse
4. **Share selections** with colleagues for consistent analysis regions
5. **Experiment with larger regions** for comprehensive tissue views

## Quick Reference Card

```bash
# See what's available
tile-stitcher explore --grid

# Quick small reconstruction
tile-stitcher stitch --region y005:008,x008:011 --output quick_test.tif --force

# Save a selection for later
tile-stitcher select --preset medium --center-y 15 --center-x 10 --save my_region.json

# Use saved selection
tile-stitcher stitch --load my_region.json --output my_analysis.tif --force

# Always use --force to skip prompts in scripts
```

Remember: Start small, test first, then scale up to larger regions for your actual analysis.