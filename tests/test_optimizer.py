"""
Tests for the room layout optimizer and stat calculator.
"""

import pytest
from src.data.furniture_db import (
    FURNITURE_DB,
    STAT_APPEAL, STAT_COMFORT, STAT_HYGIENE, STAT_FUN, STAT_HEALTH, STAT_BREEDING,
)
from src.data.room_data import (
    get_room, ROOM_BEDROOM, ROOM_BATHROOM, ROOM_BREEDING_ROOM, ROOM_LIVING_ROOM,
    ROOM_PLAYROOM,
)
from src.optimizer.stat_calculator import (
    compute_room_stats, score_against_targets, stat_efficiency,
    rank_furniture_for_targets, empty_stats,
)
from src.optimizer.layout_optimizer import (
    optimize_room_layout, RoomGrid, PlacementResult,
)
from src.data.save_parser import PlacedFurniture


class TestStatCalculator:

    def test_empty_stats_all_zero(self):
        s = empty_stats()
        for stat in s.values():
            assert stat == 0

    def test_compute_room_stats_base_appeal(self):
        room = get_room(ROOM_BEDROOM)
        stats = compute_room_stats(room, [])
        assert stats[STAT_APPEAL] == room.base_appeal

    def test_compute_room_stats_adds_furniture(self):
        room = get_room(ROOM_BATHROOM)
        item = FURNITURE_DB["litter_box"]
        stats = compute_room_stats(room, [(item, 1)])
        assert stats[STAT_HYGIENE] == item.get_stat(STAT_HYGIENE)
        assert stats[STAT_APPEAL]  == room.base_appeal + item.get_stat(STAT_APPEAL)

    def test_compute_room_stats_respects_quantity(self):
        room = get_room(ROOM_BEDROOM)
        item = FURNITURE_DB["litter_box"]
        stats2 = compute_room_stats(room, [(item, 2)])
        stats1 = compute_room_stats(room, [(item, 1)])
        assert stats2[STAT_HYGIENE] == 2 * stats1[STAT_HYGIENE]

    def test_score_all_targets_met(self):
        room_stats = {STAT_HYGIENE: 10, STAT_APPEAL: 5, STAT_COMFORT: 3}
        targets    = {STAT_HYGIENE: 8,  STAT_APPEAL: 5}
        score = score_against_targets(room_stats, targets)
        assert score == pytest.approx(1.0)

    def test_score_partially_met(self):
        room_stats = {STAT_HYGIENE: 4}
        targets    = {STAT_HYGIENE: 8}
        score = score_against_targets(room_stats, targets)
        assert score == pytest.approx(0.5)

    def test_score_empty_targets_returns_one(self):
        assert score_against_targets({}, {}) == pytest.approx(1.0)
        assert score_against_targets({STAT_APPEAL: 10}, {}) == pytest.approx(1.0)

    def test_stat_efficiency_higher_for_relevant_stat(self):
        item_h = FURNITURE_DB["litter_box"]     # hygiene-focused
        item_f = FURNITURE_DB["cat_tree"]       # fun-focused
        targets = {STAT_HYGIENE: 10}
        eff_h = stat_efficiency(item_h, targets)
        eff_f = stat_efficiency(item_f, targets)
        assert eff_h > eff_f

    def test_rank_furniture_for_targets_orders_descending(self):
        room = get_room(ROOM_BATHROOM)
        items = list(FURNITURE_DB.values())
        targets = {STAT_HYGIENE: 20}
        ranked = rank_furniture_for_targets(items, targets, room)
        scores = [s for _, s in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_rank_excludes_incompatible_categories(self):
        room = get_room(ROOM_BATHROOM)
        # Breeding items should not appear in bathroom ranking
        items = list(FURNITURE_DB.values())
        targets = {STAT_HYGIENE: 10}
        ranked = rank_furniture_for_targets(items, targets, room)
        ranked_ids = {item.item_id for item, _ in ranked}
        from src.data.furniture_db import CAT_BREEDING
        for item_id, item in FURNITURE_DB.items():
            if item.category == CAT_BREEDING:
                assert item_id not in ranked_ids, \
                    f"Breeding item {item_id!r} should not rank for bathroom"


class TestRoomGrid:

    def test_grid_created_with_correct_dimensions(self):
        room = get_room(ROOM_BEDROOM)
        grid = RoomGrid(room)
        # Grid starts empty
        assert grid.used_tiles == 0

    def test_place_floor_item(self):
        room = get_room(ROOM_BEDROOM)
        grid = RoomGrid(room)
        item = FURNITURE_DB["cat_bed"]  # 2×1 floor
        pos = grid.try_place(item)
        assert pos is not None
        assert len(grid.placed_items) == 1

    def test_place_wall_item(self):
        room = get_room(ROOM_BEDROOM)
        grid = RoomGrid(room)
        item = FURNITURE_DB["mirror"]  # 1×2 wall
        pos = grid.try_place(item)
        assert pos is not None
        placed = grid.placed_items[0]
        assert placed.y < room.wall_rows + item.height  # within wall zone

    def test_cannot_overlap(self):
        room = get_room(ROOM_BEDROOM)
        grid = RoomGrid(room)
        item = FURNITURE_DB["rug_large"]  # 4×3 floor

        # Place first
        pos1 = grid.try_place(item)
        assert pos1 is not None

        # A second large rug should find a different position or fail
        # (since the room may not have room for two 4×3 items)
        pos2 = grid.try_place(item)
        if pos2 is not None:
            assert pos1 != pos2

    def test_remove_item_frees_space(self):
        room = get_room(ROOM_BEDROOM)
        grid = RoomGrid(room)
        item = FURNITURE_DB["rug_large"]  # 4×3 floor

        pos = grid.try_place(item)
        assert pos is not None
        placed = grid.placed_items[-1]
        grid.remove_item(placed)
        assert len(grid.placed_items) == 0
        assert grid.used_tiles == 0

    def test_items_do_not_exceed_grid_bounds(self):
        room = get_room(ROOM_BEDROOM)
        grid = RoomGrid(room)
        items = [FURNITURE_DB[k] for k in list(FURNITURE_DB.keys())[:20]]
        for item in items:
            grid.try_place(item)

        for pf in grid.placed_items:
            item = FURNITURE_DB[pf.item_id]
            assert pf.x >= 0
            assert pf.y >= 0
            assert pf.x + item.width  <= room.grid_width
            assert pf.y + item.height <= room.grid_height


class TestLayoutOptimizer:

    def test_optimize_returns_placement_result(self):
        inventory = {"litter_box": 3, "cat_bed": 2, "mirror": 1}
        targets = {STAT_HYGIENE: 10, STAT_COMFORT: 5}
        result = optimize_room_layout(ROOM_BEDROOM, inventory, targets)
        assert isinstance(result, PlacementResult)

    def test_optimize_respects_max_items(self):
        inventory = {k: 5 for k in FURNITURE_DB}
        targets = {STAT_COMFORT: 50}
        result = optimize_room_layout(ROOM_BEDROOM, inventory, targets, max_items=5)
        assert len(result.placements) <= 5

    def test_optimize_placements_within_bounds(self):
        room = get_room(ROOM_BEDROOM)
        inventory = {"cat_bed": 3, "mirror": 2, "bookshelf": 1}
        targets = {STAT_COMFORT: 15}
        result = optimize_room_layout(ROOM_BEDROOM, inventory, targets)

        for pf in result.placements:
            item = FURNITURE_DB[pf.item_id]
            assert pf.x + item.width  <= room.grid_width,  f"{pf} out of bounds"
            assert pf.y + item.height <= room.grid_height, f"{pf} out of bounds"

    def test_optimize_breeding_room_uses_breeding_items(self):
        inventory = {
            "breeding_bed": 1,
            "romance_candles": 2,
            "love_potion_stand": 1,
        }
        targets = {STAT_BREEDING: 15}
        result = optimize_room_layout(ROOM_BREEDING_ROOM, inventory, targets)
        placed_ids = {p.item_id for p in result.placements}
        breeding_ids = {"breeding_bed", "romance_candles", "love_potion_stand"}
        assert len(placed_ids & breeding_ids) > 0

    def test_optimize_score_between_zero_and_one(self):
        inventory = {"cat_bed": 2, "litter_box": 2}
        targets = {STAT_COMFORT: 10, STAT_HYGIENE: 8}
        result = optimize_room_layout(ROOM_BEDROOM, inventory, targets)
        assert 0.0 <= result.score <= 1.0

    def test_optimize_no_overlap(self):
        """All placed items in the result must have non-overlapping tiles."""
        inventory = {k: 2 for k in list(FURNITURE_DB.keys())[:10]}
        targets = {STAT_COMFORT: 20}
        result = optimize_room_layout(ROOM_BEDROOM, inventory, targets)

        occupied = set()
        for pf in result.placements:
            item = FURNITURE_DB[pf.item_id]
            for dx in range(item.width):
                for dy in range(item.height):
                    tile = (pf.x + dx, pf.y + dy)
                    assert tile not in occupied, \
                        f"Overlap at {tile} from {pf.item_id}"
                    occupied.add(tile)

    def test_optimize_fill_ratio_valid(self):
        inventory = {"couch": 1, "armchair": 1, "rug_large": 1}
        targets = {STAT_COMFORT: 10}
        result = optimize_room_layout(ROOM_LIVING_ROOM, inventory, targets)
        assert 0.0 <= result.fill_ratio <= 1.0

    def test_optimize_with_empty_inventory(self):
        result = optimize_room_layout(ROOM_BEDROOM, {}, {STAT_COMFORT: 10})
        assert len(result.placements) == 0
        assert result.score == pytest.approx(0.0)

    def test_optimize_stats_match_placements(self):
        """Verify that result.stats accurately reflects what was placed."""
        from src.optimizer.stat_calculator import compute_placement_stats
        inventory = {"litter_box": 2, "bathtub": 1}
        targets = {STAT_HYGIENE: 10}
        result = optimize_room_layout(ROOM_BATHROOM, inventory, targets)

        room_def = get_room(ROOM_BATHROOM)
        computed = compute_placement_stats(room_def, result.placements)
        assert result.stats == computed
