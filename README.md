# Brain Tissue Tile Reconstruction Toolkit

Reconstruct brain tissue regions from individual microscopy tiles. Perfect for researchers who need to extract and analyze specific regions from large brain imaging datasets.

## What This Tool Does

You have **1,246 brain tissue tiles** from a cerebellum scan. This toolkit helps you:
1. **Explore** what tissue is available and where
2. **Select** specific regions you want to analyze  
3. **Reconstruct** those regions into single, analysis-ready images

Your dataset contains:
- 32×25 grid of brain tissue tiles
- 2 imaging channels with different tissue features
- 19 depth layers (z-slices) per location
- ~45MB per tile, 126GB total

## Quick Start (5 Minutes)

### 1. One-Time Setup
```bash
# Open Terminal and navigate to project
cd /Volumes/OWC__1M2_4TB/SBG_Baptiste_Morgane

# Activate environment and install
source .venv/bin/activate
pip install -e .

# Test installation
tile-stitcher --help
```

### 2. Your First Reconstruction
```bash
# See what's available
tile-stitcher explore --grid

# Create a small test region
tile-stitcher stitch --region y005:008,x008:011 --output my_first_brain_section.tif --force

# Open the result in any image viewer or ImageJ
```

That's it! You now have a 3×3 tile brain tissue reconstruction ready for analysis.

## 📖 Detailed Documentation

**New to command-line tools?** See the [Complete Getting Started Guide](docs/getting-started.md) for:
- Step-by-step installation help
- Detailed examples with proven coordinates  
- Troubleshooting common issues
- Memory and file size guidance
- Tips for sharing regions with colleagues

## Understanding Your Data

### Tile Organization

```
tiles/
├── tile_y010_x008_c0/    # Row 10, Column 8, Channel 0
│   ├── data.tif          # For ImageJ/Fiji
│   └── data.ome.zarr/    # For napari/Python
├── tile_y010_x008_c1/    # Same location, Channel 1
└── ...
```

### Coordinate System
- **y**: Row number (0-31, top to bottom)
- **x**: Column number (0-24, left to right)  
- **c**: Channel (0 or 1, different imaging conditions)

### File Formats
- **TIFF files** (.tif): Use with ImageJ, Fiji, or any image viewer
- **OME-Zarr files** (.ome.zarr/): Use with napari or Python analysis

## Common Use Cases

### Quick Analysis Regions
```bash
# Small test region (3x3 tiles, ~200MB output)
tile-stitcher stitch --region y005:008,x008:011 --output small_test.tif --force

# Medium analysis region (5x5 tiles, ~400MB output)  
tile-stitcher stitch --region y010:015,x008:013 --output medium_analysis.tif --force

# Large comprehensive region (8x8 tiles, ~1GB output)
tile-stitcher stitch --region y008:016,x006:014 --output large_region.tif --force
```

### Working with Different Channels
```bash
# Compare same region across both channels
tile-stitcher stitch --region y012:017,x010:015 --channel 0 --output region_channel0.tif --force
tile-stitcher stitch --region y012:017,x010:015 --channel 1 --output region_channel1.tif --force
```

### Sharing with Colleagues
```bash
# Save region for sharing
tile-stitcher select --region y020:025,x010:015 --save purkinje_region.json

# Colleague uses the same coordinates
tile-stitcher stitch --load purkinje_region.json --output colleague_analysis.tif --force
```

## Key Tips

- **Start small**: Test with 2x2 or 3x3 regions first (~200MB output)
- **Use suggestions**: Run `tile-stitcher explore --suggest` for proven coordinates
- **Always use --force**: Skips confirmation prompts in automated workflows
- **Name files clearly**: Include region coordinates in output filenames
- **Check coverage**: Use `tile-stitcher explore --grid` to see tissue distribution

## Quick Troubleshooting

**Installation issues?** **Commands not working?** **Out of memory?**

See the [Complete Getting Started Guide](docs/getting-started.md) for detailed troubleshooting, including:
- Step-by-step installation verification
- Memory management strategies  
- How to handle missing tiles
- Common coordinate mistakes

## Getting Help

```bash
tile-stitcher --help              # All available commands
tile-stitcher explore --help      # Options for browsing data
tile-stitcher stitch --help       # Options for reconstruction
```

For complete documentation: [Getting Started Guide](docs/getting-started.md)

## Dataset Info

- **Grid**: 32 rows × 25 columns (y:0-31, x:0-24)
- **Channels**: 2 imaging conditions per location
- **Depth**: 19 z-slices per tile
- **Coverage**: 623 tiles per channel (tissue areas only)
- **Output**: Standard TIFF files compatible with ImageJ, napari, Fiji

## Acknowledgments

This tool was developed for **Morgane Marie** and **Baptiste Philippot** to support their analysis of large-scale human cerebellum tissue imaging data. The reconstruction capabilities were specifically designed to handle their multi-terabyte microscopy dataset and enable efficient region-based analysis workflows.

## Author & License

**Sergio Bernal-Garcia** <smb2318@columbia.edu>  
MIT License - Free to use and modify