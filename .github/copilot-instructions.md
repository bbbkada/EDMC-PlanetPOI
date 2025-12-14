# EDMC-PlanetPOI Copilot Instructions

## Project Overview
Plugin for Elite Dangerous Market Connector (EDMC) that enables players to save and navigate to Points of Interest (POIs) on planetary surfaces using an in-game overlay system. The plugin integrates with Elite Dangerous game events via EDMC's journal processing.

## Architecture

### Core Components
- **load.py** - Main plugin file implementing EDMC plugin lifecycle hooks (`plugin_start3`, `journal_entry`, `dashboard_entry`, `plugin_app`, `plugin_prefs`, `prefs_changed`). Manages POI storage, GUI, and coordinates calculation.
- **overlay.py** - Wrapper for EDMCOverlay integration with graceful fallback. Displays real-time navigation overlays in-game showing bearing/distance to active POIs.
- **poi.json** - Persistent POI storage with structure: `{"body": str, "lat": float, "lon": float, "description": str, "active": bool}`

### Data Flow
1. **Journal events** (FSDJump, StartUp) → Update `CURRENT_SYSTEM` → Refresh GUI to show system-wide POIs
2. **Dashboard events** (Latitude/Longitude) → Calculate distance/bearing to active POIs → Update in-game overlay
3. **GUI interactions** → Modify `ALL_POIS` → `save_pois()` → Update `poi.json` and overlay

### State Management
- `ALL_POIS` - Global list synchronized with poi.json
- `CURRENT_SYSTEM` - Tracks player's current star system
- `last_lat`, `last_lon`, `last_body` - Captures player's last known surface position for "Save current position" feature
- Config keys: `planetpoi_calc_with_altitude`, `planetpoi_max_overlay_rows`, `planetpoi_overlay_leftmargin`

## EDMC Plugin Integration Patterns

### Required Plugin Hooks
All EDMC plugins must implement specific entry points:
- `plugin_start3(plugin_dir)` - Returns plugin name, initializes config with defaults
- `journal_entry(cmdr, is_beta, system, station, entry, state)` - Processes Elite Dangerous game events
- `dashboard_entry(cmdr, is_beta, entry)` - Real-time game state updates (coordinates, altitude, etc.)
- `plugin_app(parent, cmdr, is_beta)` - Builds main EDMC UI frame
- `plugin_prefs(parent, cmdr, is_beta)` - Builds settings UI
- `prefs_changed(cmdr, is_beta)` - Persists settings when user clicks OK

### EDMC Framework Conventions
- Use `myNotebook as nb` widgets (nb.Frame, nb.Button, nb.Label, etc.) instead of raw tkinter for theme compatibility
- Apply `theme.update(frame)` after building UI components to respect user theme settings
- Store persistent config with `config.get_int()` / `config.set()` - handles missing keys gracefully
- Use `l10n.translations.tl(context=__file__)` for internationalization (see L10n/en.strings)

### EDMCOverlay Integration
```python
# Pattern used in overlay.py
from edmcoverlay import Overlay
this.overlay = Overlay()
this.overlay.connect()
this.overlay_available = True
```
- Always wrap in try/except with graceful degradation if overlay not installed
- Use `ensure_overlay()` helper to attempt reconnection if initially unavailable
- Clear overlay messages by sending empty text to prevent stale data

## UI Development Patterns

### Dynamic UI Rebuilding
The plugin uses full widget tree destruction/recreation instead of incremental updates:
```python
def redraw_plugin_app():
    for widget in PLUGIN_PARENT.winfo_children():
        widget.destroy()
    plugin_app(PLUGIN_PARENT)
```
Trigger on state changes: system jumps, landing on bodies, POI modifications.

### Settings UI with Scrollable Frame
Preferences use custom scrolling implementation in `create_scrolled_frame()` with Canvas + Scrollbar pattern. Required because POI list can exceed screen height.

### Tkinter Variable Tracing
Checkbox state changes tracked via `trace_add('write', callback)` to auto-save POI active state and enable/disable save buttons on description edits.

## Navigation Calculations

Uses Haversine formula for great-circle surface distance:
```python
calculate_bearing_and_distance(lat1, lon1, lat2, lon2, planet_radius_m, alt1=0, alt2=0, calc_with_altitude=False)
```
- Returns (distance_meters, bearing_degrees)
- Optional 3D distance calculation when `calc_with_altitude=True`
- Bearing uses atan2 for proper quadrant handling: `(math.degrees(math.atan2(y, x)) + 360) % 360`

## File Handling

### POI Persistence
- UTF-8 encoding required: `open(POI_FILE, "r", encoding="utf8")`
- Pretty-printed JSON: `json.dump(ALL_POIS, f, indent=2)`
- Always load/save entire list (no partial updates)

### Plugin Location
Plugin resides in EDMC plugins directory: `%LOCALAPPDATA%\EDMarketConnector\plugins\EDMC-PlanetPOI`

## Common Operations

### Adding New POI
1. User enters body name (case-sensitive, exact match required), lat/lon, description
2. Create dict: `{"body": str, "lat": float, "lon": float, "description": str, "active": True}`
3. Append to `ALL_POIS`
4. Call `save_pois()` → writes poi.json
5. Call `redraw_prefs(frame)` to refresh UI

### Overlay Update Cycle
Dashboard sends coordinates → Filter for `poi.get("active", True) and poi.get("body") == bodyname` → Calculate distance/bearing for each → Format strings with bearing, distance (auto-scale m/km/Mm), description → Call `overlay.show_poi_rows(poi_texts)` with max rows from settings

### Body Name Matching
- System-level view: `poi.get("body", "").startswith(CURRENT_SYSTEM)` shows all POIs in system
- Body-level view: `poi.get("body") == current_body` exact match when on planetary surface
- Elite Dangerous format: "System Name Body Designation" (e.g., "HIP 36601 C 3 b")

### Body Name Formatting Rules
Elite Dangerous body names follow strict formatting conventions implemented in `format_body_name()`:

**Formatting Logic:**
1. Remove all whitespace from user input
2. First character: Uppercase if letter (secondary star designation), otherwise keep as-is
3. All subsequent letters: Lowercase (moon designations)
4. Insert space between every character
5. Numbers remain unchanged

**Examples:**
- `"c1ab"` → `"C 1 a b"` (secondary star C, planet 1, moons a and b)
- `"2a"` → `"2 a"` (planet 2 around primary star, moon a)
- `"B3CD"` → `"B 3 c d"` (secondary star B, planet 3, moons c and d)
- `"1"` → `"1"` (planet 1 around primary star)

**Body Name Structure:**
- **No leading letter**: Planet orbiting primary star (e.g., "1", "2 a")
- **Leading uppercase letter**: Body orbiting secondary star (e.g., "C 1", "B 3 a")
- **Lowercase letters after number**: Moons (e.g., "1 a", "C 3 a b")
- **Multiple moons**: Chain indicates orbit hierarchy (e.g., "2 a b" = moon b orbiting moon a, which orbits planet 2)

Full body name stored in poi.json combines system name + formatted body designation: `"HIP 36601 C 3 a b"`

## Development Notes
- Swedish comments in code - ignore or translate if needed
- No automated tests present - manual testing in EDMC + Elite Dangerous required
- Overlay Y-position hardcoded: `ROW_Y_START = 2`, `ROW_Y_STEP = 24` - adjust for different resolutions
- Font sizes: Main GUI uses TkDefaultFont size 9, headers size 10 bold
