"""Interactive tile selection interface."""

import json
import sys
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

# Cross-platform terminal handling
try:
    # Unix/Linux/macOS
    import termios
    import tty
    HAS_TERMIOS = True
except ImportError:
    # Windows
    import msvcrt
    HAS_TERMIOS = False

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from .tile_metadata import Region, TileIndex


class InteractiveSelector:
    """Keyboard-driven tile selection interface."""
    
    def __init__(self, tile_index: TileIndex, console: Optional[Console] = None):
        """Initialize selector with tile index."""
        self.tile_index = tile_index
        self.console = console or Console()
        self.grid_bounds = tile_index.get_grid_bounds()
        
        # Selection state
        self.channel = 0
        self.cursor_y = 0
        self.cursor_x = 0
        self.selection_start = None
        self.selection_end = None
        self.selected_region = None
        
        # Initialize cursor position to first available tile
        self._init_cursor_position()
    
    def _init_cursor_position(self):
        """Initialize cursor to first available tile."""
        if not self.grid_bounds:
            return
            
        y_min, y_max, x_min, x_max = self.grid_bounds
        
        # Find first available tile
        for y in range(y_min, y_max):
            for x in range(x_min, x_max):
                if self.tile_index.get_tile(y, x, self.channel):
                    self.cursor_y = y
                    self.cursor_x = x
                    return
    
    def run_selection_ui(self) -> Optional[Region]:
        """Run interactive selection interface."""
        
        if not self.grid_bounds:
            self.console.print("[red]No tiles available for selection[/red]")
            return None
        
        self.console.print("\n[bold]Interactive Tile Selection[/bold]")
        self.console.print("Controls: Arrow keys to move, Space to select region corners, Enter to confirm, Q to quit")
        self.console.print("Press any key to start...")
        self._wait_for_key()
        
        try:
            with Live(self._render_selection_display(), refresh_per_second=10, console=self.console) as live:
                while True:
                    key = self._get_key()
                    
                    if key == 'q' or key == 'Q':
                        return None
                    elif key == '\r' or key == '\n':  # Enter
                        if self.selected_region:
                            return self.selected_region
                        else:
                            self.console.print("\n[yellow]No region selected. Use Space to select corners.[/yellow]")
                    elif key == ' ':  # Space
                        self._handle_space_key()
                    elif key == 'c' or key == 'C':  # Toggle channel
                        self._toggle_channel()
                    elif key == '\033':  # Arrow keys start with escape
                        self._handle_arrow_keys()
                    
                    live.update(self._render_selection_display())
        
        except KeyboardInterrupt:
            return None
    
    def _handle_space_key(self):
        """Handle space key for region selection."""
        current_pos = (self.cursor_y, self.cursor_x)
        
        if self.selection_start is None:
            # Start selection
            self.selection_start = current_pos
            self.selection_end = None
            self.selected_region = None
        elif self.selection_end is None:
            # End selection
            self.selection_end = current_pos
            self._update_selected_region()
        else:
            # Reset selection
            self.selection_start = current_pos
            self.selection_end = None
            self.selected_region = None
    
    def _toggle_channel(self):
        """Toggle between available channels."""
        channels = self.tile_index.get_available_channels()
        if len(channels) > 1:
            current_idx = channels.index(self.channel)
            next_idx = (current_idx + 1) % len(channels)
            self.channel = channels[next_idx]
            
            # Reset selection when changing channels
            self.selection_start = None
            self.selection_end = None
            self.selected_region = None
    
    def _handle_arrow_keys(self):
        """Handle arrow key navigation."""
        # Read the full escape sequence
        try:
            next_char = self._get_key_raw()
            if next_char == '[':
                direction = self._get_key_raw()
                
                y_min, y_max, x_min, x_max = self.grid_bounds
                
                if direction == 'A':  # Up
                    self.cursor_y = max(y_min, self.cursor_y - 1)
                elif direction == 'B':  # Down
                    self.cursor_y = min(y_max - 1, self.cursor_y + 1)
                elif direction == 'D':  # Left
                    self.cursor_x = max(x_min, self.cursor_x - 1)
                elif direction == 'C':  # Right
                    self.cursor_x = min(x_max - 1, self.cursor_x + 1)
        except:
            pass
    
    def _update_selected_region(self):
        """Update the selected region based on start and end points."""
        if self.selection_start and self.selection_end:
            y1, x1 = self.selection_start
            y2, x2 = self.selection_end
            
            # Ensure proper ordering
            y_start = min(y1, y2)
            y_end = max(y1, y2) + 1
            x_start = min(x1, x2)
            x_end = max(x1, x2) + 1
            
            self.selected_region = Region(y_start, y_end, x_start, x_end, self.channel)
    
    def _render_selection_display(self) -> Panel:
        """Render the current selection display."""
        
        lines = []
        y_min, y_max, x_min, x_max = self.grid_bounds
        
        # Header with coordinates and channel info
        header = f"Cursor: y{self.cursor_y:02d}_x{self.cursor_x:02d} | Channel: {self.channel}"
        if self.selection_start:
            start_y, start_x = self.selection_start
            header += f" | Start: y{start_y:02d}_x{start_x:02d}"
        if self.selected_region:
            header += f" | Selected: {self.selected_region.height}x{self.selected_region.width} tiles"
        
        lines.append(header)
        lines.append("")
        
        # Column headers
        col_header = "    "
        for x in range(x_min, x_max):
            if x % 5 == 0:
                col_header += f"{x:2d}"
            else:
                col_header += "  "
        lines.append(col_header)
        
        # Grid rows
        for y in range(y_min, y_max):
            row = f"{y:2d}: "
            
            for x in range(x_min, x_max):
                cell = self._get_selection_cell(y, x)
                row += cell + " "
            
            lines.append(row)
        
        # Footer with statistics
        lines.append("")
        if self.selected_region:
            tiles = self.tile_index.get_tiles_in_region(self.selected_region)
            height, width, size_mb = self.tile_index.estimate_output_size(self.selected_region)
            
            footer = (f"Selection: {len(tiles)}/{self.selected_region.tile_count} tiles "
                     f"({height}x{width} pixels, ~{size_mb}MB)")
            lines.append(footer)
        
        # Create panel
        content = "\n".join(lines)
        title = "Interactive Tile Selection"
        
        return Panel(
            content,
            title=title,
            border_style="cyan"
        )
    
    def _get_selection_cell(self, y: int, x: int) -> str:
        """Get the display character for a cell in selection mode."""
        
        has_tile = self.tile_index.get_tile(y, x, self.channel) is not None
        is_cursor = (y == self.cursor_y and x == self.cursor_x)
        is_selected = self._is_in_selection(y, x)
        is_start = (self.selection_start and self.selection_start == (y, x))
        is_end = (self.selection_end and self.selection_end == (y, x))
        
        # Priority order: cursor > start/end > selected > has_tile
        if is_cursor:
            return "[bold magenta]><[/bold magenta]"
        elif is_start:
            return "[bold yellow]S[/bold yellow]" if has_tile else "[bold red]s[/bold red]"
        elif is_end:
            return "[bold yellow]E[/bold yellow]" if has_tile else "[bold red]e[/bold red]"
        elif is_selected:
            return "[bold yellow]##[/bold yellow]" if has_tile else "[bold red]..[/bold red]"
        elif has_tile:
            return "[green]██[/green]"
        else:
            return "[dim white]··[/dim white]"
    
    def _is_in_selection(self, y: int, x: int) -> bool:
        """Check if a position is within the current selection."""
        if not (self.selection_start and self.selection_end):
            return False
        
        y1, x1 = self.selection_start
        y2, x2 = self.selection_end
        
        y_min, y_max = min(y1, y2), max(y1, y2)
        x_min, x_max = min(x1, x2), max(x1, x2)
        
        return y_min <= y <= y_max and x_min <= x <= x_max
    
    def _get_key(self) -> str:
        """Get a single key press."""
        try:
            return self._get_key_raw()
        except:
            return ''
    
    def _get_key_raw(self) -> str:
        """Get raw key input (cross-platform)."""
        if HAS_TERMIOS:
            # Unix/Linux/macOS
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.cbreak(fd)
                key = sys.stdin.read(1)
                return key
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        else:
            # Windows
            key = msvcrt.getch()
            if isinstance(key, bytes):
                try:
                    return key.decode('utf-8')
                except UnicodeDecodeError:
                    return ''
            return key
    
    def _wait_for_key(self):
        """Wait for any key press."""
        self._get_key()
    
    def save_selection(self, region: Region, filepath: Path) -> bool:
        """Save a selection to a JSON file."""
        try:
            selection_data = {
                "region": {
                    "y_start": region.y_start,
                    "y_end": region.y_end,
                    "x_start": region.x_start,
                    "x_end": region.x_end,
                    "channel": region.channel
                },
                "metadata": {
                    "tile_count": region.tile_count,
                    "dimensions": f"{region.height}x{region.width}",
                    "created_by": "tile-stitcher interactive selector"
                }
            }
            
            with open(filepath, 'w') as f:
                json.dump(selection_data, f, indent=2)
            
            return True
        except Exception as e:
            self.console.print(f"[red]Error saving selection: {e}[/red]")
            return False
    
    def load_selection(self, filepath: Path) -> Optional[Region]:
        """Load a selection from a JSON file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            region_data = data['region']
            region = Region(
                y_start=region_data['y_start'],
                y_end=region_data['y_end'],
                x_start=region_data['x_start'],
                x_end=region_data['x_end'],
                channel=region_data['channel']
            )
            
            return region
        except Exception as e:
            self.console.print(f"[red]Error loading selection: {e}[/red]")
            return None


def quick_select_preset(
    tile_index: TileIndex, 
    preset: str, 
    center_y: Optional[int] = None, 
    center_x: Optional[int] = None,
    channel: int = 0
) -> Optional[Region]:
    """Quick selection presets without interactive interface."""
    
    presets = {
        "small": (3, 3),
        "medium": (5, 5),
        "large": (8, 8)
    }
    
    if preset not in presets:
        return None
    
    height, width = presets[preset]
    
    # Auto-center if not specified
    if center_y is None or center_x is None:
        grid_bounds = tile_index.get_grid_bounds()
        if not grid_bounds:
            return None
        
        y_min, y_max, x_min, x_max = grid_bounds
        center_y = center_y or (y_min + y_max) // 2
        center_x = center_x or (x_min + x_max) // 2
    
    # Calculate region bounds
    y_start = max(0, center_y - height // 2)
    y_end = y_start + height
    x_start = max(0, center_x - width // 2)
    x_end = x_start + width
    
    return Region(y_start, y_end, x_start, x_end, channel)