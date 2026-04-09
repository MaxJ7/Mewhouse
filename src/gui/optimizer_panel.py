"""
Optimizer Panel
----------------
UI for configuring stat targets per room and running the
automatic layout / room-assignment optimizer.

The user can:
  - Select which rooms to include in the optimisation
  - Set numeric stat targets for each stat in each room
  - Choose an optimisation goal (target or maximise)
  - Run the optimizer and see per-room results
  - Apply the generated layouts to the game state
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Callable, Optional

from src.data.furniture_db import ALL_STATS, STAT_APPEAL
from src.data.room_data import get_all_rooms, ROOM_DISPLAY_NAMES, RoomDefinition
from src.data.save_parser import GameState
from src.optimizer.layout_optimizer import optimize_room_layout, PlacementResult
from src.optimizer.room_placer import assign_furniture_to_rooms


class RoomTargetRow(ttk.Frame):
    """
    A single row in the optimizer table representing one room's targets.
    """

    def __init__(
        self,
        parent: tk.Widget,
        room_def: RoomDefinition,
        enabled: bool = True,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self._room = room_def
        self._enabled_var = tk.BooleanVar(value=enabled)
        self._stat_vars: Dict[str, tk.IntVar] = {
            s: tk.IntVar(value=0) for s in ALL_STATS
        }
        self._build()

    def _build(self) -> None:
        # Checkbox + room name
        cb = ttk.Checkbutton(
            self, variable=self._enabled_var, text=self._room.display_name,
            width=16,
        )
        cb.grid(row=0, column=0, sticky="w", padx=(4, 8))

        # Preferred stats hint
        pref = ", ".join(s.capitalize() for s in self._room.preferred_stats)
        ttk.Label(
            self, text=f"(prefers: {pref})",
            foreground="#888888", font=("Arial", 7),
        ).grid(row=1, column=0, sticky="w", padx=(24, 8))

        # Stat spinboxes
        for col, stat in enumerate(ALL_STATS, start=1):
            ttk.Label(self, text=stat[:3].capitalize(),
                      font=("Arial", 7), foreground="#555555").grid(
                row=0, column=col, padx=2,
            )
            spin = ttk.Spinbox(
                self, from_=0, to=200, width=4,
                textvariable=self._stat_vars[stat],
            )
            spin.grid(row=1, column=col, padx=2, pady=2)

        # Quick-fill preferred button
        ttk.Button(
            self, text="⬆ Fill Preferred", width=14,
            command=self._fill_preferred,
        ).grid(row=0, column=len(ALL_STATS) + 1, rowspan=2, padx=8)

    def _fill_preferred(self) -> None:
        """Set sensible default targets for preferred stats."""
        for stat in ALL_STATS:
            if stat in self._room.preferred_stats:
                self._stat_vars[stat].set(20)
            else:
                self._stat_vars[stat].set(0)

    @property
    def is_enabled(self) -> bool:
        return self._enabled_var.get()

    @property
    def targets(self) -> Dict[str, int]:
        return {s: self._stat_vars[s].get() for s in ALL_STATS}


class OptimizerPanel(ttk.Frame):
    """
    Full optimizer panel with:
    - Per-room stat targets
    - Optimisation controls
    - Results table
    - Apply button
    """

    def __init__(
        self,
        parent: tk.Widget,
        game_state: GameState,
        on_apply: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self._state = game_state
        self._on_apply = on_apply
        self._target_rows: Dict[str, RoomTargetRow] = {}
        self._last_results: Optional[Dict] = None
        self._build_ui()

    def _build_ui(self) -> None:
        # ── Header ────────────────────────────────────────────────────────
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(
            header,
            text="🏠  Room Layout Optimizer",
            font=("Arial", 13, "bold"),
        ).pack(side=tk.LEFT)

        ttk.Label(
            header,
            text="Set stat targets for each room, then click Run.",
            foreground="#555555",
        ).pack(side=tk.LEFT, padx=12)

        ttk.Button(
            header, text="✓ Apply Results",
            command=self._apply_results,
        ).pack(side=tk.RIGHT, padx=4)

        ttk.Button(
            header, text="▶ Run Optimizer",
            command=self._run_optimizer,
        ).pack(side=tk.RIGHT, padx=4)

        # ── Column headers ────────────────────────────────────────────────
        col_frame = ttk.Frame(self)
        col_frame.pack(fill=tk.X, padx=8)

        ttk.Label(col_frame, text="Room", width=16, font=("Arial", 8, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        for col, stat in enumerate(ALL_STATS, start=1):
            ttk.Label(
                col_frame, text=stat.capitalize(), width=6,
                font=("Arial", 8, "bold"), foreground="#333",
            ).grid(row=0, column=col, padx=2)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=4)

        # ── Scrollable room rows ──────────────────────────────────────────
        rows_outer = ttk.Frame(self)
        rows_outer.pack(fill=tk.BOTH, expand=True, padx=8)

        v_scroll = ttk.Scrollbar(rows_outer, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        rows_canvas = tk.Canvas(rows_outer, yscrollcommand=v_scroll.set, bg="#FAFAFA")
        rows_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.config(command=rows_canvas.yview)

        self._rows_frame = ttk.Frame(rows_canvas)
        _win = rows_canvas.create_window(0, 0, anchor="nw", window=self._rows_frame)
        self._rows_frame.bind(
            "<Configure>",
            lambda e: rows_canvas.configure(scrollregion=rows_canvas.bbox("all"))
        )
        rows_canvas.bind(
            "<Configure>",
            lambda e: rows_canvas.itemconfig(_win, width=e.width)
        )
        rows_canvas.bind("<MouseWheel>", lambda e: rows_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        rows_canvas.bind("<Button-4>",   lambda e: rows_canvas.yview_scroll(-1, "units"))
        rows_canvas.bind("<Button-5>",   lambda e: rows_canvas.yview_scroll(1, "units"))

        # ── Global controls ───────────────────────────────────────────────
        global_ctrl = ttk.LabelFrame(self, text="Global Options")
        global_ctrl.pack(fill=tk.X, padx=8, pady=4)

        self._maximise_appeal = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            global_ctrl, text="Maximise House Appeal",
            variable=self._maximise_appeal,
        ).pack(side=tk.LEFT, padx=8)

        self._share_inventory = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            global_ctrl, text="Share Inventory Across Rooms",
            variable=self._share_inventory,
        ).pack(side=tk.LEFT, padx=8)

        ttk.Label(global_ctrl, text="Max items/room:").pack(side=tk.LEFT, padx=(16, 2))
        self._max_items_var = tk.IntVar(value=30)
        ttk.Spinbox(
            global_ctrl, from_=1, to=100, width=4,
            textvariable=self._max_items_var,
        ).pack(side=tk.LEFT)

        # ── Results panel ─────────────────────────────────────────────────
        results_frame = ttk.LabelFrame(self, text="Optimisation Results")
        results_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        self._results_text = tk.Text(
            results_frame, height=8, state=tk.DISABLED,
            bg="#F0F0F0", font=("Courier", 9),
            wrap=tk.WORD,
        )
        self._results_text.pack(fill=tk.X, padx=4, pady=4)

        self.refresh()

    # ── Public API ────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Rebuild the room target rows from the current game state."""
        for w in self._rows_frame.winfo_children():
            w.destroy()
        self._target_rows.clear()

        for room_def in get_all_rooms():
            rt = room_def.room_type
            enabled = rt in self._state.unlocked_rooms
            row = RoomTargetRow(
                self._rows_frame,
                room_def,
                enabled=enabled,
            )
            row.pack(fill=tk.X, pady=1)
            ttk.Separator(self._rows_frame, orient=tk.HORIZONTAL).pack(
                fill=tk.X, pady=0
            )
            self._target_rows[rt] = row

    # ── Optimiser logic ───────────────────────────────────────────────────

    def _run_optimizer(self) -> None:
        """Run the room assignment + layout optimizer."""
        targets_per_room: Dict[str, Dict[str, int]] = {}
        for rt, row in self._target_rows.items():
            if row.is_enabled and rt in self._state.unlocked_rooms:
                targets_per_room[rt] = row.targets

        if not targets_per_room:
            messagebox.showinfo("Optimizer", "No rooms selected for optimization.")
            return

        # If maximise_appeal is on, add appeal target to all rooms
        if self._maximise_appeal.get():
            for tgt in targets_per_room.values():
                if tgt.get(STAT_APPEAL, 0) == 0:
                    tgt[STAT_APPEAL] = 30  # aspirational appeal target

        max_items = self._max_items_var.get()

        if self._share_inventory.get():
            # Use room-placer to split inventory across rooms
            assignment = assign_furniture_to_rooms(
                unlocked_rooms=list(targets_per_room.keys()),
                global_inventory=dict(self._state.inventory),
                targets_per_room=targets_per_room,
                run_layout=True,
            )
            self._last_results = {
                rt: assignment.layout_results.get(rt)
                for rt in targets_per_room
            }
        else:
            # Run layout optimizer per room independently
            self._last_results = {}
            for rt, tgt in targets_per_room.items():
                result = optimize_room_layout(
                    room_type=rt,
                    inventory=dict(self._state.inventory),
                    targets=tgt,
                    max_items=max_items,
                )
                self._last_results[rt] = result

        self._display_results()

    def _display_results(self) -> None:
        if not self._last_results:
            return

        lines = []
        lines.append("=" * 60)
        lines.append(f"{'ROOM':<20} {'Score':>6}  {'Stats Summary'}")
        lines.append("=" * 60)

        for rt, result in self._last_results.items():
            if result is None:
                lines.append(f"{ROOM_DISPLAY_NAMES.get(rt, rt):<20}  (no result)")
                continue
            name = ROOM_DISPLAY_NAMES.get(rt, rt)
            score_pct = f"{result.score * 100:.0f}%"
            stat_parts = [
                f"{s[0].upper()}:{v}"
                for s, v in result.stats.items() if v > 0
            ]
            stats_str = "  ".join(stat_parts)
            placed_count = len(result.placements)
            fill_pct = f"{result.fill_ratio * 100:.0f}%"
            lines.append(
                f"{name:<20} {score_pct:>6}  {stats_str}"
            )
            lines.append(
                f"{'':>22}  {placed_count} items placed  ({fill_pct} fill)"
            )

        lines.append("=" * 60)

        self._results_text.config(state=tk.NORMAL)
        self._results_text.delete("1.0", tk.END)
        self._results_text.insert(tk.END, "\n".join(lines))
        self._results_text.config(state=tk.DISABLED)

    def _apply_results(self) -> None:
        if not self._last_results:
            messagebox.showinfo("Apply", "Run the optimizer first.")
            return

        applied = 0
        for rt, result in self._last_results.items():
            if result is None:
                continue
            self._state.clear_room(rt)
            for pf in result.placements:
                self._state.placements[rt].append(pf)
            applied += 1

        if self._on_apply:
            self._on_apply()

        messagebox.showinfo(
            "Applied",
            f"Optimized layouts applied to {applied} room(s).\n"
            "Switch to the Layout tab to review them.",
        )
