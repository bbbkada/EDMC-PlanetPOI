# EDMC Planet POI Plugin

Plugin for [EDMC](https://github.com/EDCD/EDMarketConnector) that helps you save and navigate to Points of Interest (POIs) on planetary surfaces in Elite Dangerous.  
Perfect for saving interesting locations while exploring, organizing your discoveries, and sharing coordinates with other commanders.

## Features

### 📍 Save & Navigate POIs
- Save planetary coordinates with descriptions and notes
- Automatically captures your current position when on a surface
- Real-time in-game overlay showing bearing and distance to active POIs
- System name validation through Spansh API
- Proper Elite Dangerous body name formatting (e.g., "C 3 a b")

### 📁 Folder Organization
- Organize POIs into folders for better management
- Create nested folder structures
- Move POIs and folders between locations
- Collapsible folder view in the main UI

### 🔗 Share POIs
- Generate shareable links for any POI
- Auto-detect and paste shared links with Ctrl+V
- Copy system names to clipboard for easy navigation setup
- Share individual POIs or entire collections via JSON export/import

### ⚙️ Customizable Settings
- Adjust maximum number of overlay rows displayed
- Configure overlay horizontal position
- Toggle altitude-based distance calculation
- Enable/disable individual POI overlays with checkboxes

### 📥 Import/Export
- Export all POIs to JSON file
- Import POIs from JSON file (merge or replace)
- Backup and share your entire POI collection

## Screenshots

### Configuration Settings
Adjust overlay position, maximum visible POIs, and altitude calculation options:

![Settings](images/EDMC_Settings.png)

### Add/Edit POI Dialog
Add new POIs with system name autocomplete. Auto-fills current position when on a planetary surface. Paste shared links with Ctrl+V:

![Add POI](images/Add_poi.png)

### System View
When entering a system, see all POIs organized by body:

![System View](images/EDMC_system.png)

### Body View
On a planetary surface, see all POIs for that body. Use checkboxes to toggle overlay visibility:

![Body View](images/EDMC_gui.png)

### POI Menu
Access POI management options via the menu button (☰). Edit, move, delete, share POIs or create folders:

![POI Menu](images/dropmenu.png)

### In-Game Overlay
Real-time overlay showing bearing, distance, and description for active POIs (requires EDMCOverlay):

![Overlay](images/overlay.png)

## Installation

1. Download the [latest release](https://github.com/bbbkada/EDMC-PlanetPOI/releases) zip file
2. Extract to your EDMC plugins folder:
   - Windows: `%LOCALAPPDATA%\EDMarketConnector\plugins\`
3. Restart EDMC
4. **(Optional but recommended)** Install [EDMCOverlay](https://github.com/inorton/EDMCOverlay) for in-game overlay functionality

## Usage

### Adding POIs
- Click the **+** button in the EDMC interface
- System name will auto-fill when in a system
- Coordinates auto-fill when on a planetary surface
- Use Ctrl+V or the paste button to load shared POI links
- Add description and notes for your reference

### Managing POIs
- **Checkboxes**: Enable/disable individual POI overlays
- **Menu (☰)**: Access edit, move, delete, share, and folder operations
- **Folders**: Organize POIs into folders, create nested structures
- **System name**: Click to copy to clipboard for navigation

### Sharing POIs
- Right-click or use the menu to generate a share link
- Share the link with other commanders
- Recipients can paste the link when adding a new POI

### Settings
- Click the **⚙** (gear icon) to open configuration
- Set maximum overlay rows to avoid clutter
- Adjust overlay horizontal position to fit your HUD layout
- Enable altitude-based distance for 3D distance calculation

## Requirements

- [Elite Dangerous Market Connector (EDMC)](https://github.com/EDCD/EDMarketConnector)
- [EDMCOverlay](https://github.com/inorton/EDMCOverlay) (optional, for in-game overlay)
- Elite Dangerous (Horizons/Odyssey for planetary landings)
