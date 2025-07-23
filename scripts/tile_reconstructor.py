"""Core tile reconstruction and stitching functionality."""

import json
from pathlib import Path
from typing import Iterator, Optional, Tuple

import numpy as np
import tifffile
from tqdm import tqdm

from .tile_metadata import Region, TileIndex, TileInfo


class TileStitcher:
    """Memory-efficient tile reconstruction engine."""
    
    def __init__(self, tile_index: TileIndex):
        """Initialize stitcher with a tile index."""
        self.tile_index = tile_index
    
    def stitch_region(
        self,
        region: Region,
        output_path: Path,
        fill_missing: str = "zero",
        compression: str = "lzw",
        z_range: Optional[Tuple[int, int]] = None,
        progress: bool = True
    ) -> bool:
        """
        Stitch tiles in a region and save to output file.
        
        Args:
            region: Region to reconstruct
            output_path: Output file path
            fill_missing: How to handle missing tiles ("zero", "skip")
            compression: TIFF compression method
            z_range: Optional z-slice range (start, end)
            progress: Show progress bar
            
        Returns:
            True if successful, False otherwise
        """
        # Validate region
        valid, message = self.tile_index.validate_region(region)
        if not valid:
            print(f"Error: {message}")
            return False
        
        # Get tiles in region
        tiles = self.tile_index.get_tiles_in_region(region)
        if not tiles:
            print("Error: No tiles found in region")
            return False
        
        # Use first tile to determine properties
        reference_tile = tiles[0]
        tile_height, tile_width = reference_tile.height, reference_tile.width
        z_slices = reference_tile.z_slices
        
        # Apply z-range filter if specified
        if z_range:
            z_start, z_end = z_range
            z_start = max(0, z_start)
            z_end = min(z_slices, z_end)
            z_slices = z_end - z_start
        else:
            z_start, z_end = 0, z_slices
        
        # Calculate output dimensions
        output_height = region.height * tile_height
        output_width = region.width * tile_width
        
        print(f"Reconstructing region: {region.height}x{region.width} tiles")
        print(f"Output dimensions: {output_height}x{output_width}x{z_slices}")
        print(f"Tiles found: {len(tiles)}/{region.tile_count}")
        
        try:
            # Create output array
            output_array = np.zeros((z_slices, output_height, output_width), dtype=np.uint16)
            
            # Create tile position lookup
            tile_lookup = {}
            for tile in tiles:
                key = (tile.y, tile.x)
                tile_lookup[key] = tile
            
            # Progress bar setup
            if progress:
                pbar = tqdm(
                    total=region.tile_count,
                    desc="Stitching tiles",
                    unit="tiles"
                )
            
            # Stitch tiles
            for grid_y in range(region.height):
                for grid_x in range(region.width):
                    tile_y = region.y_start + grid_y
                    tile_x = region.x_start + grid_x
                    
                    tile = tile_lookup.get((tile_y, tile_x))
                    
                    if tile:
                        # Load and place tile
                        tile_data = self._load_tile_data(tile, z_start, z_end)
                        
                        # Calculate placement position
                        y_offset = grid_y * tile_height
                        x_offset = grid_x * tile_width
                        
                        output_array[
                            :,
                            y_offset:y_offset + tile_height,
                            x_offset:x_offset + tile_width
                        ] = tile_data
                    
                    elif fill_missing == "zero":
                        # Already filled with zeros, nothing to do
                        pass
                    elif fill_missing == "skip":
                        print(f"Warning: Missing tile at y{tile_y:03d}_x{tile_x:03d}")
                    
                    if progress:
                        pbar.update(1)
            
            if progress:
                pbar.close()
            
            # Save output
            self._save_output(output_array, output_path, compression, region)
            
            # Print summary
            size_mb = output_array.nbytes / (1024 * 1024)
            print(f"Reconstruction complete: {output_path}")
            print(f"Output size: {size_mb:.1f} MB")
            
            return True
            
        except Exception as e:
            print(f"Error during reconstruction: {e}")
            return False
    
    def _load_tile_data(self, tile: TileInfo, z_start: int, z_end: int) -> np.ndarray:
        """Load tile data from TIFF file."""
        with tifffile.TiffFile(tile.path) as tif:
            # Load specific z-range
            data = tif.asarray()[z_start:z_end, :, :]
            return data
    
    def _save_output(
        self,
        data: np.ndarray,
        output_path: Path,
        compression: str,
        region: Region
    ) -> None:
        """Save reconstructed data to TIFF file with metadata."""
        
        # Prepare metadata
        metadata = {
            "source": "tile-stitcher",
            "region": f"y{region.y_start:03d}:{region.y_end:03d}_x{region.x_start:03d}:{region.x_end:03d}",
            "channel": region.channel,
            "tile_count": region.tile_count,
            "reconstruction_method": "direct_stitching"
        }
        
        # Create ImageJ-compatible description
        z_slices, height, width = data.shape
        description = (
            f"ImageJ=1.11a\n"
            f"images={z_slices}\n"
            f"channels=1\n"
            f"slices={z_slices}\n"
            f"hyperstack=true\n"
            f"mode=grayscale\n"
            f"source=tile-stitcher\n"
            f"region={metadata['region']}\n"
            f"channel={region.channel}"
        )
        
        # Save TIFF with compression
        tifffile.imwrite(
            output_path,
            data,
            compression=compression,
            description=description,
            metadata=metadata
        )
    
    def estimate_memory_usage(self, region: Region) -> int:
        """Estimate memory usage for reconstruction in MB."""
        height, width, size_mb = self.tile_index.estimate_output_size(region)
        
        # Add overhead for processing (roughly 2x the output size)
        return int(size_mb * 2)
    
    def validate_memory_requirements(self, region: Region, max_memory_mb: int = 8192) -> Tuple[bool, str]:
        """Check if reconstruction fits within memory limits."""
        estimated_mb = self.estimate_memory_usage(region)
        
        if estimated_mb > max_memory_mb:
            return False, f"Estimated memory usage {estimated_mb}MB exceeds limit {max_memory_mb}MB"
        
        return True, f"Estimated memory usage: {estimated_mb}MB"
    
    def get_reconstruction_info(self, region: Region) -> dict:
        """Get detailed information about a planned reconstruction."""
        tiles = self.tile_index.get_tiles_in_region(region)
        height, width, size_mb = self.tile_index.estimate_output_size(region)
        memory_mb = self.estimate_memory_usage(region)
        
        missing_tiles = []
        for y in range(region.y_start, region.y_end):
            for x in range(region.x_start, region.x_end):
                if not self.tile_index.get_tile(y, x, region.channel):
                    missing_tiles.append(f"y{y:03d}_x{x:03d}")
        
        return {
            "region": {
                "y_range": f"{region.y_start}:{region.y_end}",
                "x_range": f"{region.x_start}:{region.x_end}",
                "channel": region.channel,
                "tile_dimensions": f"{region.height}x{region.width}",
                "tile_count": region.tile_count
            },
            "output": {
                "dimensions": f"{height}x{width}",
                "estimated_size_mb": size_mb,
                "estimated_memory_mb": memory_mb
            },
            "tiles": {
                "found": len(tiles),
                "missing": len(missing_tiles),
                "missing_list": missing_tiles[:10]  # Show first 10
            }
        }


def preview_reconstruction(tile_index: TileIndex, region: Region) -> None:
    """Print a preview of what a reconstruction would look like."""
    stitcher = TileStitcher(tile_index)
    info = stitcher.get_reconstruction_info(region)
    
    print("\nReconstruction Preview")
    print("=" * 50)
    print(f"Region: {info['region']['y_range']}, {info['region']['x_range']} (channel {info['region']['channel']})")
    print(f"Tiles: {info['region']['tile_dimensions']} grid ({info['region']['tile_count']} total)")
    print(f"Output: {info['output']['dimensions']} pixels (~{info['output']['estimated_size_mb']} MB)")
    print(f"Memory: ~{info['output']['estimated_memory_mb']} MB required")
    print(f"Tiles found: {info['tiles']['found']}/{info['region']['tile_count']}")
    
    if info['tiles']['missing']:
        print(f"Missing tiles: {info['tiles']['missing']} tiles")
        if info['tiles']['missing_list']:
            print(f"Examples: {', '.join(info['tiles']['missing_list'])}")
    
    print("=" * 50)