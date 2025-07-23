# OME-Zarr Tile Reconstruction CLI - Claude Development Context

## Project Overview

This project extends the existing `ome-zarr-roi-extractor` with a new CLI tool called `tile-stitcher` for reconstructing brain tissue regions from individual microscopy tiles.

### Current Status
- **Repository**: ome-zarr-roi-extractor (ready for GitHub)
- **Author**: Sergio Bernal-Garcia <smb2318@columbia.edu>
- **Environment**: Python 3.11.11 with uv package manager
- **Virtual Environment**: `.venv` (pre-configured and working)
- **Data**: 1,246 brain tissue tiles in 32x25 grid (126GB total)

## Development Guidelines

### Environment Setup
Always activate the virtual environment before running Python code:
```bash
cd /Volumes/OWC__1M2_4TB/SBG_Baptiste_Morgane
source .venv/bin/activate
```

### Package Management
Use uv for all dependency management:
```bash
uv add package_name          # Add new dependency
uv sync                      # Sync dependencies
uv pip install -e .          # Install in development mode
```

### Code Style
- Keep code simple, neat, and straightforward
- No emojis in code or comments
- Follow existing project conventions (black formatting, line length 88)
- Use meaningful variable names and clear function signatures

### Project Structure
```
/Volumes/OWC__1M2_4TB/SBG_Baptiste_Morgane/
├── .venv/                    # Virtual environment (pre-configured)
├── docs/
│   └── plan.md              # Master implementation plan
├── scripts/                 # Main package directory
│   ├── napari_roi_extractor.py    # Existing GUI tool
│   └── [new CLI modules]           # New tile reconstruction tools
├── tiles/                   # Brain tissue tile data (1,246 tiles)
├── pyproject.toml          # Project configuration
└── uv.lock                 # Dependency lock file
```

## Tile Data Structure

### Tile Organization
- **Grid**: 32x25 tiles (y: 0-31, x: 0-24)
- **Channels**: 2 channels (c0, c1) stored separately
- **Format**: Both TIFF and OME-Zarr per tile
- **Size**: 1024x1024 pixels, 19 z-slices, uint16, ~45MB each

### Tile Naming Convention
```
tile_y015_x001_c0/
├── data.tif          # TIFF format (ImageJ compatible)
└── data.ome.zarr/    # OME-Zarr format (napari compatible)
```

### Reconstruction Metadata
Each tile contains metadata for reconstruction:
- `tile_position`: "y015_x001_c0"
- `tile_bounds_yx`: "15360:16384_1024:2048" (exact pixel coordinates)

## CLI Tool Architecture

### Main Command: tile-stitcher
```bash
tile-stitcher explore    # Browse available tiles
tile-stitcher select     # Interactive tile selection
tile-stitcher stitch     # Reconstruct selected tiles
tile-stitcher recipe     # Pre-defined reconstruction workflows
```

### Core Modules
- `tile_stitcher.py` - Main CLI entry point
- `tile_metadata.py` - Tile discovery and metadata parsing
- `tile_reconstructor.py` - Core stitching engine
- `tile_browser.py` - Visualization and exploration
- `tile_selector.py` - Interactive selection interface
- `tile_recipes.py` - Common workflows

## Implementation Phases

### Phase 1: Foundation (Current)
- Update pyproject.toml with dependencies
- Create core metadata and reconstruction modules
- Basic CLI with region specification
- Test 2x2 tile reconstruction

### Phase 2: User Interface
- ASCII grid visualization
- Interactive tile selection
- Rich terminal output

### Phase 3: Polish & Recipes
- Pre-defined workflows
- Error handling and validation
- Documentation and help

## Key Technical Decisions

### Dependencies
- **CLI Framework**: argparse + rich (simple and powerful)
- **Image Processing**: tifffile, numpy (already available)
- **Metadata Source**: TIFF headers (faster than OME-Zarr)
- **Output Format**: TIFF primary, OME-Zarr optional

### Memory Strategy
- Stream tiles on-demand, never load full dataset
- Process regions in chunks for large reconstructions
- Use memory mapping where possible

### Error Handling
- Handle missing tiles gracefully (zero-fill by default)
- Validate regions before processing
- Provide clear error messages and suggestions

## Testing Strategy

### Manual Testing Commands
```bash
# Basic functionality
tile-stitcher stitch --region y015:017,x005:007 --output test.tif

# Edge cases
tile-stitcher stitch --region y000:001,x000:001 --output corner.tif
tile-stitcher stitch --region y030:032,x023:025 --output edge.tif
```

### Success Criteria
- CLI installs and runs without errors
- Can reconstruct regions from 1x1 to 10x10+ tiles
- Output files compatible with ImageJ and napari
- Memory usage reasonable for large reconstructions

## Development Notes

### Working with Large Data
- Total dataset: 126GB (too large to load entirely)
- Individual tiles: ~45MB (manageable)
- Target regions: typically 2x2 to 10x10 tiles
- Memory budget: <8GB for reconstruction operations

### Collaboration Features
- Save/load tile selections as JSON
- Pre-defined recipes for common regions
- Shareable reconstruction specifications

### Future Enhancements
- Web interface for remote browsing
- Advanced gap-filling algorithms
- Multi-threaded tile loading
- Cloud storage integration

## Important File Paths

### Data Locations
- Tiles: `/Volumes/OWC__1M2_4TB/SBG_Baptiste_Morgane/tiles/`
- Scripts: `/Volumes/OWC__1M2_4TB/SBG_Baptiste_Morgane/scripts/`
- Documentation: `/Volumes/OWC__1M2_4TB/SBG_Baptiste_Morgane/docs/`

### Key Files
- Master plan: `docs/plan.md`
- Project config: `pyproject.toml`
- Virtual env: `.venv/`
- Main CLI: `scripts/tile_stitcher.py` (to be created)

## Development Commands Reference

```bash
# Environment setup
cd /Volumes/OWC__1M2_4TB/SBG_Baptiste_Morgane
source .venv/bin/activate

# Install in development mode
uv pip install -e .

# Test CLI availability
tile-stitcher --help

# Run basic reconstruction
tile-stitcher stitch --region y015:017,x005:007 --output test_region.tif

# Check output
ls -la test_region.tif
```

This context file should be referenced throughout development to maintain consistency with project goals and conventions.