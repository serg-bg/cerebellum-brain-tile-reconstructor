"""Tile metadata parsing and indexing utilities."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import tifffile


@dataclass
class TileInfo:
    """Information about a single tile."""
    
    path: Path
    y: int
    x: int
    channel: int
    bounds_yx: Tuple[int, int, int, int]  # y_start, y_end, x_start, x_end
    size_bytes: int
    z_slices: int
    width: int
    height: int


@dataclass
class Region:
    """Defines a rectangular region of tiles."""
    
    y_start: int
    y_end: int
    x_start: int
    x_end: int
    channel: int = 0
    
    @property
    def width(self) -> int:
        return self.x_end - self.x_start
    
    @property
    def height(self) -> int:
        return self.y_end - self.y_start
    
    @property
    def tile_count(self) -> int:
        return self.width * self.height
    
    def contains_tile(self, y: int, x: int) -> bool:
        """Check if a tile position is within this region."""
        return (self.y_start <= y < self.y_end and 
                self.x_start <= x < self.x_end)


class TileIndex:
    """Fast tile discovery and metadata management."""
    
    def __init__(self, tiles_dir: Path):
        """Initialize tile index for a given tiles directory."""
        self.tiles_dir = Path(tiles_dir)
        self._tiles: Dict[str, TileInfo] = {}
        self._channels: List[int] = []
        self._grid_bounds = None
        self._scan_tiles()
    
    def _scan_tiles(self) -> None:
        """Scan the tiles directory and build the index."""
        if not self.tiles_dir.exists():
            raise FileNotFoundError(f"Tiles directory not found: {self.tiles_dir}")
        
        pattern = re.compile(r'tile_y(\d+)_x(\d+)_c(\d+)')
        channels = set()
        
        for tile_dir in self.tiles_dir.iterdir():
            if not tile_dir.is_dir():
                continue
                
            match = pattern.match(tile_dir.name)
            if not match:
                continue
            
            y, x, channel = map(int, match.groups())
            channels.add(channel)
            
            # Look for TIFF file (faster metadata access)
            tiff_path = tile_dir / "data.tif"
            if not tiff_path.exists():
                continue
            
            try:
                tile_info = self._parse_tile_metadata(tiff_path, y, x, channel)
                key = f"y{y:03d}_x{x:03d}_c{channel}"
                self._tiles[key] = tile_info
            except Exception as e:
                print(f"Warning: Failed to parse tile {tile_dir}: {e}")
                continue
        
        self._channels = sorted(channels)
        self._compute_grid_bounds()
    
    def _parse_tile_metadata(self, tiff_path: Path, y: int, x: int, channel: int) -> TileInfo:
        """Parse metadata from a TIFF file."""
        with tifffile.TiffFile(tiff_path) as tif:
            # Get basic image properties
            shape = tif.series[0].shape  # (z, height, width)
            z_slices, height, width = shape
            size_bytes = tiff_path.stat().st_size
            
            # Parse tile bounds from metadata
            bounds_yx = None
            for page in tif.pages[:1]:
                if page.description:
                    bounds_match = re.search(r'tile_bounds_yx=(\d+):(\d+)_(\d+):(\d+)', 
                                           page.description)
                    if bounds_match:
                        y_start, y_end, x_start, x_end = map(int, bounds_match.groups())
                        bounds_yx = (y_start, y_end, x_start, x_end)
                        break
            
            # Fallback: estimate bounds from grid position
            if bounds_yx is None:
                tile_size = 1024  # Standard tile size
                y_start = y * tile_size
                y_end = y_start + tile_size
                x_start = x * tile_size
                x_end = x_start + tile_size
                bounds_yx = (y_start, y_end, x_start, x_end)
            
            return TileInfo(
                path=tiff_path,
                y=y,
                x=x,
                channel=channel,
                bounds_yx=bounds_yx,
                size_bytes=size_bytes,
                z_slices=z_slices,
                width=width,
                height=height
            )
    
    def _compute_grid_bounds(self) -> None:
        """Compute the overall grid bounds."""
        if not self._tiles:
            self._grid_bounds = (0, 0, 0, 0)
            return
        
        y_coords = [info.y for info in self._tiles.values()]
        x_coords = [info.x for info in self._tiles.values()]
        
        self._grid_bounds = (
            min(y_coords),
            max(y_coords) + 1,
            min(x_coords),
            max(x_coords) + 1
        )
    
    def get_tile(self, y: int, x: int, channel: int = 0) -> Optional[TileInfo]:
        """Get tile information for a specific position."""
        key = f"y{y:03d}_x{x:03d}_c{channel}"
        return self._tiles.get(key)
    
    def get_tiles_in_region(self, region: Region) -> List[TileInfo]:
        """Get all tiles within a specified region."""
        tiles = []
        for y in range(region.y_start, region.y_end):
            for x in range(region.x_start, region.x_end):
                tile = self.get_tile(y, x, region.channel)
                if tile:
                    tiles.append(tile)
        return tiles
    
    def validate_region(self, region: Region) -> Tuple[bool, str]:
        """Validate that a region is reasonable."""
        if not self._grid_bounds:
            return False, "No tiles available"
        
        grid_y_min, grid_y_max, grid_x_min, grid_x_max = self._grid_bounds
        
        # Check bounds
        if region.y_start < grid_y_min or region.y_end > grid_y_max:
            return False, f"Y range {region.y_start}:{region.y_end} outside grid bounds {grid_y_min}:{grid_y_max}"
        
        if region.x_start < grid_x_min or region.x_end > grid_x_max:
            return False, f"X range {region.x_start}:{region.x_end} outside grid bounds {grid_x_min}:{grid_x_max}"
        
        # Check for reasonable size
        if region.tile_count > 100:
            return False, f"Region too large: {region.tile_count} tiles (max 100 recommended)"
        
        if region.tile_count == 0:
            return False, "Empty region"
        
        # Check channel availability
        if region.channel not in self._channels:
            return False, f"Channel {region.channel} not available. Available: {self._channels}"
        
        return True, "Valid region"
    
    def estimate_output_size(self, region: Region) -> Tuple[int, int, int]:
        """Estimate output dimensions (height, width, size_mb)."""
        tiles = self.get_tiles_in_region(region)
        if not tiles:
            return 0, 0, 0
        
        # Use first tile as reference
        tile = tiles[0]
        tile_height, tile_width = tile.height, tile.width
        
        output_height = region.height * tile_height
        output_width = region.width * tile_width
        
        # Estimate size in MB (uint16, 19 z-slices)
        pixels = output_height * output_width * tile.z_slices
        size_mb = (pixels * 2) / (1024 * 1024)  # 2 bytes per uint16 pixel
        
        return output_height, output_width, int(size_mb)
    
    def get_available_channels(self) -> List[int]:
        """Get list of available channels."""
        return self._channels.copy()
    
    def get_grid_bounds(self) -> Tuple[int, int, int, int]:
        """Get overall grid bounds (y_min, y_max, x_min, x_max)."""
        return self._grid_bounds
    
    def get_stats(self) -> Dict:
        """Get summary statistics."""
        if not self._tiles:
            return {}
        
        # Count tiles per channel
        channel_counts = {}
        total_size_mb = 0
        
        for tile in self._tiles.values():
            channel = tile.channel
            channel_counts[channel] = channel_counts.get(channel, 0) + 1
            total_size_mb += tile.size_bytes / (1024 * 1024)
        
        return {
            "total_tiles": len(self._tiles),
            "channels": self._channels,
            "channel_counts": channel_counts,
            "grid_bounds": self._grid_bounds,
            "total_size_mb": int(total_size_mb)
        }


def parse_region_string(region_str: str, channel: int = 0) -> Region:
    """Parse a region string like 'y015:020,x005:010' into a Region object."""
    try:
        y_part, x_part = region_str.split(',')
        
        # Parse Y range
        if ':' in y_part:
            y_start, y_end = y_part.replace('y', '').split(':')
        else:
            y_start = y_end = y_part.replace('y', '')
            y_end = str(int(y_end) + 1)
        
        # Parse X range  
        if ':' in x_part:
            x_start, x_end = x_part.replace('x', '').split(':')
        else:
            x_start = x_end = x_part.replace('x', '')
            x_end = str(int(x_end) + 1)
        
        return Region(
            y_start=int(y_start),
            y_end=int(y_end),
            x_start=int(x_start),
            x_end=int(x_end),
            channel=channel
        )
    
    except Exception as e:
        raise ValueError(f"Invalid region format '{region_str}'. Use format like 'y015:020,x005:010'") from e