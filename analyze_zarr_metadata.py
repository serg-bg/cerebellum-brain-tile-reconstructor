#!/usr/bin/env python3
"""
OME-Zarr Metadata Analysis Script
Examines the multiscale pyramid, chunking, and tiling information in an OME-Zarr file.
"""

import zarr
import json
import os
from pathlib import Path

def analyze_zarr_metadata(zarr_path):
    """Analyze OME-Zarr metadata structure."""
    
    print("=" * 80)
    print("OME-ZARR METADATA ANALYSIS")
    print("=" * 80)
    print(f"Path: {zarr_path}")
    
    if not Path(zarr_path).exists():
        print("ERROR: Path does not exist!")
        return
    
    try:
        # Open the zarr store
        store = zarr.open(zarr_path, mode='r')
        print(f"\nStore type: {type(store)}")
        print(f"Store opened successfully")
        
        # Print basic structure
        print("\n" + "=" * 60)
        print("ZARR GROUP TREE STRUCTURE")
        print("=" * 60)
        print(store.tree())
        
        # Examine root attributes (OME metadata)
        print("\n" + "=" * 60)
        print("ROOT ATTRIBUTES (OME METADATA)")
        print("=" * 60)
        for key, value in store.attrs.items():
            print(f"\n{key}:")
            if isinstance(value, (dict, list)):
                print(json.dumps(value, indent=2))
            else:
                print(f"  {value}")
        
        # Analyze multiscale levels
        print("\n" + "=" * 60)
        print("MULTISCALE PYRAMID ANALYSIS")
        print("=" * 60)
        
        multiscales = store.attrs.get('multiscales', [])
        if multiscales:
            for ms_idx, ms in enumerate(multiscales):
                print(f"\nMultiscale {ms_idx}:")
                print(f"  Name: {ms.get('name', 'N/A')}")
                print(f"  Version: {ms.get('version', 'N/A')}")
                print(f"  Type: {ms.get('type', 'N/A')}")
                
                # Axes information
                axes = ms.get('axes', [])
                print(f"  Axes ({len(axes)}):")
                for axis in axes:
                    print(f"    - {axis.get('name', 'N/A')} ({axis.get('type', 'N/A')}) unit: {axis.get('unit', 'N/A')}")
                
                # Datasets (pyramid levels)
                datasets = ms.get('datasets', [])
                print(f"  Datasets/Levels ({len(datasets)}):")
                
                for level_idx, dataset in enumerate(datasets):
                    path = dataset.get('path', f'{level_idx}')
                    print(f"    Level {level_idx} (path: {path}):")
                    
                    # Get the actual array for this level
                    if path in store:
                        array = store[path]
                        print(f"      Shape: {array.shape}")
                        print(f"      Dtype: {array.dtype}")
                        print(f"      Chunks: {array.chunks}")
                        print(f"      Compressor: {array.compressor}")
                        print(f"      Fill value: {array.fill_value}")
                        print(f"      Order: {array.order}")
                        
                        # Calculate storage info
                        total_chunks = 1
                        for dim_chunks in array.chunks:
                            if isinstance(dim_chunks, (list, tuple)):
                                total_chunks *= len(dim_chunks)
                            else:
                                # Calculate number of chunks per dimension
                                shape_dim = array.shape[len(array.shape) - len(array.chunks) + array.chunks.index(dim_chunks)]
                                total_chunks *= (shape_dim + dim_chunks - 1) // dim_chunks
                        
                        print(f"      Estimated total chunks: {total_chunks}")
                        
                        # Look for coordinate transformations
                        coord_transforms = dataset.get('coordinateTransformations', [])
                        if coord_transforms:
                            print(f"      Coordinate Transformations:")
                            for ct_idx, ct in enumerate(coord_transforms):
                                print(f"        {ct_idx}: {ct}")
        
        # Examine individual arrays in detail
        print("\n" + "=" * 60)
        print("DETAILED ARRAY ANALYSIS")
        print("=" * 60)
        
        # Check for multiple resolution levels
        resolution_levels = [key for key in store.keys() if key.isdigit()]
        print(f"Found resolution levels: {sorted(resolution_levels)}")
        
        for level in sorted(resolution_levels):
            array = store[level]
            print(f"\nLevel {level}:")
            print(f"  Array shape: {array.shape}")
            print(f"  Array chunks: {array.chunks}")
            print(f"  Array dtype: {array.dtype}")
            
            # Analyze chunk structure for tiling patterns
            if len(array.shape) >= 2:  # At least 2D
                print(f"  Spatial dimensions (last 2): {array.shape[-2:]} pixels")
                print(f"  Spatial chunks (last 2): {array.chunks[-2:]} pixels")
                
                # Calculate number of tiles in each spatial dimension
                height_tiles = (array.shape[-2] + array.chunks[-2] - 1) // array.chunks[-2]
                width_tiles = (array.shape[-1] + array.chunks[-1] - 1) // array.chunks[-1]
                print(f"  Tile grid: {height_tiles} x {width_tiles} tiles")
                print(f"  Total spatial tiles: {height_tiles * width_tiles}")
        
        # Look for any custom attributes that might indicate tiling
        print("\n" + "=" * 60)
        print("CUSTOM ATTRIBUTES ANALYSIS")
        print("=" * 60)
        
        def search_for_tile_info(group, path=""):
            """Recursively search for tile-related information."""
            for key, value in group.attrs.items():
                if any(keyword in key.lower() for keyword in ['tile', 'stitch', 'grid', 'overlap', 'position']):
                    print(f"  Found at {path}: {key} = {value}")
            
            # Check subgroups
            for subkey in group.keys():
                try:
                    subgroup = group[subkey]
                    if hasattr(subgroup, 'attrs'):
                        search_for_tile_info(subgroup, f"{path}/{subkey}")
                except:
                    pass
        
        search_for_tile_info(store)
        
        # Check the actual file structure on disk for chunk files
        print("\n" + "=" * 60)
        print("CHUNK FILE ANALYSIS")
        print("=" * 60)
        
        level_0_path = Path(zarr_path) / "0"
        if level_0_path.exists():
            chunk_files = list(level_0_path.glob("*"))
            print(f"Number of chunk files in level 0: {len(chunk_files)}")
            
            # Analyze chunk file naming pattern
            if chunk_files:
                sample_files = sorted([f.name for f in chunk_files[:10]])
                print(f"Sample chunk file names: {sample_files}")
                
                # Try to infer grid structure from file names
                if len(sample_files) > 0:
                    # Look for patterns like "x.y.z.w" which might indicate chunk coordinates
                    first_file = sample_files[0]
                    coords = first_file.split('.')
                    if len(coords) >= 4:  # Likely coordinate pattern
                        print(f"Chunk coordinate pattern detected: {len(coords)} dimensions")
                        
                        # Count unique values in each coordinate position
                        all_files = [f.name for f in chunk_files]
                        coord_ranges = []
                        for coord_idx in range(len(coords)):
                            coord_values = set()
                            for filename in all_files:
                                file_coords = filename.split('.')
                                if len(file_coords) > coord_idx:
                                    coord_values.add(file_coords[coord_idx])
                            coord_ranges.append(len(coord_values))
                        
                        print(f"Coordinate ranges: {coord_ranges}")
                        
                        # If we have spatial coordinates (likely last 2), show the grid
                        if len(coord_ranges) >= 2:
                            spatial_grid = coord_ranges[-2:]
                            print(f"Likely spatial tile grid: {spatial_grid[0]} x {spatial_grid[1]}")
        
    except Exception as e:
        print(f"Error analyzing zarr store: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    zarr_path = "/Volumes/OWC__1M2_4TB/SBG_Baptiste_Morgane/Morgane_BP_Cerebellum_Stitch.ome.zarr"
    analyze_zarr_metadata(zarr_path)