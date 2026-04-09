"""
Mewgenics Room Data
--------------------
Defines all room types in Mewgenics, their grid dimensions,
valid anchor zones (floor rows vs wall rows), and the
room-type-to-furniture compatibility map.

Grid coordinate system
  (0, 0) is the top-left tile of the room.
  x increases rightward, y increases downward.

Floor zone   = rows where floor-anchored furniture may be placed
               (typically the bottom N rows, depending on room height).
Wall zone    = rows where wall-anchored furniture may be placed
               (typically the top rows / back wall).
Ceiling zone = the very top row (used only by hanging items).
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional

# ── Room type identifiers ────────────────────────────────────────────────
ROOM_BEDROOM       = "bedroom"
ROOM_BATHROOM      = "bathroom"
ROOM_KITCHEN       = "kitchen"
ROOM_LIVING_ROOM   = "living_room"
ROOM_PLAYROOM      = "playroom"
ROOM_NURSERY       = "nursery"
ROOM_BREEDING_ROOM = "breeding_room"
ROOM_GARDEN        = "garden"
ROOM_STORAGE       = "storage"
ROOM_DINING        = "dining"

ALL_ROOM_TYPES: Tuple[str, ...] = (
    ROOM_BEDROOM, ROOM_BATHROOM, ROOM_KITCHEN, ROOM_LIVING_ROOM,
    ROOM_PLAYROOM, ROOM_NURSERY, ROOM_BREEDING_ROOM,
    ROOM_GARDEN, ROOM_STORAGE, ROOM_DINING,
)

ROOM_DISPLAY_NAMES: Dict[str, str] = {
    ROOM_BEDROOM:       "Bedroom",
    ROOM_BATHROOM:      "Bathroom",
    ROOM_KITCHEN:       "Kitchen",
    ROOM_LIVING_ROOM:   "Living Room",
    ROOM_PLAYROOM:      "Playroom",
    ROOM_NURSERY:       "Nursery",
    ROOM_BREEDING_ROOM: "Breeding Room",
    ROOM_GARDEN:        "Garden",
    ROOM_STORAGE:       "Storage Room",
    ROOM_DINING:        "Dining Room",
}


@dataclass
class RoomDefinition:
    """
    Describes the physical and functional properties of a room type.

    grid_width  – horizontal tile count (in-game standard)
    grid_height – vertical tile count
    wall_rows   – how many rows from the top are 'wall' (back wall tiles)
    ceiling_row – row index of the ceiling (usually 0); None if no ceiling
    floor_start – first row (from top) that is part of the floor zone
    base_appeal – intrinsic appeal bonus before any furniture
    compatible_categories – furniture categories that make sense in this room
    preferred_stats – stats this room type naturally wants to maximise
    description – shown in the UI
    color       – room tile background colour in the canvas
    """

    room_type: str
    display_name: str
    grid_width: int
    grid_height: int
    wall_rows: int
    floor_start: int
    base_appeal: int
    compatible_categories: List[str]
    preferred_stats: List[str]
    description: str = ""
    color: str = "#FAFAFA"
    ceiling_row: Optional[int] = None

    @property
    def floor_rows(self) -> int:
        """Number of rows in the floor zone."""
        return self.grid_height - self.floor_start

    @property
    def floor_tiles(self) -> int:
        return self.grid_width * self.floor_rows

    @property
    def wall_tiles(self) -> int:
        return self.grid_width * self.wall_rows

    @property
    def total_tiles(self) -> int:
        return self.grid_width * self.grid_height

    def is_floor_position(self, x: int, y: int) -> bool:
        return (0 <= x < self.grid_width) and (self.floor_start <= y < self.grid_height)

    def is_wall_position(self, x: int, y: int) -> bool:
        return (0 <= x < self.grid_width) and (0 <= y < self.wall_rows)

    def is_ceiling_position(self, x: int, y: int) -> bool:
        return self.ceiling_row is not None and y == self.ceiling_row and (0 <= x < self.grid_width)

    def valid_anchor_positions(self, anchor: str, item_width: int, item_height: int) -> List[Tuple[int, int]]:
        """
        Return a list of (x, y) top-left positions where an item of
        given anchor, width, and height can be placed in this room.
        """
        positions: List[Tuple[int, int]] = []

        if anchor == "floor":
            # Item bottom row must be at grid_height - 1;
            # item top row = (grid_height - 1) - (item_height - 1)
            y_top = self.grid_height - item_height
            if y_top < self.floor_start:
                return []
            for x in range(self.grid_width - item_width + 1):
                positions.append((x, y_top))

        elif anchor == "wall":
            # Item top row must be within wall_rows
            for y_top in range(self.wall_rows - item_height + 1):
                for x in range(self.grid_width - item_width + 1):
                    positions.append((x, y_top))

        elif anchor == "ceiling":
            if self.ceiling_row is not None:
                y_top = self.ceiling_row
                for x in range(self.grid_width - item_width + 1):
                    positions.append((x, y_top))

        return positions

    def to_dict(self) -> dict:
        return {
            "room_type":             self.room_type,
            "display_name":          self.display_name,
            "grid_width":            self.grid_width,
            "grid_height":           self.grid_height,
            "wall_rows":             self.wall_rows,
            "floor_start":           self.floor_start,
            "base_appeal":           self.base_appeal,
            "compatible_categories": list(self.compatible_categories),
            "preferred_stats":       list(self.preferred_stats),
            "description":           self.description,
            "color":                 self.color,
        }


# ── Import stat constants ─────────────────────────────────────────────────
from src.data.furniture_db import (
    STAT_APPEAL, STAT_COMFORT, STAT_HYGIENE, STAT_FUN, STAT_HEALTH,
    STAT_BREEDING, CAT_SLEEPING, CAT_SEATING, CAT_HYGIENE_CAT,
    CAT_FEEDING, CAT_STORAGE, CAT_DECORATION, CAT_ENTERTAINMENT,
    CAT_BREEDING, CAT_EXERCISE, CAT_LIGHTING, CAT_MISC,
)

# ── Room definitions ──────────────────────────────────────────────────────
# Standard Mewgenics room grid: 11 wide × 7 tall
# Rows 0-1  = back wall (wall zone)
# Row  2    = transition zone (can hold tall floor items or low wall items)
# Rows 3-6  = floor zone

ROOMS: Dict[str, RoomDefinition] = {}


def _room(r: RoomDefinition) -> RoomDefinition:
    ROOMS[r.room_type] = r
    return r


_room(RoomDefinition(
    room_type=ROOM_BEDROOM,
    display_name="Bedroom",
    grid_width=11,
    grid_height=7,
    wall_rows=2,
    floor_start=3,
    base_appeal=2,
    compatible_categories=[
        CAT_SLEEPING, CAT_SEATING, CAT_DECORATION,
        CAT_LIGHTING, CAT_STORAGE, CAT_MISC,
    ],
    preferred_stats=[STAT_COMFORT, STAT_APPEAL, STAT_HEALTH],
    description="The main sleeping area. Prioritises comfort and appeal.",
    color="#FFF3E0",
    ceiling_row=0,
))

_room(RoomDefinition(
    room_type=ROOM_BATHROOM,
    display_name="Bathroom",
    grid_width=9,
    grid_height=7,
    wall_rows=2,
    floor_start=3,
    base_appeal=1,
    compatible_categories=[
        CAT_HYGIENE_CAT, CAT_DECORATION, CAT_LIGHTING, CAT_MISC,
    ],
    preferred_stats=[STAT_HYGIENE, STAT_COMFORT, STAT_APPEAL],
    description="A dedicated hygiene room. Maximise hygiene stats.",
    color="#E3F2FD",
    ceiling_row=0,
))

_room(RoomDefinition(
    room_type=ROOM_KITCHEN,
    display_name="Kitchen",
    grid_width=10,
    grid_height=7,
    wall_rows=2,
    floor_start=3,
    base_appeal=2,
    compatible_categories=[
        CAT_FEEDING, CAT_STORAGE, CAT_DECORATION, CAT_LIGHTING, CAT_MISC,
    ],
    preferred_stats=[STAT_HEALTH, STAT_COMFORT, STAT_APPEAL],
    description="Where meals are prepared and served.",
    color="#F3E5F5",
    ceiling_row=0,
))

_room(RoomDefinition(
    room_type=ROOM_LIVING_ROOM,
    display_name="Living Room",
    grid_width=12,
    grid_height=7,
    wall_rows=2,
    floor_start=3,
    base_appeal=3,
    compatible_categories=[
        CAT_SEATING, CAT_ENTERTAINMENT, CAT_DECORATION,
        CAT_LIGHTING, CAT_STORAGE, CAT_MISC,
    ],
    preferred_stats=[STAT_APPEAL, STAT_COMFORT, STAT_FUN],
    description="The social hub. Focus on appeal and comfort.",
    color="#E8F5E9",
    ceiling_row=0,
))

_room(RoomDefinition(
    room_type=ROOM_PLAYROOM,
    display_name="Playroom",
    grid_width=11,
    grid_height=7,
    wall_rows=2,
    floor_start=3,
    base_appeal=2,
    compatible_categories=[
        CAT_ENTERTAINMENT, CAT_EXERCISE, CAT_DECORATION,
        CAT_LIGHTING, CAT_MISC,
    ],
    preferred_stats=[STAT_FUN, STAT_HEALTH, STAT_APPEAL],
    description="Dedicated play space. Maximise fun and health.",
    color="#E1F5FE",
    ceiling_row=0,
))

_room(RoomDefinition(
    room_type=ROOM_NURSERY,
    display_name="Nursery",
    grid_width=10,
    grid_height=7,
    wall_rows=2,
    floor_start=3,
    base_appeal=2,
    compatible_categories=[
        CAT_SLEEPING, CAT_FEEDING, CAT_DECORATION,
        CAT_LIGHTING, CAT_MISC,
    ],
    preferred_stats=[STAT_HEALTH, STAT_COMFORT, STAT_APPEAL],
    description="Safe space for kittens. Prioritise health and comfort.",
    color="#FCE4EC",
    ceiling_row=0,
))

_room(RoomDefinition(
    room_type=ROOM_BREEDING_ROOM,
    display_name="Breeding Room",
    grid_width=11,
    grid_height=7,
    wall_rows=2,
    floor_start=3,
    base_appeal=3,
    compatible_categories=[
        CAT_BREEDING, CAT_SLEEPING, CAT_DECORATION,
        CAT_LIGHTING, CAT_MISC,
    ],
    preferred_stats=[STAT_BREEDING, STAT_APPEAL, STAT_COMFORT],
    description="Optimised for breeding success. Pack in breeding furniture.",
    color="#F8BBD9",
    ceiling_row=0,
))

_room(RoomDefinition(
    room_type=ROOM_GARDEN,
    display_name="Garden",
    grid_width=14,
    grid_height=6,
    wall_rows=1,
    floor_start=2,
    base_appeal=4,
    compatible_categories=[
        CAT_DECORATION, CAT_EXERCISE, CAT_MISC,
    ],
    preferred_stats=[STAT_APPEAL, STAT_HEALTH, STAT_FUN],
    description="Outdoor garden area. Great for appeal and health.",
    color="#DCEDC8",
    ceiling_row=None,
))

_room(RoomDefinition(
    room_type=ROOM_STORAGE,
    display_name="Storage Room",
    grid_width=8,
    grid_height=7,
    wall_rows=2,
    floor_start=3,
    base_appeal=0,
    compatible_categories=[
        CAT_STORAGE, CAT_MISC,
    ],
    preferred_stats=[STAT_APPEAL, STAT_COMFORT],
    description="A utility storage room.",
    color="#EFEBE9",
    ceiling_row=0,
))

_room(RoomDefinition(
    room_type=ROOM_DINING,
    display_name="Dining Room",
    grid_width=11,
    grid_height=7,
    wall_rows=2,
    floor_start=3,
    base_appeal=2,
    compatible_categories=[
        CAT_FEEDING, CAT_SEATING, CAT_DECORATION,
        CAT_LIGHTING, CAT_MISC,
    ],
    preferred_stats=[STAT_COMFORT, STAT_APPEAL, STAT_HEALTH],
    description="Dedicated dining area.",
    color="#FFF8E1",
    ceiling_row=0,
))


def get_room(room_type: str) -> RoomDefinition:
    """Return a RoomDefinition by type identifier."""
    return ROOMS[room_type]


def get_all_rooms() -> List[RoomDefinition]:
    """Return all room definitions sorted by display name."""
    return sorted(ROOMS.values(), key=lambda r: r.display_name)
