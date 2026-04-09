"""
Stat Calculator
----------------
Utility functions for computing room and house stat totals,
efficiency scores, and compatibility checks.
"""

from typing import Dict, List, Tuple
from src.data.furniture_db import (
    FurnitureItem, FURNITURE_DB, ALL_STATS,
    STAT_APPEAL, STAT_COMFORT, STAT_HYGIENE, STAT_FUN, STAT_HEALTH, STAT_BREEDING,
)
from src.data.room_data import RoomDefinition


def empty_stats() -> Dict[str, int]:
    """Return a zeroed stat dictionary."""
    return {s: 0 for s in ALL_STATS}


def compute_room_stats(
    room_def: RoomDefinition,
    placed_items: List[Tuple[FurnitureItem, int]],  # (item, quantity)
) -> Dict[str, int]:
    """
    Compute the total stats for a room given a list of (item, quantity) tuples.
    Includes the room's base_appeal.
    """
    totals = empty_stats()
    totals[STAT_APPEAL] += room_def.base_appeal

    for item, qty in placed_items:
        for stat, val in item.stats.items():
            totals[stat] = totals.get(stat, 0) + val * qty

    return totals


def compute_placement_stats(
    room_def: RoomDefinition,
    placements: list,  # List[PlacedFurniture]
) -> Dict[str, int]:
    """Compute stats for a room from a list of PlacedFurniture objects."""
    from src.data.save_parser import PlacedFurniture
    totals = empty_stats()
    totals[STAT_APPEAL] += room_def.base_appeal
    for pf in placements:
        item = FURNITURE_DB.get(pf.item_id)
        if item:
            for stat, val in item.stats.items():
                totals[stat] = totals.get(stat, 0) + val * pf.quantity
    return totals


def score_against_targets(
    room_stats: Dict[str, int],
    targets: Dict[str, int],
) -> float:
    """
    Compute how well a room's stats meet the targets.

    Returns a score in [0, 1]:
      - 1.0  means all targets are met or exceeded
      - 0.0  means no target is met at all
    """
    if not targets:
        return 1.0

    total_weight = 0.0
    achieved_weight = 0.0

    for stat, target in targets.items():
        if target <= 0:
            continue
        total_weight += target
        achieved = min(room_stats.get(stat, 0), target)
        achieved_weight += achieved

    if total_weight == 0:
        return 1.0
    return achieved_weight / total_weight


def score_overflow(
    room_stats: Dict[str, int],
    targets: Dict[str, int],
) -> Dict[str, int]:
    """Return how much each stat exceeds its target (positive = surplus)."""
    result: Dict[str, int] = {}
    for stat in ALL_STATS:
        result[stat] = room_stats.get(stat, 0) - targets.get(stat, 0)
    return result


def stat_efficiency(item: FurnitureItem, target_stats: Dict[str, int]) -> float:
    """
    Compute the weighted efficiency of a furniture item relative to
    the target stats. Items that contribute more to desired stats per
    tile have higher efficiency.
    """
    weight_sum = sum(max(0, v) for v in target_stats.values())
    if weight_sum == 0 or item.area == 0:
        return item.stat_density

    weighted_total = 0.0
    for stat, target in target_stats.items():
        if target > 0:
            contribution = item.get_stat(stat) * target
            weighted_total += contribution

    return weighted_total / (item.area * weight_sum)


def rank_furniture_for_targets(
    items: List[FurnitureItem],
    targets: Dict[str, int],
    room_def: RoomDefinition,
) -> List[Tuple[FurnitureItem, float]]:
    """
    Rank furniture items by how well they help reach the given stat
    targets in the specified room.  Returns (item, score) sorted descending.
    """
    ranked: List[Tuple[FurnitureItem, float]] = []
    for item in items:
        # Check room compatibility
        if item.category not in room_def.compatible_categories:
            continue
        # Check there is at least one valid placement in the room
        positions = room_def.valid_anchor_positions(item.anchor, item.width, item.height)
        if not positions:
            continue
        eff = stat_efficiency(item, targets)
        ranked.append((item, eff))

    ranked.sort(key=lambda t: t[1], reverse=True)
    return ranked


def house_appeal_total(
    room_defs: List[RoomDefinition],
    room_placements: Dict[str, list],
) -> int:
    """
    Compute the total house appeal — sum of appeal stats across all rooms.
    """
    from src.data.save_parser import PlacedFurniture
    total = 0
    for room_def in room_defs:
        pf_list = room_placements.get(room_def.room_type, [])
        stats = compute_placement_stats(room_def, pf_list)
        total += stats[STAT_APPEAL]
    return total
