"""Tile visualization and exploration utilities."""

from typing import Dict, List, Optional, Set, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .tile_metadata import Region, TileIndex


class GridVisualizer:
    """Terminal-based grid display and exploration."""
    
    def __init__(self, tile_index: TileIndex, console: Optional[Console] = None):
        """Initialize visualizer with tile index."""
        self.tile_index = tile_index
        self.console = console or Console()
        self.grid_bounds = tile_index.get_grid_bounds()
        
    def render_ascii_grid(
        self, 
        channel: int = 0, 
        highlight_region: Optional[Region] = None,
        show_coordinates: bool = True,
        compact: bool = False
    ) -> None:
        """Render ASCII grid showing tile availability."""
        
        if not self.grid_bounds:
            self.console.print("[red]No tiles available[/red]")
            return
            
        y_min, y_max, x_min, x_max = self.grid_bounds
        
        # Build grid representation
        grid = {}
        for y in range(y_min, y_max):
            for x in range(x_min, x_max):
                tile = self.tile_index.get_tile(y, x, channel)
                grid[(y, x)] = tile is not None
        
        # Create title
        title = f"Tile Grid - Channel {channel}"
        if highlight_region:
            title += f" (Region: y{highlight_region.y_start}:{highlight_region.y_end}, x{highlight_region.x_start}:{highlight_region.x_end})"
        
        # Build grid display
        lines = []
        
        # Add column headers if requested
        if show_coordinates and not compact:
            header = "    "  # Row label space
            for x in range(x_min, x_max):
                if x % 5 == 0:
                    header += f"{x:2d}"
                else:
                    header += "  "
            lines.append(header)
        
        # Add rows
        for y in range(y_min, y_max):
            line = ""
            
            # Row label
            if show_coordinates and not compact:
                line += f"{y:2d}: " 
            
            # Grid cells
            for x in range(x_min, x_max):
                cell_char = self._get_cell_character(
                    y, x, grid, highlight_region, compact
                )
                line += cell_char
                
                # Add space between cells for readability (non-compact mode)
                if not compact:
                    line += " "
            
            lines.append(line)
        
        # Create panel with grid
        grid_text = "\n".join(lines)
        panel = Panel(
            grid_text,
            title=title,
            border_style="cyan"
        )
        
        self.console.print(panel)
        self._print_legend(compact)
    
    def _get_cell_character(
        self, 
        y: int, 
        x: int, 
        grid: Dict[Tuple[int, int], bool],
        highlight_region: Optional[Region],
        compact: bool
    ) -> str:
        """Get character representation for a grid cell."""
        
        has_tile = grid.get((y, x), False)
        in_highlight = (highlight_region and 
                       highlight_region.contains_tile(y, x))
        
        if compact:
            # Compact mode: single character per cell
            if in_highlight:
                return "[bold yellow]#[/bold yellow]" if has_tile else "[bold red].[/bold red]"
            else:
                return "[green]█[/green]" if has_tile else "[dim white]·[/dim white]"
        else:
            # Standard mode: two characters per cell for better visibility
            if in_highlight:
                return "[bold yellow]##[/bold yellow]" if has_tile else "[bold red]..[/bold red]"
            else:
                return "[green]██[/green]" if has_tile else "[dim white]··[/dim white]"
    
    def _print_legend(self, compact: bool) -> None:
        """Print legend explaining symbols."""
        legend_text = Text()
        
        if compact:
            legend_text.append("Legend: ")
            legend_text.append("█", style="green")
            legend_text.append(" = tile available, ")
            legend_text.append("·", style="dim white") 
            legend_text.append(" = no tile, ")
            legend_text.append("#", style="bold yellow")
            legend_text.append(" = highlighted region, ")
            legend_text.append(".", style="bold red")
            legend_text.append(" = missing in region")
        else:
            legend_text.append("Legend: ")
            legend_text.append("██", style="green")
            legend_text.append(" = tile available, ")
            legend_text.append("··", style="dim white")
            legend_text.append(" = no tile, ")
            legend_text.append("##", style="bold yellow") 
            legend_text.append(" = highlighted region, ")
            legend_text.append("..", style="bold red")
            legend_text.append(" = missing in region")
        
        self.console.print(legend_text)
    
    def show_tissue_map(self, channel: int = 0) -> None:
        """Show tissue distribution map with density information."""
        
        # Get tissue density by region
        regions = self._analyze_tissue_density(channel)
        
        self.console.print(f"\n[bold]Tissue Distribution Analysis - Channel {channel}[/bold]")
        self.render_ascii_grid(channel, compact=True)
        
        # Show density statistics
        if regions:
            self.console.print(f"\n[bold]High-density regions (good for reconstruction):[/bold]")
            for region_info in regions[:5]:  # Top 5
                region, density, tile_count = region_info
                self.console.print(
                    f"  y{region.y_start:02d}:{region.y_end:02d}, "
                    f"x{region.x_start:02d}:{region.x_end:02d} "
                    f"({tile_count}/{region.tile_count} tiles, {density:.0%} coverage)"
                )
    
    def _analyze_tissue_density(self, channel: int) -> List[Tuple[Region, float, int]]:
        """Analyze tissue density in different regions."""
        
        if not self.grid_bounds:
            return []
        
        y_min, y_max, x_min, x_max = self.grid_bounds
        regions = []
        
        # Analyze 5x5 regions with 2-tile overlap
        window_size = 5
        step_size = 3
        
        for y_start in range(y_min, y_max - window_size + 1, step_size):
            for x_start in range(x_min, x_max - window_size + 1, step_size):
                y_end = min(y_start + window_size, y_max)
                x_end = min(x_start + window_size, x_max)
                
                region = Region(y_start, y_end, x_start, x_end, channel)
                tiles = self.tile_index.get_tiles_in_region(region)
                
                if region.tile_count > 0:
                    density = len(tiles) / region.tile_count
                    if density > 0.6:  # Only show regions with >60% coverage
                        regions.append((region, density, len(tiles)))
        
        # Sort by density (descending)
        regions.sort(key=lambda x: x[1], reverse=True)
        return regions
    
    def display_region_stats(self, region: Region) -> None:
        """Display detailed statistics for a specific region."""
        
        tiles = self.tile_index.get_tiles_in_region(region) 
        height, width, size_mb = self.tile_index.estimate_output_size(region)
        
        # Build statistics
        stats_text = []
        stats_text.append(f"Region: y{region.y_start}:{region.y_end}, x{region.x_start}:{region.x_end} (channel {region.channel})")
        stats_text.append(f"Grid size: {region.height}x{region.width} tiles ({region.tile_count} total)")
        stats_text.append(f"Tiles found: {len(tiles)}/{region.tile_count} ({len(tiles)/region.tile_count:.1%} coverage)")
        stats_text.append(f"Output size: {height}x{width} pixels (~{size_mb} MB)")
        
        # Missing tiles
        missing_count = region.tile_count - len(tiles)
        if missing_count > 0:
            stats_text.append(f"Missing tiles: {missing_count}")
            
            missing_positions = []
            for y in range(region.y_start, region.y_end):
                for x in range(region.x_start, region.x_end):
                    if not self.tile_index.get_tile(y, x, region.channel):
                        missing_positions.append(f"y{y:02d}_x{x:02d}")
            
            if len(missing_positions) <= 10:
                stats_text.append(f"Missing: {', '.join(missing_positions)}")
            else:
                stats_text.append(f"Missing: {', '.join(missing_positions[:10])}... and {len(missing_positions)-10} more")
        
        # Create panel
        panel = Panel(
            "\n".join(stats_text),
            title="Region Statistics",
            border_style="blue"
        )
        
        self.console.print(panel)
        
        # Show visual representation
        self.render_ascii_grid(region.channel, highlight_region=region, compact=True)
    
    def suggest_regions(self, channel: int = 0) -> List[Region]:
        """Suggest good regions for reconstruction based on tissue density."""
        
        # Get high-density regions
        regions_analysis = self._analyze_tissue_density(channel)
        
        suggested = []
        size_categories = [
            ("Small (3x3)", 3, 3),
            ("Medium (5x5)", 5, 5), 
            ("Large (8x8)", 8, 8)
        ]
        
        for category_name, height, width in size_categories:
            best_region = None
            best_density = 0
            
            # Find best region of this size
            for region_info in regions_analysis:
                region, density, tile_count = region_info
                if (region.height == height and region.width == width and 
                    density > best_density):
                    best_region = region
                    best_density = density
            
            if best_region and best_density > 0.8:  # Only suggest if >80% coverage
                suggested.append(best_region)
        
        return suggested
    
    def print_suggestions(self, channel: int = 0) -> None:
        """Print suggested regions with CLI commands."""
        
        suggestions = self.suggest_regions(channel)
        
        if not suggestions:
            self.console.print("[yellow]No high-quality regions found for suggestions[/yellow]")
            return
        
        self.console.print(f"\n[bold]Suggested regions for channel {channel}:[/bold]")
        
        for i, region in enumerate(suggestions, 1):
            tiles = self.tile_index.get_tiles_in_region(region)
            density = len(tiles) / region.tile_count
            size_name = f"{region.height}x{region.width}"
            
            command = (f"tile-stitcher stitch --region "
                      f"y{region.y_start:03d}:{region.y_end:03d},"
                      f"x{region.x_start:03d}:{region.x_end:03d} "
                      f"--channel {channel}")
            
            self.console.print(f"\n{i}. {size_name} region ({density:.0%} coverage):")
            self.console.print(f"   [dim]{command}[/dim]")
    
    def show_overview(self, channel: int = 0) -> None:
        """Show complete overview: stats + grid + suggestions."""
        
        stats = self.tile_index.get_stats()
        
        # Dataset overview
        self.console.print(f"\n[bold]Dataset Overview - Channel {channel}[/bold]")
        overview_lines = [
            f"Total tiles: {stats.get('channel_counts', {}).get(channel, 0)}",
            f"Grid bounds: y{self.grid_bounds[0]}:{self.grid_bounds[1]}, x{self.grid_bounds[2]}:{self.grid_bounds[3]}",
            f"Coverage: {len([t for t in self.tile_index._tiles.values() if t.channel == channel])} positions"
        ]
        
        overview_panel = Panel(
            "\n".join(overview_lines),
            title=f"Channel {channel} Summary",
            border_style="green"
        )
        self.console.print(overview_panel)
        
        # Visual grid
        self.render_ascii_grid(channel, compact=False)
        
        # Suggestions
        self.print_suggestions(channel)