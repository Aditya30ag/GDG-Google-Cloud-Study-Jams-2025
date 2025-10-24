# Arcade Game Classification Fix

## Issue Identified

"Level 3: Generative AI" was incorrectly being classified as a **Skill Badge** instead of an **Arcade Game**.

### Example from data.json (User: Ivin Baiju)
**Before:**
- `# of Skill Badges Completed`: 5
- `Names of Completed Skill Badges`: "Level 3: Generative AI [Skill Badge] | Get Started with API Gateway [Skill Badge] | ..."
- `# of Arcade Games Completed`: 1
- `Names of Completed Arcade Games`: "Level 3: Generative AI [Game]"

**After:**
- `# of Skill Badges Completed`: 4
- `Names of Completed Skill Badges`: "Get Started with API Gateway [Skill Badge] | Get Started with Pub/Sub [Skill Badge] | ..."
- `# of Arcade Games Completed`: 1
- `Names of Completed Arcade Games`: "Level 3: Generative AI [Game]"

## Root Cause

The scraping script (`conversion/scrape_profiles.py`) was treating all items from Google Cloud Skills Boost profiles as skill badges, without distinguishing arcade games.

## Changes Made

### 1. Updated `scrape_profiles.py`

#### Added arcade game detection logic:
- New helper function `is_arcade_game()` that identifies arcade games by patterns:
  - "level 1:", "level 2:", "level 3:"
  - "generative ai", "gen ai"

#### Modified `extract_badges_from_html()`:
- Now returns a dictionary with both `badges` and `arcade_games`
- Separates items into skill badges (tagged with `[Skill Badge]`) and arcade games (tagged with `[Game]`)
- Maintains separate tracking with `seen_badges` and `seen_arcade` sets

#### Updated data processing:
- `fetch_profile()` now returns both badges and arcade games
- Main processing loop updates both skill badge and arcade game fields
- Retry logic also handles both types correctly

### 2. Fixed `data.json`

Manually corrected the entry for "Ivin Baiju":
- Removed "Level 3: Generative AI [Skill Badge]" from skill badges
- Kept "Level 3: Generative AI [Game]" in arcade games
- Updated counts: skill badges 5→4, total courses 6→5

## How It Works Now

When the scraper encounters a badge/game on a profile:

1. **Extract the title** from the HTML
2. **Check if it's an arcade game** using pattern matching:
   - If YES → Add to `arcade_games` list with `[Game]` suffix
   - If NO → Add to `badges` list with `[Skill Badge]` suffix
3. **Update the data.json** with separate counts and names for each category

## Future Scraping

The next time you run the scraper, it will correctly classify:
- **Skill Badges**: Traditional skill badges
- **Arcade Games**: Level 1/2/3 Generative AI games and similar arcade-style challenges

## Testing

To test the updated scraper:
```bash
python conversion/scrape_profiles.py --input main/data.json --output main/data.json --dry-run
```

This will show what changes would be made without actually writing to the file.
