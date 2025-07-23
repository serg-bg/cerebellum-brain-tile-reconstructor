"""
Main CLI entry point for tile reconstruction tool.

This tool was developed for Morgane Marie and Baptiste Philippot 
to support analysis of large-scale human cerebellum tissue imaging data.
"""

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .tile_metadata import TileIndex, parse_region_string
from .tile_reconstructor import TileStitcher, preview_reconstruction
from .tile_browser import GridVisualizer
from .tile_selector import InteractiveSelector, quick_select_preset

console = Console()


def cmd_explore(args):
    """Explore available tiles and show statistics."""
    tiles_dir = Path(args.tiles_dir)
    
    try:
        console.print(f"\n[bold]Scanning tiles in: {tiles_dir}[/bold]")
        tile_index = TileIndex(tiles_dir)
        stats = tile_index.get_stats()
        
        if not stats:
            console.print("[red]No tiles found![/red]")
            return 1
        
        # Create visualizer
        visualizer = GridVisualizer(tile_index, console)
        
        # Show basic statistics table
        table = Table(title="Tile Dataset Statistics")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total tiles", str(stats['total_tiles']))
        table.add_row("Channels", ", ".join(map(str, stats['channels'])))
        table.add_row("Grid bounds", f"y{stats['grid_bounds'][0]}:{stats['grid_bounds'][1]}, x{stats['grid_bounds'][2]}:{stats['grid_bounds'][3]}")
        table.add_row("Total size", f"{stats['total_size_mb']} MB")
        
        for channel, count in stats['channel_counts'].items():
            table.add_row(f"Channel {channel} tiles", str(count))
        
        console.print(table)
        
        # Show visual representations based on options
        if args.grid:
            visualizer.show_overview(args.channel)
        elif args.tissue_map:
            visualizer.show_tissue_map(args.channel)
        elif args.suggest:
            visualizer.print_suggestions(args.channel)
        
        return 0
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1


def cmd_stitch(args):
    """Stitch tiles in a specified region."""
    tiles_dir = Path(args.tiles_dir)
    output_path = Path(args.output)
    
    try:
        # Initialize tile index
        tile_index = TileIndex(tiles_dir)
        
        # Parse region from different sources
        if args.load:
            # Load from JSON file
            selector = InteractiveSelector(tile_index, console)
            region = selector.load_selection(Path(args.load))
            if not region:
                console.print(f"[red]Failed to load selection from: {args.load}[/red]")
                return 1
            console.print(f"[green]Loaded selection from: {args.load}[/green]")
        elif args.region:
            # Parse region string
            region = parse_region_string(args.region, args.channel)
        else:
            console.print("[red]Error: Must specify either --region or --load[/red]")
            return 1
        
        # Show preview if requested
        if args.preview:
            preview_reconstruction(tile_index, region)
            
            if not args.force:
                response = input("\nProceed with reconstruction? (y/N): ")
                if response.lower() != 'y':
                    console.print("Reconstruction cancelled.")
                    return 0
        
        # Create stitcher and reconstruct
        stitcher = TileStitcher(tile_index)
        
        # Check memory requirements
        memory_ok, memory_msg = stitcher.validate_memory_requirements(region, args.max_memory)
        if not memory_ok:
            console.print(f"[red]{memory_msg}[/red]")
            if not args.force:
                return 1
        else:
            console.print(f"[green]{memory_msg}[/green]")
        
        # Perform reconstruction
        success = stitcher.stitch_region(
            region=region,
            output_path=output_path,
            fill_missing=args.fill_missing,
            compression=args.compression,
            z_range=args.z_range,
            progress=not args.quiet
        )
        
        return 0 if success else 1
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1


def cmd_select(args):
    """Interactive tile selection or preset selection."""
    tiles_dir = Path(args.tiles_dir)
    
    try:
        tile_index = TileIndex(tiles_dir)
        
        if args.preset:
            # Quick preset selection
            region = quick_select_preset(
                tile_index, 
                args.preset, 
                args.center_y, 
                args.center_x,
                args.channel
            )
            
            if not region:
                console.print(f"[red]Invalid preset '{args.preset}' or unable to create region[/red]")
                return 1
        
        elif args.interactive:
            # Interactive selection
            selector = InteractiveSelector(tile_index, console)
            selector.channel = args.channel  # Set initial channel
            region = selector.run_selection_ui()
            
            if not region:
                console.print("Selection cancelled.")
                return 0
        
        else:
            # Parse region string
            region = parse_region_string(args.region, args.channel)
        
        # Validate region
        valid, message = tile_index.validate_region(region)
        if not valid:
            console.print(f"[red]Invalid region: {message}[/red]")
            return 1
        
        # Show region info
        visualizer = GridVisualizer(tile_index, console)
        visualizer.display_region_stats(region)
        
        # Save selection if requested
        if args.save:
            save_path = Path(args.save)
            selector = InteractiveSelector(tile_index, console)
            if selector.save_selection(region, save_path):
                console.print(f"[green]Selection saved to: {save_path}[/green]")
            else:
                return 1
        
        # Print reconstruction command
        console.print(f"\n[bold]Reconstruction command:[/bold]")
        cmd = (f"tile-stitcher stitch --region "
               f"y{region.y_start:03d}:{region.y_end:03d},"
               f"x{region.x_start:03d}:{region.x_end:03d} "
               f"--channel {region.channel}")
        console.print(f"[dim]{cmd}[/dim]")
        
        return 0
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1


def create_parser():
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="tile-stitcher",
        description="Reconstruct brain tissue regions from microscopy tiles"
    )
    
    parser.add_argument(
        "--tiles-dir",
        type=str,
        default="tiles",
        help="Directory containing tiles (default: tiles)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Explore command
    explore_parser = subparsers.add_parser("explore", help="Browse available tiles")
    explore_parser.add_argument(
        "--channel",
        type=int,
        default=0,
        help="Channel to explore (default: 0)"
    )
    explore_parser.add_argument(
        "--suggest",
        action="store_true",
        help="Show suggested regions"
    )
    explore_parser.add_argument(
        "--grid",
        action="store_true",
        help="Show visual grid overview"
    )
    explore_parser.add_argument(
        "--tissue-map",
        action="store_true",
        help="Show tissue distribution map"
    )
    
    # Select command
    select_parser = subparsers.add_parser("select", help="Select tiles for reconstruction")
    select_parser.add_argument(
        "--channel",
        type=int,
        default=0,
        help="Channel to select from (default: 0)"
    )
    select_parser.add_argument(
        "--region",
        type=str,
        help="Region string (e.g., 'y015:020,x005:010')"
    )
    select_parser.add_argument(
        "--interactive",
        action="store_true",
        help="Use interactive selection interface"
    )
    select_parser.add_argument(
        "--preset",
        choices=["small", "medium", "large"],
        help="Use preset region size"
    )
    select_parser.add_argument(
        "--center-y",
        type=int,
        help="Center Y coordinate for preset (auto-detect if not specified)"
    )
    select_parser.add_argument(
        "--center-x",
        type=int,
        help="Center X coordinate for preset (auto-detect if not specified)"
    )
    select_parser.add_argument(
        "--save",
        type=str,
        help="Save selection to JSON file"
    )
    
    # Stitch command
    stitch_parser = subparsers.add_parser("stitch", help="Reconstruct a tile region")
    stitch_parser.add_argument(
        "--region",
        type=str,
        help="Region to reconstruct (e.g., 'y015:020,x005:010')"
    )
    stitch_parser.add_argument(
        "--load",
        type=str,
        help="Load region from saved selection JSON file"
    )
    stitch_parser.add_argument(
        "--output",
        type=str,
        default="reconstructed_region.tif",
        help="Output file path (default: reconstructed_region.tif)"
    )
    stitch_parser.add_argument(
        "--channel",
        type=int,
        default=0,
        help="Channel to reconstruct (default: 0)"
    )
    stitch_parser.add_argument(
        "--fill-missing",
        choices=["zero", "skip"],
        default="zero",
        help="How to handle missing tiles (default: zero)"
    )
    stitch_parser.add_argument(
        "--compression",
        choices=["none", "lzw", "deflate"],
        default="lzw",
        help="TIFF compression method (default: lzw)"
    )
    stitch_parser.add_argument(
        "--z-range",
        type=str,
        help="Z-slice range (e.g., '5:15')"
    )
    stitch_parser.add_argument(
        "--max-memory",
        type=int,
        default=8192,
        help="Maximum memory usage in MB (default: 8192)"
    )
    stitch_parser.add_argument(
        "--preview",
        action="store_true",
        help="Show reconstruction preview before processing"
    )
    stitch_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts"
    )
    stitch_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress bars"
    )
    
    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Show help if no command specified
    if not args.command:
        parser.print_help()
        return 1
    
    # Parse z-range if provided
    if hasattr(args, 'z_range') and args.z_range:
        try:
            z_start, z_end = map(int, args.z_range.split(':'))
            args.z_range = (z_start, z_end)
        except ValueError:
            console.print(f"[red]Invalid z-range format: {args.z_range}. Use format like '5:15'[/red]")
            return 1
    
    # Dispatch to command handlers
    if args.command == "explore":
        return cmd_explore(args)
    elif args.command == "select":
        return cmd_select(args)
    elif args.command == "stitch":
        return cmd_stitch(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())