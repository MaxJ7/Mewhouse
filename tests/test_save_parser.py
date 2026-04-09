"""
Tests for the save file parser.
"""

import json
import struct
import tempfile
from pathlib import Path

import pytest

from src.data.save_parser import (
    GameState, PlacedFurniture, parse_save_file, create_demo_state,
    find_save_files, _try_parse_json,
)
from src.data.room_data import ROOM_BEDROOM, ROOM_BATHROOM, ROOM_BREEDING_ROOM


class TestPlacedFurniture:

    def test_to_dict_and_from_dict(self):
        pf = PlacedFurniture("cat_bed", x=2, y=5, room_type=ROOM_BEDROOM, quantity=1)
        d = pf.to_dict()
        restored = PlacedFurniture.from_dict(d)
        assert restored.item_id   == pf.item_id
        assert restored.x         == pf.x
        assert restored.y         == pf.y
        assert restored.room_type == pf.room_type

    def test_furniture_property_resolves(self):
        pf = PlacedFurniture("cat_bed", x=0, y=0, room_type=ROOM_BEDROOM)
        assert pf.furniture is not None
        assert pf.furniture.name == "Cat Bed"

    def test_furniture_property_unknown_id(self):
        pf = PlacedFurniture("does_not_exist", x=0, y=0)
        assert pf.furniture is None


class TestGameState:

    def test_initial_state_has_bedroom(self):
        state = GameState()
        assert ROOM_BEDROOM in state.unlocked_rooms

    def test_add_to_inventory(self):
        state = GameState()
        state.add_to_inventory("cat_bed", 3)
        assert state.inventory["cat_bed"] == 3

    def test_add_to_inventory_accumulates(self):
        state = GameState()
        state.add_to_inventory("cat_bed", 2)
        state.add_to_inventory("cat_bed", 3)
        assert state.inventory["cat_bed"] == 5

    def test_remove_from_inventory_success(self):
        state = GameState()
        state.add_to_inventory("cat_bed", 5)
        result = state.remove_from_inventory("cat_bed", 3)
        assert result is True
        assert state.inventory["cat_bed"] == 2

    def test_remove_from_inventory_removes_key_when_zero(self):
        state = GameState()
        state.add_to_inventory("cat_bed", 1)
        state.remove_from_inventory("cat_bed", 1)
        assert "cat_bed" not in state.inventory

    def test_remove_from_inventory_insufficient(self):
        state = GameState()
        state.add_to_inventory("cat_bed", 1)
        result = state.remove_from_inventory("cat_bed", 5)
        assert result is False
        assert state.inventory["cat_bed"] == 1  # unchanged

    def test_place_item(self):
        state = GameState()
        result = state.place_item("cat_bed", ROOM_BEDROOM, x=2, y=5)
        assert result is True
        placements = state.get_room_furniture(ROOM_BEDROOM)
        assert len(placements) == 1
        assert placements[0].item_id == "cat_bed"

    def test_place_item_unknown_id_fails(self):
        state = GameState()
        result = state.place_item("nonexistent_item", ROOM_BEDROOM, x=0, y=0)
        assert result is False

    def test_place_item_unknown_room_fails(self):
        state = GameState()
        result = state.place_item("cat_bed", "nonexistent_room", x=0, y=0)
        assert result is False

    def test_clear_room(self):
        state = GameState()
        state.place_item("cat_bed",    ROOM_BEDROOM, x=0, y=5)
        state.place_item("litter_box", ROOM_BEDROOM, x=3, y=5)
        state.clear_room(ROOM_BEDROOM)
        assert state.get_room_furniture(ROOM_BEDROOM) == []

    def test_get_all_owned_items_combines_inventory_and_placements(self):
        state = GameState()
        state.add_to_inventory("cat_bed", 2)
        state.place_item("cat_bed", ROOM_BEDROOM, x=0, y=5)  # 1 placed
        owned = state.get_all_owned_items()
        item_map = {item.item_id: qty for item, qty in owned}
        # 2 in inventory + 1 placed = 3 total
        assert item_map.get("cat_bed", 0) == 3

    def test_to_dict_and_load_json(self):
        state = GameState()
        state.unlocked_rooms = [ROOM_BEDROOM, ROOM_BATHROOM]
        state.add_to_inventory("litter_box", 2)
        state.place_item("cat_bed", ROOM_BEDROOM, x=0, y=5)

        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False
        ) as f:
            tmp_path = Path(f.name)

        state.save_json(tmp_path)
        restored = GameState.load_json(tmp_path)

        assert set(restored.unlocked_rooms) == {ROOM_BEDROOM, ROOM_BATHROOM}
        assert restored.inventory.get("litter_box") == 2
        bedroom_pf = restored.get_room_furniture(ROOM_BEDROOM)
        assert len(bedroom_pf) == 1
        assert bedroom_pf[0].item_id == "cat_bed"

        tmp_path.unlink()


class TestDemoState:

    def test_demo_state_has_multiple_rooms(self):
        state = create_demo_state()
        assert len(state.unlocked_rooms) >= 2

    def test_demo_state_has_inventory(self):
        state = create_demo_state()
        assert len(state.inventory) > 0

    def test_demo_state_all_inventory_items_are_valid(self):
        from src.data.furniture_db import FURNITURE_DB
        state = create_demo_state()
        for item_id in state.inventory:
            assert item_id in FURNITURE_DB, \
                f"Demo inventory contains unknown item: {item_id!r}"

    def test_demo_state_not_loaded_from_file(self):
        state = create_demo_state()
        assert state.loaded_from_file is False


class TestSaveParser:

    def test_json_round_trip(self):
        state = create_demo_state()
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False
        ) as f:
            tmp_path = Path(f.name)
        state.save_json(tmp_path)
        loaded = parse_save_file(tmp_path)
        assert set(loaded.unlocked_rooms) == set(state.unlocked_rooms)
        tmp_path.unlink()

    def test_invalid_file_raises_value_error(self):
        with tempfile.NamedTemporaryFile(
            suffix=".sav", mode="wb", delete=False
        ) as f:
            f.write(b"\x00\x01\x02GARBAGE_DATA\xff\xfe")
            tmp_path = Path(f.name)
        with pytest.raises(ValueError):
            parse_save_file(tmp_path)
        tmp_path.unlink()

    def test_try_parse_json_valid(self):
        data = json.dumps({
            "unlocked_rooms": [ROOM_BEDROOM, ROOM_BATHROOM],
            "inventory": {"cat_bed": 2},
            "placements": {},
            "game_version": "test",
        }).encode("utf-8")
        state = _try_parse_json(data)
        assert state is not None
        assert ROOM_BEDROOM in state.unlocked_rooms
        assert state.inventory["cat_bed"] == 2

    def test_try_parse_json_invalid(self):
        assert _try_parse_json(b"not json at all!") is None
