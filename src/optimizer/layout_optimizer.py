"""
Room Layout Optimizer
----------------------
Given a room definition, a furniture inventory, and stat targets,
this module finds the best placement of furniture to maximise the
target stats while respecting the room's physical constraints.

Algorithm overview
  1. Rank available furniture by weighted stat efficiency vs targets.
  2. Greedily attempt to place top-ranked items into the room grid,
     skipping items that don't fit anywhere.
  3. After the greedy pass, try a local-search improvement step that
     swaps low-efficiency placed items for better alternatives.
  4. Return a PlacementResult with the full placement list and stats.

Grid representation
  A 2-D boolean grid (width × height) tracks which tiles are occupied.
  Placed items record their top-left (x, y) position.
  The helper _fits() checks whether placing an item at (x, y) would
  overlap existing items or leave the room bounds.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.data.furniture_db import (
    FurnitureItem, FURNITURE_DB, ALL_STATS,
)
from src.data.room_data import RoomDefinition, get_room
from src.data.save_parser import PlacedFurniture
from src.optimizer.stat_calculator import (
    compute_placement_stats, score_against_targets,
    rank_furniture_for_targets, stat_efficiency, empty_stats,
)


@dataclass
class PlacementResult:
    """The result of a layout optimisation run."""

    room_type: str
    placements: List[PlacedFurniture] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)
    score: float = 0.0          # 0-1 against targets
    tiles_used: int = 0
    tiles_available: int = 0

    @property
    def fill_ratio(self) -> float:
        if self.tiles_available == 0:
            return 0.0
        return self.tiles_used / self.tiles_available


class RoomGrid:
    """
    Tracks tile occupancy for a single room.
    Coordinates: (x, y) where x is column and y is row (0 = top).
    """

    def __init__(self, room_def: RoomDefinition):
        self.room = room_def
        self._occupied: List[List[bool]] = [
            [False] * room_def.grid_height for _ in range(room_def.grid_width)
        ]
        self.placed_items: List[PlacedFurniture] = []

    def _fits(self, x: int, y: int, w: int, h: int) -> bool:
        """Return True if a w×h block starting at (x,y) is within bounds
        and all covered tiles are free."""
        if x < 0 or y < 0:
            return False
        if x + w > self.room.grid_width:
            return False
        if y + h > self.room.grid_height:
            return False
        for dx in range(w):
            for dy in range(h):
                if self._occupied[x + dx][y + dy]:
                    return False
        return True

    def _occupy(self, x: int, y: int, w: int, h: int) -> None:
        for dx in range(w):
            for dy in range(h):
                self._occupied[x + dx][y + dy] = True

    def _free(self, x: int, y: int, w: int, h: int) -> None:
        for dx in range(w):
            for dy in range(h):
                self._occupied[x + dx][y + dy] = False

    def try_place(self, item: FurnitureItem) -> Optional[Tuple[int, int]]:
        """
        Try to place *item* in the first valid position (scan order:
        left-to-right, top-to-bottom within the valid anchor zone).
        Returns (x, y) if placed, or None if no position is available.
        """
        positions = self.room.valid_anchor_positions(
            item.anchor, item.width, item.height
        )
        for (x, y) in positions:
            if self._fits(x, y, item.width, item.height):
                self._occupy(x, y, item.width, item.height)
                pf = PlacedFurniture(
                    item_id=item.item_id,
                    x=x, y=y,
                    room_type=self.room.room_type,
                )
                self.placed_items.append(pf)
                return (x, y)
        return None

    def remove_item(self, pf: PlacedFurniture) -> None:
        """Remove a placed item and free its tiles."""
        item = FURNITURE_DB.get(pf.item_id)
        if item is None:
            return
        self._free(pf.x, pf.y, item.width, item.height)
        try:
            self.placed_items.remove(pf)
        except ValueError:
            pass

    @property
    def used_tiles(self) -> int:
        total = 0
        for pf in self.placed_items:
            item = FURNITURE_DB.get(pf.item_id)
            if item:
                total += item.area
        return total

    def reset(self) -> None:
        self._occupied = [
            [False] * self.room.grid_height
            for _ in range(self.room.grid_width)
        ]
        self.placed_items = []


def optimize_room_layout(
    room_type: str,
    inventory: Dict[str, int],      # item_id -> quantity available
    targets: Dict[str, int],        # stat -> desired value
    max_items: int = 50,
    improve_iterations: int = 10,
) -> PlacementResult:
    """
    Find the best furniture layout for *room_type* using the available
    *inventory* to meet the stat *targets*.

    Parameters
    ----------
    room_type         : One of the room type constants from room_data.py
    inventory         : Furniture available to place (item_id -> quantity)
    targets           : Desired stat values  (stat_name -> int)
    max_items         : Cap on number of furniture pieces placed per room
    improve_iterations: Local search improvement iterations

    Returns
    -------
    A PlacementResult with the final placements and achieved stats.
    """
    room_def = get_room(room_type)
    grid = RoomGrid(room_def)
    result = PlacementResult(
        room_type=room_type,
        tiles_available=room_def.total_tiles,
    )

    # Build a pool of available items (respecting inventory)
    pool: List[Tuple[FurnitureItem, int]] = []
    for item_id, qty in inventory.items():
        item = FURNITURE_DB.get(item_id)
        if item and qty > 0:
            pool.append((item, qty))

    # Rank by weighted efficiency
    ranked = rank_furniture_for_targets(
        [item for item, _ in pool],
        targets,
        room_def,
    )

    # Map ranked items back to quantities
    qty_map: Dict[str, int] = {item_id: qty for item_id, qty in inventory.items()}

    # ── Greedy placement pass ─────────────────────────────────────────────
    placed_count = 0
    for item, _score in ranked:
        if placed_count >= max_items:
            break
        remaining = qty_map.get(item.item_id, 0)
        placed_this_item = 0
        while remaining > 0:
            pos = grid.try_place(item)
            if pos is None:
                break
            remaining -= 1
            qty_map[item.item_id] = remaining
            placed_this_item += 1
            placed_count += 1
            if placed_count >= max_items:
                break

    # ── Local-search improvement ──────────────────────────────────────────
    # Try replacing the least-efficient placed item with a better alternative.
    for _ in range(improve_iterations):
        if not grid.placed_items:
            break

        current_stats = compute_placement_stats(room_def, grid.placed_items)
        current_score = score_against_targets(current_stats, targets)

        # Find the placed item with the lowest contribution
        worst_pf = None
        worst_eff = float("inf")
        for pf in grid.placed_items:
            item = FURNITURE_DB.get(pf.item_id)
            if item:
                eff = stat_efficiency(item, targets)
                if eff < worst_eff:
                    worst_eff = eff
                    worst_pf = pf

        if worst_pf is None:
            break

        worst_item = FURNITURE_DB[worst_pf.item_id]

        # Find a better replacement from unplaced inventory
        best_replacement: Optional[FurnitureItem] = None
        best_replacement_eff = worst_eff

        for item_id, qty in qty_map.items():
            if qty <= 0:
                continue
            candidate = FURNITURE_DB.get(item_id)
            if candidate is None or candidate.item_id == worst_item.item_id:
                continue
            eff = stat_efficiency(candidate, targets)
            if eff > best_replacement_eff:
                positions = room_def.valid_anchor_positions(
                    candidate.anchor, candidate.width, candidate.height
                )
                if positions:
                    best_replacement = candidate
                    best_replacement_eff = eff

        if best_replacement is None:
            break

        # Temporarily remove worst, try to place best_replacement
        grid.remove_item(worst_pf)
        qty_map[worst_item.item_id] = qty_map.get(worst_item.item_id, 0) + 1

        pos = grid.try_place(best_replacement)
        if pos is not None:
            qty_map[best_replacement.item_id] -= 1
            new_stats = compute_placement_stats(room_def, grid.placed_items)
            new_score = score_against_targets(new_stats, targets)
            if new_score > current_score:
                # Keep the swap
                continue
            else:
                # Revert the swap
                grid.remove_item(grid.placed_items[-1])
                qty_map[best_replacement.item_id] += 1

        # Re-place original item
        grid.try_place(worst_item)
        qty_map[worst_item.item_id] -= 1
        break

    # ── Finalise result ───────────────────────────────────────────────────
    result.placements = list(grid.placed_items)
    result.stats = compute_placement_stats(room_def, result.placements)
    result.score = score_against_targets(result.stats, targets)
    result.tiles_used = grid.used_tiles
    return result
