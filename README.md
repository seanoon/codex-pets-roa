# codex-pets-roa

Custom desktop pet & shimeji "Roa" for [Codex Pets](https://github.com/PierroX4/codex-pets), [AgentPet](https://github.com/ntd4996/agentpet), and [Shijima](https://getshijima.app) (Android / Shimeji-ee).

## Animations (Spritesheet Rows)

| Row | Action | Preview | Description |
|:---:|:---|:---:|:---|
| 0 | **Idle** | <img src="idle_sway_perfect.gif" width="120" alt="Row 0: Idle" /> | Gentle upper-body swaying idle animation |
| 1 | **Run Right** | <img src="run_cycle_perfect.gif" width="120" alt="Row 1: Run Right" /> | Full-speed running right animation |
| 2 | **Run Left** | <img src="run_left_cycle.gif" width="120" alt="Row 2: Run Left" /> | Full-speed running left animation |
| 3 | **Wave** | <img src="wave_cycle_perfect.gif" width="120" alt="Row 3: Wave" /> | Waving hand / greeting animation |
| 4 | **Jump** | <img src="jump_cycle_perfect.gif" width="120" alt="Row 4: Jump" /> | Joyful celebration jump animation |
| 5 | **Failed** | <img src="failed_cycle_perfect.gif" width="120" alt="Row 5: Failed" /> | Crying stamp error animation |
| 6 | **Waiting** | <img src="waiting_cycle_perfect.gif" width="120" alt="Row 6: Waiting" /> | Inquisitive head-tilting waiting animation |
| 7 | **Fast Run** | <img src="fast_run_cycle.gif" width="120" alt="Row 7: Fast Run" /> | High-speed sprint animation |
| 8 | **Review** | <img src="review_cycle_perfect.gif" width="120" alt="Row 8: Review" /> | Furious laptop typing / code review animation |
| 9 | **Look Up** | <img src="lookup_cycle.gif" width="120" alt="Row 9: Look Up" /> | Upward-looking gentle sway animation |
| 10 | **Rest** | <img src="rest_cycle_perfect.gif" width="120" alt="Row 10: Rest" /> | Sitting nodding nap with floating Zzz |

### Shijima / Shimeji-ee Additional Animations

| Action | Preview | Description |
|:---|:---:|:---|
| **Wall Climb** | <img src="wall_climb_cycle.gif" width="120" alt="Wall Climb" /> | Climbing along left/right screen edges |
| **Ceiling Crawl** | <img src="ceiling_crawl_cycle.gif" width="120" alt="Ceiling Crawl" /> | Hanging and crawling along the top screen edge |
| **Pinched / Dragged** | <img src="pinched_cycle.gif" width="120" alt="Pinched / Dragged" /> | Dangling and wiggling when picked up by finger/cursor |
| **Fall & Land** | <img src="fall_land_cycle.gif" width="120" alt="Fall & Land" /> | Freefall, soft landing plop, and sitting up |

## Installation

### Codex Pets / AgentPet
Download `roa.codex-pet` from the [Releases](https://github.com/seanoon/codex-pets-roa/releases) page and import it into Codex Pets or AgentPet.

### Shijima (Android / Shijima-Qt)
Import `roa_shijima.zip` directly into the **Shijima** app on Android (or Shijima-Qt on desktop).

## Build from Source

Requirements:
- Python 3.9+
- Pillow (`pip install Pillow`)

Build the Codex Pets package:

```bash
python build.py
```

Build the Shijima (`roa_shijima.zip`) package:

```bash
python build_shijima.py
```

This will generate:
- `roa.codex-pet` (Codex Pets package bundle)
- `roa_shijima.zip` (Shijima / Shimeji-ee package bundle with `actions.xml`, `behaviors.xml`, and `shime1.png`–`shime107.png`)
- `roa_pet/spritesheet.webp` & `roa_pet/spritesheet_preview.png`
- Preview GIFs for all animations
