"""
Room Configuration Panel
--------------------------
Lets the player manage which rooms are unlocked/available,
view room details (dimensions, compatible furniture categories,
preferred stats), and manually add furniture to a specific room
by selecting from the inventory list.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable

from src.data.furniture_db import FurnitureItem, FURNITURE_DB, ALL_STATS
from src.data.room_data import get_all_rooms, RoomDefinition, ROOM_DISPLAY_NAMES
from src.data.save_parser import GameState


class RoomConfigPanel(ttk.Frame):
    """
    Shows all room types; allows the user to lock/unlock rooms
    and view details. Also exposes a "Place Furniture" workflow
    that coordinates with the LayoutPanel.
    """

    def __init__(
        self,
        parent: tk.Widget,
        game_state: GameState,
        on_room_unlock_change: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self._state = game_state
        self._on_change = on_room_unlock_change
        self._selected_room: Optional[RoomDefinition] = None
        self._build_ui()

    def _build_ui(self) -> None:
        # ── Left: room list ───────────────────────────────────────────────
        left = ttk.Frame(self)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=6)

        ttk.Label(left, text="Rooms", font=("Arial", 10, "bold")).pack(anchor="w")

        self._listbox = tk.Listbox(
            left, width=22, font=("Arial", 9),
            selectmode=tk.SINGLE, activestyle="none",
        )
        self._listbox.pack(fill=tk.BOTH, expand=True)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)

        btn_row = ttk.Frame(left)
        btn_row.pack(fill=tk.X, pady=4)
        ttk.Button(btn_row, text="✔ Unlock", command=self._unlock_room).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="✖ Lock",   command=self._lock_room).pack(side=tk.LEFT, padx=2)

        # ── Right: room detail ────────────────────────────────────────────
        right = ttk.Frame(self)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)

        self._detail_frame = ttk.LabelFrame(right, text="Room Details")
        self._detail_frame.pack(fill=tk.BOTH, expand=True)

        # Name + status
        name_row = ttk.Frame(self._detail_frame)
        name_row.pack(fill=tk.X, padx=8, pady=4)
        self._name_label = ttk.Label(name_row, text="—", font=("Arial", 12, "bold"))
        self._name_label.pack(side=tk.LEFT)
        self._status_label = ttk.Label(name_row, text="", foreground="#888888")
        self._status_label.pack(side=tk.LEFT, padx=8)

        # Grid dimensions
        dims_row = ttk.Frame(self._detail_frame)
        dims_row.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(dims_row, text="Grid Size:", width=16, anchor="w").pack(side=tk.LEFT)
        self._dims_label = ttk.Label(dims_row, text="—")
        self._dims_label.pack(side=tk.LEFT)

        # Zone info
        zone_row = ttk.Frame(self._detail_frame)
        zone_row.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(zone_row, text="Zones:", width=16, anchor="w").pack(side=tk.LEFT)
        self._zones_label = ttk.Label(zone_row, text="—")
        self._zones_label.pack(side=tk.LEFT)

        # Base appeal
        appeal_row = ttk.Frame(self._detail_frame)
        appeal_row.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(appeal_row, text="Base Appeal:", width=16, anchor="w").pack(side=tk.LEFT)
        self._appeal_label = ttk.Label(appeal_row, text="—")
        self._appeal_label.pack(side=tk.LEFT)

        # Compatible categories
        compat_row = ttk.Frame(self._detail_frame)
        compat_row.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(compat_row, text="Compatible:", width=16, anchor="w").pack(side=tk.LEFT)
        self._compat_label = ttk.Label(compat_row, text="—", wraplength=280, justify=tk.LEFT)
        self._compat_label.pack(side=tk.LEFT)

        # Preferred stats
        pref_row = ttk.Frame(self._detail_frame)
        pref_row.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(pref_row, text="Preferred Stats:", width=16, anchor="w").pack(side=tk.LEFT)
        self._pref_label = ttk.Label(pref_row, text="—")
        self._pref_label.pack(side=tk.LEFT)

        # Description
        ttk.Separator(self._detail_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=6)
        self._desc_label = ttk.Label(
            self._detail_frame, text="",
            wraplength=320, justify=tk.LEFT, foreground="#444444",
        )
        self._desc_label.pack(padx=8, anchor="w")

        # Tiny room preview canvas
        ttk.Separator(self._detail_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=6)
        self._preview_canvas = tk.Canvas(
            self._detail_frame, height=120, bg="#FFFFFF",
            highlightthickness=1, highlightbackground="#CCCCCC",
        )
        self._preview_canvas.pack(fill=tk.X, padx=8, pady=4)

        self._refresh_list()

    def refresh(self) -> None:
        self._refresh_list()

    def _refresh_list(self) -> None:
        self._listbox.delete(0, tk.END)
        all_rooms = get_all_rooms()
        for room_def in all_rooms:
            unlocked = room_def.room_type in self._state.unlocked_rooms
            prefix = "✔" if unlocked else "✖"
            self._listbox.insert(tk.END, f"{prefix} {room_def.display_name}")
            if unlocked:
                self._listbox.itemconfig(tk.END, foreground="#006600")
            else:
                self._listbox.itemconfig(tk.END, foreground="#888888")

    def _get_selected_room(self) -> Optional[RoomDefinition]:
        sel = self._listbox.curselection()
        if not sel:
            return None
        idx = sel[0]
        all_rooms = get_all_rooms()
        if idx >= len(all_rooms):
            return None
        return all_rooms[idx]

    def _on_select(self, _event=None) -> None:
        room = self._get_selected_room()
        if room is None:
            return
        self._selected_room = room
        self._show_details(room)

    def _show_details(self, room: RoomDefinition) -> None:
        unlocked = room.room_type in self._state.unlocked_rooms
        self._name_label.config(text=room.display_name)
        self._status_label.config(
            text="[Unlocked]" if unlocked else "[Locked]",
            foreground="#006600" if unlocked else "#CC0000",
        )
        self._dims_label.config(
            text=f"{room.grid_width} × {room.grid_height} tiles  "
                 f"({room.total_tiles} total)",
        )
        self._zones_label.config(
            text=f"Wall: {room.wall_rows} rows, "
                 f"Floor: {room.floor_rows} rows, "
                 f"Ceiling: {'yes' if room.ceiling_row is not None else 'no'}",
        )
        self._appeal_label.config(text=str(room.base_appeal))
        self._compat_label.config(text=", ".join(room.compatible_categories))
        self._pref_label.config(text=", ".join(s.capitalize() for s in room.preferred_stats))
        self._desc_label.config(text=room.description)
        self._draw_room_preview(room)

    def _draw_room_preview(self, room: RoomDefinition) -> None:
        c = self._preview_canvas
        c.delete("all")
        c.update_idletasks()
        cw = c.winfo_width() or 300
        ch = 110

        cell_w = cw / room.grid_width
        cell_h = ch / room.grid_height

        for y in range(room.grid_height):
            for x in range(room.grid_width):
                px1 = x * cell_w
                py1 = y * cell_h
                px2 = px1 + cell_w
                py2 = py1 + cell_h
                if y < room.wall_rows:
                    fill = "#B0C4DE"
                elif y < room.floor_start:
                    fill = "#D9D0C0"
                else:
                    fill = room.color
                c.create_rectangle(px1, py1, px2, py2,
                                   fill=fill, outline="#CCCCCC")

        # Labels
        if room.wall_rows > 0:
            c.create_text(4, 4, text="Wall", anchor="nw",
                          font=("Arial", 6), fill="#555")
        c.create_text(4, room.floor_start * cell_h + 2, text="Floor", anchor="nw",
                      font=("Arial", 6), fill="#555")

    def _unlock_room(self) -> None:
        room = self._get_selected_room()
        if room is None:
            return
        if room.room_type not in self._state.unlocked_rooms:
            self._state.unlocked_rooms.append(room.room_type)
            self._refresh_list()
            if self._on_change:
                self._on_change()
            messagebox.showinfo("Unlock", f"{room.display_name} unlocked!")

    def _lock_room(self) -> None:
        room = self._get_selected_room()
        if room is None:
            return
        if room.room_type in self._state.unlocked_rooms:
            if len(self._state.unlocked_rooms) <= 1:
                messagebox.showwarning("Lock", "You must have at least one room unlocked.")
                return
            self._state.unlocked_rooms.remove(room.room_type)
            self._refresh_list()
            if self._on_change:
                self._on_change()
