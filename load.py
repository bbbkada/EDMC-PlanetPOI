import functools
import l10n
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
import myNotebook as nb
from config import config
from theme import theme
import json
import os
import base64
import urllib.parse
import overlay  # overlay.py i samma katalog
from AutoCompleter import AutoCompleter
from heading_guidance import HeadingGuidance
import release
from release import ClientVersion, Release

# Import from new modules
from calculations import (
    calculate_bearing_and_distance,
    format_body_name,
    format_distance_with_unit,
    scale_geometry,
    safe_int
)
import poi_manager
import guidance_manager
import context_menus
import dialogs
import gui_builder

plugin_tl = functools.partial(l10n.translations.tl, context=__file__)

PLUGIN_PARENT = None
PLUGIN_FRAME = None  # Persistent frame for dynamic updates
OVERLAY_INFO_LABEL = None  # Reference to overlay info label for updates

# Release management
RELEASE_FRAME = None  # Reference to release notification frame

# Guidance section widgets for dynamic updates
GUIDANCE_FRAME = None
GUIDANCE_LEFT_LABEL = None
GUIDANCE_CENTER_LABEL = None
GUIDANCE_RIGHT_LABEL = None
FIRST_POI_LABEL = None  # Reference to first POI label for dynamic updates
GUIDANCE_DEFAULT_FG = None  # Store default foreground color for guidance center label

# Initialize POI file path
POI_FILE = os.path.join(os.path.dirname(__file__), "poi.json")
poi_manager.set_poi_file(POI_FILE)

# POI storage
ALL_POIS = []
POI_VARS = []  # List of tk.BooleanVar for checkboxes
POI_REFS = []  # List of actual POI references (same order as POI_VARS)

ALT_KEY = "planetpoi_calc_with_altitude"
ROWS_KEY = "planetpoi_max_overlay_rows"
LEFT_KEY = "planetpoi_overlay_leftmargin"
SHOW_GUI_INFO_KEY = "planetpoi_show_gui_info"
HEADING_GUIDANCE_KEY = "planetpoi_heading_guidance"  # Enable/disable heading guidance
GUIDANCE_THRESHOLD_KEY = "planetpoi_guidance_threshold"  # Degrees tolerance for "on course"
GUIDANCE_DISTANCE_KEY = "planetpoi_guidance_distance"  # Distance in meters where guidance stops

ALT_VAR = None
ROWS_VAR = None
LEFT_VAR = None
SHOW_GUI_INFO_VAR = None
HEADING_GUIDANCE_VAR = None
GUIDANCE_THRESHOLD_VAR = None
GUIDANCE_DISTANCE_VAR = None

# Store overlay info for display in GUI
OVERLAY_INFO_TEXT = ""

CURRENT_SYSTEM = None

# Latest position for "Save current location"
last_lat, last_lon, last_body = None, None, None
last_altitude, last_planet_radius = 0, 1000000
last_heading = None  # Current heading from dashboard

# Heading guidance instance for graphical arrows
heading_guidance = None
within_2km_zone = False  # Track if we're within 2km to show checkmark only once
gui_guidance_visible = False  # Track if GUI guidance widgets are currently shown

# Settings table sorting
SORT_COLUMN = "body"  # Default sort column: "body", "lat", "lon", "description"
SORT_REVERSE = False  # False = ascending, True = descending

# Functions now imported from modules: format_body_name, get_full_body_name, load_pois, save_pois, split_system_and_body
# calculations: calculate_bearing_and_distance, format_distance_with_unit, scale_geometry, safe_int
# poi_manager: load_pois, save_pois, get_full_body_name, split_system_and_body, get_all_pois_flat, create_folder, delete_item, move_item

# Wrapper functions for backward compatibility
def load_pois():
    """Wrapper for poi_manager.load_pois()"""
    global ALL_POIS
    ALL_POIS = poi_manager.load_pois()

def save_pois():
    """Wrapper for poi_manager.save_pois()"""
    poi_manager.save_pois(ALL_POIS)

def get_full_body_name(poi):
    """Wrapper for poi_manager.get_full_body_name()"""
    return poi_manager.get_full_body_name(poi)

def split_system_and_body(full_body_name):
    """Wrapper for poi_manager.split_system_and_body()"""
    return poi_manager.split_system_and_body(full_body_name)

def get_all_pois_flat(items):
    """Wrapper for poi_manager.get_all_pois_flat()"""
    return poi_manager.get_all_pois_flat(items)

def export_pois_to_file(parent_frame):
    """Export POIs to a user-selected JSON file."""
    from tkinter import filedialog
    try:
        file_path = filedialog.asksaveasfilename(
            parent=parent_frame,
            title="Export POIs",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="poi_export.json"
        )
        if file_path:
            with open(file_path, "w", encoding="utf8") as f:
                json.dump(ALL_POIS, f, indent=2)
            print(f"PPOI: POIs exported to {file_path}")
    except Exception as ex:
        print(f"PPOI: Error exporting POIs: {ex}")

def import_pois_from_file(parent_frame):
    """Import POIs from a user-selected JSON file."""
    from tkinter import filedialog, messagebox
    global ALL_POIS
    try:
        file_path = filedialog.askopenfilename(
            parent=parent_frame,
            title="Import POIs",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            with open(file_path, "r", encoding="utf8") as f:
                imported_pois = json.load(f)
            
            # Ask user if they want to replace or merge
            if ALL_POIS:  # Only ask if there are existing POIs
                result = messagebox.askyesnocancel(
                    "Import POIs",
                    "Replace existing POIs?\n\nYes = Replace all existing POIs\nNo = Add to existing POIs\nCancel = Cancel import",
                    parent=parent_frame
                )
                if result is None:  # Cancel
                    return
                elif result:  # Yes - Replace
                    ALL_POIS = imported_pois if isinstance(imported_pois, list) else []
                else:  # No - Merge
                    ALL_POIS.extend(imported_pois if isinstance(imported_pois, list) else [])
            else:
                # No existing POIs, just load the imported ones
                ALL_POIS = imported_pois if isinstance(imported_pois, list) else []
            
            save_pois()
            
            # Rebuild UI to show imported POIs
            for widget in parent_frame.winfo_children():
                widget.destroy()
            build_plugin_ui(parent_frame)
            
            print(f"PPOI: POIs imported from {file_path}")
    except Exception as ex:
        print(f"PPOI: Error importing POIs: {ex}")

def plugin_start3(plugin_dir: str) -> str:
    global ALT_VAR, ROWS_VAR, LEFT_VAR, SHOW_GUI_INFO_VAR, HEADING_GUIDANCE_VAR, GUIDANCE_THRESHOLD_VAR, GUIDANCE_DISTANCE_VAR, ALL_POIS, CURRENT_SYSTEM, last_lat, last_lon, last_body, heading_guidance, RELEASE_FRAME
    
    # Initialize release management
    Release.plugin_start(plugin_dir)
    
    # set default values if no config exists
    alt_val = config.get_int(ALT_KEY)
    ALT_VAR = tk.BooleanVar(value=bool(alt_val))

    rows_val = config.get_int(ROWS_KEY)
    if rows_val == 0:  # Default value not set
        rows_val = 10
        config.set(ROWS_KEY, rows_val)
    ROWS_VAR = tk.IntVar(value=rows_val)

    left_val = config.get_int(LEFT_KEY)
    if left_val == 0:  # Default value not set
        left_val = 500
        config.set(LEFT_KEY, left_val)
    LEFT_VAR = tk.IntVar(value=left_val)
    
    # Check if SHOW_GUI_INFO_KEY has been set before
    # Use -1 as sentinel value to detect first run
    show_gui_info_val = config.get_int(SHOW_GUI_INFO_KEY, default=-1)
    if show_gui_info_val == -1:  # First run - set default to enabled
        show_gui_info_val = 1
        config.set(SHOW_GUI_INFO_KEY, show_gui_info_val)
    SHOW_GUI_INFO_VAR = tk.BooleanVar(value=bool(show_gui_info_val))
    
    # Heading guidance setting - default enabled
    heading_guidance_val = config.get_int(HEADING_GUIDANCE_KEY, default=-1)
    if heading_guidance_val == -1:  # First run - set default to enabled
        heading_guidance_val = 1
        config.set(HEADING_GUIDANCE_KEY, heading_guidance_val)
    HEADING_GUIDANCE_VAR = tk.BooleanVar(value=bool(heading_guidance_val))
    
    # Guidance threshold (degrees tolerance for "on course") - default 4 degrees
    guidance_threshold_val = config.get_int(GUIDANCE_THRESHOLD_KEY, default=0)
    if guidance_threshold_val == 0:  # First run - set default
        guidance_threshold_val = 4
        config.set(GUIDANCE_THRESHOLD_KEY, guidance_threshold_val)
    GUIDANCE_THRESHOLD_VAR = tk.IntVar(value=guidance_threshold_val)
    
    # Guidance distance (meters where guidance stops) - default 2000m (2km)
    guidance_distance_val = config.get_int(GUIDANCE_DISTANCE_KEY, default=0)
    if guidance_distance_val == 0:  # First run - set default
        guidance_distance_val = 2000
        config.set(GUIDANCE_DISTANCE_KEY, guidance_distance_val)
    GUIDANCE_DISTANCE_VAR = tk.IntVar(value=guidance_distance_val)
   
    load_pois()  # This now calls the wrapper which updates ALL_POIS
    overlay.set_overlay_settings(ROWS_VAR.get(), LEFT_VAR.get())
    
    # Initialize heading guidance with settings from config
    guidance_threshold = GUIDANCE_THRESHOLD_VAR.get()
    heading_guidance = HeadingGuidance(center_x=600, center_y=150, on_course_threshold=guidance_threshold)
    
    # Initialize modules with dependency injection
    _init_modules()
    
    # ============== SIMULATION - HARDCODED VALUES ==============
    # Comment out these lines to disable simulation
    #CURRENT_SYSTEM = "HIP 36601"
    #last_body = "HIP 36601 C 1 a"
    #last_lat = -67.5  # Same as POI "Crystalline shards Tellerium"
    #last_lon = 127.2
    print(f"PPOI SIMULATION: System={CURRENT_SYSTEM}, Body={last_body}, Lat={last_lat}, Lon={last_lon}")
    
    # Simulate dashboard entry to trigger overlay info calculation
    simulated_entry = {
        "Latitude": last_lat,
        "Longitude": last_lon,
        "BodyName": last_body,
        "Altitude": 0,
        "PlanetRadius": 2000000  # Default planet radius
    }
    dashboard_entry(None, False, simulated_entry)
    # ============================================================
    
    return "PlanetPOI"

def _init_modules():
    """Initialize modules with dependency injection"""
    # Getter function for accessing load.py globals
    def get_globals():
        return {
            'ALL_POIS': globals()['ALL_POIS'],
            'CURRENT_SYSTEM': globals()['CURRENT_SYSTEM'],
            'last_body': globals()['last_body'],
            'last_lat': globals()['last_lat'],
            'last_lon': globals()['last_lon'],
            'last_altitude': globals()['last_altitude'],
            'last_planet_radius': globals()['last_planet_radius'],
            'last_heading': globals()['last_heading'],
            'PLUGIN_FRAME': globals()['PLUGIN_FRAME'],
            'GUIDANCE_FRAME': globals()['GUIDANCE_FRAME'],
            'GUIDANCE_LEFT_LABEL': globals()['GUIDANCE_LEFT_LABEL'],
            'GUIDANCE_CENTER_LABEL': globals()['GUIDANCE_CENTER_LABEL'],
            'GUIDANCE_RIGHT_LABEL': globals()['GUIDANCE_RIGHT_LABEL'],
            'FIRST_POI_LABEL': globals()['FIRST_POI_LABEL'],
            'POI_VARS': globals()['POI_VARS'],
            'POI_REFS': globals()['POI_REFS'],
            'SORT_COLUMN': globals()['SORT_COLUMN'],
            'SORT_REVERSE': globals()['SORT_REVERSE'],
            'ALT_VAR': globals()['ALT_VAR'],
            'ROWS_VAR': globals()['ROWS_VAR'],
            'LEFT_VAR': globals()['LEFT_VAR'],
            'SHOW_GUI_INFO_VAR': globals()['SHOW_GUI_INFO_VAR'],
            'HEADING_GUIDANCE_VAR': globals()['HEADING_GUIDANCE_VAR'],
            'GUIDANCE_THRESHOLD_VAR': globals()['GUIDANCE_THRESHOLD_VAR'],
            'GUIDANCE_DISTANCE_VAR': globals()['GUIDANCE_DISTANCE_VAR'],
            'config': config,
            'theme': theme,
            'tk': tk,
            'nb': nb,
            'ttk': ttk,
            'plugin_tl': plugin_tl,
            'overlay': overlay,
            'AutoCompleter': AutoCompleter,
            'ALT_KEY': ALT_KEY,
            'ROWS_KEY': ROWS_KEY,
            'LEFT_KEY': LEFT_KEY,
            'SHOW_GUI_INFO_KEY': SHOW_GUI_INFO_KEY,
            'HEADING_GUIDANCE_KEY': HEADING_GUIDANCE_KEY,
            'GUIDANCE_THRESHOLD_KEY': GUIDANCE_THRESHOLD_KEY,
            'GUIDANCE_DISTANCE_KEY': GUIDANCE_DISTANCE_KEY
        }
    
    # Getter function for accessing load.py callbacks
    def get_callbacks():
        return {
            'save_pois': save_pois,
            'redraw_plugin_app': redraw_plugin_app,
            'redraw_prefs': redraw_prefs,
            'show_poi_context_menu': show_poi_context_menu,
            'show_poi_context_menu_main': show_poi_context_menu_main,
            'show_menu_dropdown': show_menu_dropdown,
            'show_add_poi_dialog': show_add_poi_dialog,
            'show_add_folder_dialog': show_add_folder_dialog,
            'show_move_dialog': show_move_dialog,
            'show_share_popup': show_share_popup,
            'confirm_delete_item': confirm_delete_item,
            'delete_item': delete_item,
            'move_item': move_item,
            'count_folder_contents': count_folder_contents,
            'generate_share_url': generate_share_url,
            'remove_poi_obj': remove_poi_obj,
            'save_desc_obj': save_desc_obj,
            'export_pois_to_file': export_pois_to_file,
            'import_pois_from_file': import_pois_from_file,
            'scale_geometry': scale_geometry,
            'format_body_name': format_body_name
        }
    
    # Initialize modules with getters
    dialogs.init_dialogs(get_globals, get_callbacks)
    gui_builder.init_gui_builder(get_globals, get_callbacks)

def get_ui_scale():
    """Get UI scale factor from EDMC config (default 100%)"""
    try:
        scale = config.get_int("ui_scale")
        if scale == 0:
            scale = 100
        return scale / 100.0
    except:
        return 1.0

def show_config_dialog(parent_frame):
    """Show config dialog with settings from plugin_prefs"""
    dialog = tk.Toplevel(parent_frame)
    dialog.title("PlanetPOI Configuration")
    dialog.geometry(scale_geometry(1200, 550))
    dialog.configure(bg="#ffffff")
    dialog.transient(parent_frame)
    dialog.grab_set()
    
    # Center the dialog
    dialog.update_idletasks()
    x = parent_frame.winfo_rootx() + (parent_frame.winfo_width() // 2) - (dialog.winfo_width() // 2)
    y = parent_frame.winfo_rooty() + (parent_frame.winfo_height() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")
    
    # Add close button at bottom first (pack order matters!)
    button_frame = tk.Frame(dialog, bg="#ffffff")
    button_frame.pack(side=tk.BOTTOM, pady=(5, 15), padx=15)
    
    def close_and_refresh():
        # Save settings to config before closing (same as prefs_changed does)
        config.set(ALT_KEY, int(ALT_VAR.get()))
        config.set(ROWS_KEY, ROWS_VAR.get())
        config.set(LEFT_KEY, LEFT_VAR.get())
        config.set(SHOW_GUI_INFO_KEY, int(SHOW_GUI_INFO_VAR.get()))
        overlay.set_overlay_settings(ROWS_VAR.get(), LEFT_VAR.get())
        
        # Regenerate overlay info text if we have position data
        global OVERLAY_INFO_TEXT
        if SHOW_GUI_INFO_VAR.get() and last_body and last_lat is not None and last_lon is not None:
            visible_pois = [p for p in get_all_pois_flat(ALL_POIS) 
                           if p.get("active", True) and get_full_body_name(p) == last_body]
            
            poi_texts = []
            for p in visible_pois:
                poi_lat = p.get("lat")
                poi_lon = p.get("lon")
                if poi_lat is None or poi_lon is None:
                    continue
                
                poi_desc = p.get("description", "")
                if not poi_desc:
                    poi_desc = f"{poi_lat:.4f}, {poi_lon:.4f}"
                
                distance, bearing = calculate_bearing_and_distance(
                    last_lat, last_lon, poi_lat, poi_lon,
                    last_planet_radius,
                    last_altitude, 0,
                    calc_with_altitude=config.get_int(ALT_KEY)
                )
                
                unit = "m"
                show_dist = distance
                if distance > 1_000:
                    show_dist /= 1_000
                    unit = "km"
                if show_dist > 1_000:
                    show_dist /= 1_000
                    unit = "Mm"
                
                if unit == "m":
                    poi_texts.append(f"{round(bearing)}°/ {round(show_dist)}{unit} {poi_desc}")
                else:
                    poi_texts.append(f"{round(bearing)}°/ {show_dist:.1f}{unit} {poi_desc}")
            
            # Limit to max rows setting
            max_rows = ROWS_VAR.get()
            if max_rows > 0 and len(poi_texts) > max_rows:
                poi_texts = poi_texts[:max_rows]
            OVERLAY_INFO_TEXT = "\n".join(poi_texts) if poi_texts else ""
        elif not SHOW_GUI_INFO_VAR.get():
            OVERLAY_INFO_TEXT = ""
        
        dialog.destroy()
        redraw_plugin_app()
    
    tk.Button(button_frame, text="Close", command=close_and_refresh, width=10).pack()
    
    # Create container for scrollable frame (takes remaining space)
    container_frame = tk.Frame(dialog, bg="#ffffff")
    container_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(15, 5))
    
    # Use plugin_prefs to create properly themed frame, then reparent it
    prefs_frame = plugin_prefs(container_frame, None, False)
    prefs_frame.pack(fill=tk.BOTH, expand=True)

# Delegate dialogs to dialogs.py module
def show_add_poi_dialog(parent_frame, prefill_system=None, edit_poi=None, parent_children=None):
    """Wrapper for dialogs.show_add_poi_dialog"""
    return dialogs.show_add_poi_dialog(parent_frame, prefill_system, edit_poi, parent_children)

def redraw_plugin_app():
    global PLUGIN_FRAME, PLUGIN_PARENT
    if PLUGIN_FRAME:
        try:
            # Only destroy children of the persistent frame, not the frame itself
            for widget in PLUGIN_FRAME.winfo_children():
                widget.destroy()
            # Rebuild content inside the same frame
            build_plugin_content(PLUGIN_FRAME)
            # Apply theme to updated widgets
            PLUGIN_FRAME.update_idletasks()
            theme.update(PLUGIN_FRAME)
            if PLUGIN_PARENT:
                theme.update(PLUGIN_PARENT)
        except Exception as ex:
            print("PlanetPOI: redraw_plugin_app failed:", ex)

def journal_entry(cmdr, is_beta, system, station, entry, state):
    global CURRENT_SYSTEM, last_body
    
    # Clear overlay when jumping to a new system or entering supercruise
    if entry['event'] in ['FSDJump', 'SupercruiseEntry']:
        last_body = None
        overlay.clear_all_poi_rows()
    
    if (entry['event'] in ['FSDJump','StartUp'] and entry.get('StarSystem')):
        print(f"PPOI: Arriving at {entry['StarSystem']}")
        CURRENT_SYSTEM = entry['StarSystem']
        redraw_plugin_app()      
    if not CURRENT_SYSTEM and entry.get('StarSystem'):
        CURRENT_SYSTEM = entry['StarSystem']
        redraw_plugin_app()

def find_item_path(items, target_item):
    """Find path to item in tree structure. Returns (path_list, parent_list, index)."""
    def search(children, path=[], parents=[]):
        for idx, item in enumerate(children):
            if item is target_item:
                return (path + [item.get("name", "POI")], parents, idx)
            if item.get("type") == "folder":
                result = search(item.get("children", []), path + [item.get("name")], parents + [item])
                if result:
                    return result
        return None
    return search(items)

def get_all_pois_flat(items):
    """Get flat list of all POIs (not folders) from tree structure."""
    pois = []
    def traverse(children):
        for item in children:
            if item.get("type") == "poi":
                pois.append(item)
            elif item.get("type") == "folder":
                traverse(item.get("children", []))
    traverse(items)
    return pois

def create_folder(parent_children, folder_name):
    """Create new folder."""
    new_folder = {
        "type": "folder",
        "name": folder_name,
        "children": []
    }
    parent_children.append(new_folder)
    save_pois()
    return new_folder

def delete_item(items, target_item):
    """Delete item (POI or folder) from tree."""
    def remove_from(children):
        for idx, item in enumerate(children):
            if item is target_item:
                children.pop(idx)
                return True
            if item.get("type") == "folder":
                if remove_from(item.get("children", [])):
                    return True
        return False
    if remove_from(items):
        save_pois()
        return True
    return False

def move_item(items, target_item, new_parent_children):
    """Move item to new parent folder."""
    # First remove from current location
    if delete_item(items, target_item):
        # Then add to new location
        new_parent_children.append(target_item)
        save_pois()
        return True
    return False

def copy_poi_systemname(poi):
    """Copy POI system name to clipboard."""
    try:
        system_name = poi.get("system", "")
        # Get root window for clipboard
        root = tk._default_root
        if root:
            root.clipboard_clear()
            root.clipboard_append(system_name)
            print(f"Copied system name to clipboard: {system_name}")
    except Exception as ex:
        print(f"Error copying system name: {ex}")

def edit_poi_in_menu(frame, poi):
    """Open edit dialog for POI from menu - uses same dialog as add POI."""
    try:
        show_add_poi_dialog(frame, prefill_system=poi.get("system"), edit_poi=poi)
    except Exception as ex:
        print(f"Error editing POI: {ex}")

def share_poi_link(poi):
    """Copy POI share link to clipboard."""
    try:
        share_url = generate_share_url(poi)
        # Get root window for clipboard
        root = tk._default_root
        if root:
            root.clipboard_clear()
            root.clipboard_append(share_url)
            print(f"Copied share link to clipboard: {share_url}")
    except Exception as ex:
        print(f"Error sharing POI: {ex}")

def show_item_actions_popup(item, item_type, frame, body_name):
    """Show popup menu with actions for a folder or POI."""
    popup = tk.Menu(frame, tearoff=0)
    
    if item_type == "folder":
        popup.add_command(
            label=plugin_tl("Add new POI"),
            command=lambda: show_add_poi_dialog(frame, body_name, parent_children=item.get("children", []))
        )
        popup.add_command(
            label=plugin_tl("Add folder"),
            command=lambda: show_add_folder_dialog(frame, item.get("children", []))
        )
        popup.add_command(
            label=plugin_tl("Move folder"),
            command=lambda: show_move_dialog(frame, item, "folder")
        )
        popup.add_command(
            label=plugin_tl("Delete folder"),
            command=lambda: confirm_delete_item(frame, item, "folder")
        )
    else:  # POI
        popup.add_command(
            label=plugin_tl("Copy systemname"),
            command=lambda: copy_poi_systemname(item)
        )
        popup.add_command(
            label=plugin_tl("Share link"),
            command=lambda: show_share_popup(frame, item)
        )
        popup.add_command(
            label=plugin_tl("Edit"),
            command=lambda: edit_poi_in_menu(frame, item)
        )
        popup.add_command(
            label=plugin_tl("Move POI"),
            command=lambda: show_move_dialog(frame, item, "poi")
        )
        popup.add_command(
            label=plugin_tl("Delete POI"),
            command=lambda: confirm_delete_item(frame, item, "poi")
        )
    
    try:
        theme.update(popup)
    except Exception:
        pass
    
    # Show popup at mouse position
    try:
        x = frame.winfo_pointerx()
        y = frame.winfo_pointery()
        popup.tk_popup(x, y)
    finally:
        popup.grab_release()

def show_menu_dropdown(frame, button, body_name):
    """Show dropdown menu when hamburger icon is clicked."""
    # Create menu widget that follows EDMC theme
    menu = tk.Menu(button, tearoff=0)
    
    # Add top menu items
    menu.add_command(label=plugin_tl("Add new POI"), command=lambda: show_add_poi_dialog(frame, body_name))
    menu.add_command(label=plugin_tl("Add root folder"), command=lambda: show_add_folder_dialog(frame, ALL_POIS))
    menu.add_command(label=plugin_tl("Settings"), command=lambda: show_config_dialog(frame))
    menu.add_separator()
    
    # Build hierarchical menu structure
    def add_items_to_menu(parent_menu, items, indent=0):
        """Recursively add folders and POIs to menu."""
        # Sort items alphabetically by folder name or POI description
        sorted_items = sorted(items, key=lambda x: x.get("name", "").lower() if x.get("type") == "folder" else x.get("description", "").lower())
        for item in sorted_items:
            item_type = item.get("type", "poi")
            
            if item_type == "folder":
                folder_name = item.get("name", "Unnamed Folder")
                folder_submenu = tk.Menu(parent_menu, tearoff=0)
                
                # Create actions submenu for folder
                actions_submenu = tk.Menu(folder_submenu, tearoff=0)
                actions_submenu.add_command(
                    label=plugin_tl("Add new POI"),
                    command=lambda i=item: show_add_poi_dialog(frame, body_name, parent_children=i.get("children", []))
                )
                actions_submenu.add_command(
                    label=plugin_tl("Add folder"),
                    command=lambda i=item: show_add_folder_dialog(frame, i.get("children", []))
                )
                actions_submenu.add_command(
                    label=plugin_tl("Move folder"),
                    command=lambda i=item: show_move_dialog(frame, i, "folder")
                )
                actions_submenu.add_command(
                    label=plugin_tl("Delete folder"),
                    command=lambda i=item: confirm_delete_item(frame, i, "folder")
                )
                
                # Add actions submenu at top
                folder_submenu.add_cascade(label=f"⚡ {plugin_tl('Actions')}", menu=actions_submenu)
                folder_submenu.add_separator()
                
                # Add children recursively
                children = item.get("children", [])
                if children:
                    add_items_to_menu(folder_submenu, children, indent + 1)
                else:
                    folder_submenu.add_command(label=plugin_tl("(Empty)"), state='disabled')
                
                # Add folder to parent menu
                prefix = "  " * indent + "📁 "
                parent_menu.add_cascade(label=f"{prefix}{folder_name}", menu=folder_submenu)
                
                try:
                    theme.update(folder_submenu)
                    theme.update(actions_submenu)
                except Exception:
                    pass
                    
            elif item_type == "poi":
                desc = item.get("description", "").strip()
                if not desc:
                    continue  # Skip POIs without description
                
                # Check if POI is active
                is_active = item.get("active", True)
                
                # Use different icons for system POIs (no lat/lon) vs planet POIs (with lat/lon)
                lat = item.get("lat")
                lon = item.get("lon")
                has_coords = lat not in ["", None] and lon not in ["", None]
                poi_icon = "🌍" if has_coords else "⭐"  # Planet POI vs System POI
                
                prefix = "  " * indent + poi_icon + " "
                menu_label = desc if len(desc) <= 30 else desc[:27] + "..."
                
                # Create submenu for POI with actions directly
                poi_submenu = tk.Menu(parent_menu, tearoff=0)
                
                # Add Activate/Deactivate option
                toggle_label = plugin_tl("Deactivate") if is_active else plugin_tl("Activate")
                poi_submenu.add_command(
                    label=toggle_label,
                    command=lambda p=item: toggle_poi_active(p, frame)
                )
                poi_submenu.add_separator()
                
                poi_submenu.add_command(
                    label=plugin_tl("Copy systemname"),
                    command=lambda p=item: copy_poi_systemname(p)
                )
                poi_submenu.add_command(
                    label=plugin_tl("Share link"),
                    command=lambda p=item: show_share_popup(frame, p)
                )
                poi_submenu.add_command(
                    label=plugin_tl("Edit"),
                    command=lambda p=item: edit_poi_in_menu(frame, p)
                )
                poi_submenu.add_command(
                    label=plugin_tl("Move POI"),
                    command=lambda p=item: show_move_dialog(frame, p, "poi")
                )
                poi_submenu.add_command(
                    label=plugin_tl("Delete POI"),
                    command=lambda p=item: confirm_delete_item(frame, p, "poi")
                )
                
                # Add POI with submenu - use gray color if inactive
                cascade_kwargs = {
                    "label": f"{prefix}{menu_label}",
                    "menu": poi_submenu
                }
                if not is_active:
                    cascade_kwargs["foreground"] = "gray"
                
                parent_menu.add_cascade(**cascade_kwargs)
                
                try:
                    theme.update(poi_submenu)
                except Exception:
                    pass
    
    # Add all items from root level
    add_items_to_menu(menu, ALL_POIS)
    
    # Apply theme to menu
    try:
        theme.update(menu)
    except Exception:
        pass
    
    # Show menu at button position
    try:
        x = button.winfo_rootx()
        y = button.winfo_rooty() + button.winfo_height()
        menu.post(x, y)
    except Exception as ex:
        print(f"Error showing menu: {ex}")
        menu.post(x, y)
    except Exception as ex:
        print(f"Error showing menu: {ex}")

def show_poi_context_menu_main(event, poi, frame):
    """Show context menu for POI in main plugin window."""
    menu = tk.Menu(event.widget, tearoff=0)
    
    # Toggle active
    current_state = poi.get("active", True)
    toggle_text = plugin_tl("Deactivate POI") if current_state else plugin_tl("Activate POI")
    menu.add_command(
        label=toggle_text,
        command=lambda: toggle_poi_active(poi, frame)
    )
    menu.add_separator()
    
    # Copy options
    lat = poi.get("lat")
    lon = poi.get("lon")
    if lat is not None and lon is not None:
        menu.add_command(
            label=plugin_tl("Copy coordinates"),
            command=lambda: copy_to_clipboard(event.widget, f"{lat}, {lon}")
        )
    
    menu.add_command(
        label=plugin_tl("Copy system name"),
        command=lambda: copy_to_clipboard(event.widget, poi.get("system", ""))
    )
    menu.add_command(
        label=plugin_tl("Copy body name"),
        command=lambda: copy_to_clipboard(event.widget, get_full_body_name(poi))
    )
    menu.add_separator()
    
    # Actions
    menu.add_command(
        label=plugin_tl("Edit"),
        command=lambda: edit_poi_in_menu(frame, poi)
    )
    menu.add_command(
        label=plugin_tl("Share link"),
        command=lambda: show_share_popup(frame, poi)
    )
    menu.add_command(
        label=plugin_tl("Move POI"),
        command=lambda: show_move_dialog(frame, poi, "poi")
    )
    menu.add_separator()
    
    menu.add_command(
        label=plugin_tl("Delete POI"),
        command=lambda: confirm_delete_item(frame, poi, "poi")
    )
    
    try:
        theme.update(menu)
    except Exception:
        pass
    
    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()

def toggle_poi_active(poi, frame):
    """Toggle POI active status and update overlay info text."""
    poi["active"] = not poi.get("active", True)
    save_pois()
    
    # Update OVERLAY_INFO_TEXT for GUI display (without sending to actual overlay)
    global OVERLAY_INFO_TEXT
    if last_body and last_lat is not None and last_lon is not None:
        visible_pois = [p for p in get_all_pois_flat(ALL_POIS) 
                       if p.get("active", True) and get_full_body_name(p) == last_body]
        
        poi_texts = []
        for p in visible_pois:
            poi_lat = p.get("lat")
            poi_lon = p.get("lon")
            if poi_lat is None or poi_lon is None:
                continue
            
            poi_desc = p.get("description", "")
            if not poi_desc:
                poi_desc = f"{poi_lat:.4f}, {poi_lon:.4f}"
            
            distance, bearing = calculate_bearing_and_distance(
                last_lat, last_lon, poi_lat, poi_lon,
                last_planet_radius,
                last_altitude, 0,
                calc_with_altitude=config.get_int(ALT_KEY)
            )
            
            unit = "m"
            show_dist = distance
            if distance > 1_000:
                show_dist /= 1_000
                unit = "km"
            if show_dist > 1_000:
                show_dist /= 1_000
                unit = "Mm"
            
            if unit == "m":
                poi_texts.append(f"{round(bearing)}°/ {round(show_dist)}{unit} {poi_desc}")
            else:
                poi_texts.append(f"{round(bearing)}°/ {show_dist:.1f}{unit} {poi_desc}")
        
        # Limit to max rows setting
        max_rows = config.get_int(ROWS_KEY)
        if max_rows > 0 and len(poi_texts) > max_rows:
            poi_texts = poi_texts[:max_rows]
        OVERLAY_INFO_TEXT = "\n".join(poi_texts) if poi_texts else ""
    
    # Update GUI immediately
    redraw_plugin_app()

def open_poi_folder():
    """Open the folder containing poi.json."""
    import subprocess
    folder = os.path.dirname(POI_FILE)
    try:
        os.startfile(folder)
    except Exception as ex:
        print(f"Error opening folder: {ex}")

def export_pois():
    """Export POIs to a text file."""
    export_file = os.path.join(os.path.dirname(__file__), "poi_export.txt")
    try:
        with open(export_file, "w", encoding="utf8") as f:
            f.write("Elite Dangerous POI Export\n")
            f.write("=" * 50 + "\n\n")
            for poi in get_all_pois_flat(ALL_POIS):
                f.write(f"Body: {poi.get('body', 'Unknown')}\n")
                f.write(f"Latitude: {poi.get('lat', 0):.6f}\n")
                f.write(f"Longitude: {poi.get('lon', 0):.6f}\n")
                f.write(f"Description: {poi.get('description', '')}\n")
                f.write(f"Active: {poi.get('active', True)}\n")
                f.write("-" * 50 + "\n")
        print(f"POIs exported to {export_file}")
        # Show success message
        try:
            import tkinter.messagebox as mb
            mb.showinfo("Export Complete", f"POIs exported to:\n{export_file}")
        except Exception:
            pass
    except Exception as ex:
        print(f"Error exporting POIs: {ex}")

def show_about_dialog():
    """Show about dialog."""
    try:
        import tkinter.messagebox as mb
        mb.showinfo(
            "About EDMC-PlanetPOI",
            "EDMC-PlanetPOI\n\n"
            "Save and navigate to Points of Interest on planetary surfaces.\n\n"
            "Version: 1.0\n"
            "https://github.com/yourusername/EDMC-PlanetPOI"
        )
    except Exception as ex:
        print(f"Error showing about dialog: {ex}")

def show_add_folder_dialog(frame, parent_children):
    """Wrapper for dialogs.show_add_folder_dialog"""
    return dialogs.show_add_folder_dialog(frame, parent_children)

def get_item_location_path(items, target_item, path=""):
    """Get the folder path where an item is located."""
    for item in items:
        if item is target_item:
            return path if path else plugin_tl("(Root level)")
        if item.get("type") == "folder":
            folder_name = item.get("name", "Unnamed")
            new_path = f"{path} > {folder_name}" if path else folder_name
            children = item.get("children", [])
            result = get_item_location_path(children, target_item, new_path)
            if result:
                return result
    return None

def show_move_dialog(frame, item, item_type, is_prefs=False):
    """Wrapper for dialogs.show_move_dialog"""
    return dialogs.show_move_dialog(frame, item, item_type, is_prefs)

def count_folder_contents(folder):
    """Count total subfolders and POIs in a folder recursively."""
    subfolder_count = 0
    poi_count = 0
    
    def count_recursive(children):
        nonlocal subfolder_count, poi_count
        for item in children:
            if item.get("type") == "folder":
                subfolder_count += 1
                count_recursive(item.get("children", []))
            elif item.get("type") == "poi":
                poi_count += 1
    
    count_recursive(folder.get("children", []))
    return subfolder_count, poi_count

def confirm_delete_item(frame, item, item_type):
    """Wrapper for dialogs.confirm_delete_item"""
    return dialogs.confirm_delete_item(frame, item, item_type)

# Delegate to gui_builder module
def build_plugin_content(frame):
    """Wrapper for gui_builder.build_plugin_content that updates global widget references"""
    global GUIDANCE_LEFT_LABEL, GUIDANCE_CENTER_LABEL, GUIDANCE_RIGHT_LABEL, FIRST_POI_LABEL, GUIDANCE_FRAME, GUIDANCE_DEFAULT_FG
    
    # Call gui_builder and get widget references
    widgets = gui_builder.build_plugin_content(frame)
    
    # Update global widget references
    if widgets:
        GUIDANCE_FRAME = widgets.get('GUIDANCE_FRAME')
        GUIDANCE_LEFT_LABEL = widgets.get('GUIDANCE_LEFT_LABEL')
        GUIDANCE_CENTER_LABEL = widgets.get('GUIDANCE_CENTER_LABEL')
        GUIDANCE_RIGHT_LABEL = widgets.get('GUIDANCE_RIGHT_LABEL')
        FIRST_POI_LABEL = widgets.get('FIRST_POI_LABEL')
        GUIDANCE_DEFAULT_FG = widgets.get('GUIDANCE_DEFAULT_FG')


def plugin_app(parent, cmdr=None, is_beta=None):
    """Create the persistent plugin frame and return it."""
    global PLUGIN_PARENT, PLUGIN_FRAME, RELEASE_FRAME
    PLUGIN_PARENT = parent
    
    # Create container frame for both release widget and plugin content
    container_frame = tk.Frame(parent)
    container_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
    
    # Add release notification widget at the top
    RELEASE_FRAME = Release(container_frame, ClientVersion.version(), 0)
    theme.update(RELEASE_FRAME)
    
    # Create persistent frame - use tk.Frame, let theme handle background
    PLUGIN_FRAME = tk.Frame(container_frame, highlightthickness=1)
    PLUGIN_FRAME.grid(row=1, column=0, columnspan=2, sticky="nsew")
    
    # Build initial content
    build_plugin_content(PLUGIN_FRAME)
    
    # Apply theme - makes tk widgets get proper theme colors
    theme.update(PLUGIN_FRAME)
    theme.update(parent)
    
    return container_frame



def plugin_prefs(parent, cmdr, is_beta):
    outer_frame = nb.Frame(parent)
    outer_frame.columnconfigure(0, weight=1)
    
    # Add release update settings at the top (row 0)
    if RELEASE_FRAME:
        RELEASE_FRAME.plugin_prefs(outer_frame, cmdr, is_beta, 0)
    
    # Add main plugin settings below (row 1)
    scroll_frame = create_scrolled_frame(outer_frame)
    scroll_frame.grid(row=1, column=0, sticky="NSEW")
    build_plugin_ui(scroll_frame)
    
    return outer_frame

# Delegate to gui_builder module
def create_scrolled_frame(parent):
    """Wrapper for gui_builder.create_scrolled_frame"""
    return gui_builder.create_scrolled_frame(parent)


def safe_int(val, fallback):
    try:
        return int(val)
    except Exception:
        return fallback

# Remove duplicate - now imported from calculations module

# Delegate to gui_builder module
def build_plugin_ui(frame):
    """Wrapper for gui_builder.build_plugin_ui"""
    return gui_builder.build_plugin_ui(frame)

# Duplicate split_system_and_body removed - now imported from poi_manager module

def parse_share_url(url):
    """
    Parse a share URL and extract POI data
    Returns dict with POI data or None if invalid
    """
    try:
        # Extract hash part after #
        if '#' not in url:
            return None
        
        base64_str = url.split('#', 1)[1].strip()
        if not base64_str:
            return None
        
        # Add padding if needed
        while len(base64_str) % 4 != 0:
            base64_str += '='
        
        # Decode base64url to JSON
        base64_bytes = base64_str.replace('-', '+').replace('_', '/').encode('utf-8')
        json_bytes = base64.urlsafe_b64decode(base64_bytes)
        json_str = json_bytes.decode('utf-8')
        poi_data = json.loads(json_str)
        
        # Validate required fields
        if poi_data.get('v') != 1:
            return None
        
        # Support both old format (body) and new format (system + body)
        if 'system' in poi_data:
            # New format
            if 'lat' not in poi_data or 'lon' not in poi_data:
                return None
        elif 'body' in poi_data:
            # Old format - migrate to new format
            full_body = poi_data.get('body', '')
            system_name, body_part = split_system_and_body(full_body)
            poi_data['system'] = system_name
            poi_data['body'] = body_part
        else:
            return None
            return None
        
        return poi_data
    except Exception as e:
        print(f"PPOI: Failed to parse share URL: {e}")
        return None

def generate_share_url(poi):
    """
    Generate a shareable URL for a POI based on the format used in share/index.html
    URL format: https://bbbkada.github.io/EDMC-PlanetPOI/share/#<base64url_encoded_json>
    """
    # Create POI object matching the format expected by index.html
    poi_data = {
        "v": 1,
        "system": poi.get("system", ""),
        "body": poi.get("body", ""),
        "lat": poi.get("lat", 0),
        "lon": poi.get("lon", 0),
        "description": poi.get("description", ""),
        "active": poi.get("active", True)
    }
    
    # Convert to JSON and encode to base64url
    json_str = json.dumps(poi_data, separators=(',', ':'))
    json_bytes = json_str.encode('utf-8')
    base64_bytes = base64.urlsafe_b64encode(json_bytes)
    base64_str = base64_bytes.decode('utf-8').rstrip('=')
    
    return f"https://bbbkada.github.io/EDMC-PlanetPOI/share/#{base64_str}"

# Delegate to dialogs module
def show_share_popup(parent, poi):
    """Wrapper for dialogs.show_share_popup"""
    return dialogs.show_share_popup(parent, poi)

def create_poi_context_menu(parent_widget, poi, frame, active_var=None):
    """Create and show context menu for POI row."""
    menu = tk.Menu(parent_widget, tearoff=0)
    
    # Toggle active status
    if active_var:
        current_state = active_var.get()
        toggle_text = plugin_tl("Deactivate POI") if current_state else plugin_tl("Activate POI")
        menu.add_command(
            label=toggle_text,
            command=lambda: active_var.set(not current_state)
        )
        menu.add_separator()
    
    # Copy options
    menu.add_command(
        label=plugin_tl("Copy coordinates"), 
        command=lambda: copy_to_clipboard(parent_widget, f"{poi.get('lat', '')}, {poi.get('lon', '')}")
    )
    menu.add_command(
        label=plugin_tl("Copy system name"), 
        command=lambda: copy_to_clipboard(parent_widget, poi.get("system", ""))
    )
    menu.add_command(
        label=plugin_tl("Copy body name"), 
        command=lambda: copy_to_clipboard(parent_widget, get_full_body_name(poi))
    )
    menu.add_separator()
    
    # Actions
    menu.add_command(
        label=plugin_tl("Share POI"), 
        command=lambda: show_share_popup(frame, poi)
    )
    menu.add_command(
        label=plugin_tl("Move POI"), 
        command=lambda: show_move_dialog(frame, poi, "poi", is_prefs=True)
    )
    menu.add_separator()
    
    menu.add_command(
        label=plugin_tl("Delete POI"), 
        command=lambda: confirm_delete_item(frame, poi, "poi")
    )
    
    return menu

def copy_to_clipboard(widget, text):
    """Copy text to clipboard."""
    widget.clipboard_clear()
    widget.clipboard_append(text)

def show_poi_context_menu(event, poi, frame, active_var=None):
    """Show context menu at mouse position."""
    menu = create_poi_context_menu(event.widget, poi, frame, active_var)
    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()

def redraw_prefs(frame):
    for widget in frame.winfo_children():
        widget.destroy()
    build_plugin_ui(frame)

def remove_poi_obj(poi, frame):
    """Remove POI by object reference."""
    if delete_item(ALL_POIS, poi):
        redraw_prefs(frame)

def save_desc_obj(poi, desc_var, frame, savebtn):
    """Save description by POI object reference."""
    poi["description"] = desc_var.get()
    save_pois()
    savebtn.config(state='disabled')
    try:
        frame.info_label.config(text=plugin_tl("Description updated!"))
    except Exception:
        pass

def add_manual_poi(body_entry, lat_entry, lon_entry, desc_entry, frame):
    body = body_entry.get().strip()
    try:
        lat = float(lat_entry.get().replace(",", "."))
        lon = float(lon_entry.get().replace(",", "."))
    except ValueError:
        frame.info_label.config(text=plugin_tl("Invalid input!"))
        return
    desc = desc_entry.get().strip()
    # Split body into system and body parts
    system_name, body_part = split_system_and_body(body)
    ALL_POIS.append({
        "type": "poi",
        "system": system_name,
        "body": body_part,
        "lat": lat,
        "lon": lon,
        "description": desc,
        "notes": "",
        "active": True
    })
    save_pois()
    redraw_prefs(frame)

def save_current_poi(frame):
    if last_lat is not None and last_lon is not None and last_body:
        # Split last_body into system and body parts
        system_part, body_part = split_system_and_body(last_body)
        ALL_POIS.append({
            "type": "poi",
            "system": system_part,
            "body": body_part,
            "lat": last_lat,
            "lon": last_lon,
            "description": "",
            "notes": "",
            "active": True
        })
        save_pois()
        redraw_prefs(frame)
    else:
        try:
            frame.info_label.config(text=plugin_tl("No valid planet/location to save!"))
        except Exception:
            pass

def prefs_changed(cmdr, is_beta):
    global ALT_VAR, ROWS_VAR, LEFT_VAR, SHOW_GUI_INFO_VAR, HEADING_GUIDANCE_VAR, GUIDANCE_THRESHOLD_VAR, GUIDANCE_DISTANCE_VAR, heading_guidance, POI_REFS, RELEASE_FRAME
    
    # Save release settings
    if RELEASE_FRAME:
        RELEASE_FRAME.prefs_changed(cmdr, is_beta)
    
    # Update active status for all POIs using POI_REFS (matches order of POI_VARS)
    for i, var in enumerate(POI_VARS):
        if i < len(POI_REFS):
            POI_REFS[i]["active"] = var.get()
    config.set(ALT_KEY, 1 if ALT_VAR.get() else 0)
    config.set(ROWS_KEY, ROWS_VAR.get())
    config.set(LEFT_KEY, LEFT_VAR.get())
    config.set(SHOW_GUI_INFO_KEY, 1 if SHOW_GUI_INFO_VAR.get() else 0)
    config.set(HEADING_GUIDANCE_KEY, 1 if HEADING_GUIDANCE_VAR.get() else 0)
    config.set(GUIDANCE_THRESHOLD_KEY, GUIDANCE_THRESHOLD_VAR.get())
    config.set(GUIDANCE_DISTANCE_KEY, GUIDANCE_DISTANCE_VAR.get())
    overlay.set_overlay_settings(ROWS_VAR.get(), LEFT_VAR.get())
    
    # Update heading guidance threshold if it exists
    if heading_guidance:
        heading_guidance.on_course_threshold = GUIDANCE_THRESHOLD_VAR.get()
    
    save_pois()
    redraw_plugin_app()

def update_overlay_for_current_position():
    """Update overlay based on current position. Called after adding/editing POI or from dashboard updates."""
    global OVERLAY_INFO_TEXT, OVERLAY_INFO_LABEL, within_2km_zone, gui_guidance_visible
    
    # If we don't have valid position data, clear overlay
    if last_lat is None or last_lon is None or not last_body:
        overlay.clear_all_poi_rows()
        if heading_guidance:
            heading_guidance.clear()
        OVERLAY_INFO_TEXT = ""
        return
    
    # Get all active POIs for current body
    visible_pois = [poi for poi in get_all_pois_flat(ALL_POIS) if poi.get("active", True) and get_full_body_name(poi) == last_body]
    
    # Check if heading guidance is enabled
    guidance_enabled = config.get_int(HEADING_GUIDANCE_KEY, default=1) == 1
    
    poi_texts = []
    closest_bearing = None
    closest_distance = None
    target_poi_index = 0  # Index of the POI being guided to
    
    for idx, poi in enumerate(visible_pois):
        poi_lat = poi.get("lat")
        poi_lon = poi.get("lon")
        poi_desc = poi.get("description", "")
        
        distance, bearing = calculate_bearing_and_distance(
            last_lat, last_lon,
            poi_lat, poi_lon,
            last_planet_radius,
            last_altitude, 0,  # alt1 = current, alt2 = 0
            calc_with_altitude=config.get_int(ALT_KEY)
        )
        
        # Track closest POI for heading guidance (first POI only when guidance enabled)
        if idx == 0:
            closest_distance = distance
            closest_bearing = bearing
            target_poi_index = 0
        
        if not poi_desc:
            if poi_lat is not None and poi_lon is not None:
                poi_desc = f"{poi_lat:.4f}, {poi_lon:.4f}"
            else:
                poi_desc = "(No description)"
        
        unit = "m"
        show_dist = distance
        if distance > 1_000:
            show_dist /= 1_000
            unit = "km"
        if show_dist > 1_000:
            show_dist /= 1_000
            unit = "Mm"
        
        if unit == "m":
            poi_texts.append((f"{round(bearing)}°/ {round(show_dist)}{unit} {poi_desc}", idx == 0 and guidance_enabled))
        else:
            poi_texts.append((f"{round(bearing)}°/ {show_dist:.1f}{unit} {poi_desc}", idx == 0 and guidance_enabled))
    
    if poi_texts:
        # Show POI rows with different colors - first POI orange (target), rest gray if guidance enabled
        overlay.show_poi_rows_with_colors(poi_texts)
        
        # Show graphical heading guidance if enabled and we have heading and a target bearing
        if guidance_enabled and heading_guidance and last_heading is not None and closest_bearing is not None:
            # Adjust Y-position based on number of POI rows
            arrow_y = overlay.ROW_Y_START + (len(poi_texts) * overlay.ROW_Y_STEP) + 30
            heading_guidance.center_y = arrow_y
            heading_guidance.center_x = overlay.OVERLAY_LEFT_MARGIN + 150  # Center relative to POI texts
            
            # Get guidance distance from config
            guidance_distance = config.get_int(GUIDANCE_DISTANCE_KEY, default=2000)
            
            # Handle guidance zone based on distance
            if closest_distance < guidance_distance:  # Within guidance stop distance
                if not within_2km_zone:
                    # First time within zone - show checkmark ONCE
                    heading_guidance.show_checkmark()
                    within_2km_zone = True
                else:
                    # Already within zone - show NOTHING (clear all)
                    heading_guidance.clear()
            else:  # Outside guidance zone
                # Left the zone - reset flag
                if within_2km_zone:
                    within_2km_zone = False
                # Show arrows/green circle as normal
                heading_guidance.update(last_heading, closest_bearing)
        elif heading_guidance:
            heading_guidance.clear()
        
        # Store overlay info for GUI display - limit to max rows
        max_rows = config.get_int(ROWS_KEY)
        gui_poi_texts = [text for text, _ in poi_texts[:max_rows]] if max_rows > 0 and len(poi_texts) > max_rows else [text for text, _ in poi_texts]
        OVERLAY_INFO_TEXT = "\n".join(gui_poi_texts)
    else:
        overlay.clear_all_poi_rows()
        if heading_guidance:
            heading_guidance.clear()
        OVERLAY_INFO_TEXT = ""

def dashboard_entry(cmdr, is_beta, entry):
    global last_lat, last_lon, last_body, last_altitude, last_planet_radius, last_heading, CURRENT_SYSTEM, OVERLAY_INFO_TEXT, within_2km_zone, gui_guidance_visible

    altitude = entry.get("Altitude") or 0
    lat = entry.get("Latitude")
    lon = entry.get("Longitude")
    bodyname = entry.get("BodyName")
    heading = entry.get("Heading")  # Get current heading from dashboard
    planet_radius = entry.get("PlanetRadius") or 1000000  # Default radius if missing
    
    # Update heading if available
    if heading is not None:
        last_heading = heading
    
    # Track body changes AND first coordinate acquisition
    body_changed = False
    prev_body = last_body
    first_coords = False  # Track if this is first time getting coords
    
    # Update last_body even if we don't have coordinates (e.g., in orbit)
    if bodyname:
        last_body = bodyname
        body_changed = str(prev_body) != str(bodyname)
        # Only update coordinates if we have them (on surface)
        if lat is not None and lon is not None:
            # Check if this is the first time we get coordinates
            if last_lat is None or last_lon is None:
                first_coords = True
            last_lat, last_lon = lat, lon
            last_altitude, last_planet_radius = altitude, planet_radius
    else:
        # No body anymore - clear everything
        if last_body:
            last_body = None
            last_heading = None
            within_2km_zone = False  # Reset checkmark flag
            gui_guidance_visible = False  # Reset GUI guidance state
            OVERLAY_INFO_TEXT = ""
            overlay.clear_all_poi_rows()
            if heading_guidance:
                heading_guidance.clear()
            redraw_plugin_app()
            return
    
    # Rebuild GUI only if body changed or first coords received
    if body_changed or first_coords:
        gui_guidance_visible = False  # Reset GUI guidance state on body/coords change
        redraw_plugin_app()
    
    # Update overlay for current position (does not rebuild GUI)
    if lat is not None and lon is not None and bodyname:
        update_overlay_for_current_position()
        
        # Update GUI widgets dynamically without rebuilding (if show_gui_info is enabled)
        if config.get_int(SHOW_GUI_INFO_KEY) and last_heading is not None:
            matching_pois = [poi for poi in get_all_pois_flat(ALL_POIS) if get_full_body_name(poi) == last_body and poi.get("active", True)]
            if matching_pois:
                first_poi = matching_pois[0]
                poi_lat = first_poi.get("lat")
                poi_lon = first_poi.get("lon")
                
                if poi_lat is not None and poi_lon is not None:
                    distance, bearing = calculate_bearing_and_distance(
                        last_lat, last_lon, poi_lat, poi_lon,
                        last_planet_radius, last_altitude, 0,
                        calc_with_altitude=config.get_int(ALT_KEY)
                    )
                    
                    show_dist, unit = format_distance_with_unit(distance)
                    
                    # Update FIRST_POI_LABEL
                    if FIRST_POI_LABEL is not None:
                        desc = first_poi.get("description", "")
                        if not desc:
                            desc = f"{poi_lat:.4f}, {poi_lon:.4f}"
                        if unit == "m":
                            display_text = f"{desc} - {round(bearing)}°/ {round(show_dist)}{unit}"
                        else:
                            display_text = f"{desc} - {round(bearing)}°/ {show_dist:.1f}{unit}"
                        FIRST_POI_LABEL.config(text=display_text)
                    
                    # Update guidance widgets if they exist, or rebuild GUI if state changed
                    guidance_distance = config.get_int(GUIDANCE_DISTANCE_KEY, default=2000)
                    should_show_guidance = distance >= guidance_distance
                    
                    # Check if GUI guidance state needs to change
                    if should_show_guidance != gui_guidance_visible:
                        # State changed - trigger full GUI rebuild to add/remove widgets
                        gui_guidance_visible = should_show_guidance
                        redraw_plugin_app()
                        return  # GUI rebuild will handle everything
                    
                    # GUI state is correct - just update widget content if widgets exist
                    if should_show_guidance and GUIDANCE_CENTER_LABEL is not None:
                        # Calculate deviation
                        guidance_threshold = config.get_int(GUIDANCE_THRESHOLD_KEY, default=4)
                        deviation = bearing - last_heading
                        # Normalize to -180 to +180
                        while deviation > 180:
                            deviation -= 360
                        while deviation < -180:
                            deviation += 360
                        on_course = abs(deviation) <= guidance_threshold
                        
                        # Calculate number of arrows
                        num_arrows = 0
                        if not on_course:
                            abs_deviation = abs(deviation)
                            if abs_deviation > guidance_threshold:
                                max_deviation = 90
                                arrow_fraction = min((abs_deviation - guidance_threshold) / (max_deviation - guidance_threshold), 1.0)
                                num_arrows = int(arrow_fraction * 4) + 1
                                num_arrows = min(num_arrows, 4)
                        
                        # Update guidance labels
                        left_arrows = "<" * num_arrows if deviation < -guidance_threshold else ""
                        GUIDANCE_LEFT_LABEL.config(text=left_arrows)
                        
                        if unit == "m":
                            center_text = f"{round(bearing)}°/ {round(show_dist)}{unit}"
                        else:
                            center_text = f"{round(bearing)}°/ {show_dist:.1f}{unit}"
                        
                        # Update text
                        GUIDANCE_CENTER_LABEL.config(text=center_text)
                        
                        # Update color based on on_course status
                        if on_course:
                            GUIDANCE_CENTER_LABEL.config(foreground="#00aa00")
                        else:
                            # Get current theme's default foreground color by creating temp label
                            import tkinter as tk
                            temp_label = tk.Label()
                            theme.update(temp_label)
                            default_fg = temp_label.cget("foreground")
                            temp_label.destroy()
                            GUIDANCE_CENTER_LABEL.config(foreground=default_fg)
                        
                        right_arrows = ">" * num_arrows if deviation > guidance_threshold else ""
                        GUIDANCE_RIGHT_LABEL.config(text=right_arrows)

