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

POI_FILE = os.path.join(os.path.dirname(__file__), "poi.json")
ALL_POIS = []
POI_VARS = []

ALT_KEY = "planetpoi_calc_with_altitude"
ROWS_KEY = "planetpoi_max_overlay_rows"
LEFT_KEY = "planetpoi_overlay_leftmargin"

ALT_VAR = None
ROWS_VAR = None
LEFT_VAR = None

CURRENT_SYSTEM = None

# Latest position for "Save current location"
last_lat, last_lon, last_body = None, None, None

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

def load_pois():
    global ALL_POIS
    if os.path.isfile(POI_FILE):
        with open(POI_FILE, "r", encoding="utf8") as f:
            ALL_POIS = json.load(f)
    else:
        ALL_POIS = []

def save_pois():
    global ALL_POIS
    print("saving pois")
    with open(POI_FILE, "w", encoding="utf8") as f:
        json.dump(ALL_POIS, f, indent=2)

def plugin_start3(plugin_dir: str) -> str:
    global ALT_VAR, ROWS_VAR, LEFT_VAR, ALL_POIS, CURRENT_SYSTEM, last_lat, last_lon, last_body
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
   
    load_pois()
    overlay.set_overlay_settings(ROWS_VAR.get(), LEFT_VAR.get())
    
    # ============== SIMULATION - HARDCODED VALUES ==============
    # Comment out these lines to disable simulation
    #CURRENT_SYSTEM = "HIP 36601"
    #last_body = "HIP 36601 C 3 b"
    #last_lat = -62.5  # Same as POI "Crystalline shards Tellerium"
    #last_lon = -127.2
    print(f"PPOI SIMULATION: System={CURRENT_SYSTEM}, Body={last_body}, Lat={last_lat}, Lon={last_lon}")
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
        dialog.destroy()
        redraw_plugin_app()
    
    tk.Button(button_frame, text="Close", command=close_and_refresh, width=10).pack()
    
    # Create container for scrollable frame (takes remaining space)
    container_frame = tk.Frame(dialog, bg="#ffffff")
    container_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(15, 5))
    
    # Use plugin_prefs to create properly themed frame, then reparent it
    prefs_frame = plugin_prefs(container_frame, None, False)
    prefs_frame.pack(fill=tk.BOTH, expand=True)

def show_add_poi_dialog(parent_frame, prefill_body=None):
    """Show dialog to add a new POI"""
    dialog = tk.Toplevel(parent_frame)
    dialog.title("Add New POI")
    dialog.geometry(scale_geometry(480, 360))
    dialog.transient(parent_frame)
    dialog.grab_set()
    
    # Center the dialog
    dialog.update_idletasks()
    x = parent_frame.winfo_rootx() + (parent_frame.winfo_width() // 2) - (dialog.winfo_width() // 2)
    y = parent_frame.winfo_rooty() + (parent_frame.winfo_height() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")
    
    # Determine auto-fill values
    auto_system = CURRENT_SYSTEM or ""
    auto_body = ""
    auto_lat = ""
    auto_lon = ""
    
    # If we have a current body position, extract system and body parts
    if last_body and last_lat is not None and last_lon is not None:
        # last_body is full name like "HIP 87621 2 a"
        # Try to extract system and body
        if auto_system and last_body.startswith(auto_system):
            # Body is everything after the system name
            auto_body = last_body[len(auto_system):].strip()
            auto_lat = str(last_lat)
            auto_lon = str(last_lon)
    
    # If prefill_body provided (from button click), use it to determine system/body
    if prefill_body:
        if auto_system and prefill_body.startswith(auto_system):
            auto_body = prefill_body[len(auto_system):].strip()
        else:
            # If prefill_body doesn't match current system, just use it as-is in system field
            auto_system = prefill_body
            auto_body = ""
    
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
    desc_var = tk.StringVar()
    desc_entry = tk.Entry(dialog, textvariable=desc_var, width=30)
    desc_entry.grid(row=row, column=1, padx=(10, 20), pady=5, sticky="ew")
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
                # Extract system and body from full body name using intelligent split
                full_body = poi_data.get('body', '')
                system_name, body_part = split_system_and_body(full_body)
                
                # Fill in all fields
                system_entry.set_text(system_name, placeholder_style=False)
                body_var.set(body_part)
                lat_var.set(str(poi_data.get('lat', '')))
                lon_var.set(str(poi_data.get('lon', '')))
                desc_var.set(poi_data.get('description', ''))
                
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
                    
                    # Extract system and body from full body name using intelligent split
                    full_body = poi_data.get('body', '')
                    system_name, body_part = split_system_and_body(full_body)
                    
                    # Fill in all fields
                    system_entry.set_text(system_name, placeholder_style=False)
                    body_var.set(body_part)
                    lat_var.set(str(poi_data.get('lat', '')))
                    lon_var.set(str(poi_data.get('lon', '')))
                    desc_var.set(poi_data.get('description', ''))
                    
                    status_label.config(text="✓ Auto-loaded from shared link", fg="green")
        except Exception:
            pass
    
    # Bind paste event to all entry fields
    system_entry.bind('<Control-v>', on_paste)
    body_entry.bind('<Control-v>', on_paste)
    lat_entry.bind('<Control-v>', on_paste)
    lon_entry.bind('<Control-v>', on_paste)
    desc_entry.bind('<Control-v>', on_paste)
    
    def save_and_close():
        system = system_var.get().strip()
        body = body_var.get().strip()
        
        if not system:
            status_label.config(text="System name is required!", fg="red")
            return
        
        # Format body name with proper spacing and capitalization
        if body:
            formatted_body = format_body_name(body)
            full_body = f"{system} {formatted_body}"
        else:
            full_body = system
        
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
        new_poi = {
            "body": full_body,
            "lat": lat,
            "lon": lon,
            "description": desc,
            "active": True
        }
        ALL_POIS.append(new_poi)
        print(f"PPOI: Added new POI: {new_poi}")
        print(f"PPOI: Total POIs now: {len(ALL_POIS)}")
        save_pois()
        redraw_plugin_app()
        dialog.destroy()
    
    # Buttons aligned to the right, same as inputs and paste button
    button_frame = tk.Frame(dialog)
    button_frame.grid(row=row, column=1, sticky="e", padx=(10, 20), pady=(5, 20))
    
    tk.Button(button_frame, text="Cancel", command=dialog.destroy, width=10).pack(side="left", padx=(0, 5))
    tk.Button(button_frame, text="Save", command=save_and_close, width=10).pack(side="left")
    
    # Focus on body name if system is pre-filled, otherwise focus on system
    if auto_system:
        body_entry.focus()
    else:
        system_entry.focus()

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
    global CURRENT_SYSTEM
    
    if (entry['event'] in ['FSDJump','StartUp'] and entry.get('StarSystem')):
        print(f"PPOI: Arriving at {entry['StarSystem']}")
        CURRENT_SYSTEM = entry['StarSystem']
        redraw_plugin_app()      
    if not CURRENT_SYSTEM and entry.get('StarSystem'):
        CURRENT_SYSTEM = entry['StarSystem']
        redraw_plugin_app()

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
            matching_system_pois = [poi for poi in ALL_POIS if poi.get("body", "").startswith(CURRENT_SYSTEM)]
        
        if matching_system_pois:
            header_frame = tk.Frame(frame)
            header_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=2, pady=2)
            header_frame.grid_columnconfigure(0, weight=1)
            
            system_label = tk.Label(header_frame, text=plugin_tl("PPOI: Poi's in {system}").format(system=CURRENT_SYSTEM))
            system_label.grid(row=0, column=0, sticky="w")
            theme.update(system_label)
            tk.Button(header_frame, text="➕", command=lambda: show_add_poi_dialog(frame, CURRENT_SYSTEM), 
                     width=3, height=1, borderwidth=0, highlightthickness=0, relief="flat").grid(row=0, column=1, sticky="e", padx=(0, 2))
            tk.Button(header_frame, text="🔧", command=lambda: show_config_dialog(frame), 
                     width=3, height=1, borderwidth=0, highlightthickness=0, relief="flat").grid(row=0, column=2, sticky="e")
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
                
                poi_desc = poi.get("body", "")[len(CURRENT_SYSTEM) +1 :] + " - " + desc
                poi_label = tk.Label(
                    frame,
                    text=poi_desc,
                    font=small_font
                )
                poi_label.grid(row=row, column=0, sticky="w", padx=2, pady=0)
                theme.update(poi_label)
                row += 1
        else:    
            header_frame = tk.Frame(frame)
            header_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=2, pady=2)
            header_frame.grid_columnconfigure(0, weight=1)
            
            no_system_label = tk.Label(header_frame, text=plugin_tl("PPOI: No poi's in system"))
            no_system_label.grid(row=0, column=0, sticky="w")
            theme.update(no_system_label)
            tk.Button(header_frame, text="➕", command=lambda: show_add_poi_dialog(frame, CURRENT_SYSTEM), 
                     width=3, height=1, borderwidth=0, highlightthickness=0, relief="flat").grid(row=0, column=1, sticky="e", padx=(0, 2))
            tk.Button(header_frame, text="🔧", command=lambda: show_config_dialog(frame), 
                     width=3, height=1, borderwidth=0, highlightthickness=0, relief="flat").grid(row=0, column=2, sticky="e")
            theme.update(header_frame)
        
        return

    matching_pois = [poi for poi in ALL_POIS if poi.get("body") == current_body]
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
    
    tk.Button(header_frame, text="➕", command=lambda: show_add_poi_dialog(frame, current_body), 
             width=3, height=1, borderwidth=0, highlightthickness=0, relief="flat").grid(row=0, column=1, sticky="e", padx=(0, 2))
    tk.Button(header_frame, text="🔧", command=lambda: show_config_dialog(frame), 
             width=3, height=1, borderwidth=0, highlightthickness=0, relief="flat").grid(row=0, column=2, sticky="e")
    theme.update(header_frame)
    row += 1

    for idx, poi in enumerate(matching_pois):
        active_var = tk.BooleanVar(value=poi.get("active", True))
        cb = tk.Checkbutton(
            frame,
            variable=active_var
        )
        cb.grid(row=row, column=0, sticky="w", padx=2, pady=0)
        theme.update(cb)

        desc = poi.get("description", "")
        if not desc:
            lat = poi.get("lat")
            lon = poi.get("lon")
            if lat is not None and lon is not None:
                desc = f"{lat:.4f}, {lon:.4f}"
            else:
                desc = "(No description)"
        desc_label = tk.Label(
            frame,
            text=desc,
            font=small_font
        )
        desc_label.grid(row=row, column=1, sticky="w", padx=2, pady=0)
        theme.update(desc_label)

        def on_toggle(i=idx, v=active_var):
            matching_pois[i]["active"] = v.get()
            save_pois()

        active_var.trace_add('write', lambda *args, i=idx, v=active_var: on_toggle(i, v))
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
    global ALT_VAR, ROWS_VAR, LEFT_VAR,POI_VARS
    row = 0

    # Headers on same row
    nb.Label(frame, text=plugin_tl("Calculate distance with altitude")).grid(row=row, column=0, columnspan=2,sticky="w", padx=(0, 8))
    nb.Label(frame, text=plugin_tl("Max overlay rows")).grid(row=row, column=2, sticky="w", padx=(0, 8))
    nb.Label(frame, text=plugin_tl("Overlay left margin (pixels)")).grid(row=row, column=3,columnspan=3, sticky="w")
    row += 1

    # Widgets on same row
    cb = nb.Checkbutton(frame, variable=ALT_VAR, width=2)
    cb.grid(row=row, column=0, columnspan=2,sticky="w", padx=(0, 4))
    rows_entry = nb.EntryMenu(frame, textvariable=ROWS_VAR, width=4)
    rows_entry.grid(row=row, column=2, sticky="w", padx=(0, 8))
    left_entry = nb.EntryMenu(frame, textvariable=LEFT_VAR, width=6)
    left_entry.grid(row=row, column=3,columnspan=3, sticky="w")
    row += 1

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
    for col, header in enumerate(headers):
        # No padding for copy icon column
        padding = 0 if col == 1 else 2
        nb.Label(table_frame, text=header, font=('TkDefaultFont', 9, 'bold')).grid(row=table_row, column=col, padx=padding, pady=2, sticky="w")
    table_row += 1

    POI_VARS = []
    for idx, poi in enumerate(ALL_POIS):
        active_var = tk.BooleanVar(value=poi.get("active", True))
        cb = nb.Checkbutton(table_frame, variable=active_var, width=2)
        try:
            cb.configure(background="white")
        except:
            pass  # If background can't be set, continue anyway
        cb.grid(row=table_row, column=0, sticky="w", padx=(0, 0))
        POI_VARS.append(active_var)

        # Copy system name button (using Label for minimal space)
        def copy_system(body_name):
            system, _ = split_system_and_body(body_name)
            table_frame.clipboard_clear()
            table_frame.clipboard_append(system)
        
        copy_label = nb.Label(table_frame, text="📋", cursor="hand2")
        copy_label.grid(row=table_row, column=1, sticky="e", padx=(0, 2))
        copy_label.bind("<Button-1>", lambda e, b=poi.get("body", ""): copy_system(b))

        nb.Label(table_frame, text=poi.get("body", ""), anchor="w").grid(row=table_row, column=2, padx=2, pady=2, sticky="w")
        nb.Label(table_frame, text=poi.get("lat", ""), anchor="w").grid(row=table_row, column=3, padx=2, pady=2, sticky="w")
        nb.Label(table_frame, text=poi.get("lon", ""), anchor="w").grid(row=table_row, column=4, padx=2, pady=2, sticky="w")

        desc_var = tk.StringVar(value=poi.get("description", ""))
        desc_entry = nb.EntryMenu(table_frame, textvariable=desc_var, width=28)
        desc_entry.grid(row=table_row, column=5, sticky="w", padx=(2,2))

        delbtn = nb.Button(table_frame, text=plugin_tl("Delete"), command=lambda i=idx: remove_poi(i, frame), width=7)
        delbtn.grid(row=table_row, column=6, sticky="w", padx=(2,2))

        savebtn = nb.Button(table_frame, text=plugin_tl("Save"), state='disabled', width=7)
        savebtn.grid(row=table_row, column=7, sticky="w", padx=(2,2))

        sharebtn = nb.Button(table_frame, text=plugin_tl("Share"), command=lambda i=idx: show_share_popup(frame, i), width=7)
        sharebtn.grid(row=table_row, column=8, sticky="w", padx=(2,2))

        def on_desc_change(*args, i=idx, v=desc_var, btn=savebtn):
            current = v.get()
            original = ALL_POIS[i].get("description", "")
            btn.config(state=('normal' if current != original else 'disabled'))

        desc_var.trace_add('write', lambda *args, i=idx, v=desc_var, btn=savebtn: on_desc_change(i=i, v=v, btn=btn))
        savebtn.config(command=lambda i=idx, v=desc_var, btn=savebtn: save_desc(i, v, frame, btn))
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
    Body designation always starts with a digit (planet number).
    Examples:
    - "Orrere 2 b" -> ("Orrere", "2 b")
    - "Synuefe AA-P c22-7 5 c" -> ("Synuefe AA-P c22-7", "5 c")
    - "HIP 36601 C 3 a" -> ("HIP 36601", "C 3 a")
    """
    if not full_body_name:
        return "", ""
    
    # Find the last space followed by a digit or uppercase letter (body designation start)
    # Body can start with: digit (planet around primary star) or uppercase letter (secondary star)
    for i in range(len(full_body_name) - 1, 0, -1):
        if full_body_name[i-1] == ' ':
            char_after_space = full_body_name[i]
            # Body designation starts with digit OR uppercase letter
            if char_after_space.isdigit() or (char_after_space.isupper() and char_after_space.isalpha()):
                system_name = full_body_name[:i-1]
                body_part = full_body_name[i:]
                return system_name, body_part
    
    # If no valid split found, return full name as system
    return full_body_name, ""

def split_system_and_body(full_body_name):
    """
    Split a full body name into system and body parts.
    Body designation starts with either:
    - A single uppercase letter followed by space and digit (secondary star): "B 5 c", "C 3 a"
    - A digit (planet around primary star): "2 b", "5 c"
    
    Examples:
    - "Orrere 2 b" -> ("Orrere", "2 b")
    - "Synuefe AA-P c22-7 5 c" -> ("Synuefe AA-P c22-7", "5 c")
    - "HIP 36601 C 3 a" -> ("HIP 36601", "C 3 a")
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
    
    # If no secondary star found, look for space followed by digit (primary star planet)
    for i in range(len(full_body_name) - 1, 0, -1):
        if full_body_name[i-1] == ' ':
            char_after_space = full_body_name[i]
            if char_after_space.isdigit():
                system_name = full_body_name[:i-1]
                body_part = full_body_name[i:]
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
        if 'body' not in poi_data or 'lat' not in poi_data or 'lon' not in poi_data:
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

def show_share_popup(parent, idx):
    """
    Show popup dialog with shareable URL and copy button
    """
    poi = ALL_POIS[idx]
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

def redraw_prefs(frame):
    for widget in frame.winfo_children():
        widget.destroy()
    build_plugin_ui(frame)

def remove_poi(idx, frame):
    ALL_POIS.pop(idx)
    save_pois()
    redraw_prefs(frame)

def save_desc(idx, desc_var, frame, savebtn):
    ALL_POIS[idx]["description"] = desc_var.get()
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
    ALL_POIS.append({
        "body": body,
        "lat": lat,
        "lon": lon,
        "description": desc,
        "active": True
    })
    save_pois()
    redraw_prefs(frame)

def save_current_poi(frame):
    if last_lat is not None and last_lon is not None and last_body:
        ALL_POIS.append({
            "body": last_body,
            "lat": last_lat,
            "lon": last_lon,
            "description": "",
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
    global ALT_VAR, ROWS_VAR, LEFT_VAR
    for i, var in enumerate(POI_VARS):
        ALL_POIS[i]["active"] = var.get()
    config.set(ALT_KEY, 1 if ALT_VAR.get() else 0)
    config.set(ROWS_KEY, ROWS_VAR.get())
    config.set(LEFT_KEY, LEFT_VAR.get())
    overlay.set_overlay_settings(ROWS_VAR.get(), LEFT_VAR.get())
    save_pois()
    redraw_plugin_app()

def dashboard_entry(cmdr, is_beta, entry):
    global last_lat, last_lon, last_body,CURRENT_SYSTEM

    altitude = entry.get("Altitude") or 0
    lat = entry.get("Latitude")
    lon = entry.get("Longitude")
    bodyname = entry.get("BodyName")
    planet_radius = entry.get("PlanetRadius")
    print(f"dash:{entry}")
    if lat is not None and lon is not None and bodyname:
        prev_body = last_body
        last_lat, last_lon, last_body = lat, lon, bodyname
        if str(prev_body) != str(bodyname):
            redraw_plugin_app()
 
    if bodyname is None and last_body:
        last_body = None
        overlay.clear_all_poi_rows()
        redraw_plugin_app()
        return

    visible_pois = [poi for poi in ALL_POIS if poi.get("active", True) and poi.get("body") == bodyname]

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
    else:
        overlay.clear_all_poi_rows()


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
