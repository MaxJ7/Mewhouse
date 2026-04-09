"""
Furniture Inventory Panel
--------------------------
Displays all furniture owned by the player, with filtering,
sorting, and the ability to drag/add items to the layout canvas.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, List, Dict, Callable

from src.data.furniture_db import (
    FurnitureItem, FURNITURE_DB, ALL_STATS, ALL_CATEGORIES,
    STAT_APPEAL, STAT_COMFORT, STAT_HYGIENE, STAT_FUN, STAT_HEALTH, STAT_BREEDING,
)
from src.data.save_parser import GameState


class FurnitureTooltip:
    """Shows a tooltip with detailed furniture stats."""

    def __init__(self, widget: tk.Widget):
        self._widget = widget
        self._tip_window: Optional[tk.Toplevel] = None
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        self._text = ""

    def set_text(self, text: str) -> None:
        self._text = text

    def _on_enter(self, event: tk.Event) -> None:
        if not self._text:
            return
        x = self._widget.winfo_rootx() + 20
        y = self._widget.winfo_rooty() + 20
        self._tip_window = tw = tk.Toplevel(self._widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw, text=self._text, justify=tk.LEFT,
            background="#FFFFE0", relief=tk.SOLID, borderwidth=1,
            font=("Arial", 9), padx=6, pady=4,
        )
        label.pack()

    def _on_leave(self, _event: tk.Event) -> None:
        if self._tip_window:
            self._tip_window.destroy()
            self._tip_window = None


class FurnitureCard(ttk.Frame):
    """A compact card widget representing one furniture item + quantity."""

    def __init__(
        self,
        parent: tk.Widget,
        item: FurnitureItem,
        quantity: int,
        on_add_to_room: Optional[Callable[[FurnitureItem], None]] = None,
        **kwargs,
    ):
        super().__init__(parent, relief=tk.RIDGE, borderwidth=1, **kwargs)
        self._item = item
        self._qty = quantity
        self._on_add = on_add_to_room
        self._build()

    def _build(self) -> None:
        item = self._item

        # Colour swatch
        swatch = tk.Canvas(self, width=20, height=20, bg=item.color,
                           highlightthickness=1, highlightbackground="#888888")
        swatch.grid(row=0, column=0, rowspan=2, padx=(4, 6), pady=4, sticky="ns")

        # Name
        name_lbl = ttk.Label(
            self, text=item.name,
            font=("Arial", 9, "bold"),
            wraplength=130, anchor="w",
        )
        name_lbl.grid(row=0, column=1, sticky="w", padx=0, pady=(4, 0))

        # Dimensions + anchor
        dim_text = (
            f"{item.width}×{item.height} tiles  "
            f"[{item.anchor}]  "
            f"{item.category}"
        )
        ttk.Label(self, text=dim_text, foreground="#555555",
                  font=("Arial", 7)).grid(
            row=1, column=1, sticky="w", padx=0, pady=0,
        )

        # Stats (compact row)
        stat_parts = [
            f"{s[0].upper()}:{v}"
            for s, v in item.stats.items() if v > 0
        ]
        stat_text = "  ".join(stat_parts) if stat_parts else "No stats"
        ttk.Label(self, text=stat_text, foreground="#2a6e2a",
                  font=("Arial", 8)).grid(
            row=2, column=1, sticky="w", padx=0, pady=(0, 2),
        )

        # Quantity badge
        qty_lbl = ttk.Label(
            self,
            text=f"×{self._qty}",
            font=("Arial", 9, "bold"),
            foreground="#333333",
        )
        qty_lbl.grid(row=0, column=2, rowspan=2, padx=(6, 4), pady=4, sticky="e")

        # Add-to-room button
        if self._on_add:
            btn = ttk.Button(
                self, text="➕ Add",
                command=lambda: self._on_add(self._item),
                width=6,
            )
            btn.grid(row=2, column=2, padx=4, pady=2, sticky="e")

        # Tooltip
        tip_text = (
            f"{item.name}\n"
            f"Size   : {item.width} × {item.height} tiles\n"
            f"Anchor : {item.anchor}\n"
            f"Area   : {item.area} tiles\n"
            f"Category: {item.category}\n"
            f"Tier   : {'★' * item.tier}\n"
            f"\nStats:\n"
        ) + "\n".join(
            f"  {s.capitalize():<10}: +{v}"
            for s, v in item.stats.items() if v > 0
        ) + (
            f"\n\n{item.description}" if item.description else ""
        )
        tip = FurnitureTooltip(self)
        tip.set_text(tip_text)

    def update_quantity(self, qty: int) -> None:
        self._qty = qty
        # Rebuild to reflect new quantity
        for widget in self.winfo_children():
            widget.destroy()
        self._build()


class FurnitureInventoryPanel(ttk.Frame):
    """
    Scrollable list of all furniture items owned by the player,
    with filtering by category and searching by name.
    """

    def __init__(
        self,
        parent: tk.Widget,
        game_state: GameState,
        on_add_to_room: Optional[Callable[[FurnitureItem], None]] = None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self._state = game_state
        self._on_add = on_add_to_room
        self._cards: List[FurnitureCard] = []
        self._build_ui()

    def _build_ui(self) -> None:
        # ── Filter toolbar ────────────────────────────────────────────────
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=6, pady=4)

        ttk.Label(toolbar, text="🔍").pack(side=tk.LEFT)
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refresh_list())
        search_entry = ttk.Entry(toolbar, textvariable=self._search_var, width=18)
        search_entry.pack(side=tk.LEFT, padx=(2, 8))

        ttk.Label(toolbar, text="Category:").pack(side=tk.LEFT)
        self._cat_var = tk.StringVar(value="All")
        cat_options = ["All"] + list(ALL_CATEGORIES)
        cat_combo = ttk.Combobox(
            toolbar, textvariable=self._cat_var,
            values=cat_options, width=14, state="readonly",
        )
        cat_combo.pack(side=tk.LEFT, padx=(2, 8))
        cat_combo.bind("<<ComboboxSelected>>", lambda *_: self._refresh_list())

        ttk.Label(toolbar, text="Sort:").pack(side=tk.LEFT)
        self._sort_var = tk.StringVar(value="Name")
        sort_combo = ttk.Combobox(
            toolbar, textvariable=self._sort_var,
            values=["Name", "Category", "Size", "Stat Total", "Efficiency"],
            width=10, state="readonly",
        )
        sort_combo.pack(side=tk.LEFT, padx=2)
        sort_combo.bind("<<ComboboxSelected>>", lambda *_: self._refresh_list())

        # Count label
        self._count_label = ttk.Label(toolbar, text="", foreground="#555555")
        self._count_label.pack(side=tk.RIGHT, padx=6)

        # ── Scrollable item list ──────────────────────────────────────────
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)

        v_scroll = ttk.Scrollbar(container, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._list_canvas = tk.Canvas(
            container, yscrollcommand=v_scroll.set, bg="#F9F9F9"
        )
        self._list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.config(command=self._list_canvas.yview)

        self._items_frame = ttk.Frame(self._list_canvas)
        self._canvas_window = self._list_canvas.create_window(
            0, 0, anchor="nw", window=self._items_frame
        )
        self._items_frame.bind("<Configure>", self._on_frame_configure)
        self._list_canvas.bind("<Configure>", self._on_canvas_configure)
        self._list_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._list_canvas.bind("<Button-4>",   self._on_mousewheel)
        self._list_canvas.bind("<Button-5>",   self._on_mousewheel)

        self._refresh_list()

    # ── List management ───────────────────────────────────────────────────

    def refresh(self) -> None:
        self._refresh_list()

    def _refresh_list(self) -> None:
        for widget in self._items_frame.winfo_children():
            widget.destroy()
        self._cards.clear()

        items = self._get_filtered_sorted_items()
        self._count_label.config(text=f"{len(items)} items")

        for item, qty in items:
            card = FurnitureCard(
                self._items_frame, item, qty,
                on_add_to_room=self._on_add,
            )
            card.pack(fill=tk.X, padx=4, pady=2)
            self._cards.append(card)

        self._items_frame.update_idletasks()
        self._list_canvas.config(
            scrollregion=self._list_canvas.bbox("all")
        )

    def _get_filtered_sorted_items(self) -> List[tuple]:
        """Return [(FurnitureItem, quantity)] after filtering and sorting."""
        search = self._search_var.get().lower().strip()
        cat_filter = self._cat_var.get()
        sort_by = self._sort_var.get()

        owned = self._state.get_all_owned_items()
        # Also show unowned items from DB as qty=0 so players can plan
        owned_ids = {item.item_id for item, _ in owned}
        for item in FURNITURE_DB.values():
            if item.item_id not in owned_ids:
                owned.append((item, 0))

        filtered = []
        for item, qty in owned:
            if search and search not in item.name.lower():
                continue
            if cat_filter != "All" and item.category != cat_filter:
                continue
            filtered.append((item, qty))

        key_map = {
            "Name":       lambda t: t[0].name,
            "Category":   lambda t: (t[0].category, t[0].name),
            "Size":       lambda t: (t[0].area, t[0].name),
            "Stat Total": lambda t: (-t[0].stat_total, t[0].name),
            "Efficiency": lambda t: (-t[0].stat_density, t[0].name),
        }
        filtered.sort(key=key_map.get(sort_by, key_map["Name"]))
        return filtered

    # ── Canvas scroll helpers ─────────────────────────────────────────────

    def _on_frame_configure(self, _event=None) -> None:
        self._list_canvas.configure(
            scrollregion=self._list_canvas.bbox("all")
        )

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self._list_canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        if event.num == 4:
            self._list_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._list_canvas.yview_scroll(1, "units")
        else:
            self._list_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
