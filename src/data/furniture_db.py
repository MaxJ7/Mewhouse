"""
Mewgenics Furniture Database
-----------------------------
Comprehensive database of all Mewgenics furniture items with:
  - Exact grid dimensions (width x height in tiles)
  - Anchor point (where the item snaps to — 'floor', 'wall', or 'ceiling')
  - Stats provided (appeal, comfort, hygiene, fun, health, breeding)
  - Category for filtering / room-compatibility checks
  - Whether the item is wall-mounted or free-standing
  - Visual colour used in the room layout canvas

Dimensions follow the in-game convention:
  width  = number of horizontal tiles occupied
  height = number of vertical tiles occupied (including wall height for
           tall items like bookshelves/cabinets)

Anchor point semantics
  'floor'   – item sits on the floor; placement is validated from the
               bottom row of the item upwards.
  'wall'    – item is hung on a wall; placement is validated from the
               top row of the room downwards.
  'ceiling' – item hangs from the ceiling (rare).

Stats are integer values representing the raw bonus the item contributes
to the room total.  The optimizer uses these values when computing how
well a proposed layout meets the user's targets.
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple, List

# ── Stat names ──────────────────────────────────────────────────────────────
STAT_APPEAL    = "appeal"
STAT_COMFORT   = "comfort"
STAT_HYGIENE   = "hygiene"
STAT_FUN       = "fun"
STAT_HEALTH    = "health"
STAT_BREEDING  = "breeding"

ALL_STATS: Tuple[str, ...] = (
    STAT_APPEAL, STAT_COMFORT, STAT_HYGIENE, STAT_FUN, STAT_HEALTH, STAT_BREEDING
)

# ── Categories ───────────────────────────────────────────────────────────────
CAT_SEATING     = "Seating"
CAT_SLEEPING    = "Sleeping"
CAT_HYGIENE_CAT = "Hygiene"
CAT_FEEDING     = "Feeding"
CAT_STORAGE     = "Storage"
CAT_DECORATION  = "Decoration"
CAT_ENTERTAINMENT = "Entertainment"
CAT_BREEDING    = "Breeding"
CAT_EXERCISE    = "Exercise"
CAT_LIGHTING    = "Lighting"
CAT_MISC        = "Miscellaneous"

ALL_CATEGORIES: Tuple[str, ...] = (
    CAT_SEATING, CAT_SLEEPING, CAT_HYGIENE_CAT, CAT_FEEDING,
    CAT_STORAGE, CAT_DECORATION, CAT_ENTERTAINMENT, CAT_BREEDING,
    CAT_EXERCISE, CAT_LIGHTING, CAT_MISC,
)


@dataclass
class FurnitureItem:
    """Represents a single piece of Mewgenics furniture."""

    # Unique identifier used in save files and internal logic
    item_id: str

    # Human-readable name shown in the UI
    name: str

    # Grid dimensions
    width: int          # tiles wide
    height: int         # tiles tall (floor-to-ceiling for tall items)

    # Where the item anchors in the room
    anchor: str         # 'floor' | 'wall' | 'ceiling'

    # Stat bonuses provided
    stats: Dict[str, int]

    # Functional category
    category: str

    # Display colour in the canvas grid (tkinter colour string)
    color: str = "#A0C4FF"

    # Whether this item can only be unlocked (not purchasable by default)
    unlockable: bool = False

    # Rarity / cost tier (1 = cheap, 5 = expensive)
    tier: int = 1

    # Description shown in tooltips
    description: str = ""

    @property
    def area(self) -> int:
        """Total grid tiles occupied."""
        return self.width * self.height

    @property
    def stat_total(self) -> int:
        """Sum of all positive stat values."""
        return sum(v for v in self.stats.values() if v > 0)

    @property
    def stat_density(self) -> float:
        """Stat total per tile — higher is more efficient."""
        return self.stat_total / self.area if self.area > 0 else 0.0

    def get_stat(self, stat_name: str) -> int:
        return self.stats.get(stat_name, 0)

    def to_dict(self) -> dict:
        return {
            "item_id":     self.item_id,
            "name":        self.name,
            "width":       self.width,
            "height":      self.height,
            "anchor":      self.anchor,
            "stats":       dict(self.stats),
            "category":    self.category,
            "color":       self.color,
            "unlockable":  self.unlockable,
            "tier":        self.tier,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FurnitureItem":
        return cls(**d)


# ── Master furniture catalogue ────────────────────────────────────────────
# All furniture items present in Mewgenics.
# Sources: in-game observation + community wiki (mewgenics.wiki.gg/wiki/Furniture)
FURNITURE_DB: Dict[str, FurnitureItem] = {}

def _reg(item: FurnitureItem) -> FurnitureItem:
    """Register an item in the global database and return it."""
    FURNITURE_DB[item.item_id] = item
    return item


# ── Hygiene furniture ─────────────────────────────────────────────────────

_reg(FurnitureItem(
    item_id="litter_box",
    name="Litter Box",
    width=2, height=1,
    anchor="floor",
    stats={STAT_HYGIENE: 3},
    category=CAT_HYGIENE_CAT,
    color="#C8E6C9",
    tier=1,
    description="Basic litter box. Essential for hygiene.",
))

_reg(FurnitureItem(
    item_id="deluxe_litter_box",
    name="Deluxe Litter Box",
    width=2, height=1,
    anchor="floor",
    stats={STAT_HYGIENE: 5, STAT_APPEAL: 1},
    category=CAT_HYGIENE_CAT,
    color="#A5D6A7",
    tier=2,
    description="An upgraded litter box with a hood.",
))

_reg(FurnitureItem(
    item_id="automatic_litter_box",
    name="Automatic Litter Box",
    width=2, height=2,
    anchor="floor",
    stats={STAT_HYGIENE: 8, STAT_APPEAL: 2},
    category=CAT_HYGIENE_CAT,
    color="#66BB6A",
    tier=3,
    description="Self-cleaning litter box. Maximum hygiene.",
    unlockable=True,
))

_reg(FurnitureItem(
    item_id="sink",
    name="Sink",
    width=1, height=2,
    anchor="floor",
    stats={STAT_HYGIENE: 4},
    category=CAT_HYGIENE_CAT,
    color="#B3E5FC",
    tier=2,
    description="Keeps paws clean.",
))

_reg(FurnitureItem(
    item_id="bathtub",
    name="Bathtub",
    width=3, height=2,
    anchor="floor",
    stats={STAT_HYGIENE: 7, STAT_COMFORT: 3},
    category=CAT_HYGIENE_CAT,
    color="#81D4FA",
    tier=3,
    description="A luxurious bathing spot.",
))

_reg(FurnitureItem(
    item_id="shower",
    name="Shower",
    width=2, height=3,
    anchor="floor",
    stats={STAT_HYGIENE: 6, STAT_COMFORT: 1},
    category=CAT_HYGIENE_CAT,
    color="#4FC3F7",
    tier=2,
    description="Quick and efficient bathing.",
))

_reg(FurnitureItem(
    item_id="toilet",
    name="Toilet",
    width=1, height=2,
    anchor="floor",
    stats={STAT_HYGIENE: 3, STAT_COMFORT: 1},
    category=CAT_HYGIENE_CAT,
    color="#E1F5FE",
    tier=1,
    description="Basic toilet.",
))

_reg(FurnitureItem(
    item_id="mirror",
    name="Mirror",
    width=1, height=2,
    anchor="wall",
    stats={STAT_HYGIENE: 2, STAT_APPEAL: 2},
    category=CAT_HYGIENE_CAT,
    color="#B0BEC5",
    tier=1,
    description="Wall-mounted mirror for grooming.",
))

_reg(FurnitureItem(
    item_id="large_mirror",
    name="Large Mirror",
    width=2, height=3,
    anchor="wall",
    stats={STAT_HYGIENE: 3, STAT_APPEAL: 4},
    category=CAT_HYGIENE_CAT,
    color="#90A4AE",
    tier=2,
    description="Full-length wall mirror.",
))

# ── Sleeping / Comfort furniture ─────────────────────────────────────────

_reg(FurnitureItem(
    item_id="cat_bed",
    name="Cat Bed",
    width=2, height=1,
    anchor="floor",
    stats={STAT_COMFORT: 4, STAT_HEALTH: 1},
    category=CAT_SLEEPING,
    color="#FFCCBC",
    tier=1,
    description="Soft bed for napping.",
))

_reg(FurnitureItem(
    item_id="deluxe_cat_bed",
    name="Deluxe Cat Bed",
    width=2, height=2,
    anchor="floor",
    stats={STAT_COMFORT: 7, STAT_APPEAL: 2, STAT_HEALTH: 2},
    category=CAT_SLEEPING,
    color="#FF8A65",
    tier=2,
    description="Premium memory-foam cat bed.",
))

_reg(FurnitureItem(
    item_id="cat_hammock",
    name="Cat Hammock",
    width=2, height=2,
    anchor="wall",
    stats={STAT_COMFORT: 5, STAT_FUN: 2},
    category=CAT_SLEEPING,
    color="#FFAB91",
    tier=2,
    description="Wall-mounted hammock for cats that like to hang.",
))

_reg(FurnitureItem(
    item_id="double_bed",
    name="Double Cat Bed",
    width=3, height=2,
    anchor="floor",
    stats={STAT_COMFORT: 10, STAT_APPEAL: 3, STAT_HEALTH: 2},
    category=CAT_SLEEPING,
    color="#EF9A9A",
    tier=3,
    description="Spacious double bed for pairs.",
    unlockable=True,
))

_reg(FurnitureItem(
    item_id="breeding_bed",
    name="Breeding Bed",
    width=3, height=2,
    anchor="floor",
    stats={STAT_COMFORT: 6, STAT_BREEDING: 8, STAT_APPEAL: 2},
    category=CAT_BREEDING,
    color="#F48FB1",
    tier=3,
    description="Special bed that boosts breeding success.",
    unlockable=True,
))

_reg(FurnitureItem(
    item_id="couch",
    name="Couch",
    width=3, height=2,
    anchor="floor",
    stats={STAT_COMFORT: 6, STAT_APPEAL: 4},
    category=CAT_SEATING,
    color="#CE93D8",
    tier=2,
    description="Comfy couch for lounging.",
))

_reg(FurnitureItem(
    item_id="loveseat",
    name="Loveseat",
    width=2, height=2,
    anchor="floor",
    stats={STAT_COMFORT: 4, STAT_APPEAL: 3, STAT_BREEDING: 2},
    category=CAT_SEATING,
    color="#BA68C8",
    tier=2,
    description="Small sofa for two.",
))

_reg(FurnitureItem(
    item_id="armchair",
    name="Armchair",
    width=2, height=2,
    anchor="floor",
    stats={STAT_COMFORT: 5, STAT_APPEAL: 3},
    category=CAT_SEATING,
    color="#AB47BC",
    tier=2,
    description="Single plush armchair.",
))

_reg(FurnitureItem(
    item_id="rocking_chair",
    name="Rocking Chair",
    width=2, height=2,
    anchor="floor",
    stats={STAT_COMFORT: 4, STAT_FUN: 2, STAT_APPEAL: 2},
    category=CAT_SEATING,
    color="#9C27B0",
    tier=2,
    description="Cats love rocking in this chair.",
))

_reg(FurnitureItem(
    item_id="cushion",
    name="Floor Cushion",
    width=1, height=1,
    anchor="floor",
    stats={STAT_COMFORT: 2, STAT_APPEAL: 1},
    category=CAT_SEATING,
    color="#E1BEE7",
    tier=1,
    description="Small floor cushion.",
))

# ── Feeding furniture ─────────────────────────────────────────────────────

_reg(FurnitureItem(
    item_id="food_bowl",
    name="Food Bowl",
    width=1, height=1,
    anchor="floor",
    stats={STAT_COMFORT: 3, STAT_HEALTH: 2},
    category=CAT_FEEDING,
    color="#FFF9C4",
    tier=1,
    description="Basic food bowl.",
))

_reg(FurnitureItem(
    item_id="water_bowl",
    name="Water Bowl",
    width=1, height=1,
    anchor="floor",
    stats={STAT_HYGIENE: 2, STAT_HEALTH: 2},
    category=CAT_FEEDING,
    color="#E3F2FD",
    tier=1,
    description="Fresh water bowl.",
))

_reg(FurnitureItem(
    item_id="double_bowl",
    name="Double Bowl",
    width=2, height=1,
    anchor="floor",
    stats={STAT_COMFORT: 3, STAT_HYGIENE: 2, STAT_HEALTH: 3},
    category=CAT_FEEDING,
    color="#FFF176",
    tier=1,
    description="Combined food and water bowl.",
))

_reg(FurnitureItem(
    item_id="automatic_feeder",
    name="Automatic Feeder",
    width=2, height=2,
    anchor="floor",
    stats={STAT_COMFORT: 5, STAT_HEALTH: 4, STAT_APPEAL: 1},
    category=CAT_FEEDING,
    color="#FFEE58",
    tier=3,
    description="Timed automatic feeder.",
    unlockable=True,
))

_reg(FurnitureItem(
    item_id="water_fountain",
    name="Water Fountain",
    width=1, height=2,
    anchor="floor",
    stats={STAT_HYGIENE: 4, STAT_HEALTH: 4, STAT_APPEAL: 2},
    category=CAT_FEEDING,
    color="#64B5F6",
    tier=3,
    description="Circulating water fountain.",
    unlockable=True,
))

_reg(FurnitureItem(
    item_id="fridge",
    name="Mini Fridge",
    width=1, height=2,
    anchor="floor",
    stats={STAT_COMFORT: 2, STAT_HEALTH: 3, STAT_APPEAL: 1},
    category=CAT_FEEDING,
    color="#B0BEC5",
    tier=2,
    description="Keeps treats fresh.",
))

# ── Entertainment / Fun furniture ─────────────────────────────────────────

_reg(FurnitureItem(
    item_id="scratching_post",
    name="Scratching Post",
    width=1, height=2,
    anchor="floor",
    stats={STAT_FUN: 4, STAT_HEALTH: 1},
    category=CAT_ENTERTAINMENT,
    color="#BCAAA4",
    tier=1,
    description="Classic scratching post.",
))

_reg(FurnitureItem(
    item_id="deluxe_scratching_post",
    name="Deluxe Scratching Post",
    width=1, height=3,
    anchor="floor",
    stats={STAT_FUN: 6, STAT_HEALTH: 2, STAT_APPEAL: 1},
    category=CAT_ENTERTAINMENT,
    color="#A1887F",
    tier=2,
    description="Taller, sturdier scratching post.",
))

_reg(FurnitureItem(
    item_id="cat_tree",
    name="Cat Tree",
    width=2, height=3,
    anchor="floor",
    stats={STAT_FUN: 7, STAT_COMFORT: 3, STAT_APPEAL: 3},
    category=CAT_ENTERTAINMENT,
    color="#8D6E63",
    tier=3,
    description="Multi-level cat tree with perches.",
))

_reg(FurnitureItem(
    item_id="mega_cat_tree",
    name="Mega Cat Tree",
    width=3, height=4,
    anchor="floor",
    stats={STAT_FUN: 10, STAT_COMFORT: 5, STAT_APPEAL: 5},
    category=CAT_ENTERTAINMENT,
    color="#795548",
    tier=4,
    description="Giant cat tree with multiple levels and toys.",
    unlockable=True,
))

_reg(FurnitureItem(
    item_id="toy_box",
    name="Toy Box",
    width=2, height=1,
    anchor="floor",
    stats={STAT_FUN: 5, STAT_APPEAL: 1},
    category=CAT_ENTERTAINMENT,
    color="#FFE082",
    tier=2,
    description="Box full of various cat toys.",
))

_reg(FurnitureItem(
    item_id="tv",
    name="Television",
    width=2, height=2,
    anchor="wall",
    stats={STAT_FUN: 6, STAT_APPEAL: 3},
    category=CAT_ENTERTAINMENT,
    color="#424242",
    tier=3,
    description="Cats find TV mesmerising.",
    unlockable=True,
))

_reg(FurnitureItem(
    item_id="fish_tank",
    name="Fish Tank",
    width=2, height=2,
    anchor="floor",
    stats={STAT_FUN: 5, STAT_APPEAL: 6, STAT_COMFORT: 2},
    category=CAT_ENTERTAINMENT,
    color="#00BCD4",
    tier=3,
    description="Mesmerising fish tank.",
    unlockable=True,
))

_reg(FurnitureItem(
    item_id="bird_cage",
    name="Bird Cage",
    width=2, height=3,
    anchor="floor",
    stats={STAT_FUN: 7, STAT_APPEAL: 4},
    category=CAT_ENTERTAINMENT,
    color="#FFF59D",
    tier=3,
    description="Bird cage — cats are fascinated.",
    unlockable=True,
))

_reg(FurnitureItem(
    item_id="exercise_wheel",
    name="Exercise Wheel",
    width=2, height=2,
    anchor="floor",
    stats={STAT_FUN: 5, STAT_HEALTH: 6},
    category=CAT_EXERCISE,
    color="#A5D6A7",
    tier=3,
    description="Cat exercise wheel for active cats.",
    unlockable=True,
))

_reg(FurnitureItem(
    item_id="tunnel",
    name="Cat Tunnel",
    width=3, height=1,
    anchor="floor",
    stats={STAT_FUN: 6, STAT_HEALTH: 2},
    category=CAT_EXERCISE,
    color="#80CBC4",
    tier=2,
    description="Collapsible tunnel for play.",
))

_reg(FurnitureItem(
    item_id="laser_pointer",
    name="Laser Pointer Mount",
    width=1, height=1,
    anchor="wall",
    stats={STAT_FUN: 8, STAT_HEALTH: 3},
    category=CAT_ENTERTAINMENT,
    color="#EF5350",
    tier=3,
    description="Automatic wall-mounted laser pointer.",
    unlockable=True,
))

# ── Decoration / Appeal furniture ─────────────────────────────────────────

_reg(FurnitureItem(
    item_id="plant_small",
    name="Small Plant",
    width=1, height=2,
    anchor="floor",
    stats={STAT_APPEAL: 3},
    category=CAT_DECORATION,
    color="#81C784",
    tier=1,
    description="A small decorative plant.",
))

_reg(FurnitureItem(
    item_id="plant_large",
    name="Large Plant",
    width=2, height=3,
    anchor="floor",
    stats={STAT_APPEAL: 6, STAT_HEALTH: 1},
    category=CAT_DECORATION,
    color="#4CAF50",
    tier=2,
    description="A large leafy plant.",
))

_reg(FurnitureItem(
    item_id="flower_pot",
    name="Flower Pot",
    width=1, height=1,
    anchor="floor",
    stats={STAT_APPEAL: 2},
    category=CAT_DECORATION,
    color="#F48FB1",
    tier=1,
    description="A cute flower pot.",
))

_reg(FurnitureItem(
    item_id="painting_small",
    name="Small Painting",
    width=1, height=1,
    anchor="wall",
    stats={STAT_APPEAL: 3},
    category=CAT_DECORATION,
    color="#FFAB40",
    tier=1,
    description="A small wall painting.",
))

_reg(FurnitureItem(
    item_id="painting_large",
    name="Large Painting",
    width=2, height=2,
    anchor="wall",
    stats={STAT_APPEAL: 7},
    category=CAT_DECORATION,
    color="#FF6F00",
    tier=2,
    description="A large decorative painting.",
))

_reg(FurnitureItem(
    item_id="window",
    name="Window",
    width=2, height=2,
    anchor="wall",
    stats={STAT_APPEAL: 5, STAT_COMFORT: 2},
    category=CAT_DECORATION,
    color="#B3E5FC",
    tier=2,
    description="Natural light window. Cats love sitting here.",
))

_reg(FurnitureItem(
    item_id="bay_window",
    name="Bay Window",
    width=3, height=2,
    anchor="wall",
    stats={STAT_APPEAL: 8, STAT_COMFORT: 4, STAT_FUN: 2},
    category=CAT_DECORATION,
    color="#81D4FA",
    tier=3,
    description="Spacious bay window with sitting ledge.",
    unlockable=True,
))

_reg(FurnitureItem(
    item_id="rug_small",
    name="Small Rug",
    width=2, height=2,
    anchor="floor",
    stats={STAT_APPEAL: 2, STAT_COMFORT: 2},
    category=CAT_DECORATION,
    color="#FFCCBC",
    tier=1,
    description="A cosy small rug.",
))

_reg(FurnitureItem(
    item_id="rug_large",
    name="Large Rug",
    width=4, height=3,
    anchor="floor",
    stats={STAT_APPEAL: 5, STAT_COMFORT: 4},
    category=CAT_DECORATION,
    color="#FFAB91",
    tier=2,
    description="A luxurious large rug.",
))

_reg(FurnitureItem(
    item_id="lamp_floor",
    name="Floor Lamp",
    width=1, height=3,
    anchor="floor",
    stats={STAT_APPEAL: 3, STAT_COMFORT: 1},
    category=CAT_LIGHTING,
    color="#FFF9C4",
    tier=1,
    description="A tall floor lamp.",
))

_reg(FurnitureItem(
    item_id="lamp_table",
    name="Table Lamp",
    width=1, height=1,
    anchor="floor",
    stats={STAT_APPEAL: 2},
    category=CAT_LIGHTING,
    color="#FFF59D",
    tier=1,
    description="Small decorative table lamp.",
))

_reg(FurnitureItem(
    item_id="chandelier",
    name="Chandelier",
    width=2, height=2,
    anchor="ceiling",
    stats={STAT_APPEAL: 8, STAT_COMFORT: 2},
    category=CAT_LIGHTING,
    color="#FFD54F",
    tier=4,
    description="Elegant ceiling chandelier.",
    unlockable=True,
))

_reg(FurnitureItem(
    item_id="fairy_lights",
    name="Fairy Lights",
    width=4, height=1,
    anchor="wall",
    stats={STAT_APPEAL: 4, STAT_COMFORT: 2},
    category=CAT_LIGHTING,
    color="#FFFDE7",
    tier=1,
    description="Strings of decorative fairy lights.",
))

# ── Storage furniture ─────────────────────────────────────────────────────

_reg(FurnitureItem(
    item_id="bookshelf",
    name="Bookshelf",
    width=2, height=3,
    anchor="floor",
    stats={STAT_APPEAL: 4, STAT_FUN: 1},
    category=CAT_STORAGE,
    color="#BCAAA4",
    tier=2,
    description="A bookshelf full of interesting things.",
))

_reg(FurnitureItem(
    item_id="dresser",
    name="Dresser",
    width=2, height=2,
    anchor="floor",
    stats={STAT_APPEAL: 3, STAT_COMFORT: 1},
    category=CAT_STORAGE,
    color="#D7CCC8",
    tier=2,
    description="A dresser for storage.",
))

_reg(FurnitureItem(
    item_id="wardrobe",
    name="Wardrobe",
    width=2, height=3,
    anchor="floor",
    stats={STAT_APPEAL: 4, STAT_COMFORT: 2},
    category=CAT_STORAGE,
    color="#EFEBE9",
    tier=2,
    description="A large wardrobe — cats hide inside.",
))

_reg(FurnitureItem(
    item_id="cabinet_wall",
    name="Wall Cabinet",
    width=2, height=2,
    anchor="wall",
    stats={STAT_APPEAL: 3, STAT_HYGIENE: 1},
    category=CAT_STORAGE,
    color="#CFD8DC",
    tier=2,
    description="Wall-mounted storage cabinet.",
))

_reg(FurnitureItem(
    item_id="toy_shelf",
    name="Toy Shelf",
    width=2, height=2,
    anchor="wall",
    stats={STAT_FUN: 4, STAT_APPEAL: 2},
    category=CAT_STORAGE,
    color="#B2EBF2",
    tier=2,
    description="Wall shelf for toys and trinkets.",
))

# ── Breeding-specific furniture ───────────────────────────────────────────

_reg(FurnitureItem(
    item_id="incubator",
    name="Kitten Incubator",
    width=2, height=2,
    anchor="floor",
    stats={STAT_HEALTH: 6, STAT_BREEDING: 5, STAT_COMFORT: 3},
    category=CAT_BREEDING,
    color="#F8BBD9",
    tier=4,
    description="Keeps kittens warm and healthy.",
    unlockable=True,
))

_reg(FurnitureItem(
    item_id="breeding_shrine",
    name="Breeding Shrine",
    width=3, height=3,
    anchor="floor",
    stats={STAT_BREEDING: 12, STAT_APPEAL: 4, STAT_COMFORT: 2},
    category=CAT_BREEDING,
    color="#EC407A",
    tier=5,
    description="A mystical shrine that greatly boosts breeding success.",
    unlockable=True,
))

_reg(FurnitureItem(
    item_id="love_potion_stand",
    name="Love Potion Stand",
    width=1, height=2,
    anchor="floor",
    stats={STAT_BREEDING: 6, STAT_APPEAL: 3},
    category=CAT_BREEDING,
    color="#F06292",
    tier=3,
    description="Dispenses love potions to improve breeding.",
    unlockable=True,
))

_reg(FurnitureItem(
    item_id="romance_candles",
    name="Romance Candles",
    width=2, height=1,
    anchor="floor",
    stats={STAT_BREEDING: 4, STAT_APPEAL: 5, STAT_COMFORT: 2},
    category=CAT_BREEDING,
    color="#F48FB1",
    tier=2,
    description="Sets a romantic mood for breeding.",
))

_reg(FurnitureItem(
    item_id="vanity",
    name="Vanity Table",
    width=2, height=3,
    anchor="floor",
    stats={STAT_APPEAL: 6, STAT_HYGIENE: 3, STAT_BREEDING: 2},
    category=CAT_BREEDING,
    color="#FCE4EC",
    tier=3,
    description="Vanity table for grooming — increases appeal for breeding.",
    unlockable=True,
))

# ── Miscellaneous ─────────────────────────────────────────────────────────

_reg(FurnitureItem(
    item_id="clock",
    name="Wall Clock",
    width=1, height=1,
    anchor="wall",
    stats={STAT_APPEAL: 2},
    category=CAT_MISC,
    color="#CFD8DC",
    tier=1,
    description="A decorative wall clock.",
))

_reg(FurnitureItem(
    item_id="fireplace",
    name="Fireplace",
    width=3, height=3,
    anchor="wall",
    stats={STAT_COMFORT: 8, STAT_APPEAL: 7, STAT_HEALTH: 2},
    category=CAT_MISC,
    color="#EF9A9A",
    tier=4,
    description="Warm fireplace — cats gather around it.",
    unlockable=True,
))

_reg(FurnitureItem(
    item_id="radiator",
    name="Radiator",
    width=2, height=2,
    anchor="wall",
    stats={STAT_COMFORT: 5, STAT_HEALTH: 2},
    category=CAT_MISC,
    color="#E0E0E0",
    tier=2,
    description="Keeps the room warm.",
))

_reg(FurnitureItem(
    item_id="cat_door",
    name="Cat Door",
    width=1, height=1,
    anchor="wall",
    stats={STAT_FUN: 2, STAT_COMFORT: 1},
    category=CAT_MISC,
    color="#A5D6A7",
    tier=1,
    description="Small door for cats to come and go.",
))

_reg(FurnitureItem(
    item_id="wall_shelf",
    name="Wall Shelf",
    width=2, height=1,
    anchor="wall",
    stats={STAT_APPEAL: 2, STAT_FUN: 1},
    category=CAT_MISC,
    color="#D7CCC8",
    tier=1,
    description="A simple wall-mounted shelf.",
))


# ── Helper functions ──────────────────────────────────────────────────────

def get_furniture(item_id: str) -> FurnitureItem:
    """Return a FurnitureItem by its ID. Raises KeyError if not found."""
    return FURNITURE_DB[item_id]


def get_all_furniture() -> List[FurnitureItem]:
    """Return all furniture items sorted by name."""
    return sorted(FURNITURE_DB.values(), key=lambda f: f.name)


def get_by_category(category: str) -> List[FurnitureItem]:
    """Return all furniture items in a given category."""
    return [f for f in FURNITURE_DB.values() if f.category == category]


def get_by_anchor(anchor: str) -> List[FurnitureItem]:
    """Return all furniture items with the given anchor type."""
    return [f for f in FURNITURE_DB.values() if f.anchor == anchor]


def get_top_stat_items(stat: str, n: int = 10) -> List[FurnitureItem]:
    """Return the top-n items sorted by a specific stat value."""
    return sorted(
        FURNITURE_DB.values(),
        key=lambda f: f.get_stat(stat),
        reverse=True,
    )[:n]
