"""
Mewgenics Save File Parser
---------------------------
Reads and parses Mewgenics save files to extract:
  - Which house rooms have been unlocked
  - The player's furniture inventory
  - Current room configurations / furniture placements

Mewgenics save data location (auto-detected):
  Windows : %APPDATA%\\Mewgenics\\
  macOS   : ~/Library/Application Support/Mewgenics/
  Linux   : ~/.local/share/Mewgenics/  (Steam) or
            ~/.steam/steam/userdata/<id>/... (Steam cloud)

Save file format:
  Mewgenics (by Edmund McMillen / Four Horses) stores its save data
  as binary-serialised structures.  The exact binary layout varies by
  game version; this parser handles the most common layout and falls
  back to a JSON-based format for modded / exported saves.

If no real save is found, the parser returns a demo / default state
that lets the user explore the optimiser without needing the game.
"""

import json
import os
import struct
import platform
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from src.data.furniture_db import (
    FURNITURE_DB, FurnitureItem, get_all_furniture,
    STAT_APPEAL, STAT_COMFORT, STAT_HYGIENE, STAT_FUN, STAT_HEALTH, STAT_BREEDING,
)
from src.data.room_data import (
    ALL_ROOM_TYPES, ROOM_BEDROOM, ROOM_BATHROOM, ROOM_KITCHEN,
    ROOM_LIVING_ROOM, ROOM_PLAYROOM, ROOM_NURSERY, ROOM_BREEDING_ROOM,
    ROOM_GARDEN, ROOM_STORAGE, ROOM_DINING,
)

logger = logging.getLogger(__name__)


# ── Data classes ────────────────────────────────────────────────────────────

class PlacedFurniture:
    """A single piece of furniture placed in a room."""

    def __init__(
        self,
        item_id: str,
        x: int,
        y: int,
        room_type: str = "",
        quantity: int = 1,
    ):
        self.item_id = item_id
        self.x = x
        self.y = y
        self.room_type = room_type
        self.quantity = quantity

    @property
    def furniture(self) -> Optional[FurnitureItem]:
        return FURNITURE_DB.get(self.item_id)

    def to_dict(self) -> dict:
        return {
            "item_id":   self.item_id,
            "x":         self.x,
            "y":         self.y,
            "room_type": self.room_type,
            "quantity":  self.quantity,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PlacedFurniture":
        return cls(
            item_id=d["item_id"],
            x=d["x"],
            y=d["y"],
            room_type=d.get("room_type", ""),
            quantity=d.get("quantity", 1),
        )

    def __repr__(self) -> str:
        return f"PlacedFurniture({self.item_id!r} @ ({self.x},{self.y}) in {self.room_type!r})"


class GameState:
    """
    The complete state loaded from (or defaulting for) a Mewgenics save.
    """

    def __init__(self):
        # Rooms the player has unlocked
        self.unlocked_rooms: List[str] = [ROOM_BEDROOM]

        # Furniture inventory: item_id -> quantity owned (not placed)
        self.inventory: Dict[str, int] = {}

        # Furniture currently placed in rooms: room_type -> [PlacedFurniture]
        self.placements: Dict[str, List[PlacedFurniture]] = {
            rt: [] for rt in ALL_ROOM_TYPES
        }

        # Miscellaneous save metadata
        self.save_path: Optional[Path] = None
        self.game_version: str = "unknown"
        self.loaded_from_file: bool = False

    # ── inventory helpers ─────────────────────────────────────────────────

    def add_to_inventory(self, item_id: str, qty: int = 1) -> None:
        self.inventory[item_id] = self.inventory.get(item_id, 0) + qty

    def remove_from_inventory(self, item_id: str, qty: int = 1) -> bool:
        have = self.inventory.get(item_id, 0)
        if have < qty:
            return False
        self.inventory[item_id] = have - qty
        if self.inventory[item_id] == 0:
            del self.inventory[item_id]
        return True

    def get_all_owned_items(self) -> List[Tuple[FurnitureItem, int]]:
        """Return (FurnitureItem, total_quantity) for every owned item
        (inventory + placed combined)."""
        totals: Dict[str, int] = dict(self.inventory)
        for placements in self.placements.values():
            for p in placements:
                totals[p.item_id] = totals.get(p.item_id, 0) + p.quantity
        result = []
        for item_id, qty in totals.items():
            item = FURNITURE_DB.get(item_id)
            if item:
                result.append((item, qty))
        return sorted(result, key=lambda t: t[0].name)

    # ── placement helpers ─────────────────────────────────────────────────

    def place_item(self, item_id: str, room_type: str, x: int, y: int) -> bool:
        if item_id not in FURNITURE_DB:
            return False
        if room_type not in ALL_ROOM_TYPES:
            return False
        pf = PlacedFurniture(item_id=item_id, x=x, y=y, room_type=room_type)
        self.placements[room_type].append(pf)
        return True

    def clear_room(self, room_type: str) -> None:
        self.placements[room_type] = []

    def get_room_furniture(self, room_type: str) -> List[PlacedFurniture]:
        return self.placements.get(room_type, [])

    # ── serialisation ─────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "unlocked_rooms": self.unlocked_rooms,
            "inventory":      self.inventory,
            "placements": {
                rt: [p.to_dict() for p in ps]
                for rt, ps in self.placements.items()
            },
            "game_version":   self.game_version,
        }

    def save_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)
        logger.info("Saved state to %s", path)

    @classmethod
    def load_json(cls, path: Path) -> "GameState":
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        state = cls()
        state.unlocked_rooms = data.get("unlocked_rooms", [ROOM_BEDROOM])
        state.inventory = data.get("inventory", {})
        raw_placements = data.get("placements", {})
        for rt, items in raw_placements.items():
            state.placements[rt] = [PlacedFurniture.from_dict(d) for d in items]
        state.game_version = data.get("game_version", "json-export")
        state.save_path = path
        state.loaded_from_file = True
        return state


# ── Save file location detection ────────────────────────────────────────────

def _candidate_save_dirs() -> List[Path]:
    """Return candidate directories where Mewgenics saves might live."""
    candidates: List[Path] = []
    system = platform.system()

    if system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            candidates.append(Path(appdata) / "Mewgenics")
        candidates.append(Path.home() / "AppData" / "Roaming" / "Mewgenics")
        candidates.append(Path.home() / "AppData" / "Local" / "Mewgenics")

    elif system == "Darwin":
        candidates.append(Path.home() / "Library" / "Application Support" / "Mewgenics")

    else:  # Linux / Steam
        xdg = os.environ.get("XDG_DATA_HOME", "")
        if xdg:
            candidates.append(Path(xdg) / "Mewgenics")
        candidates.append(Path.home() / ".local" / "share" / "Mewgenics")
        # Steam cloud saves
        steam_base = Path.home() / ".steam" / "steam" / "userdata"
        if steam_base.exists():
            for user_dir in steam_base.iterdir():
                candidates.append(user_dir / "1876570" / "remote")

    return candidates


def find_save_files() -> List[Path]:
    """Return a list of discovered Mewgenics save file paths."""
    found: List[Path] = []
    for directory in _candidate_save_dirs():
        if not directory.exists():
            continue
        for ext in ("*.sav", "*.json", "*.dat", "save*"):
            found.extend(directory.glob(ext))
    return found


# ── Binary save parser ───────────────────────────────────────────────────────
# Mewgenics uses a custom binary format.  The parser below handles the
# structure documented by the community.  Unknown chunks are skipped safely.

_MAGIC = b"MEWG"
_VERSION_OFFSET = 4


def _try_parse_binary(data: bytes) -> Optional[GameState]:
    """
    Attempt to parse a raw binary save file.  Returns None if the data
    does not look like a recognised Mewgenics save.
    """
    if len(data) < 8:
        return None
    if data[:4] != _MAGIC:
        return None

    state = GameState()
    try:
        version = struct.unpack_from("<I", data, _VERSION_OFFSET)[0]
        state.game_version = str(version)

        # Locate the room-unlock bitmask (offset 8, 4 bytes)
        room_mask = struct.unpack_from("<I", data, 8)[0]
        room_list = list(ALL_ROOM_TYPES)
        for i, rt in enumerate(room_list):
            if room_mask & (1 << i):
                state.unlocked_rooms.append(rt)

        # Inventory section starts at offset 12:
        #   uint16 count, then count * (uint8 id_len, char[] id, uint16 qty)
        offset = 12
        if offset + 2 <= len(data):
            item_count = struct.unpack_from("<H", data, offset)[0]
            offset += 2
            for _ in range(item_count):
                if offset + 1 > len(data):
                    break
                id_len = data[offset]
                offset += 1
                item_id = data[offset:offset + id_len].decode("utf-8", errors="replace")
                offset += id_len
                if offset + 2 > len(data):
                    break
                qty = struct.unpack_from("<H", data, offset)[0]
                offset += 2
                state.add_to_inventory(item_id, qty)

        state.loaded_from_file = True
        return state

    except struct.error as exc:
        logger.debug("Binary parse failed: %s", exc)
        return None


def _try_parse_json(data: bytes) -> Optional[GameState]:
    """Attempt to parse a JSON-formatted save."""
    try:
        text = data.decode("utf-8")
        raw = json.loads(text)
        state = GameState()
        state.unlocked_rooms = raw.get("unlocked_rooms", [ROOM_BEDROOM])
        state.inventory = raw.get("inventory", {})
        for rt, items in raw.get("placements", {}).items():
            state.placements[rt] = [PlacedFurniture.from_dict(d) for d in items]
        state.game_version = raw.get("game_version", "json")
        state.loaded_from_file = True
        return state
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def parse_save_file(path: Path) -> GameState:
    """
    Parse a Mewgenics save file at the given path.
    Tries binary format first, then JSON.
    Raises ValueError if the file cannot be parsed.
    """
    with open(path, "rb") as fh:
        data = fh.read()

    state = _try_parse_binary(data) or _try_parse_json(data)
    if state is None:
        raise ValueError(f"Could not parse save file: {path}")

    state.save_path = path
    logger.info("Loaded save from %s (version=%s)", path, state.game_version)
    return state


# ── Default / demo state ─────────────────────────────────────────────────────

def create_demo_state() -> GameState:
    """
    Create a realistic demo GameState for users who don't have a save file.
    Includes a selection of common furniture and a few unlocked rooms.
    """
    state = GameState()
    state.game_version = "demo"
    state.loaded_from_file = False

    # Unlock a few rooms
    state.unlocked_rooms = [
        ROOM_BEDROOM, ROOM_BATHROOM, ROOM_LIVING_ROOM, ROOM_KITCHEN,
    ]

    # Populate inventory with a realistic set of items
    starter_items = {
        "litter_box":        2,
        "cat_bed":           3,
        "food_bowl":         4,
        "water_bowl":        4,
        "scratching_post":   2,
        "plant_small":       3,
        "couch":             1,
        "cushion":           4,
        "bookshelf":         1,
        "painting_small":    2,
        "lamp_floor":        2,
        "rug_small":         2,
        "window":            2,
        "flower_pot":        3,
        "sink":              1,
        "toilet":            1,
        "mirror":            1,
        "double_bowl":       1,
        "toy_box":           1,
        "dresser":           1,
        "tv":                1,
        "cat_tree":          1,
        "fish_tank":         1,
        "bathtub":           1,
        "breeding_bed":      1,
        "romance_candles":   2,
        "vanity":            1,
        "fairy_lights":      2,
        "wall_shelf":        2,
    }

    for item_id, qty in starter_items.items():
        if item_id in FURNITURE_DB:
            state.add_to_inventory(item_id, qty)

    return state


# ── Auto-load helper ─────────────────────────────────────────────────────────

def auto_load() -> GameState:
    """
    Try to find and load a Mewgenics save file automatically.
    Falls back to the demo state if nothing is found.
    """
    saves = find_save_files()
    for path in saves:
        try:
            return parse_save_file(path)
        except Exception as exc:
            logger.warning("Could not load %s: %s", path, exc)

    logger.info("No save file found — loading demo state.")
    return create_demo_state()
