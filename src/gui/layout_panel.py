"""
Layout Panel — Canvas-based room grid visualiser.
Displays furniture placed in a room on a tile grid.
Supports manual drag-to-place, highlight on hover, and selection.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional, Tuple, Callable

from src.data.furniture_db import FurnitureItem, FURNITURE_DB, ALL_STATS
from src.data.room_data import RoomDefinition
from src.data.save_parser import PlacedFurniture

# Visual constants
TILE_SIZE   = 48      # pixels per grid tile
GRID_COLOR  = "#CCCCCC"
BG_COLOR    = "#F5F5F5"
WALL_COLOR  = "#B0C4DE"
FLOOR_COLOR = "#E8E0D0"
SELECT_OUTLINE = "#FF6600"
HOVER_OUTLINE  = "#0066CC"
EMPTY_TILE_FILL = "#FAFAFA"


class LayoutCanvas(tk.Canvas):
    """
    A Canvas widget that displays a room grid and the furniture placed in it.

    External API
    ------------
    load_room(room_def, placements)  – redraw with new room/placements data
    get_placements()                  – return current list of PlacedFurniture
    clear()                           – remove all placed items
    set_on_change(callback)           – called whenever placements change
    """

    def __init__(self, parent: tk.Widget, **kwargs):
        super().__init__(parent, bg=BG_COLOR, **kwargs)
        self._room: Optional[RoomDefinition] = None
        self._placements: List[PlacedFurniture] = []
        self._selected: Optional[PlacedFurniture] = None
        self._hover_tile: Optional[Tuple[int, int]] = None
        self._on_change: Optional[Callable] = None

        # Drag state
        self._drag_item: Optional[PlacedFurniture] = None
        self._drag_offset: Tuple[int, int] = (0, 0)

        self.bind("<Motion>",        self._on_motion)
        self.bind("<Button-1>",      self._on_click)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Button-3>",      self._on_right_click)

    # ── Public API ────────────────────────────────────────────────────────

    def load_room(self, room_def: RoomDefinition, placements: List[PlacedFurniture]) -> None:
        self._room = room_def
        self._placements = list(placements)
        self._selected = None
        self._resize_canvas()
        self._redraw()

    def get_placements(self) -> List[PlacedFurniture]:
        return list(self._placements)

    def clear(self) -> None:
        self._placements = []
        self._selected = None
        self._redraw()
        self._notify_change()

    def set_on_change(self, callback: Callable) -> None:
        self._on_change = callback

    def add_furniture(self, item: FurnitureItem, x: int, y: int) -> bool:
        """Place *item* at grid tile (x, y). Returns False if occupied."""
        if self._room is None:
            return False
        if self._is_occupied(x, y, item.width, item.height, exclude=None):
            return False
        pf = PlacedFurniture(item_id=item.item_id, x=x, y=y,
                             room_type=self._room.room_type)
        self._placements.append(pf)
        self._redraw()
        self._notify_change()
        return True

    def remove_selected(self) -> None:
        if self._selected is not None:
            try:
                self._placements.remove(self._selected)
            except ValueError:
                pass
            self._selected = None
            self._redraw()
            self._notify_change()

    # ── Internal helpers ──────────────────────────────────────────────────

    def _resize_canvas(self) -> None:
        if self._room is None:
            return
        w = self._room.grid_width  * TILE_SIZE + 2
        h = self._room.grid_height * TILE_SIZE + 2
        self.config(width=w, height=h)

    def _px(self, tile: int) -> int:
        """Tile coordinate to pixel (top-left of tile)."""
        return tile * TILE_SIZE + 1

    def _tile(self, px: int) -> int:
        """Pixel to tile coordinate."""
        return (px - 1) // TILE_SIZE

    def _redraw(self) -> None:
        self.delete("all")
        if self._room is None:
            return
        self._draw_background()
        self._draw_grid()
        self._draw_furniture()

    def _draw_background(self) -> None:
        r = self._room
        # Wall zone
        for y in range(r.wall_rows):
            for x in range(r.grid_width):
                self._draw_tile(x, y, WALL_COLOR)
        # Floor zone
        for y in range(r.floor_start, r.grid_height):
            for x in range(r.grid_width):
                self._draw_tile(x, y, FLOOR_COLOR)
        # Transition zone
        for y in range(r.wall_rows, r.floor_start):
            for x in range(r.grid_width):
                mid_color = "#D9D0C0"
                self._draw_tile(x, y, mid_color)

    def _draw_tile(self, x: int, y: int, fill: str) -> None:
        px = self._px(x)
        py = self._px(y)
        self.create_rectangle(
            px, py, px + TILE_SIZE, py + TILE_SIZE,
            fill=fill, outline=GRID_COLOR, width=1,
        )

    def _draw_grid(self) -> None:
        if self._room is None:
            return
        r = self._room
        # Zone labels
        if r.wall_rows > 0:
            self.create_text(
                self._px(0) + 4, self._px(0) + 4,
                text="Wall", anchor="nw",
                fill="#666666", font=("Arial", 7),
            )
        self.create_text(
            self._px(0) + 4, self._px(r.floor_start) + 4,
            text="Floor", anchor="nw",
            fill="#666666", font=("Arial", 7),
        )

    def _draw_furniture(self) -> None:
        for pf in self._placements:
            item = FURNITURE_DB.get(pf.item_id)
            if item is None:
                continue
            px = self._px(pf.x)
            py = self._px(pf.y)
            pw = item.width  * TILE_SIZE
            ph = item.height * TILE_SIZE

            is_selected = (pf is self._selected)
            outline_color = SELECT_OUTLINE if is_selected else "#444444"
            outline_width = 3 if is_selected else 1

            # Furniture body
            self.create_rectangle(
                px + 1, py + 1,
                px + pw - 1, py + ph - 1,
                fill=item.color,
                outline=outline_color,
                width=outline_width,
                tags=("furniture",),
            )

            # Name label (truncated to fit)
            max_chars = max(1, (item.width * TILE_SIZE) // 7)
            label = item.name if len(item.name) <= max_chars else item.name[:max_chars - 1] + "…"
            font_size = max(6, min(9, TILE_SIZE // 6))
            self.create_text(
                px + pw // 2, py + ph // 2,
                text=label,
                fill="#000000",
                font=("Arial", font_size, "bold"),
                width=pw - 4,
                tags=("furniture",),
            )

            # Stat mini-badges (top-right corner)
            if item.stat_total > 0:
                badge_text = f"+{item.stat_total}"
                self.create_text(
                    px + pw - 3, py + 3,
                    text=badge_text,
                    anchor="ne",
                    fill="#1a1a1a",
                    font=("Arial", 6),
                    tags=("furniture",),
                )

    def _placement_at(self, x: int, y: int) -> Optional[PlacedFurniture]:
        """Return the PlacedFurniture that occupies tile (x, y), or None."""
        for pf in reversed(self._placements):
            item = FURNITURE_DB.get(pf.item_id)
            if item is None:
                continue
            if (pf.x <= x < pf.x + item.width and
                    pf.y <= y < pf.y + item.height):
                return pf
        return None

    def _is_occupied(
        self, x: int, y: int, w: int, h: int,
        exclude: Optional[PlacedFurniture]
    ) -> bool:
        if self._room is None:
            return True
        if x < 0 or y < 0:
            return True
        if x + w > self._room.grid_width or y + h > self._room.grid_height:
            return True
        for pf in self._placements:
            if pf is exclude:
                continue
            item = FURNITURE_DB.get(pf.item_id)
            if item is None:
                continue
            if (x < pf.x + item.width and x + w > pf.x and
                    y < pf.y + item.height and y + h > pf.y):
                return True
        return False

    # ── Event handlers ────────────────────────────────────────────────────

    def _on_motion(self, event: tk.Event) -> None:
        tx = self._tile(event.x)
        ty = self._tile(event.y)
        if (tx, ty) != self._hover_tile:
            self._hover_tile = (tx, ty)
            self._redraw()
            pf = self._placement_at(tx, ty)
            if pf:
                item = FURNITURE_DB.get(pf.item_id)
                if item:
                    # Highlight hovered item
                    ix = self._px(pf.x)
                    iy = self._px(pf.y)
                    iw = item.width  * TILE_SIZE
                    ih = item.height * TILE_SIZE
                    self.create_rectangle(
                        ix + 1, iy + 1, ix + iw - 1, iy + ih - 1,
                        outline=HOVER_OUTLINE, width=2, fill="",
                    )

    def _on_click(self, event: tk.Event) -> None:
        tx = self._tile(event.x)
        ty = self._tile(event.y)
        pf = self._placement_at(tx, ty)
        self._selected = pf
        self._drag_item = pf
        if pf:
            self._drag_offset = (tx - pf.x, ty - pf.y)
        self._redraw()

    def _on_release(self, event: tk.Event) -> None:
        if self._drag_item is not None:
            tx = self._tile(event.x)
            ty = self._tile(event.y)
            item = FURNITURE_DB.get(self._drag_item.item_id)
            if item:
                new_x = tx - self._drag_offset[0]
                new_y = ty - self._drag_offset[1]
                if not self._is_occupied(
                    new_x, new_y, item.width, item.height,
                    exclude=self._drag_item,
                ):
                    # Check anchor zone compatibility
                    positions = self._room.valid_anchor_positions(
                        item.anchor, item.width, item.height
                    ) if self._room else []
                    if (new_x, new_y) in positions or True:  # allow free placement
                        self._drag_item.x = max(0, min(new_x, (self._room.grid_width  - item.width)  if self._room else 0))
                        self._drag_item.y = max(0, min(new_y, (self._room.grid_height - item.height) if self._room else 0))
                        self._notify_change()
        self._drag_item = None
        self._redraw()

    def _on_right_click(self, event: tk.Event) -> None:
        tx = self._tile(event.x)
        ty = self._tile(event.y)
        pf = self._placement_at(tx, ty)
        if pf:
            self._selected = pf
            self._redraw()
            menu = tk.Menu(self, tearoff=0)
            item = FURNITURE_DB.get(pf.item_id)
            if item:
                menu.add_command(label=f"Remove {item.name}", command=self.remove_selected)
                menu.add_separator()
                menu.add_command(label=f"Stats: {item.stats}", state=tk.DISABLED)
            menu.tk_popup(event.x_root, event.y_root)

    def _notify_change(self) -> None:
        if self._on_change:
            self._on_change()


class LayoutPanel(ttk.Frame):
    """
    A complete panel showing:
    - A room selector (left)
    - The room grid canvas (centre)
    - A stat summary (right)
    - Controls: Clear room / Remove selected
    """

    def __init__(self, parent: tk.Widget, game_state, **kwargs):
        super().__init__(parent, **kwargs)
        self._state = game_state
        self._current_room: Optional[RoomDefinition] = None
        self._build_ui()

    def _build_ui(self) -> None:
        # ── Top toolbar ───────────────────────────────────────────────────
        toolbar = ttk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=6, pady=4)

        ttk.Label(toolbar, text="Room:").pack(side=tk.LEFT)
        self._room_var = tk.StringVar()
        self._room_combo = ttk.Combobox(
            toolbar, textvariable=self._room_var, width=18, state="readonly"
        )
        self._room_combo.pack(side=tk.LEFT, padx=(4, 10))
        self._room_combo.bind("<<ComboboxSelected>>", self._on_room_selected)

        ttk.Button(toolbar, text="Remove Selected",
                   command=self._remove_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Clear Room",
                   command=self._clear_room).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="↺ Refresh",
                   command=self.refresh).pack(side=tk.RIGHT, padx=2)

        # ── Main area: canvas + stats sidebar ────────────────────────────
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # Scrollable canvas container
        canvas_frame = ttk.LabelFrame(main_frame, text="Room Layout")
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        v_scroll.pack(side=tk.RIGHT,  fill=tk.Y)

        self._canvas = LayoutCanvas(canvas_frame, width=400, height=300)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._canvas.config(
            xscrollcommand=h_scroll.set,
            yscrollcommand=v_scroll.set,
            scrollregion=(0, 0, 1200, 800),
        )
        h_scroll.config(command=self._canvas.xview)
        v_scroll.config(command=self._canvas.yview)
        self._canvas.set_on_change(self._on_layout_change)

        # Stats sidebar
        stats_frame = ttk.LabelFrame(main_frame, text="Room Stats", width=160)
        stats_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))
        stats_frame.pack_propagate(False)

        self._stat_labels: Dict[str, ttk.Label] = {}
        for stat in ALL_STATS:
            row = ttk.Frame(stats_frame)
            row.pack(fill=tk.X, padx=6, pady=2)
            ttk.Label(row, text=stat.capitalize() + ":", width=10,
                      anchor="w").pack(side=tk.LEFT)
            lbl = ttk.Label(row, text="—", width=6, anchor="e")
            lbl.pack(side=tk.RIGHT)
            self._stat_labels[stat] = lbl

        ttk.Separator(stats_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=4)
        self._fill_label = ttk.Label(stats_frame, text="Fill: —", foreground="#555555")
        self._fill_label.pack(padx=6, pady=2)

        # ── Legend ────────────────────────────────────────────────────────
        legend = ttk.LabelFrame(self, text="Legend")
        legend.pack(fill=tk.X, padx=6, pady=(0, 4))
        items = [
            (WALL_COLOR,  "Wall zone"),
            (FLOOR_COLOR, "Floor zone"),
            ("#D9D0C0",   "Transition"),
        ]
        for color, label in items:
            fr = ttk.Frame(legend)
            fr.pack(side=tk.LEFT, padx=6)
            box = tk.Canvas(fr, width=14, height=14, bg=color,
                            highlightthickness=1, highlightbackground="#888")
            box.pack(side=tk.LEFT)
            ttk.Label(fr, text=label).pack(side=tk.LEFT, padx=2)

        self.refresh()

    # ── Refresh / data helpers ────────────────────────────────────────────

    def refresh(self) -> None:
        """Reload room list from game state and redraw."""
        from src.data.room_data import ROOMS, ROOM_DISPLAY_NAMES
        unlocked = self._state.unlocked_rooms
        display = [ROOM_DISPLAY_NAMES.get(r, r) for r in unlocked]
        self._room_combo["values"] = display

        if unlocked:
            if not self._room_var.get() or self._room_var.get() not in display:
                self._room_combo.current(0)
            self._load_current_room()

    def _load_current_room(self) -> None:
        from src.data.room_data import ROOMS, ROOM_DISPLAY_NAMES
        idx = self._room_combo.current()
        if idx < 0:
            return
        unlocked = self._state.unlocked_rooms
        if idx >= len(unlocked):
            return
        room_type = unlocked[idx]
        room_def = ROOMS.get(room_type)
        if room_def is None:
            return
        self._current_room = room_def
        placements = self._state.get_room_furniture(room_type)
        self._canvas.load_room(room_def, placements)
        self._update_stats()

    def _update_stats(self) -> None:
        from src.optimizer.stat_calculator import compute_placement_stats
        from src.data.room_data import ROOMS
        if self._current_room is None:
            return
        placements = self._canvas.get_placements()
        stats = compute_placement_stats(self._current_room, placements)
        for stat, lbl in self._stat_labels.items():
            val = stats.get(stat, 0)
            lbl.config(text=str(val), foreground="#006600" if val > 0 else "#444444")

        used = sum(
            FURNITURE_DB[p.item_id].area
            for p in placements
            if p.item_id in FURNITURE_DB
        )
        total = self._current_room.total_tiles
        pct = (used / total * 100) if total else 0
        self._fill_label.config(text=f"Fill: {used}/{total} ({pct:.0f}%)")

    # ── Event handlers ────────────────────────────────────────────────────

    def _on_room_selected(self, _event=None) -> None:
        self._load_current_room()

    def _on_layout_change(self) -> None:
        """Sync canvas placements back to game state."""
        if self._current_room is None:
            return
        from src.data.room_data import ROOMS
        self._state.placements[self._current_room.room_type] = \
            self._canvas.get_placements()
        self._update_stats()

    def _remove_selected(self) -> None:
        self._canvas.remove_selected()

    def _clear_room(self) -> None:
        if self._current_room is None:
            return
        if messagebox.askyesno(
            "Clear Room",
            f"Remove all furniture from {self._current_room.display_name}?",
        ):
            self._canvas.clear()
            self._state.clear_room(self._current_room.room_type)
