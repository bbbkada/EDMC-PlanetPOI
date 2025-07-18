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

plugin_tl = functools.partial(l10n.translations.tl, context=__file__)

PLUGIN_PARENT = None

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
    try:
        alt_val = config.get_int(ALT_KEY)
    except Exception:
        alt_val = 0
    ALT_VAR = tk.BooleanVar(value=bool(alt_val))

    try:
        rows_val = config.get_int(ROWS_KEY)
    except Exception:
        rows_val = 10
    ROWS_VAR = tk.IntVar(value=rows_val)

    try:
        left_val = config.get_int(LEFT_KEY)
    except Exception:
        left_val = 500
    LEFT_VAR = tk.IntVar(value=left_val)
   
    load_pois()
    overlay.set_overlay_settings(ROWS_VAR.get(), LEFT_VAR.get())
    return "PlanetPOI"


def redraw_plugin_app():
    global PLUGIN_PARENT
    if PLUGIN_PARENT:
        try:
            for widget in PLUGIN_PARENT.winfo_children():
                widget.destroy()
            plugin_app(PLUGIN_PARENT)
        except Exception as ex:
            print("PlanetPOI: redraw_plugin_app failed (parent destroyed?):", ex)
            PLUGIN_PARENT = None

def journal_entry(cmdr, is_beta, system, station, entry, state):
    global CURRENT_SYSTEM
    
    if (entry['event'] in ['FSDJump','StartUp'] and entry.get('StarSystem')):
        print(f"PPOI: Arriving at {entry['StarSystem']}")
        CURRENT_SYSTEM = entry['StarSystem']
        redraw_plugin_app()      
    if not CURRENT_SYSTEM and entry.get('StarSystem'):
        CURRENT_SYSTEM = entry['StarSystem']
        redraw_plugin_app()

def plugin_app(parent, cmdr=None, is_beta=None):
    global last_body, PLUGIN_PARENT
    PLUGIN_PARENT = parent
    matching_system_pois = None
    
    # Liten font för POI-listan
    small_font = tkfont.Font(size=9)  # Justera till 8 eller 10 vid behov

    parent.grid_columnconfigure(0, weight=1)
        
    frame = tk.Frame(parent, highlightthickness=2)
    frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
    frame.grid_columnconfigure(1, weight=1)
    row = 0

    print("plugin_app last_body:", last_body)
    current_body = last_body

    if not current_body:
        if CURRENT_SYSTEM:
            matching_system_pois = [poi for poi in ALL_POIS if poi.get("body", "").startswith(CURRENT_SYSTEM)]
        
        if matching_system_pois:
            tk.Label(frame, text=plugin_tl(f"PPOI: Poi's in {CURRENT_SYSTEM}")).grid(row=row, column=0, sticky="w",padx=2, pady=2)
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
            tk.Label(frame, text=plugin_tl(f"PPOI: No poi's in system")).grid(row=row, column=0, sticky="w")
        
        theme.update(frame)
        theme.update(parent)
        return frame

    matching_pois = [poi for poi in ALL_POIS if poi.get("body") == current_body]

    # Rubrik
    tk.Label(
        frame,
        text=f"PPOI: {current_body}",
        font=('TkDefaultFont', 10, 'bold')
    ).grid(row=row, column=0, columnspan=2, sticky="w", padx=2, pady=2)
    row += 1

    for idx, poi in enumerate(matching_pois):
        active_var = tk.BooleanVar(value=poi.get("active", True))
        cb = tk.Checkbutton(
            frame,
            variable=active_var,
            font=small_font,
            height=1,
            padx=0,
            pady=0,
            borderwidth=0
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
            print("matching_pois id:", id(matching_pois[i]))
            for poi in ALL_POIS:
                print("ALL_POIS id:", id(poi))
            matching_pois[i]["active"] = v.get()
            save_pois()
            # overlay.show_poi_rows()

        active_var.trace_add('write', lambda *args, i=idx, v=active_var: on_toggle(i, v))
        row += 1

    if not matching_pois:
        tk.Label(
            frame,
            text=plugin_tl("PPOI: No POIs for this body")
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=2)

    theme.update(frame)
    theme.update(parent)
    return frame



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

    sep = ttk.Separator(frame, orient='horizontal')
    sep.grid(row=row, column=0, columnspan=7, sticky="ew", pady=8)
    row += 1

    nb.Label(frame, text=plugin_tl("Add new manual POI:"), font=('TkDefaultFont', 10, 'bold')).grid(row=row, column=0, columnspan=7, sticky="w")
    row += 1

    body_entry = nb.EntryMenu(frame, width=8)
    body_entry.grid(row=row, column=0, sticky="w", padx=(2,2))
    lat_entry = nb.EntryMenu(frame, width=16)
    lat_entry.grid(row=row, column=1, sticky="w", padx=(2,2))
    lon_entry = nb.EntryMenu(frame, width=16)
    lon_entry.grid(row=row, column=2, sticky="w", padx=(2,2))
    desc_entry = nb.EntryMenu(frame, width=28)
    desc_entry.grid(row=row, column=3, sticky="w", padx=(2,2))

    addbtn = nb.Button(
        frame, text=plugin_tl("Add"),
        command=lambda: add_manual_poi(body_entry, lat_entry, lon_entry, desc_entry, frame), width=7
    )
    addbtn.grid(row=row, column=4, columnspan=2,sticky="w", padx=(2,2))

    nb.Label(frame, text=plugin_tl("Body Name")).grid(row=row+1, column=0, sticky="w")
    nb.Label(frame, text=plugin_tl("Latitude")).grid(row=row+1, column=1, sticky="w")
    nb.Label(frame, text=plugin_tl("Longitude")).grid(row=row+1, column=2, sticky="w")
    nb.Label(frame, text=plugin_tl("Description")).grid(row=row+1, column=3, columnspan=3,sticky="w")

    row += 2

    # ----------- Save current position-rad, divider och rubrik -----------
    global last_lat, last_lon, last_body
    if last_lat is not None and last_lon is not None and last_body:
        sep2 = ttk.Separator(frame, orient='horizontal')
        sep2.grid(row=row, column=0, columnspan=7, sticky="ew", pady=(16, 2))
        row += 1

        nb.Label(
            frame,
            text=plugin_tl("Save current position") +
                 f" ({plugin_tl('Current')}: {last_body} {round(last_lat,5)}, {round(last_lon,5)})",
            font=('TkDefaultFont', 10, 'bold')
        ).grid(row=row, column=0, columnspan=7, sticky="w")
        row += 1

        savebtn = nb.Button(
            frame, text=plugin_tl("Save current position"),
            command=lambda: save_current_poi(frame)
        )
        savebtn.grid(row=row, column=0, columnspan=2, sticky="w")

        row += 1
        info_label = nb.Label(frame, text="")
        info_label.grid(row=row, column=0, columnspan=7, sticky="w")
        frame.info_label = info_label  # För status/meddelande om du vill

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
