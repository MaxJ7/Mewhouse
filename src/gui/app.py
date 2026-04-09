"""
Mewhouse — Main Application Window
=====================================
A GUI tool for planning and optimising Mewgenics house room layouts.

Features
--------
  • Import your Mewgenics save file to load your actual furniture inventory
  • Browse all furniture with detailed stats, dimensions, and anchor info
  • Visualise room layouts on an accurate grid canvas
  • Manually place, move (drag), and remove furniture
  • Set per-room stat targets and run the automatic optimizer
  • Apply optimised layouts directly to your planning canvas
  • Export the plan as a Mewhouse JSON save for future reference

Tabs
----
  1. Inventory   – Browse and filter all furniture items
  2. Rooms       – Manage unlocked rooms and view room details
  3. Layout      – Visual canvas editor for room furniture placement
  4. Optimizer   – Stat targets and automatic optimisation
  5. Save/Import – Load from a Mewgenics save or export plan
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import logging

from src.data.save_parser import (
    GameState, auto_load, parse_save_file, create_demo_state,
    find_save_files,
)
from src.data.furniture_db import FurnitureItem
from src.data.room_data import ROOM_DISPLAY_NAMES
from src.gui.furniture_panel import FurnitureInventoryPanel
from src.gui.room_panel import RoomConfigPanel
from src.gui.layout_panel import LayoutPanel
from src.gui.optimizer_panel import OptimizerPanel
from src.optimizer.stat_calculator import house_appeal_total
from src.data.room_data import get_all_rooms

logger = logging.getLogger(__name__)

APP_TITLE = "Mewhouse — Mewgenics Room Optimizer"
APP_VERSION = "1.0.0"
WINDOW_MIN_WIDTH  = 1000
WINDOW_MIN_HEIGHT = 680


class MewhouseApp(tk.Tk):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE}  v{APP_VERSION}")
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.geometry(f"{WINDOW_MIN_WIDTH + 100}x{WINDOW_MIN_HEIGHT + 60}")
        self._configure_style()
        self._state: GameState = create_demo_state()
        self._build_ui()
        self._update_status()

    # ── Style ─────────────────────────────────────────────────────────────

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook.Tab", font=("Arial", 10))
        style.configure("Header.TLabel", font=("Arial", 11, "bold"))
        style.configure("Stat.TLabel", font=("Arial", 9))
        style.configure("TButton", font=("Arial", 9))

    # ── UI construction ───────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # ── Menu bar ──────────────────────────────────────────────────────
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Save File…",       command=self._load_save)
        file_menu.add_command(label="Auto-detect Save File", command=self._auto_load_save)
        file_menu.add_separator()
        file_menu.add_command(label="Export Plan (JSON)…",   command=self._export_plan)
        file_menu.add_command(label="Import Plan (JSON)…",   command=self._import_plan)
        file_menu.add_separator()
        file_menu.add_command(label="Reset to Demo State",   command=self._reset_demo)
        file_menu.add_separator()
        file_menu.add_command(label="Exit",                  command=self.quit)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About…",      command=self._show_about)
        help_menu.add_command(label="Furniture Guide…", command=self._show_furniture_guide)

        # ── Top status bar ────────────────────────────────────────────────
        self._status_bar = ttk.Frame(self, relief=tk.SUNKEN)
        self._status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self._status_label = ttk.Label(self._status_bar, text="", padding=(6, 2))
        self._status_label.pack(side=tk.LEFT)
        self._appeal_label = ttk.Label(self._status_bar, text="", padding=(6, 2),
                                       foreground="#006600")
        self._appeal_label.pack(side=tk.RIGHT)

        # ── Notebook tabs ─────────────────────────────────────────────────
        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Tab 1: Inventory
        self._inventory_panel = FurnitureInventoryPanel(
            self._notebook, self._state,
            on_add_to_room=self._on_add_to_room,
        )
        self._notebook.add(self._inventory_panel, text="  🪑 Inventory  ")

        # Tab 2: Rooms
        self._room_panel = RoomConfigPanel(
            self._notebook, self._state,
            on_room_unlock_change=self._on_rooms_changed,
        )
        self._notebook.add(self._room_panel, text="  🏠 Rooms  ")

        # Tab 3: Layout
        self._layout_panel = LayoutPanel(self._notebook, self._state)
        self._notebook.add(self._layout_panel, text="  🗺 Layout  ")

        # Tab 4: Optimizer
        self._optimizer_panel = OptimizerPanel(
            self._notebook, self._state,
            on_apply=self._on_optimizer_applied,
        )
        self._notebook.add(self._optimizer_panel, text="  ⚙ Optimizer  ")

        # Tab 5: Save / Import
        save_tab = self._build_save_tab()
        self._notebook.add(save_tab, text="  💾 Save/Import  ")

        self._notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _build_save_tab(self) -> ttk.Frame:
        frame = ttk.Frame(self._notebook)

        # Header
        ttk.Label(frame, text="Save File Management",
                  font=("Arial", 12, "bold")).pack(padx=12, pady=(12, 4), anchor="w")
        ttk.Label(
            frame,
            text=(
                "Load your Mewgenics save to populate the furniture inventory\n"
                "and room unlock status automatically.\n\n"
                "If no save is found, you can use the Demo State to explore the tool."
            ),
            foreground="#444444", justify=tk.LEFT,
        ).pack(padx=12, pady=4, anchor="w")

        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=12, pady=8)

        # Auto-detect
        detect_frame = ttk.LabelFrame(frame, text="Auto-detect Mewgenics Save")
        detect_frame.pack(fill=tk.X, padx=12, pady=4)

        self._detected_paths_var = tk.StringVar(value="(click Scan to search)")
        ttk.Label(detect_frame, textvariable=self._detected_paths_var,
                  wraplength=500, justify=tk.LEFT, foreground="#555").pack(
            padx=8, pady=6, anchor="w"
        )
        detect_btn_row = ttk.Frame(detect_frame)
        detect_btn_row.pack(padx=8, pady=4, anchor="w")
        ttk.Button(detect_btn_row, text="🔍 Scan for Save Files",
                   command=self._scan_saves).pack(side=tk.LEFT, padx=2)
        ttk.Button(detect_btn_row, text="⬆ Load Detected Save",
                   command=self._auto_load_save).pack(side=tk.LEFT, padx=2)

        # Manual load
        manual_frame = ttk.LabelFrame(frame, text="Manual Load / Export")
        manual_frame.pack(fill=tk.X, padx=12, pady=4)

        manual_btn_row = ttk.Frame(manual_frame)
        manual_btn_row.pack(padx=8, pady=6, anchor="w")
        ttk.Button(manual_btn_row, text="📂 Load Save File…",
                   command=self._load_save).pack(side=tk.LEFT, padx=2)
        ttk.Button(manual_btn_row, text="📂 Import Plan (JSON)…",
                   command=self._import_plan).pack(side=tk.LEFT, padx=2)
        ttk.Button(manual_btn_row, text="💾 Export Plan (JSON)…",
                   command=self._export_plan).pack(side=tk.LEFT, padx=2)
        ttk.Button(manual_btn_row, text="🔄 Reset to Demo",
                   command=self._reset_demo).pack(side=tk.LEFT, padx=2)

        # Current state summary
        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=12, pady=8)
        state_frame = ttk.LabelFrame(frame, text="Current State Summary")
        state_frame.pack(fill=tk.X, padx=12, pady=4)
        self._state_summary_text = tk.Text(
            state_frame, height=8, state=tk.DISABLED,
            bg="#F5F5F5", font=("Courier", 9),
        )
        self._state_summary_text.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(state_frame, text="↺ Refresh Summary",
                   command=self._refresh_state_summary).pack(padx=6, pady=(0, 6), anchor="w")

        return frame

    # ── Event handlers ─────────────────────────────────────────────────────

    def _on_tab_changed(self, _event=None) -> None:
        """Refresh the active tab on switch."""
        idx = self._notebook.index(self._notebook.select())
        if idx == 0:
            self._inventory_panel.refresh()
        elif idx == 1:
            self._room_panel.refresh()
        elif idx == 2:
            self._layout_panel.refresh()
        elif idx == 3:
            self._optimizer_panel.refresh()
        elif idx == 4:
            self._refresh_state_summary()
        self._update_status()

    def _on_add_to_room(self, item: FurnitureItem) -> None:
        """Called when user clicks 'Add' on a furniture card; switches to Layout tab."""
        self._notebook.select(2)  # Layout tab
        self._layout_panel.refresh()
        messagebox.showinfo(
            "Add Furniture",
            f"Switched to the Layout tab.\n\n"
            f"Click on the room grid to place '{item.name}'.\n"
            f"(Manual placement coming: use the optimizer to auto-place.)",
        )

    def _on_rooms_changed(self) -> None:
        self._layout_panel.refresh()
        self._optimizer_panel.refresh()
        self._update_status()

    def _on_optimizer_applied(self) -> None:
        self._layout_panel.refresh()
        self._update_status()

    # ── File operations ───────────────────────────────────────────────────

    def _load_save(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Mewgenics Save File",
            filetypes=[
                ("Save files", "*.sav *.json *.dat"),
                ("All files",  "*.*"),
            ],
        )
        if not path:
            return
        try:
            self._state = parse_save_file(Path(path))
            self._reload_all_panels()
            messagebox.showinfo("Loaded", f"Save loaded!\nVersion: {self._state.game_version}")
        except Exception as exc:
            messagebox.showerror("Load Error", str(exc))

    def _auto_load_save(self) -> None:
        try:
            self._state = auto_load()
            self._reload_all_panels()
            src = "save file" if self._state.loaded_from_file else "demo state"
            messagebox.showinfo("Loaded", f"Loaded from {src}.\nVersion: {self._state.game_version}")
        except Exception as exc:
            messagebox.showerror("Load Error", str(exc))

    def _export_plan(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export Mewhouse Plan",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self._state.save_json(Path(path))
            messagebox.showinfo("Exported", f"Plan saved to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export Error", str(exc))

    def _import_plan(self) -> None:
        path = filedialog.askopenfilename(
            title="Import Mewhouse Plan",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self._state = GameState.load_json(Path(path))
            self._reload_all_panels()
            messagebox.showinfo("Imported", "Plan imported successfully.")
        except Exception as exc:
            messagebox.showerror("Import Error", str(exc))

    def _reset_demo(self) -> None:
        if messagebox.askyesno("Reset", "Reset to demo state? All current data will be lost."):
            self._state = create_demo_state()
            self._reload_all_panels()

    def _scan_saves(self) -> None:
        saves = find_save_files()
        if saves:
            paths_str = "\n".join(str(p) for p in saves[:8])
            self._detected_paths_var.set(paths_str)
        else:
            self._detected_paths_var.set("No Mewgenics save files found on this system.")

    def _reload_all_panels(self) -> None:
        """Reload all panels after state change."""
        self._inventory_panel._state = self._state
        self._room_panel._state = self._state
        self._layout_panel._state = self._state
        self._optimizer_panel._state = self._state
        self._inventory_panel.refresh()
        self._room_panel.refresh()
        self._layout_panel.refresh()
        self._optimizer_panel.refresh()
        self._update_status()

    # ── Status bar ────────────────────────────────────────────────────────

    def _update_status(self) -> None:
        rooms = len(self._state.unlocked_rooms)
        items = sum(self._state.inventory.values())
        placed = sum(len(v) for v in self._state.placements.values())
        src = "Save File" if self._state.loaded_from_file else "Demo State"

        self._status_label.config(
            text=f"{src}  |  Rooms unlocked: {rooms}  |  "
                 f"Inventory: {items} items  |  Placed: {placed} items"
        )

        # Compute house appeal
        room_defs = [r for r in get_all_rooms()
                     if r.room_type in self._state.unlocked_rooms]
        appeal = house_appeal_total(room_defs, self._state.placements)
        self._appeal_label.config(text=f"🏠 House Appeal: {appeal}")

    # ── State summary ─────────────────────────────────────────────────────

    def _refresh_state_summary(self) -> None:
        from src.optimizer.stat_calculator import compute_placement_stats
        from src.data.room_data import ROOMS
        lines = []
        lines.append(f"Source   : {'Save File' if self._state.loaded_from_file else 'Demo State'}")
        lines.append(f"Version  : {self._state.game_version}")
        lines.append(f"Rooms    : {', '.join(ROOM_DISPLAY_NAMES.get(r, r) for r in self._state.unlocked_rooms)}")
        lines.append("")
        lines.append("Inventory:")
        owned = self._state.get_all_owned_items()
        for item, qty in owned[:20]:
            lines.append(f"  {item.name:<28} ×{qty}")
        if len(owned) > 20:
            lines.append(f"  … and {len(owned) - 20} more items")
        lines.append("")
        lines.append("Current Room Stats:")
        for rt in self._state.unlocked_rooms:
            room_def = ROOMS.get(rt)
            if room_def is None:
                continue
            pfs = self._state.get_room_furniture(rt)
            stats = compute_placement_stats(room_def, pfs)
            stat_str = "  ".join(f"{s[0].upper()}:{v}" for s, v in stats.items() if v > 0)
            lines.append(f"  {room_def.display_name:<20} {stat_str or '(empty)'}")

        self._state_summary_text.config(state=tk.NORMAL)
        self._state_summary_text.delete("1.0", tk.END)
        self._state_summary_text.insert(tk.END, "\n".join(lines))
        self._state_summary_text.config(state=tk.DISABLED)

    # ── Help dialogs ──────────────────────────────────────────────────────

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About Mewhouse",
            f"Mewhouse  v{APP_VERSION}\n\n"
            "A room layout optimizer for Mewgenics.\n\n"
            "How to use:\n"
            "  1. Load your save file (File → Load Save File)\n"
            "     or use the built-in Demo State.\n"
            "  2. In the Rooms tab, unlock the rooms you have.\n"
            "  3. In the Optimizer tab, set stat targets.\n"
            "  4. Click Run Optimizer to generate layouts.\n"
            "  5. Review layouts in the Layout tab.\n"
            "  6. Export your plan for reference.\n\n"
            "Furniture grid conventions:\n"
            "  • Blue rows  = wall zone (wall-anchored items)\n"
            "  • Cream rows = floor zone (floor-anchored items)\n"
            "  • Drag items to reposition them on the canvas.\n"
            "  • Right-click an item to remove it.",
        )

    def _show_furniture_guide(self) -> None:
        from src.data.furniture_db import FURNITURE_DB, ALL_CATEGORIES
        win = tk.Toplevel(self)
        win.title("Furniture Guide")
        win.geometry("700x500")

        ttk.Label(win, text="Mewgenics Furniture Guide",
                  font=("Arial", 12, "bold")).pack(padx=12, pady=8)

        # Filter
        filter_frame = ttk.Frame(win)
        filter_frame.pack(fill=tk.X, padx=12)
        ttk.Label(filter_frame, text="Category:").pack(side=tk.LEFT)
        cat_var = tk.StringVar(value="All")
        cat_combo = ttk.Combobox(filter_frame, textvariable=cat_var,
                                 values=["All"] + list(ALL_CATEGORIES),
                                 width=16, state="readonly")
        cat_combo.pack(side=tk.LEFT, padx=4)

        # Table
        cols = ("Name", "Size", "Anchor", "Category", "Appeal", "Comfort",
                "Hygiene", "Fun", "Health", "Breeding")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=20)
        widths = [160, 60, 60, 100, 55, 60, 60, 50, 55, 65]
        for col, w in zip(cols, widths):
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="center" if w < 100 else "w")

        vsb = ttk.Scrollbar(win, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=12, pady=8)
        vsb.pack(side=tk.LEFT, fill=tk.Y, pady=8)

        def populate(cat="All"):
            tree.delete(*tree.get_children())
            for item in sorted(FURNITURE_DB.values(), key=lambda f: f.name):
                if cat != "All" and item.category != cat:
                    continue
                tree.insert("", tk.END, values=(
                    item.name,
                    f"{item.width}×{item.height}",
                    item.anchor,
                    item.category,
                    item.get_stat("appeal"),
                    item.get_stat("comfort"),
                    item.get_stat("hygiene"),
                    item.get_stat("fun"),
                    item.get_stat("health"),
                    item.get_stat("breeding"),
                ))

        cat_combo.bind("<<ComboboxSelected>>", lambda e: populate(cat_var.get()))
        populate()
