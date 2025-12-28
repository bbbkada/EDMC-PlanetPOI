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
plugin_tl = functools.partial(l10n.translations.tl, context=__file__)

PLUGIN_PARENT = None
PLUGIN_FRAME = None  # Persistent frame for dynamic updates
OVERLAY_INFO_LABEL = None  # Reference to overlay info label for updates

POI_FILE = os.path.join(os.path.dirname(__file__), "poi.json")
ALL_POIS = []
POI_VARS = []

ALT_KEY = "planetpoi_calc_with_altitude"
ROWS_KEY = "planetpoi_max_overlay_rows"
LEFT_KEY = "planetpoi_overlay_leftmargin"
SHOW_GUI_INFO_KEY = "planetpoi_show_gui_info"

ALT_VAR = None
ROWS_VAR = None
LEFT_VAR = None
SHOW_GUI_INFO_VAR = None

# Store overlay info for display in GUI
OVERLAY_INFO_TEXT = ""

CURRENT_SYSTEM = None

# Latest position for "Save current location"
last_lat, last_lon, last_body = None, None, None

# Settings table sorting
SORT_COLUMN = "body"  # Default sort column: "body", "lat", "lon", "description"
SORT_REVERSE = False  # False = ascending, True = descending

def format_body_name(body_name):
    """
    Format body name according to Elite Dangerous naming rules.
    Examples: 
    - "c1ab" -> "C 1 a b"
    - "c11b" -> "C 11 b"
    - "2a" -> "2 a"
    - "B3CD" -> "B 3 c d"
    """
    if not body_name:
        return ""
    
    # Remove all whitespace
    body_name = body_name.replace(" ", "").strip()
    if not body_name:
        return ""
    
    result = []
    for i, char in enumerate(body_name):
        if i == 0:
            # First character: uppercase if letter, otherwise keep as-is
            result.append(char.upper() if char.isalpha() else char)
        else:
            prev_char = body_name[i-1]
            # Add space UNLESS both current and previous are digits (to keep numbers together like "11")
            if not (prev_char.isdigit() and char.isdigit()):
                result.append(" ")
            # Lowercase if letter
            result.append(char.lower() if char.isalpha() else char)
    
    return "".join(result)

def get_full_body_name(poi):
    """Get full body name from POI (combines system + body)."""
    system = poi.get("system", "")
    body = poi.get("body", "")
    if body:
        return f"{system} {body}"
    return system

def load_pois():
    global ALL_POIS
    if os.path.isfile(POI_FILE):
        with open(POI_FILE, "r", encoding="utf8") as f:
            data = json.load(f)
            # Migrate old format to new folder-based format with separate system/body
            if data and isinstance(data, list):
                migrated = False
                for item in data:
                    # Check if POI needs migration (has old "body" field but not "system" field)
                    if item.get("type") == "poi" and "body" in item and "system" not in item:
                        # Old format: {"body": "HIP 36601 C 3 b"}
                        # New format: {"system": "HIP 36601", "body": "C 3 b"}
                        full_body = item.get("body", "")
                        system_name, body_part = split_system_and_body(full_body)
                        item["system"] = system_name
                        item["body"] = body_part
                        migrated = True
                        print(f"Migrated POI: {full_body} -> system={system_name}, body={body_part}")
                    # Also ensure old non-typed POIs get type field
                    elif "type" not in item:
                        item["type"] = "poi"
                        if "body" in item and "system" not in item:
                            full_body = item.get("body", "")
                            system_name, body_part = split_system_and_body(full_body)
                            item["system"] = system_name
                            item["body"] = body_part
                            migrated = True
                
                if migrated:
                    print("Saving migrated POI format...")
                    ALL_POIS = data
                    save_pois()  # Save migrated format
                else:
                    ALL_POIS = data
            else:
                ALL_POIS = []
    else:
        ALL_POIS = []

def save_pois():
    global ALL_POIS
    print("saving pois")
    with open(POI_FILE, "w", encoding="utf8") as f:
        json.dump(ALL_POIS, f, indent=2)

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
    global ALT_VAR, ROWS_VAR, LEFT_VAR, SHOW_GUI_INFO_VAR, ALL_POIS, CURRENT_SYSTEM, last_lat, last_lon, last_body
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
   
    load_pois()
    overlay.set_overlay_settings(ROWS_VAR.get(), LEFT_VAR.get())
    
    # ============== SIMULATION - HARDCODED VALUES ==============
    # Comment out these lines to disable simulation
    CURRENT_SYSTEM = "HIP 36601"
    last_body = "HIP 36601 C 1 a"
    last_lat = -67.5  # Same as POI "Crystalline shards Tellerium"
    last_lon = 127.2
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

def get_ui_scale():
    """Get UI scale factor from EDMC config (default 100%)"""
    try:
        scale = config.get_int("ui_scale")
        if scale == 0:
            scale = 100
        return scale / 100.0
    except:
        return 1.0

def scale_geometry(width, height, scale=None):
    """Scale dialog geometry with softer scaling curve"""
    if scale is None:
        scale = get_ui_scale()
    # Use softer scaling: 75% of scale + 25% base to avoid over-scaling
    adjusted_scale = 0.72 * scale + 0.25
    return f"{int(width * adjusted_scale)}x{int(height * adjusted_scale)}"

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
                    2000000, 0, 0, calc_with_altitude=False
                )
                
                unit = "m"
                show_dist = distance
                if distance > 1_000:
                    show_dist /= 1_000
                    unit = "km"
                if show_dist > 1_000:
                    show_dist /= 1_000
                    unit = "Mm"
                poi_texts.append(f"{round(bearing)}° / {round(show_dist, 2)}{unit} {poi_desc}")
            
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

def show_add_poi_dialog(parent_frame, prefill_system=None, edit_poi=None, parent_children=None):
    """Show dialog to add a new POI or edit existing POI"""
    dialog = tk.Toplevel(parent_frame)
    is_edit_mode = edit_poi is not None
    # If no parent specified, use root
    if parent_children is None:
        parent_children = ALL_POIS
    dialog.title("Edit POI" if is_edit_mode else "Add New POI")
    dialog.geometry(scale_geometry(550, 650))
    dialog.transient(parent_frame)
    dialog.grab_set()
    
    # Center the dialog and ensure it stays within screen bounds
    dialog.update_idletasks()
    screen_width = dialog.winfo_screenwidth()
    screen_height = dialog.winfo_screenheight()
    dialog_width = dialog.winfo_width()
    dialog_height = dialog.winfo_height()
    
    # Calculate centered position
    x = parent_frame.winfo_rootx() + (parent_frame.winfo_width() // 2) - (dialog_width // 2)
    y = parent_frame.winfo_rooty() + (parent_frame.winfo_height() // 2) - (dialog_height // 2)
    
    # Ensure dialog stays within screen bounds
    x = max(0, min(x, screen_width - dialog_width))
    y = max(0, min(y, screen_height - dialog_height))
    
    dialog.geometry(f"+{x}+{y}")
    
    # Determine auto-fill values
    auto_system = CURRENT_SYSTEM or ""
    auto_body = ""
    auto_lat = ""
    auto_lon = ""
    auto_desc = ""
    auto_notes = ""
    
    # If editing existing POI, prefill with its data
    if is_edit_mode:
        auto_system = edit_poi.get("system", "")
        auto_body = edit_poi.get("body", "")
        lat_val = edit_poi.get("lat", "")
        lon_val = edit_poi.get("lon", "")
        auto_lat = str(lat_val) if lat_val not in ["", None] else ""
        auto_lon = str(lon_val) if lon_val not in ["", None] else ""
        auto_desc = edit_poi.get("description", "")
        auto_notes = edit_poi.get("notes", "")
    else:
        # If we have a current body position, extract system and body parts
        if last_body:
            # Split last_body into system and body parts
            system_part, body_part = split_system_and_body(last_body)
            auto_system = system_part
            auto_body = body_part
            if last_lat is not None and last_lon is not None:
                auto_lat = str(last_lat)
                auto_lon = str(last_lon)
        
        # If prefill_system provided (from button click or folder), use it
        # But it might also contain a full body name, so split it first
        if prefill_system:
            system_part, body_part = split_system_and_body(prefill_system)
            auto_system = system_part if system_part else prefill_system
            # Only override body if we didn't already have one from last_body
            if body_part and not auto_body:
                auto_body = body_part
    
    # Configure dialog grid
    dialog.grid_columnconfigure(1, weight=1)
    
    row = 0
    
    # Paste button at the top - function defined later after all variables exist
    paste_btn_placeholder = None  # Will be created after variables are defined
    paste_btn = tk.Button(dialog, text="📋 Paste shared link", width=18)
    paste_btn.grid(row=row, column=1, sticky="e", padx=(10, 20), pady=(5, 10))
    row += 1
    
    tk.Label(dialog, text="System Name:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
    
    # Use AutoCompleter for system name with Spansh API
    system_entry = AutoCompleter(dialog, "System Name", width=30)
    system_entry.grid(row=row, column=1, padx=(10, 20), pady=5, sticky="ew")
    
    # Set the initial value if we have one
    if auto_system:
        system_entry.set_text(auto_system, placeholder_style=False)
    
    system_var = system_entry.var
    row += 1
    # AutoCompleter uses two rows (one for entry, one for dropdown list when shown)
    row += 1
    
    tk.Label(dialog, text="Body Name:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
    body_var = tk.StringVar(value=auto_body)
    body_entry = tk.Entry(dialog, textvariable=body_var, width=30)
    body_entry.grid(row=row, column=1, padx=(10, 20), pady=5, sticky="ew")
    row += 1
    
    tk.Label(dialog, text="Latitude:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
    lat_var = tk.StringVar(value=auto_lat)
    lat_entry = tk.Entry(dialog, textvariable=lat_var, width=30)
    lat_entry.grid(row=row, column=1, padx=(10, 20), pady=5, sticky="ew")
    row += 1
    
    tk.Label(dialog, text="Longitude:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
    lon_var = tk.StringVar(value=auto_lon)
    lon_entry = tk.Entry(dialog, textvariable=lon_var, width=30)
    lon_entry.grid(row=row, column=1, padx=(10, 20), pady=5, sticky="ew")
    row += 1
    
    tk.Label(dialog, text="Description:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
    desc_var = tk.StringVar(value=auto_desc)
    desc_entry = tk.Entry(dialog, textvariable=desc_var, width=30)
    desc_entry.grid(row=row, column=1, padx=(10, 20), pady=5, sticky="ew")
    row += 1
    
    tk.Label(dialog, text="Notes:").grid(row=row, column=0, sticky="nw", padx=10, pady=5)
    notes_text = tk.Text(dialog, width=40, height=8, wrap=tk.WORD, font="TkDefaultFont")
    notes_text.grid(row=row, column=1, padx=(10, 20), pady=5, sticky="ew")
    if auto_notes:
        notes_text.insert("1.0", auto_notes)
    row += 1
    
    status_label = tk.Label(dialog, text="", fg="red")
    status_label.grid(row=row, column=0, columnspan=2, pady=(2, 5))
    row += 1
    
    # Configure paste button now that all variables are defined
    def paste_from_clipboard():
        try:
            clipboard_text = dialog.clipboard_get().strip()
            poi_data = parse_share_url(clipboard_text)
            
            if poi_data:
                # Use system and body from parsed data (already in new format)
                system_name = poi_data.get('system', '')
                body_part = poi_data.get('body', '')
                
                # Fill in all fields
                system_entry.set_text(system_name, placeholder_style=False)
                body_var.set(body_part)
                lat_var.set(str(poi_data.get('lat', '')))
                lon_var.set(str(poi_data.get('lon', '')))
                desc_var.set(poi_data.get('description', ''))
                notes_text.delete("1.0", tk.END)
                notes_text.insert("1.0", poi_data.get('notes', ''))
                
                status_label.config(text="✓ Loaded from shared link", fg="green")
            else:
                status_label.config(text="No valid link found in clipboard", fg="red")
        except Exception as e:
            status_label.config(text="No link found in clipboard", fg="red")
    
    # Set the command for the paste button that was created earlier
    paste_btn.config(command=paste_from_clipboard)
    
    # Auto-detect share link when pasting into any field
    def on_paste(event):
        widget = event.widget
        dialog.after(10, lambda: check_for_share_link(widget))
    
    def check_for_share_link(widget):
        try:
            text = widget.get()
            if 'github.io/EDMC-PlanetPOI' in text or '#' in text:
                poi_data = parse_share_url(text)
                if poi_data:
                    # Clear the pasted URL from the field
                    if widget == system_entry:
                        system_entry.set_text("", placeholder_style=False)
                    elif hasattr(widget, 'delete'):
                        widget.delete(0, tk.END)
                    
                    # Use system and body from parsed data (already in new format)
                    system_name = poi_data.get('system', '')
                    body_part = poi_data.get('body', '')
                    
                    # Fill in all fields
                    system_entry.set_text(system_name, placeholder_style=False)
                    body_var.set(body_part)
                    lat_var.set(str(poi_data.get('lat', '')))
                    lon_var.set(str(poi_data.get('lon', '')))
                    desc_var.set(poi_data.get('description', ''))
                    notes_text.delete("1.0", tk.END)
                    notes_text.insert("1.0", poi_data.get('notes', ''))
                    
                    status_label.config(text="✓ Auto-loaded from shared link", fg="green")
        except Exception:
            pass
    
    # Bind paste event to all entry fields
    system_entry.bind('<Control-v>', on_paste)
    body_entry.bind('<Control-v>', on_paste)
    lat_entry.bind('<Control-v>', on_paste)
    lon_entry.bind('<Control-v>', on_paste)
    desc_entry.bind('<Control-v>', on_paste)
    notes_text.bind('<Control-v>', on_paste)
    
    def save_and_close():
        system = system_var.get().strip()
        body = body_var.get().strip()
        
        if not system:
            status_label.config(text="System name is required!", fg="red")
            return
        
        # Format body name with proper spacing and capitalization
        if body:
            formatted_body = format_body_name(body)
        else:
            formatted_body = ""
        
        # Allow empty lat/lon for system-only POIs
        lat_str = lat_var.get().strip().replace(",", ".")
        lon_str = lon_var.get().strip().replace(",", ".")
        
        if lat_str and lon_str:
            try:
                lat = float(lat_str)
                lon = float(lon_str)
            except ValueError:
                status_label.config(text="Invalid latitude or longitude!", fg="red")
                return
        else:
            # Store as empty strings for system-only POIs
            lat = ""
            lon = ""
        
        desc = desc_var.get().strip()
        notes = notes_text.get("1.0", tk.END).strip()
        
        if is_edit_mode:
            # Update existing POI
            edit_poi["system"] = system
            edit_poi["body"] = formatted_body
            edit_poi["lat"] = lat
            edit_poi["lon"] = lon
            edit_poi["description"] = desc
            edit_poi["notes"] = notes
            print(f"PPOI: Updated POI: system={system}, body={formatted_body}")
        else:
            # Create new POI
            new_poi = {
                "type": "poi",
                "system": system,
                "body": formatted_body,
                "lat": lat,
                "lon": lon,
                "description": desc,
                "notes": notes,
                "active": True
            }
            parent_children.append(new_poi)
            print(f"PPOI: Added new POI: system={system}, body={formatted_body}")
            print(f"PPOI: Total items now: {len(ALL_POIS)}")
        
        save_pois()
        redraw_plugin_app()
        dialog.destroy()
    
    # Buttons aligned to the right, same as inputs and paste button
    button_frame = tk.Frame(dialog)
    button_frame.grid(row=row, column=1, sticky="e", padx=(10, 20), pady=(5, 20))
    
    tk.Button(button_frame, text="Cancel", command=dialog.destroy, width=10).pack(side="left", padx=(0, 5))
    tk.Button(button_frame, text="Save", command=save_and_close, width=10).pack(side="left")
    
    # Focus on description field by default (system and body are usually pre-filled)
    desc_entry.focus()

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
            command=lambda: share_poi_link(item)
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
                    command=lambda p=item: share_poi_link(p)
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
        command=lambda: share_poi_link(poi)
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
                2000000, 0, 0, calc_with_altitude=False
            )
            
            unit = "m"
            show_dist = distance
            if distance > 1_000:
                show_dist /= 1_000
                unit = "km"
            if show_dist > 1_000:
                show_dist /= 1_000
                unit = "Mm"
            poi_texts.append(f"{round(bearing)}° / {round(show_dist, 2)}{unit} {poi_desc}")
        
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
    """Show dialog to add new folder."""
    popup = tk.Toplevel()
    popup.title(plugin_tl("Add Folder"))
    popup.geometry(scale_geometry(400, 150))
    
    tk.Label(popup, text=plugin_tl("Folder name:")).pack(pady=10)
    
    name_var = tk.StringVar()
    entry = tk.Entry(popup, textvariable=name_var, width=40)
    entry.pack(pady=10, padx=20)
    entry.focus()
    
    def save_and_close(event=None):
        folder_name = name_var.get().strip()
        if folder_name:
            create_folder(parent_children, folder_name)
            redraw_plugin_app()
            popup.destroy()
    
    # Bind Enter key to submit
    entry.bind("<Return>", save_and_close)
    popup.bind("<Return>", save_and_close)
    
    tk.Button(popup, text=plugin_tl("Add"), command=save_and_close).pack(pady=10)
    
    try:
        theme.update(popup)
    except Exception:
        pass

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
    """Show dialog to move POI or folder to different parent."""
    # Auto-detect if we're in a config dialog by checking toplevel
    in_config_dialog = False
    try:
        toplevel = frame.winfo_toplevel()
        # If the toplevel is not the main window and has a title, we're likely in a dialog
        if toplevel.winfo_class() == 'Toplevel' and 'Configuration' in str(toplevel.title()):
            in_config_dialog = True
            is_prefs = True
    except Exception:
        pass
    
    # Get the toplevel window properly
    if is_prefs:
        # For prefs, find the toplevel window (Settings window)
        parent = frame.winfo_toplevel()
    else:
        # For main window, use frame directly
        parent = frame
    
    popup = tk.Toplevel()
    popup.title(plugin_tl(f"Move {item_type}"))
    popup.geometry(scale_geometry(500, 450))
    
    # Make it a proper modal dialog
    if is_prefs:
        popup.transient(parent)
    
    # Label at top
    tk.Label(popup, text=plugin_tl("Select destination folder:")).pack(pady=(10, 5), padx=10)
    
    # Create listbox with all folders - use pack with explicit height
    listbox_frame = tk.Frame(popup)
    listbox_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
    
    scrollbar = tk.Scrollbar(listbox_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    listbox = tk.Listbox(listbox_frame, width=50, yscrollcommand=scrollbar.set)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=listbox.yview)
    
    # Add root level option
    folder_map = {0: ALL_POIS}  # Map index to folder's children list
    current_parent = None  # Will track which folder contains the item
    current_index = None
    
    listbox.insert(tk.END, "(Root level)")
    
    # Find current parent of item
    def find_parent(items, target, parent=None):
        for it in items:
            if it is target:
                return parent
            if it.get("type") == "folder":
                result = find_parent(it.get("children", []), target, it)
                if result is not None:
                    return result
        return None
    
    current_parent = find_parent(ALL_POIS, item)
    
    # Check if item is at root level
    if current_parent is None and item in ALL_POIS:
        current_index = 0
    
    # Recursively add folders
    def add_folders(items, indent=0):
        nonlocal current_index
        for it in items:
            if it.get("type") == "folder" and it is not item:  # Don't show item itself
                idx = listbox.size()
                folder_map[idx] = it.get("children", [])
                prefix = "  " * indent + "📁 "
                listbox.insert(tk.END, f"{prefix}{it.get('name', 'Unnamed')}")
                
                # Check if this folder is the current parent
                if it is current_parent:
                    current_index = idx
                
                add_folders(it.get("children", []), indent + 1)
    
    add_folders(ALL_POIS)
    
    # Select and highlight current location
    if current_index is not None:
        listbox.selection_set(current_index)
        listbox.activate(current_index)
        listbox.see(current_index)
    
    def move_and_close():
        selection = listbox.curselection()
        if selection:
            idx = selection[0]
            target_children = folder_map.get(idx, ALL_POIS)
            if move_item(ALL_POIS, item, target_children):
                save_pois()
                # Release grab and destroy popup BEFORE redrawing
                if is_prefs:
                    popup.grab_release()
                popup.destroy()
                # Only redraw main window if NOT in config dialog
                if not in_config_dialog:
                    redraw_plugin_app()
                    # Only redraw prefs if we're in EDMC Settings (not config dialog)
                    if is_prefs:
                        try:
                            frame.after(10, lambda: redraw_prefs(frame))
                        except Exception as e:
                            print(f"Error redrawing prefs: {e}")
    
    def cancel_and_close():
        if is_prefs:
            popup.grab_release()
        popup.destroy()
    
    # Button at bottom with proper frame
    button_frame = tk.Frame(popup)
    button_frame.pack(side=tk.BOTTOM, pady=10, padx=10)
    tk.Button(button_frame, text=plugin_tl("Move"), command=move_and_close, width=15).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text=plugin_tl("Cancel"), command=cancel_and_close, width=15).pack(side=tk.LEFT, padx=5)
    
    popup.focus_set()
    if is_prefs:
        popup.grab_set()

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
    """Confirm and delete item."""
    try:
        import tkinter.messagebox as mb
        item_name = item.get("description", "") if item_type == "poi" else item.get("name", "")
        
        # Build confirmation message
        if item_type == "folder":
            subfolder_count, poi_count = count_folder_contents(item)
            if subfolder_count > 0 or poi_count > 0:
                message = plugin_tl(f"Are you sure you want to delete this folder?\n\n{item_name}\n\n")
                message += plugin_tl("This will also delete:\n")
                if subfolder_count > 0:
                    message += plugin_tl(f"• {subfolder_count} subfolder(s)\n")
                if poi_count > 0:
                    message += plugin_tl(f"• {poi_count} POI(s)")
            else:
                message = plugin_tl(f"Are you sure you want to delete this {item_type}?\n\n{item_name}")
        else:
            message = plugin_tl(f"Are you sure you want to delete this {item_type}?\n\n{item_name}")
        
        if mb.askyesno(
            plugin_tl(f"Delete {item_type}"),
            message
        ):
            if delete_item(ALL_POIS, item):
                redraw_plugin_app()
    except Exception as ex:
        print(f"Error deleting item: {ex}")

def build_plugin_content(frame):
    """Build/rebuild the content inside the persistent plugin frame."""
    # Liten font för POI-listan
    small_font = tkfont.Font(size=9)  # Justera till 8 eller 10 vid behov
    
    frame.grid_columnconfigure(0, weight=0, minsize=25)  # Checkbox column - fixed width
    frame.grid_columnconfigure(1, weight=1)  # Text column - expands
    row = 0

    print("build_plugin_content last_body:", last_body)
    current_body = last_body

    if not current_body:
        matching_system_pois = []
        if CURRENT_SYSTEM:
            matching_system_pois = [poi for poi in get_all_pois_flat(ALL_POIS) if poi.get("system", "") == CURRENT_SYSTEM]
        
        if matching_system_pois:
            header_frame = tk.Frame(frame)
            header_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=2, pady=2)
            header_frame.grid_columnconfigure(0, weight=1)
            
            system_label = tk.Label(header_frame, text=plugin_tl("PPOI: Poi's in {system}").format(system=CURRENT_SYSTEM))
            system_label.grid(row=0, column=0, sticky="w")
            theme.update(system_label)
            menu_btn = tk.Button(header_frame, text="☰", width=3, height=1, borderwidth=0, highlightthickness=0, relief="flat")
            menu_btn.config(command=lambda b=menu_btn: show_menu_dropdown(frame, b, CURRENT_SYSTEM))
            menu_btn.grid(row=0, column=1, sticky="e")
            theme.update(header_frame)
            row += 1
            for idx, poi in enumerate(matching_system_pois):
                desc = poi.get("description", "")
                if not desc:
                    lat = poi.get("lat")
                    lon = poi.get("lon")
                    if lat is not None and lon is not None:
                        desc = f"{lat:.4f}, {lon:.4f}"
                    else:
                        desc = "(No description)"
                
                body_part = poi.get("body", "")
                if body_part:
                    poi_desc = body_part + " - " + desc
                else:
                    poi_desc = desc
                
                # Check if POI is active
                is_active = poi.get("active", True)
                
                # Create label with conditional foreground color
                label_kwargs = {
                    "text": poi_desc,
                    "font": small_font
                }
                if not is_active:
                    label_kwargs["foreground"] = "gray"
                
                poi_label = tk.Label(frame, **label_kwargs)
                poi_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=2, pady=0)
                theme.update(poi_label)
                
                # Bind right-click to POI label in system view
                poi_label.bind("<Button-3>", lambda e, p=poi: show_poi_context_menu_main(e, p, frame))
                
                row += 1
        else:    
            header_frame = tk.Frame(frame)
            header_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=2, pady=2)
            header_frame.grid_columnconfigure(0, weight=1)
            
            no_system_label = tk.Label(header_frame, text=plugin_tl("PPOI: No poi's in system"))
            no_system_label.grid(row=0, column=0, sticky="w")
            theme.update(no_system_label)
            menu_btn = tk.Button(header_frame, text="☰", width=3, height=1, borderwidth=0, highlightthickness=0, relief="flat")
            menu_btn.config(command=lambda b=menu_btn: show_menu_dropdown(frame, b, CURRENT_SYSTEM))
            menu_btn.grid(row=0, column=1, sticky="e")
            theme.update(header_frame)
        
        return

    matching_pois = [poi for poi in get_all_pois_flat(ALL_POIS) if get_full_body_name(poi) == current_body]
    print(f"PPOI: build_plugin_content - current_body={current_body}, found {len(matching_pois)} POIs")

    # Header with add button
    header_frame = tk.Frame(frame)
    header_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=2, pady=2)
    header_frame.grid_columnconfigure(0, weight=1)
    
    body_label = tk.Label(
        header_frame,
        text=f"PPOI: {current_body}",
        font=('TkDefaultFont', 10, 'bold')
    )
    body_label.grid(row=0, column=0, sticky="w")
    theme.update(body_label)
    
    menu_btn = tk.Button(header_frame, text="☰", width=3, height=1, borderwidth=0, highlightthickness=0, relief="flat")
    menu_btn.config(command=lambda b=menu_btn: show_menu_dropdown(frame, b, current_body))
    menu_btn.grid(row=0, column=1, sticky="e")
    theme.update(header_frame)
    row += 1
    
    # Show overlay info in GUI if enabled AND there is text to show
    global OVERLAY_INFO_LABEL
    if config.get_int(SHOW_GUI_INFO_KEY) and OVERLAY_INFO_TEXT:
        # Create italic bold font for directions to distinguish from POIs
        directions_font = tkfont.Font(size=9, slant="italic", weight="bold")
        
        # Create frame with border for directions - let theme handle colors
        directions_frame = tk.Frame(frame, relief="groove", borderwidth=2)
        directions_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=2, pady=(2, 5))
        
        # Add label inside the frame - theme will apply appropriate colors
        info_label = tk.Label(
            directions_frame, 
            text=OVERLAY_INFO_TEXT, 
            font=directions_font, 
            anchor="w", 
            justify="left"
        )
        info_label.pack(padx=4, pady=2, fill="both")
        
        # Apply theme to both frame and label
        theme.update(directions_frame)
        theme.update(info_label)
        OVERLAY_INFO_LABEL = info_label
        row += 1
    else:
        OVERLAY_INFO_LABEL = None

    for idx, poi in enumerate(matching_pois):
        desc = poi.get("description", "")
        if not desc:
            lat = poi.get("lat")
            lon = poi.get("lon")
            if lat is not None and lon is not None:
                desc = f"{lat:.4f}, {lon:.4f}"
            else:
                desc = "(No description)"
        
        # Check if POI is active
        is_active = poi.get("active", True)
        
        # Create label with conditional foreground color
        label_kwargs = {
            "text": desc,
            "font": small_font
        }
        if not is_active:
            label_kwargs["foreground"] = "gray"
        
        desc_label = tk.Label(frame, **label_kwargs)
        desc_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=2, pady=0)
        theme.update(desc_label)
        
        # Bind right-click to description label
        desc_label.bind("<Button-3>", lambda e, p=poi: show_poi_context_menu_main(e, p, frame))

        row += 1

    if not matching_pois:
        no_poi_label = tk.Label(
            frame,
            text=plugin_tl("PPOI: No POIs for this body")
        )
        no_poi_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=2)
        theme.update(no_poi_label)


def plugin_app(parent, cmdr=None, is_beta=None):
    """Create the persistent plugin frame and return it."""
    global PLUGIN_PARENT, PLUGIN_FRAME
    PLUGIN_PARENT = parent
    
    # Create persistent frame - use tk.Frame, let theme handle background
    PLUGIN_FRAME = tk.Frame(parent, highlightthickness=1)
    PLUGIN_FRAME.grid(row=0, column=0, columnspan=2, sticky="nsew")
    
    # Build initial content
    build_plugin_content(PLUGIN_FRAME)
    
    # Apply theme - makes tk widgets get proper theme colors
    theme.update(PLUGIN_FRAME)
    theme.update(parent)
    
    return PLUGIN_FRAME



def plugin_prefs(parent, cmdr, is_beta):
    outer_frame = nb.Frame(parent)
    scroll_frame = create_scrolled_frame(outer_frame)
    build_plugin_ui(scroll_frame)
    return outer_frame

def create_scrolled_frame(parent):
    try:
        bg = parent.cget("background")
    except Exception:
        try:
            bg = parent["bg"]
        except Exception:
            bg = "#ffffff"

    canvas = tk.Canvas(parent, borderwidth=0, highlightthickness=0, background=bg)
    scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas, background=bg)

    scroll_frame_id = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    def _on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    scroll_frame.bind("<Configure>", _on_frame_configure)
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    parent.grid_rowconfigure(0, weight=1)
    parent.grid_columnconfigure(0, weight=1)

    return scroll_frame


def safe_int(val, fallback):
    try:
        return int(val)
    except Exception:
        return fallback

def build_plugin_ui(frame):
    global ALT_VAR, ROWS_VAR, LEFT_VAR, SHOW_GUI_INFO_VAR, POI_VARS
    row = 0

    # Headers on same row
    nb.Label(frame, text=plugin_tl("Calculate distance with altitude")).grid(row=row, column=0, columnspan=2,sticky="w", padx=(0, 8))
    nb.Label(frame, text=plugin_tl("Max overlay rows")).grid(row=row, column=2, sticky="w", padx=(0, 8))
    nb.Label(frame, text=plugin_tl("Overlay left margin (pixels)")).grid(row=row, column=3, sticky="w")
    row += 1

    # Widgets on same row
    cb = nb.Checkbutton(frame, variable=ALT_VAR, width=2)
    cb.grid(row=row, column=0, columnspan=2,sticky="w", padx=(0, 4))
    rows_entry = nb.EntryMenu(frame, textvariable=ROWS_VAR, width=4)
    rows_entry.grid(row=row, column=2, sticky="w", padx=(0, 8))
    left_entry = nb.EntryMenu(frame, textvariable=LEFT_VAR, width=6)
    left_entry.grid(row=row, column=3, sticky="w", padx=(0, 8))
    export_btn = nb.Button(frame, text=plugin_tl("Export POIs"), command=lambda: export_pois_to_file(frame), width=12)
    export_btn.grid(row=row, column=4, sticky="w", padx=(0, 4))
    import_btn = nb.Button(frame, text=plugin_tl("Import POIs"), command=lambda: import_pois_from_file(frame), width=12)
    import_btn.grid(row=row, column=5, sticky="w", padx=(0, 4))
    row += 1
    
    # Show overlay info in GUI option
    nb.Label(frame, text=plugin_tl("Show overlay info in GUI")).grid(row=row, column=0, columnspan=2, sticky="w", padx=(0, 8))
    show_gui_cb = nb.Checkbutton(frame, variable=SHOW_GUI_INFO_VAR, width=2)
    show_gui_cb.grid(row=row, column=2, sticky="w", padx=(0, 4))
    row += 1
    
    # Configure column widths to prevent text clipping
    frame.grid_columnconfigure(0, weight=0)
    frame.grid_columnconfigure(1, weight=0)
    frame.grid_columnconfigure(2, weight=0)
    frame.grid_columnconfigure(3, weight=0)
    frame.grid_columnconfigure(4, weight=0, minsize=100)
    frame.grid_columnconfigure(5, weight=0, minsize=100)

    sep = ttk.Separator(frame, orient='horizontal')
    sep.grid(row=row, column=0, columnspan=8, sticky="ew", pady=8)
    row += 1

    # Create separate frame for table to avoid column conflicts with top controls
    # Use tk.Frame instead of nb.Frame so we can set background color
    table_frame = tk.Frame(frame, background="white")
    
    table_frame.grid(row=row, column=0, columnspan=8, sticky="nsew")
    frame.grid_rowconfigure(row, weight=1)  # Let table expand
    
    # Reset row counter for table frame
    table_row = 0
    
    nb.Label(table_frame, text=plugin_tl("Saved POIs"), font=('TkDefaultFont', 10, 'bold')).grid(row=table_row, column=0, columnspan=9, sticky="w")
    table_row += 1

    # Sorting function
    def sort_by_column(column):
        global SORT_COLUMN, SORT_REVERSE
        if SORT_COLUMN == column:
            SORT_REVERSE = not SORT_REVERSE
        else:
            SORT_COLUMN = column
            SORT_REVERSE = False
        redraw_prefs(frame)

    headers = [
        plugin_tl("Active"),
        "",  # Copy system icon column - no header text to avoid expanding
        plugin_tl("Body Name"),
        plugin_tl("Latitude"),
        plugin_tl("Longitude"),
        plugin_tl("Description"),
        plugin_tl("Delete"),
        plugin_tl("Save"),
        plugin_tl("Share")
    ]
    
    # Column names for sorting
    sortable_columns = {
        2: "body",
        5: "description"
    }
    
    for col, header in enumerate(headers):
        # No padding for copy icon column
        padding = 0 if col == 1 else 2
        
        # Make sortable columns clickable
        if col in sortable_columns:
            # Add sort indicator
            sort_indicator = ""
            if SORT_COLUMN == sortable_columns[col]:
                sort_indicator = " ▼" if SORT_REVERSE else " ▲"
            
            header_label = nb.Label(table_frame, text=header + sort_indicator, font=('TkDefaultFont', 9, 'bold'), cursor="hand2")
            header_label.grid(row=table_row, column=col, padx=padding, pady=2, sticky="w")
            header_label.bind("<Button-1>", lambda e, c=sortable_columns[col]: sort_by_column(c))
        else:
            nb.Label(table_frame, text=header, font=('TkDefaultFont', 9, 'bold')).grid(row=table_row, column=col, padx=padding, pady=2, sticky="w")
    table_row += 1

    POI_VARS = []
    # Sort POIs based on selected column and direction
    all_pois_flat = get_all_pois_flat(ALL_POIS)
    
    if SORT_COLUMN == "body":
        all_pois_sorted = sorted(all_pois_flat, key=lambda p: (p.get("system", "").lower(), p.get("body", "").lower()), reverse=SORT_REVERSE)
    elif SORT_COLUMN == "lat":
        all_pois_sorted = sorted(all_pois_flat, key=lambda p: (p.get("lat") if p.get("lat") is not None else 0), reverse=SORT_REVERSE)
    elif SORT_COLUMN == "lon":
        all_pois_sorted = sorted(all_pois_flat, key=lambda p: (p.get("lon") if p.get("lon") is not None else 0), reverse=SORT_REVERSE)
    elif SORT_COLUMN == "description":
        all_pois_sorted = sorted(all_pois_flat, key=lambda p: p.get("description", "").lower(), reverse=SORT_REVERSE)
    else:
        all_pois_sorted = sorted(all_pois_flat, key=lambda p: (p.get("system", "").lower(), p.get("body", "").lower()), reverse=SORT_REVERSE)
    
    for idx, poi in enumerate(all_pois_sorted):
        active_var = tk.BooleanVar(value=poi.get("active", True))
        cb = nb.Checkbutton(table_frame, variable=active_var, width=2)
        try:
            cb.configure(background="white")
        except:
            pass  # If background can't be set, continue anyway
        cb.grid(row=table_row, column=0, sticky="w", padx=(0, 0))
        POI_VARS.append(active_var)
        
        # Bind right-click to checkbox
        cb.bind("<Button-3>", lambda e, p=poi, av=active_var: show_poi_context_menu(e, p, frame, av))

        # Copy system name button (using Label for minimal space)
        def copy_system(system_name):
            table_frame.clipboard_clear()
            table_frame.clipboard_append(system_name)
        
        copy_label = nb.Label(table_frame, text="📋", cursor="hand2")
        copy_label.grid(row=table_row, column=1, sticky="e", padx=(0, 2))
        copy_label.bind("<Button-1>", lambda e, s=poi.get("system", ""): copy_system(s))
        copy_label.bind("<Button-3>", lambda e, p=poi, av=active_var: show_poi_context_menu(e, p, frame, av))
        
        # Show full body name (system + body) in table
        body_label = nb.Label(table_frame, text=get_full_body_name(poi), anchor="w")
        body_label.grid(row=table_row, column=2, padx=2, pady=2, sticky="w")
        body_label.bind("<Button-3>", lambda e, p=poi, av=active_var: show_poi_context_menu(e, p, frame, av))
        
        lat_label = nb.Label(table_frame, text=poi.get("lat", ""), anchor="w")
        lat_label.grid(row=table_row, column=3, padx=2, pady=2, sticky="w")
        lat_label.bind("<Button-3>", lambda e, p=poi, av=active_var: show_poi_context_menu(e, p, frame, av))
        
        lon_label = nb.Label(table_frame, text=poi.get("lon", ""), anchor="w")
        lon_label.grid(row=table_row, column=4, padx=2, pady=2, sticky="w")
        lon_label.bind("<Button-3>", lambda e, p=poi, av=active_var: show_poi_context_menu(e, p, frame, av))

        desc_var = tk.StringVar(value=poi.get("description", ""))
        desc_entry = nb.EntryMenu(table_frame, textvariable=desc_var, width=28)
        desc_entry.grid(row=table_row, column=5, sticky="w", padx=(2,2))
        desc_entry.bind("<Button-3>", lambda e, p=poi, av=active_var: show_poi_context_menu(e, p, frame, av))

        delbtn = nb.Button(table_frame, text=plugin_tl("Delete"), command=lambda p=poi: remove_poi_obj(p, frame), width=7)
        delbtn.grid(row=table_row, column=6, sticky="w", padx=(2,2))
        delbtn.bind("<Button-3>", lambda e, p=poi, av=active_var: show_poi_context_menu(e, p, frame, av))

        savebtn = nb.Button(table_frame, text=plugin_tl("Save"), state='disabled', width=7)
        savebtn.grid(row=table_row, column=7, sticky="w", padx=(2,2))
        savebtn.bind("<Button-3>", lambda e, p=poi, av=active_var: show_poi_context_menu(e, p, frame, av))

        sharebtn = nb.Button(table_frame, text=plugin_tl("Share"), command=lambda p=poi: show_share_popup(frame, p), width=7)
        sharebtn.grid(row=table_row, column=8, sticky="w", padx=(2,2))
        sharebtn.bind("<Button-3>", lambda e, p=poi, av=active_var: show_poi_context_menu(e, p, frame, av))

        def on_desc_change(*args, p=poi, v=desc_var, btn=savebtn):
            current = v.get()
            original = p.get("description", "")
            btn.config(state=('normal' if current != original else 'disabled'))

        desc_var.trace_add('write', lambda *args, p=poi, v=desc_var, btn=savebtn: on_desc_change(p=p, v=v, btn=btn))
        savebtn.config(command=lambda p=poi, v=desc_var, btn=savebtn: save_desc_obj(p, v, frame, btn))
        table_row += 1

    # ------ Grid column configuration for clean layout (only for table_frame) ------
    table_frame.grid_columnconfigure(0, minsize=22, weight=0)     # Active (very narrow)
    table_frame.grid_columnconfigure(1, minsize=15, weight=0)     # Copy system icon (very minimal)
    table_frame.grid_columnconfigure(2, minsize=120, weight=0)    # Body Name
    table_frame.grid_columnconfigure(3, minsize=84, weight=0)     # Latitude
    table_frame.grid_columnconfigure(4, minsize=100, weight=0)    # Longitude
    table_frame.grid_columnconfigure(5, minsize=210, weight=2)    # Description (wide & expands)
    table_frame.grid_columnconfigure(6, minsize=60, weight=0)     # Delete
    table_frame.grid_columnconfigure(7, minsize=70, weight=0)     # Save
    table_frame.grid_columnconfigure(8, minsize=70, weight=0)     # Share


def split_system_and_body(full_body_name):
    """
    Split a full body name into system and body parts.
    Body designation starts with either:
    - A single uppercase letter followed by space and digit (secondary star): "B 5 c", "C 3 a"
    - A single digit or digit sequence for planet around primary star: "1", "2 b", "5 c", "10"
    
    The key insight: Elite system names contain hyphens and can end with numbers like "d13-35",
    but body designations are ALWAYS standalone segments separated by spaces.
    System names never end with a single standalone digit/letter - they end with number-dash-number patterns.
    
    Examples:
    - "Orrere 2 b" -> ("Orrere", "2 b")
    - "Synuefe AA-P c22-7 5 c" -> ("Synuefe AA-P c22-7", "5 c")
    - "HIP 36601 C 3 a" -> ("HIP 36601", "C 3 a")
    - "Wredguia PI-B d13-35 1" -> ("Wredguia PI-B d13-35", "1")
    - "Outotz LS-K d8-3 B 5 c" -> ("Outotz LS-K d8-3", "B 5 c")
    """
    if not full_body_name:
        return "", ""
    
    # First, try to find space followed by single uppercase letter, then space, then digit
    # This is a secondary star designation (e.g., "B 5 c", "C 3 a")
    for i in range(len(full_body_name) - 3, 0, -1):  # -3 because we need "X Y" at minimum
        if full_body_name[i-1] == ' ':
            char_after_space = full_body_name[i]
            # Check if it's a single uppercase letter
            if char_after_space.isupper() and char_after_space.isalpha():
                # Check if next character is a space and the one after is a digit
                if i + 2 < len(full_body_name):
                    if full_body_name[i+1] == ' ' and full_body_name[i+2].isdigit():
                        system_name = full_body_name[:i-1]
                        body_part = full_body_name[i:]
                        return system_name, body_part
    
    # If no secondary star found, look for the LAST space followed by digit(s)
    # This handles primary star planets like "1", "2 b", "10 a"
    # We look from the end to find the rightmost space + digit combo
    parts = full_body_name.split(' ')
    if len(parts) >= 2:
        # Check if the last part or last two parts form a body designation
        last_part = parts[-1]
        
        # Check if last part starts with a digit (body designation)
        if last_part and last_part[0].isdigit():
            # This is the body designation
            body_part = ' '.join(parts[len(parts)-1:])
            system_name = ' '.join(parts[:len(parts)-1])
            return system_name, body_part
        
        # Check if last part is a single lowercase letter (moon) and second-to-last starts with digit
        if len(parts) >= 2 and len(last_part) == 1 and last_part.islower():
            second_last = parts[-2]
            if second_last and second_last[0].isdigit():
                # "2 b" pattern
                body_part = ' '.join(parts[len(parts)-2:])
                system_name = ' '.join(parts[:len(parts)-2])
                return system_name, body_part
    
    # If no valid split found, return full name as system
    return full_body_name, ""

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

def show_share_popup(parent, poi):
    """
    Show popup dialog with shareable URL and copy button
    """
    share_url = generate_share_url(poi)
    
    # Create popup window
    popup = tk.Toplevel(parent)
    popup.title(plugin_tl("Share POI"))
    popup.geometry(scale_geometry(500, 170))
    popup.resizable(False, False)
    popup.transient(parent)
    
    # Center popup
    popup.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (popup.winfo_width() // 2)
    y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (popup.winfo_height() // 2)
    popup.geometry(f"+{x}+{y}")
    
    # Label
    label = tk.Label(popup, text=plugin_tl("Copy this link to share the POI:"))
    label.pack(pady=(10, 5), padx=10)
    
    # URL input field
    url_var = tk.StringVar(value=share_url)
    url_entry = tk.Entry(popup, textvariable=url_var, width=60)
    url_entry.pack(pady=5, padx=10, fill=tk.X)
    url_entry.select_range(0, tk.END)
    url_entry.focus()
    
    # Copy button
    def copy_to_clipboard():
        popup.clipboard_clear()
        popup.clipboard_append(share_url)
        popup.destroy()
    
    copy_btn = tk.Button(popup, text=plugin_tl("Copy to clipboard"), command=copy_to_clipboard)
    copy_btn.pack(pady=10)
    
    # Close popup when clicking outside or pressing Escape
    def close_popup(event=None):
        popup.destroy()
    
    popup.bind("<Escape>", close_popup)
    popup.bind("<FocusOut>", lambda e: popup.after(100, lambda: popup.destroy() if not popup.focus_get() else None))
    
    popup.grab_set()

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
    global ALT_VAR, ROWS_VAR, LEFT_VAR, SHOW_GUI_INFO_VAR
    # Update active status for all flat POIs
    flat_pois = get_all_pois_flat(ALL_POIS)
    for i, var in enumerate(POI_VARS):
        if i < len(flat_pois):
            flat_pois[i]["active"] = var.get()
    config.set(ALT_KEY, 1 if ALT_VAR.get() else 0)
    config.set(ROWS_KEY, ROWS_VAR.get())
    config.set(LEFT_KEY, LEFT_VAR.get())
    config.set(SHOW_GUI_INFO_KEY, 1 if SHOW_GUI_INFO_VAR.get() else 0)
    overlay.set_overlay_settings(ROWS_VAR.get(), LEFT_VAR.get())
    save_pois()
    redraw_plugin_app()

def dashboard_entry(cmdr, is_beta, entry):
    global last_lat, last_lon, last_body, CURRENT_SYSTEM, OVERLAY_INFO_TEXT

    altitude = entry.get("Altitude") or 0
    lat = entry.get("Latitude")
    lon = entry.get("Longitude")
    bodyname = entry.get("BodyName")
    planet_radius = entry.get("PlanetRadius") or 1000000  # Default radius if missing
    
    if lat is not None and lon is not None and bodyname:
        prev_body = last_body
        last_lat, last_lon, last_body = lat, lon, bodyname
        body_changed = str(prev_body) != str(bodyname)
 
    # Only clear overlay if we're definitely not on a body anymore
    if bodyname is None and last_body:
        last_body = None
        OVERLAY_INFO_TEXT = ""
        overlay.clear_all_poi_rows()
        redraw_plugin_app()
        return
    
    # If we don't have coordinates, skip update
    if lat is None or lon is None or bodyname is None:
        OVERLAY_INFO_TEXT = ""
        return

    # Update overlay on EVERY dashboard update when we have coordinates
    visible_pois = [poi for poi in get_all_pois_flat(ALL_POIS) if poi.get("active", True) and get_full_body_name(poi) == bodyname]

    poi_texts = []
    for poi in visible_pois:
        poi_lat = poi.get("lat")
        poi_lon = poi.get("lon")
        poi_desc = poi.get("description", "")

        distance, bearing = calculate_bearing_and_distance(
            lat, lon,
            poi_lat, poi_lon,
            planet_radius,
            altitude, 0,  # alt1 = current, alt2 = 0
            calc_with_altitude=config.get(ALT_KEY, False)
        )

        if not poi_desc:
            if lat is not None and lon is not None:
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
        poi_texts.append(f"{round(bearing)}° / {round(show_dist, 2)}{unit} {poi_desc}")
    
    if poi_texts:
        overlay.show_poi_rows(poi_texts)
        # Store overlay info for GUI display - limit to max rows
        max_rows = config.get_int(ROWS_KEY)
        gui_poi_texts = poi_texts[:max_rows] if max_rows > 0 and len(poi_texts) > max_rows else poi_texts
        OVERLAY_INFO_TEXT = "\n".join(gui_poi_texts)
        # If body changed, redraw entire GUI to show directions
        if body_changed:
            redraw_plugin_app()
        # Otherwise just update the label directly if it exists
        elif OVERLAY_INFO_LABEL and config.get_int(SHOW_GUI_INFO_KEY):
            try:
                OVERLAY_INFO_LABEL.config(text=OVERLAY_INFO_TEXT)
            except:
                pass  # Label might not exist anymore
    else:
        overlay.clear_all_poi_rows()
        OVERLAY_INFO_TEXT = ""
        # If body changed, redraw GUI
        if body_changed:
            redraw_plugin_app()
        elif OVERLAY_INFO_LABEL:
            try:
                OVERLAY_INFO_LABEL.config(text="")
            except:
                pass


def calculate_bearing_and_distance(lat1, lon1, lat2, lon2, planet_radius_m, alt1=0, alt2=0, calc_with_altitude=False):
    import math
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    surface_distance = planet_radius_m * c

    if calc_with_altitude:
        delta_alt = (alt2 - alt1)
        distance = math.sqrt(surface_distance**2 + delta_alt**2)
    else:
        distance = surface_distance

    y = math.sin(dlambda) * math.cos(phi2)
    x = math.cos(phi1)*math.sin(phi2) - math.sin(phi1)*math.cos(phi2)*math.cos(dlambda)
    bearing = (math.degrees(math.atan2(y, x)) + 360) % 360
    return distance, bearing
