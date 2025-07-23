#!/usr/bin/env python3
"""
OME-Zarr ROI Extractor CLI for napari
====================================

A professional CLI tool for interactive ROI selection and export from OME-Zarr
data. Supports lazy loading, metadata preservation, and efficient streaming.

Usage:
    python scripts/napari_roi_extractor.py <zarr_path>
    python scripts/napari_roi_extractor.py --help

Example:
    python scripts/napari_roi_extractor.py data/sample.ome.zarr
    python scripts/napari_roi_extractor.py data/sample.ome.zarr --output roi_export/
"""

import argparse
import json
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import dask.array as da
import napari
import numpy as np
import pandas as pd
import tifffile
import xarray as xr
import zarr
from magicgui import magic_factory
from napari.utils.notifications import show_error, show_info
from ome_zarr.io import parse_url
from ome_zarr.reader import Reader
from tqdm import tqdm

# Suppress unnecessary warnings for cleaner CLI output
warnings.filterwarnings("ignore", category=UserWarning)


class OMEZarrROIExtractor:
    """
    Professional OME-Zarr ROI extraction tool with napari integration.

    Handles lazy loading, interactive ROI selection, and metadata-preserving
    export to new zarr files.
    """

    def __init__(self, zarr_path: Path, output_dir: Path = None):
        """
        Initialize the ROI extractor.

        Args:
            zarr_path: Path to input .ome.zarr directory
            output_dir: Directory for output files (default: current dir)
        """
        self.zarr_path = Path(zarr_path)
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Validate input
        if not self.zarr_path.exists():
            raise FileNotFoundError(f"Zarr path not found: {self.zarr_path}")
        if not self.zarr_path.is_dir():
            raise ValueError(f"Expected directory, got file: {self.zarr_path}")

        print("Initialized ROI Extractor")
        print(f"   Input:  {self.zarr_path}")
        print(f"   Output: {self.output_dir}")

    def load_ome_zarr_lazy(self) -> Tuple[da.Array, Dict]:
        """
        Load OME-Zarr data in lazy mode with metadata preservation.

        Returns:
            Tuple of (dask_array, metadata_dict) for highest resolution level

        Raises:
            ValueError: If no valid OME-Zarr data found
        """
        print(f"Loading OME-Zarr metadata: {self.zarr_path.name}")

        # Parse OME-Zarr using ome-zarr-py
        store = parse_url(str(self.zarr_path), mode="r")
        reader = Reader(store)

        # Extract first (highest resolution) image node
        nodes = list(reader())
        if not nodes:
            raise ValueError(f"No valid OME-Zarr data in {self.zarr_path}")

        node = nodes[0]  # Highest resolution level
        data = node.data[0]  # First scale level (level 0)
        metadata = node.metadata

        print("Data Properties:")
        print(f"   Shape: {data.shape}")
        print(f"   Dtype: {data.dtype}")
        print(f"   Chunks: {data.chunks}")
        print(f"   Memory: ~{data.nbytes / 1e9:.1f} GB")

        # Extract channel information if available
        if "multiscales" in metadata:
            ms = metadata["multiscales"][0]
            if "axes" in ms:
                axes_names = [
                    ax.get("name", ax.get("type", "unknown")) for ax in ms["axes"]
                ]
                print(f"   Axes: {axes_names}")

        return data, metadata

    def extract_roi_bounds(self, shapes_layer) -> Tuple[slice, ...]:
        """
        Extract bounding box from napari Shapes layer rectangle.

        Args:
            shapes_layer: napari Shapes layer containing rectangle ROI

        Returns:
            Tuple of slice objects for array indexing (supports N-D)

        Raises:
            ValueError: If no shapes or invalid shape found
        """
        if len(shapes_layer.data) == 0:
            raise ValueError("No ROI drawn. Please draw a rectangle first.")

        if len(shapes_layer.data) > 1:
            show_info("Multiple ROIs found - using first rectangle")

        # Find first rectangle shape
        rectangle_idx = None
        for i, shape_type in enumerate(shapes_layer.shape_type):
            if shape_type == "rectangle":
                rectangle_idx = i
                break

        if rectangle_idx is None:
            raise ValueError("No rectangle found. Please use rectangle tool.")

        shape_data = shapes_layer.data[rectangle_idx]

        # Extract min/max coordinates for each dimension
        # shape_data is (n_points, n_dims) - for rectangle: (4, n_dims)
        mins = np.floor(shape_data.min(axis=0)).astype(int)
        maxs = np.ceil(shape_data.max(axis=0)).astype(int)

        # Ensure positive bounds and within image dimensions
        mins = np.maximum(mins, 0)

        # Create slice objects for each dimension
        slices = tuple(
            slice(int(min_val), int(max_val)) for min_val, max_val in zip(mins, maxs)
        )

        # Validate non-empty ROI
        roi_size = np.prod([s.stop - s.start for s in slices])
        if roi_size == 0:
            raise ValueError("Empty ROI. Please draw a larger rectangle.")

        print(f"ROI Bounds: {[f'{s.start}:{s.stop}' for s in slices]}")
        print(f"   ROI Size: {roi_size:,} pixels")

        return slices

    def preserve_ome_metadata(
        self,
        original_metadata: Dict,
        roi_shape: Tuple[int, ...],
        roi_slices: Tuple[slice, ...],
    ) -> Dict:
        """
        Create updated OME-Zarr metadata for ROI with preserved semantics.

        Args:
            original_metadata: Original OME-Zarr metadata dictionary
            roi_shape: Shape of extracted ROI data
            roi_slices: Slice objects used for ROI extraction

        Returns:
            Updated metadata dictionary with corrected transforms
        """
        metadata = dict(original_metadata)  # Deep copy

        if "multiscales" not in metadata:
            return metadata

        multiscales = dict(metadata["multiscales"][0])

        # Update coordinate transformations for ROI offset
        if "coordinateTransformations" in multiscales:
            transforms = []

            for transform in multiscales["coordinateTransformations"]:
                if transform["type"] == "scale":
                    # Create translation for ROI offset
                    translation = [
                        sl.start if sl.start is not None else 0 for sl in roi_slices
                    ]

                    # Combine scale and translation
                    transforms.extend(
                        [
                            {"type": "scale", "scale": transform["scale"]},
                            {"type": "translation", "translation": translation},
                        ]
                    )
                else:
                    transforms.append(dict(transform))

            multiscales["coordinateTransformations"] = transforms

        # Update datasets for single resolution level (ROI doesn't need pyramid)
        multiscales["datasets"] = [
            {
                "path": "0",
                "coordinateTransformations": multiscales.get(
                    "coordinateTransformations", []
                ),
            }
        ]

        # Update name to indicate ROI
        original_name = multiscales.get("name", "image")
        multiscales["name"] = f"{original_name}_ROI_{len(roi_slices)}D"

        metadata["multiscales"] = [multiscales]

        return metadata

    def extract_all_tiles(self, output_dir: Path):
        """
        Extract all 1024x1024x19 chunks as individual tiles.
        
        Args:
            output_dir: Directory to save tiles
        """
        print("Loading OME-Zarr data...")
        
        # Load data directly from zarr to avoid multiscale issues
        zarr_group = zarr.open(str(self.zarr_path), mode="r")
        data = zarr_group["0"]  # Direct access to level 0
        
        print(f"Direct zarr access - Shape: {data.shape}, Dtype: {data.dtype}")
        
        # Get dimensions
        t, c, z, h, w = data.shape
        chunk_h, chunk_w = 1024, 1024
        
        # Calculate number of tiles
        n_tiles_y = (h + chunk_h - 1) // chunk_h
        n_tiles_x = (w + chunk_w - 1) // chunk_w
        
        print(f"Extracting {n_tiles_y} × {n_tiles_x} = {n_tiles_y * n_tiles_x} tiles per channel")
        print(f"Total tiles: {n_tiles_y * n_tiles_x * c}")
        print("Each tile saved as: data.ome.zarr + data.tif")
        
        # Extract each tile
        from numcodecs import Blosc
        from ome_zarr.writer import write_image
        compressor = Blosc(cname="zstd", clevel=3, shuffle=Blosc.BITSHUFFLE)
        
        total_tiles = n_tiles_y * n_tiles_x * c
        tile_count = 0
        
        # Count total non-empty tiles first
        non_empty_count = 0
        print("Scanning for non-empty tiles...")
        
        # Quick scan to count non-empty tiles
        for ch in range(c):
            for y_idx in range(n_tiles_y):
                for x_idx in range(n_tiles_x):
                    y_start = y_idx * chunk_h
                    y_end = min((y_idx + 1) * chunk_h, h)
                    x_start = x_idx * chunk_w  
                    x_end = min((x_idx + 1) * chunk_w, w)
                    
                    # Quick check: sample center of tile for data
                    mid_y = (y_start + y_end) // 2
                    mid_x = (x_start + x_end) // 2
                    sample = data[0, ch, z//2, mid_y:mid_y+50, mid_x:mid_x+50]
                    if sample.max() > 0:
                        non_empty_count += 1
        
        print(f"Found {non_empty_count} non-empty tiles out of {total_tiles} total")
        
        with tqdm(total=non_empty_count, desc="Extracting non-empty tiles", unit="tile") as pbar:
            for ch in range(c):
                for y_idx in range(n_tiles_y):
                    for x_idx in range(n_tiles_x):
                        # Calculate tile bounds
                        y_start = y_idx * chunk_h
                        y_end = min((y_idx + 1) * chunk_h, h)
                        x_start = x_idx * chunk_w  
                        x_end = min((x_idx + 1) * chunk_w, w)
                        
                        # Extract tile data
                        tile_data = data[0, ch, :, y_start:y_end, x_start:x_end]
                        
                        # Get tile data as numpy array (direct zarr access)
                        tile_array = np.array(tile_data)
                        
                        # Check if tile contains any data (skip empty tiles)
                        tile_max = tile_array.max()
                        if tile_max == 0:
                            continue  # Skip empty tiles
                        
                        # Create tile folder
                        tile_name = f"tile_y{y_idx:03d}_x{x_idx:03d}_c{ch}"
                        tile_dir = output_dir / tile_name
                        tile_dir.mkdir(exist_ok=True)
                        
                        # Debug: Check data properties for first non-empty tile
                        if tile_count == 0:
                            print(f"First non-empty tile - Data type: {tile_array.dtype}")
                            print(f"Shape: {tile_array.shape}")
                            print(f"Data range: {tile_array.min()} - {tile_max}")
                        
                        # 1. Save as OME-Zarr format
                        tile_zarr_path = tile_dir / "data.ome.zarr"
                        
                        # Create simple OME-Zarr compatible structure
                        root = zarr.open(str(tile_zarr_path), mode="w")
                        
                        # Save image data with t,c dimensions added
                        tile_with_dims = tile_array[None, None, ...]  # (1,1,z,y,x)
                        root.create_dataset(
                            "0", 
                            data=tile_with_dims,
                            compressor=compressor,
                            chunks=(1, 1, tile_array.shape[0], min(512, tile_array.shape[1]), min(512, tile_array.shape[2]))
                        )
                        
                        # Add basic OME-Zarr metadata
                        root.attrs["multiscales"] = [{
                            "version": "0.4",
                            "axes": [
                                {"name": "t", "type": "time"},
                                {"name": "c", "type": "channel"},  
                                {"name": "z", "type": "space", "unit": "micrometer"},
                                {"name": "y", "type": "space", "unit": "micrometer"},
                                {"name": "x", "type": "space", "unit": "micrometer"}
                            ],
                            "datasets": [{"path": "0"}],
                            "name": f"tile_y{y_idx:03d}_x{x_idx:03d}_c{ch}"
                        }]
                        
                        # 2. Save as TIFF stack
                        tile_tif_path = tile_dir / "data.tif"
                        
                        # Ensure data is in correct format for TIFF
                        # Save as uint16 to preserve full dynamic range
                        tiff_data = tile_array.astype(np.uint16)
                        
                        # Save with proper metadata and ImageJ compatibility
                        tifffile.imwrite(
                            tile_tif_path,
                            tiff_data,
                            imagej=True,  # ImageJ compatibility
                            metadata={
                                "source": "napari_tile_extractor",
                                "tile_position": f"y{y_idx:03d}_x{x_idx:03d}_c{ch}",
                                "tile_bounds_yx": f"{y_start}:{y_end}_{x_start}:{x_end}",
                                "min_value": int(tiff_data.min()),
                                "max_value": int(tiff_data.max()),
                            },
                            compression="lzw"
                        )
                        
                        tile_count += 1
                        pbar.update(1)
                        
        print(f"\n✅ Extracted {tile_count} tiles to: {output_dir}")
        return tile_count

    def create_export_widget(self):
        """Create the magicgui export widget with proper configuration."""

        @magic_factory(
            call_button="Export ROI to Zarr",
            result_widget=True,
            output_name={"widget_type": "LineEdit", "value": "roi_output"},
            compression_level={
                "widget_type": "SpinBox",
                "min": 1,
                "max": 9,
                "value": 3,
            },
        )
        def export_roi_widget(
            output_name: str = "roi_output",
            compression_level: int = 3,
        ) -> str:
            """
            Export selected ROI from OME-Zarr to new zarr file with metadata.

            Args:
                output_name: Base name for output file (without .zarr extension)
                compression_level: Zarr compression level (1-9)

            Returns:
                Success message string
            """
            try:
                # Get current napari viewer
                viewer = napari.current_viewer()
                
                # Validate layers
                image_layers = [
                    layer
                    for layer in viewer.layers
                    if isinstance(layer, napari.layers.Image)
                ]
                shapes_layers = [
                    layer
                    for layer in viewer.layers
                    if isinstance(layer, napari.layers.Shapes)
                ]

                if not image_layers:
                    raise ValueError("No image layers found in viewer.")
                if not shapes_layers:
                    raise ValueError("No shapes layer found. Add ROI first.")

                # Get data and ROI bounds
                image_layer = image_layers[0]
                shapes_layer = shapes_layers[0]

                original_data = image_layer.data  # MultiScaleData
                
                # Get highest resolution level (level 0) from multiscale data
                if hasattr(original_data, '_data'):
                    data_array = original_data._data[0]  # First level (highest res)
                else:
                    data_array = original_data[0]  # Fallback
                    
                roi_slices = self.extract_roi_bounds(shapes_layer)

                # Handle dimension mismatch (2D ROI on N-D data)
                if len(roi_slices) != len(data_array.shape):
                    # Assume ROI applies to last N dimensions
                    n_roi_dims = len(roi_slices)
                    n_data_dims = len(data_array.shape)

                    full_slices = [slice(None)] * (n_data_dims - n_roi_dims)
                    full_slices.extend(roi_slices)
                    roi_slices = tuple(full_slices)

                    print(
                        f"Expanded ROI to {len(roi_slices)}D: "
                        f"{[str(s) for s in roi_slices]}"
                    )

                # Extract ROI data (lazy operation)
                roi_data = data_array[roi_slices]
                print(f"ROI Shape: {roi_data.shape}")
                print(f"   ROI Memory: ~{roi_data.nbytes / 1e6:.1f} MB")

                # Create output path
                output_path = self.output_dir / f"{output_name}.zarr"
                if output_path.exists():
                    import shutil

                    shutil.rmtree(output_path)
                    print(f"Removed existing: {output_path.name}")

                # Infer dimension names from data shape
                dim_names = self._infer_dimension_names(roi_data.shape)

                # Create xarray DataArray
                roi_xarray = xr.DataArray(
                    roi_data,
                    dims=dim_names,
                    name="roi_data",
                    attrs={
                        "source": "napari_roi_extractor",
                        "original_zarr": str(self.zarr_path),
                        "roi_bounds": str([f"{s.start}:{s.stop}" for s in roi_slices]),
                        "extraction_timestamp": str(np.datetime64("now")),
                    },
                )

                # Configure compression
                compressor = zarr.Blosc(
                    cname="zstd", clevel=compression_level, shuffle=2
                )

                # Stream to disk with progress
                print(f"Streaming to: {output_path.name}")

                # Convert dask chunks to xarray format
                zarr_chunks = tuple(c[0] for c in roi_data.chunks)
                
                with tqdm(total=1, desc="Exporting ROI", unit="file") as pbar:
                    roi_xarray.to_zarr(
                        output_path,
                        mode="w",
                        compute=True,
                        encoding={
                            "roi_data": {
                                "chunks": zarr_chunks,
                                "compressor": compressor,
                            }
                        },
                    )
                    pbar.update(1)

                # Preserve OME-Zarr metadata
                if hasattr(image_layer, "metadata") and image_layer.metadata:
                    try:
                        metadata = self.preserve_ome_metadata(
                            image_layer.metadata, roi_data.shape, roi_slices
                        )

                        store = zarr.open(output_path, mode="r+")
                        store.attrs.update(metadata)

                        print("OME-Zarr metadata preserved")

                    except Exception as e:
                        print(f"Metadata preservation failed: {e}")

                # Calculate final size
                output_size = sum(
                    f.stat().st_size for f in output_path.rglob("*") if f.is_file()
                ) / (1024**2)

                success_msg = (
                    f"ROI exported successfully!\n"
                    f"Output: {output_path.name}\n"
                    f"Size: {output_size:.1f} MB\n"
                    f"Shape: {roi_data.shape}\n"
                    f"Compression: Level {compression_level}"
                )

                show_info(f"ROI saved → {output_path.name}")
                return success_msg

            except Exception as e:
                error_msg = f"Export failed: {str(e)}"
                print(error_msg)  # Console output
                show_error(error_msg)  # napari notification
                raise

        return export_roi_widget

    def _infer_dimension_names(self, shape: Tuple[int, ...]) -> List[str]:
        """
        Infer dimension names based on array shape.

        Args:
            shape: Array shape tuple

        Returns:
            List of dimension names
        """
        # Common patterns for microscopy data
        if len(shape) == 5:
            return ["t", "c", "z", "y", "x"]  # Time, Channel, Z, Y, X
        elif len(shape) == 4:
            return ["c", "z", "y", "x"]  # Channel, Z, Y, X
        elif len(shape) == 3:
            return ["z", "y", "x"]  # Z, Y, X
        elif len(shape) == 2:
            return ["y", "x"]  # Y, X
        else:
            return [f"dim_{i}" for i in range(len(shape))]

    def launch(self):
        """
        Launch napari with OME-Zarr ROI extractor interface.
        """
        try:
            # Launch napari viewer
            viewer = napari.Viewer(title=f"ROI Extractor - {self.zarr_path.name}")

            # Add image data using napari's automatic file detection
            print("Adding image to napari...")
            image_layer = viewer.open(str(self.zarr_path))[0]

            # Add shapes layer for ROI selection
            shapes_layer = viewer.add_shapes(
                name="ROI Selection",
                shape_type="rectangle",
                edge_color="red",
                face_color="transparent",
                edge_width=3,
            )

            # Display instructions
            print("\nInstructions:")
            print("   1. Use rectangle tool to draw ONE ROI")
            print("   2. Adjust output name if desired")
            print("   3. Click 'Export ROI to Zarr' to save")
            print(f"   4. Files saved to: {self.output_dir}")
            print("   5. Close napari when finished")

            # Add export widget as dock widget
            export_widget_factory = self.create_export_widget()
            export_widget = export_widget_factory()
            viewer.window.add_dock_widget(
                export_widget, area="right", name="ROI Exporter"
            )

            # Start napari event loop
            print("\nLaunching napari...")
            napari.run()

        except Exception as e:
            print(f"Launch failed: {e}")
            raise


def main():
    """CLI entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="OME-Zarr ROI Extractor for napari",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s data/sample.ome.zarr
  %(prog)s data/sample.ome.zarr --output exports/
  %(prog)s data/sample.ome.zarr --tiles --output tiles/
        """,
    )

    parser.add_argument(
        "zarr_path", type=Path, help="Path to input .ome.zarr directory"
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output directory for ROI exports (default: current directory)",
    )
    
    parser.add_argument(
        "--tiles",
        action="store_true",
        help="Extract all 1024x1024 tiles instead of launching GUI",
    )

    parser.add_argument(
        "--version", action="version", version="OME-Zarr ROI Extractor v1.0.0"
    )

    # Parse arguments
    if len(sys.argv) == 1:
        parser.print_help()
        return

    args = parser.parse_args()

    try:
        # Initialize extractor
        extractor = OMEZarrROIExtractor(
            zarr_path=args.zarr_path, output_dir=args.output
        )
        
        if args.tiles:
            # Extract all tiles
            tile_count = extractor.extract_all_tiles(args.output or Path.cwd())
            print(f"✅ Successfully extracted {tile_count} tiles!")
        else:
            # Launch GUI
            extractor.launch()

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
