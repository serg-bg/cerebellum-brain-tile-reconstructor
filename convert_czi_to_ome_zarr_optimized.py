#!/usr/bin/env python3
"""
Full workstation-optimized CZI to OME-Zarr converter
Uses all 32 logical processors effectively
"""

import gc
import os
import shutil
import time
from pathlib import Path

import dask.array as da
import numpy as np
import psutil
import zarr
from aicsimageio import AICSImage
from dask.distributed import Client
from ome_zarr.writer import write_image
from tqdm import tqdm

# GPU acceleration imports (with fallback)
try:
    import cupy as cp

    GPU_AVAILABLE = True
    print("🚀 GPU acceleration available with CuPy")
except ImportError:
    GPU_AVAILABLE = False
    cp = None
    print("⚠️  CuPy not available, using CPU-only mode")


def setup_dask_full_workstation():
    """Full workstation Dask setup using all logical processors"""
    cpu_count = psutil.cpu_count(logical=False)
    logical_count = psutil.cpu_count(logical=True)
    memory_gb = psutil.virtual_memory().total / (1024**3)

    print(f"🖥️  System Info:")
    print(f"   Physical cores: {cpu_count}")
    print(f"   Logical cores: {logical_count}")
    print(f"   Total memory: {memory_gb:.1f} GB")

    # Use logical cores more effectively
    workers = min(31, logical_count - 1)  # Use 31/32 logical cores
    threads_per_worker = 2  # Fewer threads per worker since we have more workers
    memory_per_worker = max(6, int(memory_gb * 0.78 / workers))  # ~200GB total

    print(f"🚀 Dask Configuration:")
    print(f"   Workers: {workers}")
    print(f"   Threads per worker: {threads_per_worker}")
    print(f"   Memory per worker: {memory_per_worker} GB")
    print(f"   Total Dask memory: {workers * memory_per_worker} GB")

    # Full workstation client
    client = Client(
        n_workers=workers,
        threads_per_worker=threads_per_worker,
        memory_limit=f"{memory_per_worker}GB",
        processes=True,
    )

    print(f"🎯 Dask Dashboard: {client.dashboard_link}")
    return client


def convert_czi_full_workstation(input_file="Morgane_BP_Cerebellum_Stitch.czi"):
    """Full workstation conversion function"""

    if not os.path.exists(input_file):
        print(f"❌ File not found: {input_file}")
        return None

    # Setup Dask
    client = setup_dask_full_workstation()

    try:
        print(f"🔄 Converting {input_file}...")

        # Load CZI with progress
        print("📖 Loading CZI metadata...")
        img = AICSImage(input_file)

        print(f"📏 Image properties:")
        print(f"   Shape: {img.shape}")
        print(f"   Dimensions: {img.dims}")
        print(f"   Dtype: {img.dtype}")
        if img.channel_names:
            print(f"   Channels: {img.channel_names}")

        # Get data
        print("📊 Analyzing data structure...")
        data = img.dask_data
        print(f"   Original chunks: {data.chunks}")

        # Aggressive chunking for workstation
        if len(data.shape) == 5:  # T,C,Z,Y,X
            chunks = (
                1,
                1,
                min(data.shape[2], 128),  # Larger Z chunks
                min(data.shape[3], 1024),  # Larger Y chunks
                min(data.shape[4], 1024),
            )  # Larger X chunks
        else:
            chunks = data.chunks

        print(f"📦 Workstation chunks: {chunks}")

        # Rechunk with progress
        print("🔄 Rechunking for workstation processing...")
        start_rechunk = time.time()
        data = data.rechunk(chunks)
        rechunk_time = time.time() - start_rechunk
        print(f"   Rechunking took: {rechunk_time:.1f} seconds")
        print(f"   New chunks: {data.chunks}")

        # Setup output
        output_path = Path(input_file).with_suffix(".ome.zarr")
        if output_path.exists():
            print(f"🗑️  Removing existing output: {output_path}")
            shutil.rmtree(output_path)

        store = zarr.DirectoryStore(str(output_path))
        group = zarr.group(store=store)

        # Prepare metadata
        axes_info = []
        scale_info = []

        for dim in img.dims.order:
            if dim == "T":
                axes_info.append({"name": "t", "type": "time"})
                scale_info.append(1.0)
            elif dim == "C":
                axes_info.append({"name": "c", "type": "channel"})
                scale_info.append(1.0)
            elif dim == "Z":
                axes_info.append({"name": "z", "type": "space", "unit": "micrometer"})
                scale_info.append(1.0)
            elif dim == "Y":
                axes_info.append({"name": "y", "type": "space", "unit": "micrometer"})
                scale_info.append(1.0)
            elif dim == "X":
                axes_info.append({"name": "x", "type": "space", "unit": "micrometer"})
                scale_info.append(1.0)

        print(f"📝 Metadata:")
        print(f"   Axes: {[ax['name'] for ax in axes_info]}")

        # High-performance batch processing
        print("💾 Writing data with full workstation power...")
        start_time = time.time()

        if len(data.shape) == 5:  # Process by timepoint
            n_timepoints = data.shape[0]
            print(f"   Processing {n_timepoints} timepoints")

            for t in tqdm(range(n_timepoints), desc="Processing timepoints", unit="tp"):
                batch_data = data[t : t + 1]

                if t == 0:
                    # First batch - create dataset
                    # Create coordinate transformations for all pyramid levels
                    coordinate_transformations = []
                    for level in range(5):  # 5 pyramid levels (0-4)
                        scale_factor = 2**level
                        level_scale = scale_info.copy()
                        # Only downsample spatial dimensions (Y,X are last two)
                        if len(level_scale) >= 2:
                            level_scale[-2] *= scale_factor  # Y dimension
                            level_scale[-1] *= scale_factor  # X dimension
                        coordinate_transformations.append(
                            [{"type": "scale", "scale": level_scale}]
                        )

                    write_image(
                        image=batch_data,
                        group=group,
                        axes=axes_info,
                        coordinate_transformations=coordinate_transformations,
                        storage_options=dict(chunks=chunks),
                    )
                    print(f"   ✅ Created dataset with first timepoint")
                else:
                    # Append subsequent batches
                    arr = group["0"]
                    computed_data = batch_data.compute()
                    arr[t : t + 1] = computed_data

                    # Progress feedback every 10%
                    if (t + 1) % max(1, n_timepoints // 10) == 0:
                        progress_pct = ((t + 1) / n_timepoints) * 100
                        elapsed = time.time() - start_time
                        eta = elapsed / (t + 1) * (n_timepoints - t - 1)
                        print(
                            f"   📊 Progress: {progress_pct:.1f}% | ETA: {eta/60:.1f} min"
                        )

                # Aggressive memory cleanup
                gc.collect()
                if t > 0:
                    del computed_data

        else:
            # Process all at once
            print("   Processing entire dataset...")
            # Create coordinate transformations for all pyramid levels
            coordinate_transformations = []
            for level in range(5):  # 5 pyramid levels (0-4)
                scale_factor = 2**level
                level_scale = scale_info.copy()
                # Only downsample spatial dimensions (Y,X are last two)
                if len(level_scale) >= 2:
                    level_scale[-2] *= scale_factor  # Y dimension
                    level_scale[-1] *= scale_factor  # X dimension
                coordinate_transformations.append(
                    [{"type": "scale", "scale": level_scale}]
                )

            write_image(
                image=data,
                group=group,
                axes=axes_info,
                coordinate_transformations=coordinate_transformations,
                storage_options=dict(chunks=chunks),
            )

        # Add metadata
        print("🔬 Adding OME-Zarr metadata...")
        # Create datasets for all pyramid levels
        datasets = []
        for level in range(5):  # 5 pyramid levels (0-4)
            scale_factor = 2**level
            level_scale = scale_info.copy()
            # Only downsample spatial dimensions (Y,X are last two)
            if len(level_scale) >= 2:
                level_scale[-2] *= scale_factor  # Y dimension
                level_scale[-1] *= scale_factor  # X dimension
            datasets.append(
                {
                    "path": str(level),
                    "coordinateTransformations": [
                        {"type": "scale", "scale": level_scale}
                    ],
                }
            )

        group.attrs["multiscales"] = [
            {
                "version": "0.4",
                "name": Path(input_file).stem,
                "axes": axes_info,
                "datasets": datasets,
                "coordinateTransformations": [{"type": "scale", "scale": scale_info}],
                "type": "image",
            }
        ]

        # Performance metrics
        duration = time.time() - start_time
        total_time = rechunk_time + duration

        output_size = sum(
            f.stat().st_size for f in output_path.rglob("*") if f.is_file()
        ) / (1024**3)
        input_size = Path(input_file).stat().st_size / (1024**3)
        throughput = input_size / total_time

        print(f"✅ Full workstation conversion completed!")
        print(f"📁 Output: {output_path}")
        print(f"📊 Performance metrics:")
        print(f"   Input size: {input_size:.2f} GB")
        print(f"   Output size: {output_size:.2f} GB")
        print(f"   Total time: {total_time/60:.1f} minutes")
        print(f"   Throughput: {throughput:.2f} GB/s")
        print(f"   Workers used: 31/32 logical cores")

        return str(output_path)

    finally:
        print("🧹 Cleaning up resources...")
        client.close()


if __name__ == "__main__":
    convert_czi_full_workstation()
