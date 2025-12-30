"""
GUI Builder module for EDMC-PlanetPOI
Contains main GUI building functions (build_plugin_content, build_plugin_ui, etc.)
"""

import tkinter as tk
import tkinter.font as tkfont
import myNotebook as nb
from tkinter import ttk
from config import config
from theme import theme
from calculations import calculate_bearing_and_distance, format_distance_with_unit
from poi_manager import get_full_body_name, get_all_pois_flat
import functools
import l10n

plugin_tl = functools.partial(l10n.translations.tl, context=__file__)

# External dependencies
get_globals = None
get_callbacks = None


def init_gui_builder(globals_getter, callbacks_getter):
    """Initialize GUI builder with getters for external dependencies"""
    global get_globals, get_callbacks
    get_globals = globals_getter
    get_callbacks = callbacks_getter


def create_scrolled_frame(parent):
    """Create a scrollable frame"""
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


def build_plugin_content(frame):
    """Build/rebuild the content inside the persistent plugin frame"""
    # Check if module is initialized
    if get_globals is None or get_callbacks is None:
        print("PPOI ERROR: gui_builder not initialized!")
        return
    
    g = get_globals()
    cb = get_callbacks()
    
    # Get globals
    last_body = g['last_body']
    last_lat = g['last_lat']
    last_lon = g['last_lon']
    last_heading = g['last_heading']
    last_altitude = g['last_altitude']
    last_planet_radius = g['last_planet_radius']
    CURRENT_SYSTEM = g['CURRENT_SYSTEM']
    ALL_POIS = g['ALL_POIS']
    SHOW_GUI_INFO_KEY = g['SHOW_GUI_INFO_KEY']
    ALT_KEY = g['ALT_KEY']
    GUIDANCE_DISTANCE_KEY = g['GUIDANCE_DISTANCE_KEY']
    GUIDANCE_THRESHOLD_KEY = g['GUIDANCE_THRESHOLD_KEY']
    
    small_font = tkfont.Font(size=9)
    
    frame.grid_columnconfigure(0, weight=0, minsize=25)
    frame.grid_columnconfigure(1, weight=1)
    row = 0

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
            menu_btn.config(command=lambda b=menu_btn: cb['show_menu_dropdown'](frame, b, CURRENT_SYSTEM))
            menu_btn.grid(row=0, column=1, sticky="e")
            theme.update(header_frame)
            row += 1
            
            for poi in matching_system_pois:
                desc = poi.get("description", "")
                if not desc:
                    lat = poi.get("lat")
                    lon = poi.get("lon")
                    if lat is not None and lon is not None:
                        desc = f"{lat:.4f}, {lon:.4f}"
                    else:
                        desc = "(No description)"
                
                body_part = poi.get("body", "")
                poi_desc = body_part + " - " + desc if body_part else desc
                is_active = poi.get("active", True)
                
                label_kwargs = {"text": poi_desc, "font": small_font}
                if not is_active:
                    label_kwargs["foreground"] = "gray"
                
                poi_label = tk.Label(frame, **label_kwargs)
                poi_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=2, pady=0)
                theme.update(poi_label)
                poi_label.bind("<Button-3>", lambda e, p=poi: cb['show_poi_context_menu_main'](e, p, frame))
                
                row += 1
        else:    
            header_frame = tk.Frame(frame)
            header_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=2, pady=2)
            header_frame.grid_columnconfigure(0, weight=1)
            
            no_system_label = tk.Label(header_frame, text=plugin_tl("PPOI: No poi's in system"))
            no_system_label.grid(row=0, column=0, sticky="w")
            theme.update(no_system_label)
            menu_btn = tk.Button(header_frame, text="☰", width=3, height=1, borderwidth=0, highlightthickness=0, relief="flat")
            menu_btn.config(command=lambda b=menu_btn: cb['show_menu_dropdown'](frame, b, CURRENT_SYSTEM))
            menu_btn.grid(row=0, column=1, sticky="e")
            theme.update(header_frame)
        
        return

    matching_pois = [poi for poi in get_all_pois_flat(ALL_POIS) if get_full_body_name(poi) == current_body]

    # Header with menu button
    header_frame = tk.Frame(frame)
    header_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=2, pady=2)
    header_frame.grid_columnconfigure(0, weight=1)
    
    body_label = tk.Label(header_frame, text=f"PPOI: {current_body}", font=('TkDefaultFont', 10, 'bold'))
    body_label.grid(row=0, column=0, sticky="w")
    theme.update(body_label)
    
    menu_btn = tk.Button(header_frame, text="☰", width=3, height=1, borderwidth=0, highlightthickness=0, relief="flat")
    menu_btn.config(command=lambda b=menu_btn: cb['show_menu_dropdown'](frame, b, current_body))
    menu_btn.grid(row=0, column=1, sticky="e")
    theme.update(header_frame)
    row += 1
    
    # Guidance section
    if config.get_int(SHOW_GUI_INFO_KEY) and matching_pois:
        first_active_poi = None
        for poi in matching_pois:
            if poi.get("active", True):
                first_active_poi = poi
                break
        
        if first_active_poi and last_lat is not None and last_lon is not None:
            poi_lat = first_active_poi.get("lat")
            poi_lon = first_active_poi.get("lon")
            
            if poi_lat is not None and poi_lon is not None:
                distance, bearing = calculate_bearing_and_distance(
                    last_lat, last_lon, poi_lat, poi_lon,
                    last_planet_radius,
                    last_altitude, 0,
                    calc_with_altitude=config.get_int(ALT_KEY)
                )
                
                guidance_distance = config.get_int(GUIDANCE_DISTANCE_KEY, default=2000)
                
                if distance >= guidance_distance:
                    show_dist, unit = format_distance_with_unit(distance)
                    
                    guidance_threshold = config.get_int(GUIDANCE_THRESHOLD_KEY, default=4)
                    on_course = False
                    deviation = 0
                    
                    if last_heading is not None:
                        deviation = bearing - last_heading
                        while deviation > 180:
                            deviation -= 360
                        while deviation < -180:
                            deviation += 360
                        on_course = abs(deviation) <= guidance_threshold
                    
                    guidance_frame = tk.Frame(frame, relief="solid", borderwidth=1, highlightbackground="white", highlightthickness=1)
                    guidance_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=2, pady=(2, 5))
                    
                    guidance_frame.grid_columnconfigure(0, weight=0, minsize=40)
                    guidance_frame.grid_columnconfigure(1, weight=1)
                    guidance_frame.grid_columnconfigure(2, weight=0, minsize=40)
                    
                    num_arrows = 0
                    if not on_course and last_heading is not None:
                        abs_deviation = abs(deviation)
                        if abs_deviation > guidance_threshold:
                            max_deviation = 90
                            arrow_fraction = min((abs_deviation - guidance_threshold) / (max_deviation - guidance_threshold), 1.0)
                            num_arrows = int(arrow_fraction * 4) + 1
                            num_arrows = min(num_arrows, 4)
                    
                    left_arrows = "<" * num_arrows if deviation < -guidance_threshold else ""
                    left_label = tk.Label(guidance_frame, text=left_arrows, font=('TkDefaultFont', 12), anchor="e")
                    left_label.grid(row=0, column=0, sticky="e", padx=(2, 0))
                    
                    center_text = f"{round(bearing)}° / {round(show_dist)}{unit}"
                    center_color = "#00aa00" if on_course else None
                    center_kwargs = {"text": center_text, "font": ('TkDefaultFont', 10, 'bold'), "anchor": "center"}
                    if center_color:
                        center_kwargs["foreground"] = center_color
                    center_label = tk.Label(guidance_frame, **center_kwargs)
                    center_label.grid(row=0, column=1, sticky="ew", padx=2)
                    
                    right_arrows = ">" * num_arrows if deviation > guidance_threshold else ""
                    right_label = tk.Label(guidance_frame, text=right_arrows, font=('TkDefaultFont', 12), anchor="w")
                    right_label.grid(row=0, column=2, sticky="w", padx=(0, 2))
                    
                    theme.update(guidance_frame)
                    theme.update(left_label)
                    theme.update(center_label)
                    theme.update(right_label)
                    
                    # Store references for guidance_manager
                    g['GUIDANCE_FRAME'] = guidance_frame
                    g['GUIDANCE_LEFT_LABEL'] = left_label
                    g['GUIDANCE_CENTER_LABEL'] = center_label
                    g['GUIDANCE_RIGHT_LABEL'] = right_label
                    g['GUIDANCE_DEFAULT_FG'] = center_label.cget("foreground")  # Save default color after theme applied
                    
                    row += 1
                else:
                    g['GUIDANCE_FRAME'] = None
                    g['GUIDANCE_LEFT_LABEL'] = None
                    g['GUIDANCE_CENTER_LABEL'] = None
                    g['GUIDANCE_RIGHT_LABEL'] = None
            else:
                g['GUIDANCE_FRAME'] = None
                g['GUIDANCE_LEFT_LABEL'] = None
                g['GUIDANCE_CENTER_LABEL'] = None
                g['GUIDANCE_RIGHT_LABEL'] = None
        else:
            g['GUIDANCE_FRAME'] = None
            g['GUIDANCE_LEFT_LABEL'] = None
            g['GUIDANCE_CENTER_LABEL'] = None
            g['GUIDANCE_RIGHT_LABEL'] = None
    else:
        g['GUIDANCE_FRAME'] = None
        g['GUIDANCE_LEFT_LABEL'] = None
        g['GUIDANCE_CENTER_LABEL'] = None
        g['GUIDANCE_RIGHT_LABEL'] = None
    
    g['OVERLAY_INFO_LABEL'] = None

    # POI list
    shown_first_active = False
    g['FIRST_POI_LABEL'] = None
    
    for poi in matching_pois:
        desc = poi.get("description", "")
        if not desc:
            lat = poi.get("lat")
            lon = poi.get("lon")
            if lat is not None and lon is not None:
                desc = f"{lat:.4f}, {lon:.4f}"
            else:
                desc = "(No description)"
        
        is_active = poi.get("active", True)
        
        display_text = desc
        if is_active and not shown_first_active and last_lat is not None and last_lon is not None:
            poi_lat = poi.get("lat")
            poi_lon = poi.get("lon")
            
            if poi_lat is not None and poi_lon is not None:
                distance, bearing = calculate_bearing_and_distance(
                    last_lat, last_lon, poi_lat, poi_lon,
                    last_planet_radius,
                    last_altitude, 0,
                    calc_with_altitude=config.get_int(ALT_KEY)
                )
                
                show_dist, unit = format_distance_with_unit(distance)
                display_text = f"{desc} - {round(bearing)}°/{round(show_dist)}{unit}"
                shown_first_active = True
        
        label_kwargs = {"text": display_text, "font": small_font}
        if not is_active:
            label_kwargs["foreground"] = "gray"
        
        desc_label = tk.Label(frame, **label_kwargs)
        desc_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=2, pady=0)
        theme.update(desc_label)
        
        if is_active and shown_first_active and g['FIRST_POI_LABEL'] is None and poi_lat is not None and poi_lon is not None:
            g['FIRST_POI_LABEL'] = desc_label
        
        desc_label.bind("<Button-3>", lambda e, p=poi: cb['show_poi_context_menu_main'](e, p, frame))

        row += 1

    if not matching_pois:
        no_poi_label = tk.Label(frame, text=plugin_tl("PPOI: No POIs for this body"))
        no_poi_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=2)
        theme.update(no_poi_label)
    
    # Return widget references
    return {
        'GUIDANCE_FRAME': g.get('GUIDANCE_FRAME'),
        'GUIDANCE_LEFT_LABEL': g.get('GUIDANCE_LEFT_LABEL'),
        'GUIDANCE_CENTER_LABEL': g.get('GUIDANCE_CENTER_LABEL'),
        'GUIDANCE_RIGHT_LABEL': g.get('GUIDANCE_RIGHT_LABEL'),
        'FIRST_POI_LABEL': g.get('FIRST_POI_LABEL'),
        'GUIDANCE_DEFAULT_FG': g.get('GUIDANCE_DEFAULT_FG')
    }


def build_plugin_ui(frame):
    """Build the plugin settings UI (in EDMC Settings)"""
    # Check if module is initialized
    if get_globals is None or get_callbacks is None:
        print("PPOI ERROR: gui_builder not initialized!")
        return
    
    g = get_globals()
    cb = get_callbacks()
    
    # Get global vars
    ALT_VAR = g['ALT_VAR']
    ROWS_VAR = g['ROWS_VAR']
    LEFT_VAR = g['LEFT_VAR']
    SHOW_GUI_INFO_VAR = g['SHOW_GUI_INFO_VAR']
    HEADING_GUIDANCE_VAR = g['HEADING_GUIDANCE_VAR']
    GUIDANCE_THRESHOLD_VAR = g['GUIDANCE_THRESHOLD_VAR']
    GUIDANCE_DISTANCE_VAR = g['GUIDANCE_DISTANCE_VAR']
    ALL_POIS = g['ALL_POIS']
    SORT_COLUMN = g['SORT_COLUMN']
    SORT_REVERSE = g['SORT_REVERSE']
    
    row = 0

    # Settings row 1
    nb.Label(frame, text=plugin_tl("Calculate distance with altitude")).grid(row=row, column=0, columnspan=2,sticky="w", padx=(0, 8))
    nb.Label(frame, text=plugin_tl("Max overlay rows")).grid(row=row, column=2, sticky="w", padx=(0, 8))
    nb.Label(frame, text=plugin_tl("Overlay left margin (pixels)")).grid(row=row, column=3, sticky="w")
    row += 1

    cb_alt = nb.Checkbutton(frame, variable=ALT_VAR, width=2)
    cb_alt.grid(row=row, column=0, columnspan=2,sticky="w", padx=(0, 4))
    rows_entry = nb.EntryMenu(frame, textvariable=ROWS_VAR, width=4)
    rows_entry.grid(row=row, column=2, sticky="w", padx=(0, 8))
    left_entry = nb.EntryMenu(frame, textvariable=LEFT_VAR, width=6)
    left_entry.grid(row=row, column=3, sticky="w", padx=(0, 8))
    export_btn = nb.Button(frame, text=plugin_tl("Export POIs"), command=lambda: cb['export_pois_to_file'](frame), width=12)
    export_btn.grid(row=row, column=4, sticky="w", padx=(0, 4))
    import_btn = nb.Button(frame, text=plugin_tl("Import POIs"), command=lambda: cb['import_pois_from_file'](frame), width=12)
    import_btn.grid(row=row, column=5, sticky="w", padx=(0, 4))
    row += 1
    
    # Settings row 2
    nb.Label(frame, text=plugin_tl("Show overlay info in EDMC GUI")).grid(row=row, column=0, columnspan=2, sticky="w", padx=(0, 8))
    show_gui_cb = nb.Checkbutton(frame, variable=SHOW_GUI_INFO_VAR, width=2)
    show_gui_cb.grid(row=row, column=2, sticky="w", padx=(0, 4))
    
    nb.Label(frame, text=plugin_tl("Enable Heading Guidance")).grid(row=row, column=3, sticky="w", padx=(8, 8))
    heading_guidance_cb = nb.Checkbutton(frame, variable=HEADING_GUIDANCE_VAR, width=2)
    heading_guidance_cb.grid(row=row, column=4, sticky="w", padx=(0, 4))
    row += 1
    
    # Settings row 3
    nb.Label(frame, text=plugin_tl("Guidance angle tolerance (degrees)")).grid(row=row, column=0, columnspan=2, sticky="w", padx=(0, 8))
    guidance_threshold_entry = nb.EntryMenu(frame, textvariable=GUIDANCE_THRESHOLD_VAR, width=4)
    guidance_threshold_entry.grid(row=row, column=2, sticky="w", padx=(0, 8))
    
    nb.Label(frame, text=plugin_tl("Guidance stop distance (meters)")).grid(row=row, column=3, sticky="w", padx=(8, 8))
    guidance_distance_entry = nb.EntryMenu(frame, textvariable=GUIDANCE_DISTANCE_VAR, width=6)
    guidance_distance_entry.grid(row=row, column=4, sticky="w", padx=(0, 4))
    row += 1
    
    # Column configuration
    for col in range(6):
        frame.grid_columnconfigure(col, weight=0, minsize=100 if col >= 4 else 0)

    sep = ttk.Separator(frame, orient='horizontal')
    sep.grid(row=row, column=0, columnspan=8, sticky="ew", pady=8)
    row += 1

    # POI Table
    table_frame = tk.Frame(frame, background="white")
    table_frame.grid(row=row, column=0, columnspan=8, sticky="nsew")
    frame.grid_rowconfigure(row, weight=1)
    
    table_row = 0
    nb.Label(table_frame, text=plugin_tl("Saved POIs"), font=('TkDefaultFont', 10, 'bold')).grid(row=table_row, column=0, columnspan=9, sticky="w")
    table_row += 1

    # Sorting function
    def sort_by_column(column):
        g['SORT_COLUMN'] = column
        g['SORT_REVERSE'] = not g['SORT_REVERSE'] if g['SORT_COLUMN'] == column else False
        cb['redraw_prefs'](frame)

    headers = [
        plugin_tl("Active"),
        "",
        plugin_tl("Body Name"),
        plugin_tl("Latitude"),
        plugin_tl("Longitude"),
        plugin_tl("Description"),
        plugin_tl("Delete"),
        plugin_tl("Save"),
        plugin_tl("Share")
    ]
    
    sortable_columns = {2: "body", 5: "description"}
    
    for col, header in enumerate(headers):
        padding = 0 if col == 1 else 2
        
        if col in sortable_columns:
            sort_indicator = ""
            if SORT_COLUMN == sortable_columns[col]:
                sort_indicator = " ▼" if SORT_REVERSE else " ▲"
            
            header_label = nb.Label(table_frame, text=header + sort_indicator, font=('TkDefaultFont', 9, 'bold'), cursor="hand2")
            header_label.grid(row=table_row, column=col, padx=padding, pady=2, sticky="w")
            header_label.bind("<Button-1>", lambda e, c=sortable_columns[col]: sort_by_column(c))
        else:
            nb.Label(table_frame, text=header, font=('TkDefaultFont', 9, 'bold')).grid(row=table_row, column=col, padx=padding, pady=2, sticky="w")
    table_row += 1

    g['POI_VARS'] = []
    g['POI_REFS'] = []
    
    all_pois_flat = get_all_pois_flat(ALL_POIS)
    
    # Sort POIs
    if SORT_COLUMN == "body":
        all_pois_sorted = sorted(all_pois_flat, key=lambda p: (p.get("system", "").lower(), p.get("body", "").lower()), reverse=SORT_REVERSE)
    elif SORT_COLUMN == "description":
        all_pois_sorted = sorted(all_pois_flat, key=lambda p: p.get("description", "").lower(), reverse=SORT_REVERSE)
    else:
        all_pois_sorted = sorted(all_pois_flat, key=lambda p: (p.get("system", "").lower(), p.get("body", "").lower()), reverse=SORT_REVERSE)
    
    for poi in all_pois_sorted:
        active_var = tk.BooleanVar(value=poi.get("active", True))
        cb_poi = nb.Checkbutton(table_frame, variable=active_var, width=2)
        try:
            cb_poi.configure(background="white")
        except:
            pass
        cb_poi.grid(row=table_row, column=0, sticky="w", padx=(0, 0))
        g['POI_VARS'].append(active_var)
        g['POI_REFS'].append(poi)
        
        cb_poi.bind("<Button-3>", lambda e, p=poi, av=active_var: cb['show_poi_context_menu'](e, p, frame, av))

        # Copy system button
        def copy_system(system_name):
            table_frame.clipboard_clear()
            table_frame.clipboard_append(system_name)
        
        copy_label = nb.Label(table_frame, text="📋", cursor="hand2")
        copy_label.grid(row=table_row, column=1, sticky="e", padx=(0, 2))
        copy_label.bind("<Button-1>", lambda e, s=poi.get("system", ""): copy_system(s))
        copy_label.bind("<Button-3>", lambda e, p=poi, av=active_var: cb['show_poi_context_menu'](e, p, frame, av))
        
        # Body name
        body_label = nb.Label(table_frame, text=get_full_body_name(poi), anchor="w")
        body_label.grid(row=table_row, column=2, padx=2, pady=2, sticky="w")
        body_label.bind("<Button-3>", lambda e, p=poi, av=active_var: cb['show_poi_context_menu'](e, p, frame, av))
        
        # Lat/Lon
        lat_label = nb.Label(table_frame, text=poi.get("lat", ""), anchor="w")
        lat_label.grid(row=table_row, column=3, padx=2, pady=2, sticky="w")
        lat_label.bind("<Button-3>", lambda e, p=poi, av=active_var: cb['show_poi_context_menu'](e, p, frame, av))
        
        lon_label = nb.Label(table_frame, text=poi.get("lon", ""), anchor="w")
        lon_label.grid(row=table_row, column=4, padx=2, pady=2, sticky="w")
        lon_label.bind("<Button-3>", lambda e, p=poi, av=active_var: cb['show_poi_context_menu'](e, p, frame, av))

        # Description
        desc_var = tk.StringVar(value=poi.get("description", ""))
        desc_entry = nb.EntryMenu(table_frame, textvariable=desc_var, width=28)
        desc_entry.grid(row=table_row, column=5, sticky="w", padx=(2,2))
        desc_entry.bind("<Button-3>", lambda e, p=poi, av=active_var: cb['show_poi_context_menu'](e, p, frame, av))

        # Buttons
        delbtn = nb.Button(table_frame, text=plugin_tl("Delete"), command=lambda p=poi: cb['remove_poi_obj'](p, frame), width=7)
        delbtn.grid(row=table_row, column=6, sticky="w", padx=(2,2))
        delbtn.bind("<Button-3>", lambda e, p=poi, av=active_var: cb['show_poi_context_menu'](e, p, frame, av))

        savebtn = nb.Button(table_frame, text=plugin_tl("Save"), state='disabled', width=7)
        savebtn.grid(row=table_row, column=7, sticky="w", padx=(2,2))
        savebtn.bind("<Button-3>", lambda e, p=poi, av=active_var: cb['show_poi_context_menu'](e, p, frame, av))

        sharebtn = nb.Button(table_frame, text=plugin_tl("Share"), command=lambda p=poi: cb['show_share_popup'](frame, p), width=7)
        sharebtn.grid(row=table_row, column=8, sticky="w", padx=(2,2))
        sharebtn.bind("<Button-3>", lambda e, p=poi, av=active_var: cb['show_poi_context_menu'](e, p, frame, av))

        def on_desc_change(*args, p=poi, v=desc_var, btn=savebtn):
            current = v.get()
            original = p.get("description", "")
            btn.config(state=('normal' if current != original else 'disabled'))

        desc_var.trace_add('write', lambda *args, p=poi, v=desc_var, btn=savebtn: on_desc_change(p=p, v=v, btn=btn))
        savebtn.config(command=lambda p=poi, v=desc_var, btn=savebtn: cb['save_desc_obj'](p, v, frame, btn))
        table_row += 1

    # Column configuration
    table_frame.grid_columnconfigure(0, minsize=22, weight=0)
    table_frame.grid_columnconfigure(1, minsize=15, weight=0)
    table_frame.grid_columnconfigure(2, minsize=120, weight=0)
    table_frame.grid_columnconfigure(3, minsize=84, weight=0)
    table_frame.grid_columnconfigure(4, minsize=100, weight=0)
    table_frame.grid_columnconfigure(5, minsize=210, weight=2)
    table_frame.grid_columnconfigure(6, minsize=60, weight=0)
    table_frame.grid_columnconfigure(7, minsize=70, weight=0)
    table_frame.grid_columnconfigure(8, minsize=70, weight=0)
