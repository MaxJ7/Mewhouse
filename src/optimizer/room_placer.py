"""
Room Placer / Furniture Assigner
----------------------------------
Determines the optimal assignment of furniture items to rooms so that
each room's stat targets are best met.  When multiple rooms share the
same furniture pool, this module divides the pool intelligently.

Algorithm
  1. For each room, compute a "want vector" — how much more of each stat
     it still needs after receiving its naturally-compatible furniture.
  2. For contested items (items that could help multiple rooms), assign
     them to the room with the highest marginal gain.
  3. Return a per-room inventory mapping that the layout optimizer can
     then use to arrange furniture inside each room.
"""

from typing import Dict, List, Tuple, Optional
from src.data.furniture_db import (
    FurnitureItem, FURNITURE_DB, ALL_STATS,
    STAT_APPEAL, STAT_COMFORT, STAT_HYGIENE, STAT_FUN, STAT_HEALTH, STAT_BREEDING,
)
from src.data.room_data import RoomDefinition, get_room, get_all_rooms
from src.optimizer.stat_calculator import (
    stat_efficiency, rank_furniture_for_targets,
    compute_room_stats, score_against_targets, empty_stats,
)
from src.optimizer.layout_optimizer import optimize_room_layout, PlacementResult


class RoomAssignment:
    """
    Holds the assignment result for all rooms.
    """

    def __init__(self):
        # room_type -> {item_id: quantity}
        self.room_inventories: Dict[str, Dict[str, int]] = {}
        # room_type -> PlacementResult (filled after layout optimisation)
        self.layout_results: Dict[str, PlacementResult] = {}

    def get_inventory(self, room_type: str) -> Dict[str, int]:
        return self.room_inventories.get(room_type, {})

    def set_inventory(self, room_type: str, inv: Dict[str, int]) -> None:
        self.room_inventories[room_type] = inv

    def total_score(self, targets_per_room: Dict[str, Dict[str, int]]) -> float:
        """Average score across all rooms that have targets."""
        scores = []
        for rt, result in self.layout_results.items():
            tgt = targets_per_room.get(rt, {})
            if any(v > 0 for v in tgt.values()):
                scores.append(result.score)
        return sum(scores) / len(scores) if scores else 0.0


def assign_furniture_to_rooms(
    unlocked_rooms: List[str],
    global_inventory: Dict[str, int],     # item_id -> total quantity
    targets_per_room: Dict[str, Dict[str, int]],  # room_type -> {stat: value}
    run_layout: bool = True,
) -> RoomAssignment:
    """
    Assign furniture from *global_inventory* to rooms in *unlocked_rooms*
    to best meet *targets_per_room*.

    Parameters
    ----------
    unlocked_rooms     : Room types the player has access to
    global_inventory   : All furniture the player owns
    targets_per_room   : Per-room stat targets
    run_layout         : If True, also run layout optimisation per room

    Returns
    -------
    A RoomAssignment with per-room inventories (and optionally layouts).
    """
    assignment = RoomAssignment()
    remaining_inventory: Dict[str, int] = dict(global_inventory)

    # ── Pass 1: assign exclusive items (only useful to one room) ──────────
    for room_type in unlocked_rooms:
        room_def = get_room(room_type)
        targets = targets_per_room.get(room_type, {})
        assignment.set_inventory(room_type, {})

        # Identify items compatible exclusively with this room type
        exclusive_items: List[FurnitureItem] = []
        for item_id, qty in list(remaining_inventory.items()):
            if qty <= 0:
                continue
            item = FURNITURE_DB.get(item_id)
            if item is None:
                continue
            if item.category not in room_def.compatible_categories:
                continue
            # Check if this item is incompatible with all other rooms
            other_rooms = [r for r in unlocked_rooms if r != room_type]
            compatible_elsewhere = any(
                item.category in get_room(r).compatible_categories
                for r in other_rooms
            )
            if not compatible_elsewhere:
                exclusive_items.append(item)

        # Give all exclusive items to this room
        for item in exclusive_items:
            qty = remaining_inventory.pop(item.item_id, 0)
            if qty > 0:
                assignment.room_inventories[room_type][item.item_id] = qty

    # ── Pass 2: greedily assign contested items by marginal gain ──────────
    contested: List[Tuple[str, int]] = [
        (iid, qty) for iid, qty in remaining_inventory.items() if qty > 0
    ]

    for item_id, total_qty in contested:
        item = FURNITURE_DB.get(item_id)
        if item is None:
            continue

        # Compute marginal efficiency for this item in each eligible room
        room_scores: List[Tuple[str, float]] = []
        for room_type in unlocked_rooms:
            room_def = get_room(room_type)
            if item.category not in room_def.compatible_categories:
                continue
            targets = targets_per_room.get(room_type, {})
            eff = stat_efficiency(item, targets) if targets else item.stat_density
            room_scores.append((room_type, eff))

        if not room_scores:
            continue

        # Sort rooms by descending marginal gain
        room_scores.sort(key=lambda t: t[1], reverse=True)

        qty_left = total_qty
        for room_type, _eff in room_scores:
            if qty_left <= 0:
                break
            # Give up to half the remaining quantity to each room,
            # minimum 1 (ensure top room always gets at least 1).
            give = max(1, qty_left // max(len(room_scores), 1))
            give = min(give, qty_left)

            inv = assignment.room_inventories.setdefault(room_type, {})
            inv[item_id] = inv.get(item_id, 0) + give
            qty_left -= give

        # Any leftovers go to the top room
        if qty_left > 0 and room_scores:
            top_room = room_scores[0][0]
            inv = assignment.room_inventories.setdefault(top_room, {})
            inv[item_id] = inv.get(item_id, 0) + qty_left

    # ── Pass 3: run layout optimisation per room (optional) ───────────────
    if run_layout:
        for room_type in unlocked_rooms:
            inv = assignment.room_inventories.get(room_type, {})
            targets = targets_per_room.get(room_type, {})
            try:
                result = optimize_room_layout(
                    room_type=room_type,
                    inventory=inv,
                    targets=targets,
                )
                assignment.layout_results[room_type] = result
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning(
                    "Layout optimisation failed for %s: %s", room_type, exc
                )

    return assignment
