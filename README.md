# Mewhouse — Mewgenics Room Layout Optimizer

A Python desktop application that reads your **Mewgenics** save data and
generates optimised furniture layouts for each room, maximising the stats
that matter most for breeding, comfort, hygiene, appeal, and more.

---

## Features

| Feature | Details |
|---------|---------|
| 📂 **Save File Import** | Auto-detects or manually loads your Mewgenics save. Supports binary and JSON formats. Falls back to a realistic demo state if no save is found. |
| 🪑 **Furniture Inventory** | Browse all 50+ furniture items with dimensions, anchor types, stat bonuses, and efficiency scores. Filter by category, search by name, sort by any stat. |
| 🏠 **Room Manager** | View and unlock/lock all 10 room types. Shows grid size, zone layout (wall/floor/ceiling), base appeal, compatible categories, and preferred stats. |
| 🗺 **Visual Layout Canvas** | Accurate tile-grid room visualiser. Drag furniture to reposition. Right-click to remove. Colour-coded wall/floor/transition zones. Real-time stat sidebar. |
| ⚙ **Automatic Optimizer** | Set per-room stat targets, then click **Run**. The optimizer assigns furniture from your shared inventory to rooms and generates optimal placements using a greedy + local-search algorithm. |
| 💾 **Export / Import** | Export your plan as JSON for future reference. Import plans to continue where you left off. |

---

## Quick Start

### Requirements
- Python 3.8 or newer
- `tkinter` (usually included; on Debian/Ubuntu: `sudo apt-get install python3-tk`)

### Run
```bash
python main.py
```

### Workflow
1. **Load your save** — *File → Load Save File…* or use *Auto-detect*.  
   If you don't have the game, the built-in Demo State works fine.
2. **Unlock rooms** — Switch to the **Rooms** tab and tick which rooms you have.
3. **Set targets** — Switch to the **Optimizer** tab and enter stat goals per room.  
   Click *⬆ Fill Preferred* on any row to auto-fill sensible defaults.
4. **Run the optimizer** — Click **▶ Run Optimizer**. Results appear in the panel below.
5. **Apply layouts** — Click **✓ Apply Results** to push generated layouts to all rooms.
6. **Review** — Switch to the **Layout** tab to inspect, tweak, or manually adjust each room.
7. **Export** — *File → Export Plan* to save your plan as JSON.

---

## Project Structure

```
Mewhouse/
├── main.py                     # Entry point
├── requirements.txt
├── src/
│   ├── data/
│   │   ├── furniture_db.py     # 50+ furniture items: dimensions, stats, anchor types
│   │   ├── room_data.py        # 10 room types: grid sizes, zones, compatibility
│   │   └── save_parser.py      # Mewgenics save file parser + demo state
│   ├── optimizer/
│   │   ├── stat_calculator.py  # Stat totals, scoring, efficiency ranking
│   │   ├── layout_optimizer.py # Greedy + local-search room layout optimizer
│   │   └── room_placer.py      # Multi-room furniture assignment
│   └── gui/
│       ├── app.py              # Main application window + menus
│       ├── furniture_panel.py  # Inventory browser with filtering/sorting
│       ├── room_panel.py       # Room manager (unlock/lock, details, preview)
│       ├── layout_panel.py     # Canvas grid editor with drag-and-drop
│       └── optimizer_panel.py  # Stat targets UI + optimizer runner
└── tests/
    ├── test_furniture.py       # Furniture database tests (17 tests)
    ├── test_optimizer.py       # Optimizer + stat calculator tests (28 tests)
    └── test_save_parser.py     # Save file parser tests (20 tests)
```

---

## Furniture System

Furniture is modelled with all properties needed to ensure layouts are
**achievable in-game**:

| Property | Description |
|----------|-------------|
| `width × height` | Exact tile footprint |
| `anchor` | `floor` / `wall` / `ceiling` — where the item snaps |
| `stats` | Appeal, Comfort, Hygiene, Fun, Health, Breeding bonuses |
| `category` | Used for room compatibility checking |
| `tier` | Cost/rarity level (1–5) |

The optimizer only places items in valid zones (wall items on the back wall,
floor items on the floor zone) and never overlaps tiles, guaranteeing that
every generated layout can be replicated in Mewgenics.

---

## Optimizer Algorithm

1. **Rank furniture** by weighted efficiency against the room's stat targets  
   (stat contribution per tile, weighted by how much each target needs that stat).
2. **Greedy placement**: place top-ranked items one by one in the first valid
   position that doesn't overlap existing items.
3. **Local-search improvement**: attempt to swap the least-efficient placed
   item for a better candidate from unplaced inventory.
4. **Multi-room assignment** (`room_placer.py`): items exclusive to one room
   go directly to that room; contested items are distributed by marginal gain.

---

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

65 tests — all should pass.
