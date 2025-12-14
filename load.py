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

# latest position för "Save current location"
last_lat, last_lon, last_body = None, None, None

def format_body_name(body_name):
    """
    Format body name according to Elite Dangerous naming rules.
    Examples: 
    - "c1ab" -> "C 1 a b"
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
            # Add space before character, lowercase if letter
            result.append(" ")
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
    global ALT_VAR, ROWS_VAR, LEFT_VAR, ALL_POIS
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
    return "PlanetPOI"


def show_add_poi_dialog(parent_frame, prefill_body=None):
    """Show dialog to add a new POI"""
    dialog = tk.Toplevel(parent_frame)
    dialog.title("Add New POI")
    dialog.geometry("480x360")
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
    
    def save_and_close():
        system = system_var.get().strip()
        body = body_var.get().strip()
        
        if not system:
            status_label.config(text="System name is required!")
            return
        
        # Format body name with proper spacing and capitalization
        if body:
            formatted_body = format_body_name(body)
            full_body = f"{system} {formatted_body}"
        else:
            full_body = system
            
        try:
            lat = float(lat_var.get().replace(",", "."))
            lon = float(lon_var.get().replace(",", "."))
        except ValueError:
            status_label.config(text="Invalid latitude or longitude!")
            return
        
        desc = desc_var.get().strip()
        ALL_POIS.append({
            "body": full_body,
            "lat": lat,
            "lon": lon,
            "description": desc,
            "active": True
        })
        save_pois()
        dialog.destroy()
        redraw_plugin_app()
    
    # Buttons aligned to the right
    button_frame = tk.Frame(dialog)
    button_frame.grid(row=row, column=1, sticky="e", padx=(10, 20), pady=(5, 15))
    
    tk.Button(button_frame, text="Cancel", command=dialog.destroy, width=10).pack(side="left", padx=(0, 5))
    tk.Button(button_frame, text="Save", command=save_and_close, width=10).pack(side="left")
    
    # Focus on body name if system is pre-filled, otherwise focus on system
    if auto_system:
        body_entry.focus()
    else:
        system_entry.focus()

def redraw_plugin_app():
    global PLUGIN_FRAME
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
    
    frame.grid_columnconfigure(0, weight=1)
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
            
            tk.Label(header_frame, text=plugin_tl(f"PPOI: Poi's in {CURRENT_SYSTEM}")).grid(row=0, column=0, sticky="w")
            tk.Button(header_frame, text="➕", command=lambda: show_add_poi_dialog(frame, CURRENT_SYSTEM), 
                     width=3, height=1, borderwidth=0, highlightthickness=0, relief="flat").grid(row=0, column=1, sticky="e")
            theme.update(header_frame)  # Apply theme to header_frame and its children
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
                tk.Label(
                    frame,
                    text=poi_desc,
                    font=small_font
                ).grid(row=row, column=0, sticky="w", padx=2, pady=0)
                row += 1
        else:    
            header_frame = tk.Frame(frame)
            header_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=2, pady=2)
            header_frame.grid_columnconfigure(0, weight=1)
            
            tk.Label(header_frame, text=plugin_tl(f"PPOI: No poi's in system")).grid(row=0, column=0, sticky="w")
            tk.Button(header_frame, text="➕", command=lambda: show_add_poi_dialog(frame, CURRENT_SYSTEM), 
                     width=3, height=1, borderwidth=0, highlightthickness=0, relief="flat").grid(row=0, column=1, sticky="e")
            theme.update(header_frame)  # Apply theme to header_frame and its children
        
        return

    matching_pois = [poi for poi in ALL_POIS if poi.get("body") == current_body]

    # Header with add button
    header_frame = tk.Frame(frame)
    header_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=2, pady=2)
    header_frame.grid_columnconfigure(0, weight=1)
    
    tk.Label(
        header_frame,
        text=f"PPOI: {current_body}",
        font=('TkDefaultFont', 10, 'bold')
    ).grid(row=0, column=0, sticky="w")
    
    tk.Button(header_frame, text="➕", command=lambda: show_add_poi_dialog(frame, current_body), 
             width=3, height=1, borderwidth=0, highlightthickness=0, relief="flat").grid(row=0, column=1, sticky="e")
    theme.update(header_frame)  # Apply theme to header_frame and its children
    row += 1

    for idx, poi in enumerate(matching_pois):
        active_var = tk.BooleanVar(value=poi.get("active", True))
        cb = tk.Checkbutton(
            frame,
            variable=active_var
        )
        cb.grid(row=row, column=0, sticky="w", padx=2, pady=0)

        desc = poi.get("description", "")
        if not desc:
            lat = poi.get("lat")
            lon = poi.get("lon")
            if lat is not None and lon is not None:
                desc = f"{lat:.4f}, {lon:.4f}"
            else:
                desc = "(No description)"
        tk.Label(
            frame,
            text=desc,
            font=small_font
        ).grid(row=row, column=1, sticky="w", padx=2, pady=0)

        def on_toggle(i=idx, v=active_var):
            matching_pois[i]["active"] = v.get()
            save_pois()

        active_var.trace_add('write', lambda *args, i=idx, v=active_var: on_toggle(i, v))
        row += 1

    if not matching_pois:
        tk.Label(
            frame,
            text=plugin_tl("PPOI: No POIs for this body")
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=2)


def plugin_app(parent, cmdr=None, is_beta=None):
    """Create the persistent plugin frame and return it."""
    global PLUGIN_PARENT, PLUGIN_FRAME
    PLUGIN_PARENT = parent
    
    # Create persistent frame - use tk.Frame as root, with tk widgets inside
    PLUGIN_FRAME = tk.Frame(parent)
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

    canvas = tk.Canvas(parent, borderwidth=0, background=bg)
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

    # Rubriker på samma rad
    nb.Label(frame, text=plugin_tl("Calculate distance with altitude")).grid(row=row, column=0, columnspan=2,sticky="w", padx=(0, 8))
    nb.Label(frame, text=plugin_tl("Max overlay rows")).grid(row=row, column=2, sticky="w", padx=(0, 8))
    nb.Label(frame, text=plugin_tl("Overlay left margin (pixels)")).grid(row=row, column=3,columnspan=3, sticky="w")
    row += 1

    # Widgets på samma rad
    cb = nb.Checkbutton(frame, variable=ALT_VAR, width=2)
    cb.grid(row=row, column=0, columnspan=2,sticky="w", padx=(0, 8))
    rows_entry = nb.EntryMenu(frame, textvariable=ROWS_VAR, width=4)
    rows_entry.grid(row=row, column=2, sticky="w", padx=(0, 8))
    left_entry = nb.EntryMenu(frame, textvariable=LEFT_VAR, width=6)
    left_entry.grid(row=row, column=3,columnspan=3, sticky="w")
    row += 1

    sep = ttk.Separator(frame, orient='horizontal')
    sep.grid(row=row, column=0, columnspan=7, sticky="ew", pady=8)
    row += 1

    nb.Label(frame, text=plugin_tl("Saved POIs"), font=('TkDefaultFont', 10, 'bold')).grid(row=row, column=0, columnspan=7, sticky="w")
    row += 1

    headers = [
        plugin_tl("Active"),
        plugin_tl("Body Name"),
        plugin_tl("Latitude"),
        plugin_tl("Longitude"),
        plugin_tl("Description"),
        plugin_tl("Delete"),
        plugin_tl("Save")
    ]
    for col, header in enumerate(headers):
        nb.Label(frame, text=header, font=('TkDefaultFont', 9, 'bold')).grid(row=row, column=col, padx=2, pady=2, sticky="w")
    row += 1

    POI_VARS = []
    for idx, poi in enumerate(ALL_POIS):
        active_var = tk.BooleanVar(value=poi.get("active", True))
        cb = nb.Checkbutton(frame, variable=active_var, width=2)
        cb.grid(row=row, column=0, sticky="w", padx=(0, 0))
        POI_VARS.append(active_var)

        nb.Label(frame, text=poi.get("body", ""), anchor="w").grid(row=row, column=1, padx=2, pady=2, sticky="w")
        nb.Label(frame, text=poi.get("lat", ""), anchor="w").grid(row=row, column=2, padx=2, pady=2, sticky="w")
        nb.Label(frame, text=poi.get("lon", ""), anchor="w").grid(row=row, column=3, padx=2, pady=2, sticky="w")

        desc_var = tk.StringVar(value=poi.get("description", ""))
        desc_entry = nb.EntryMenu(frame, textvariable=desc_var, width=28)
        desc_entry.grid(row=row, column=4, sticky="w", padx=(2,2))

        delbtn = nb.Button(frame, text=plugin_tl("Delete"), command=lambda i=idx: remove_poi(i, frame), width=7)
        delbtn.grid(row=row, column=5, sticky="w", padx=(2,2))

        savebtn = nb.Button(frame, text=plugin_tl("Save"), state='disabled', width=7)
        savebtn.grid(row=row, column=6, sticky="w", padx=(2,2))

        def on_desc_change(*args, i=idx, v=desc_var, btn=savebtn):
            current = v.get()
            original = ALL_POIS[i].get("description", "")
            btn.config(state=('normal' if current != original else 'disabled'))

        desc_var.trace_add('write', lambda *args, i=idx, v=desc_var, btn=savebtn: on_desc_change(i=i, v=v, btn=btn))
        savebtn.config(command=lambda i=idx, v=desc_var, btn=savebtn: save_desc(i, v, frame, btn))
        row += 1

    # ------ Grid-kolumnjustering för snygg layout ------
    frame.grid_columnconfigure(0, minsize=22, weight=0)     # Active (supersmal)
    frame.grid_columnconfigure(1, minsize=120, weight=0)    # Body Name
    frame.grid_columnconfigure(2, minsize=84, weight=0)     # Latitude
    frame.grid_columnconfigure(3, minsize=100, weight=0)    # Longitude
    frame.grid_columnconfigure(4, minsize=210, weight=2)    # Description (bred & expanderar)
    frame.grid_columnconfigure(5, minsize=60, weight=0)     # Delete
    frame.grid_columnconfigure(6, minsize=70, weight=0)     # Save


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
