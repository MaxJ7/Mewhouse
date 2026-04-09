"""
Tests for the furniture database.
"""

import pytest
from src.data.furniture_db import (
    FURNITURE_DB, FurnitureItem, get_all_furniture, get_by_category,
    get_by_anchor, get_top_stat_items,
    ALL_STATS, ALL_CATEGORIES,
    STAT_APPEAL, STAT_COMFORT, STAT_HYGIENE, STAT_FUN, STAT_HEALTH, STAT_BREEDING,
    CAT_SLEEPING, CAT_HYGIENE_CAT, CAT_FEEDING, CAT_ENTERTAINMENT,
)


class TestFurnitureDatabase:

    def test_database_not_empty(self):
        assert len(FURNITURE_DB) > 0

    def test_all_items_have_required_fields(self):
        for item_id, item in FURNITURE_DB.items():
            assert item.item_id == item_id, f"ID mismatch for {item_id}"
            assert item.name, f"Empty name for {item_id}"
            assert item.width > 0,  f"Non-positive width for {item_id}"
            assert item.height > 0, f"Non-positive height for {item_id}"
            assert item.anchor in ("floor", "wall", "ceiling"), \
                f"Invalid anchor {item.anchor!r} for {item_id}"
            assert item.category in ALL_CATEGORIES, \
                f"Unknown category {item.category!r} for {item_id}"

    def test_all_stats_are_non_negative(self):
        for item_id, item in FURNITURE_DB.items():
            for stat, val in item.stats.items():
                assert val >= 0, \
                    f"Negative stat {stat}={val} for {item_id}"

    def test_stat_keys_are_valid(self):
        for item_id, item in FURNITURE_DB.items():
            for stat in item.stats:
                assert stat in ALL_STATS, \
                    f"Unknown stat {stat!r} in {item_id}"

    def test_area_calculation(self):
        item = FURNITURE_DB["litter_box"]
        assert item.area == item.width * item.height

    def test_stat_total(self):
        item = FURNITURE_DB["litter_box"]
        assert item.stat_total == sum(v for v in item.stats.values() if v > 0)

    def test_stat_density(self):
        item = FURNITURE_DB["breeding_shrine"]
        assert item.stat_density == pytest.approx(item.stat_total / item.area)

    def test_get_stat_missing_returns_zero(self):
        item = FURNITURE_DB["litter_box"]  # only has hygiene
        assert item.get_stat(STAT_FUN) == 0

    def test_to_dict_and_back(self):
        original = FURNITURE_DB["cat_tree"]
        d = original.to_dict()
        restored = FurnitureItem.from_dict(d)
        assert restored.item_id == original.item_id
        assert restored.name    == original.name
        assert restored.width   == original.width
        assert restored.height  == original.height
        assert restored.stats   == original.stats

    def test_get_all_furniture_sorted(self):
        items = get_all_furniture()
        names = [i.name for i in items]
        assert names == sorted(names)

    def test_get_by_category(self):
        hygiene_items = get_by_category(CAT_HYGIENE_CAT)
        assert len(hygiene_items) > 0
        for item in hygiene_items:
            assert item.category == CAT_HYGIENE_CAT

    def test_get_by_anchor(self):
        wall_items = get_by_anchor("wall")
        assert len(wall_items) > 0
        for item in wall_items:
            assert item.anchor == "wall"

    def test_get_top_stat_items(self):
        top_appeal = get_top_stat_items(STAT_APPEAL, n=5)
        assert len(top_appeal) <= 5
        # Verify they are sorted descending
        appeals = [i.get_stat(STAT_APPEAL) for i in top_appeal]
        assert appeals == sorted(appeals, reverse=True)

    def test_breeding_items_have_breeding_stat(self):
        from src.data.furniture_db import CAT_BREEDING
        breeding_items = get_by_category(CAT_BREEDING)
        assert len(breeding_items) > 0
        for item in breeding_items:
            assert item.get_stat(STAT_BREEDING) > 0

    def test_floor_anchored_items_have_positive_dimensions(self):
        floor_items = get_by_anchor("floor")
        for item in floor_items:
            assert item.width >= 1
            assert item.height >= 1

    def test_litter_box_stats(self):
        lb = FURNITURE_DB["litter_box"]
        assert lb.get_stat(STAT_HYGIENE) >= 1
        assert lb.anchor == "floor"

    def test_breeding_bed_has_breeding_stat(self):
        bb = FURNITURE_DB["breeding_bed"]
        assert bb.get_stat(STAT_BREEDING) > 0
        assert bb.anchor == "floor"
