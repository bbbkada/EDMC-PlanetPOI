"""
Guidance Manager module for EDMC-PlanetPOI
Handles dynamic guidance widget updates and overlay management
"""

# These will be set by load.py
GUIDANCE_LEFT_LABEL = None
GUIDANCE_CENTER_LABEL = None
GUIDANCE_RIGHT_LABEL = None
FIRST_POI_LABEL = None

# References to load.py globals (set by init function)
get_config = None
get_last_position = None
get_poi_manager = None
get_theme = None


def init_guidance_manager(config_getter, position_getter, poi_getter, theme_getter):
    """Initialize guidance manager with getters for external dependencies"""
    global get_config, get_last_position, get_poi_manager, get_theme
    get_config = config_getter
    get_last_position = position_getter
    get_poi_manager = poi_getter
    get_theme = theme_getter


def set_guidance_labels(left, center, right, first_poi):
    """Set references to guidance labels"""
    global GUIDANCE_LEFT_LABEL, GUIDANCE_CENTER_LABEL, GUIDANCE_RIGHT_LABEL, FIRST_POI_LABEL
    GUIDANCE_LEFT_LABEL = left
    GUIDANCE_CENTER_LABEL = center
    GUIDANCE_RIGHT_LABEL = right
    FIRST_POI_LABEL = first_poi


def update_guidance_widgets():
    """
    Update Guidance section widgets dynamically without full GUI rebuild.
    
    Returns:
        True: Successfully updated widgets
        False: Conditions not met for showing guidance (no action needed)
        "rebuild": Widgets need to be created OR removed - trigger full GUI rebuild
    """
    from PlanetPOI.calculations import calculate_bearing_and_distance, format_distance_with_unit
    import tkinter as tk
    
    config = get_config()
    pos_data = get_last_position()
    poi_mgr = get_poi_manager()
    theme = get_theme()
    
    last_lat = pos_data['lat']
    last_lon = pos_data['lon']
    last_body = pos_data['body']
    last_heading = pos_data['heading']
    last_planet_radius = pos_data['planet_radius']
    last_altitude = pos_data['altitude']
    
    # First check if conditions are met for showing guidance at all
    guidance_should_exist = False
    
    # Check basic requirements
    if (config.get_int("planetpoi_show_gui_info") and 
        last_lat is not None and last_lon is not None and 
        last_body and last_heading is not None):
        
        # Find first active POI
        from PlanetPOI.poi_manager import get_full_body_name, get_all_pois_flat, ALL_POIS
        matching_pois = [poi for poi in get_all_pois_flat(ALL_POIS) if get_full_body_name(poi) == last_body]
        first_active_poi = None
        for poi in matching_pois:
            if poi.get("active", True):
                first_active_poi = poi
                break
        
        if first_active_poi:
            poi_lat = first_active_poi.get("lat")
            poi_lon = first_active_poi.get("lon")
            
            if poi_lat is not None and poi_lon is not None:
                # Calculate distance to check if outside stop distance
                distance, bearing = calculate_bearing_and_distance(
                    last_lat, last_lon, poi_lat, poi_lon,
                    last_planet_radius,
                    last_altitude, 0,
                    calc_with_altitude=config.get_int("planetpoi_calc_with_altitude")
                )
                
                guidance_distance = config.get_int("planetpoi_guidance_distance", default=2000)
                if distance >= guidance_distance:
                    guidance_should_exist = True
    
    # Check if we have guidance widgets
    widgets_exist = (GUIDANCE_LEFT_LABEL is not None and 
                     GUIDANCE_CENTER_LABEL is not None and 
                     GUIDANCE_RIGHT_LABEL is not None)
    
    # If widgets should exist but don't - need to create them
    if guidance_should_exist and not widgets_exist:
        print("PPOI: Guidance should exist but doesn't - triggering rebuild to create")
        return "rebuild"
    
    # If widgets exist but shouldn't - need to remove them
    if not guidance_should_exist and widgets_exist:
        print("PPOI: Guidance exists but shouldn't - triggering rebuild to remove")
        return "rebuild"
    
    # If widgets shouldn't exist and don't - nothing to do
    if not guidance_should_exist and not widgets_exist:
        return False
    
    # At this point: widgets exist AND should exist - update them
    # Re-fetch the data we need (already calculated above but in different scope)
    from PlanetPOI.poi_manager import get_full_body_name, get_all_pois_flat, ALL_POIS
    matching_pois = [poi for poi in get_all_pois_flat(ALL_POIS) if get_full_body_name(poi) == last_body]
    first_active_poi = None
    for poi in matching_pois:
        if poi.get("active", True):
            first_active_poi = poi
            break
    
    poi_lat = first_active_poi.get("lat")
    poi_lon = first_active_poi.get("lon")
    
    distance, bearing = calculate_bearing_and_distance(
        last_lat, last_lon, poi_lat, poi_lon,
        last_planet_radius,
        last_altitude, 0,
        calc_with_altitude=config.get_int("planetpoi_calc_with_altitude")
    )
    
    # Format distance
    show_dist, unit = format_distance_with_unit(distance)
    
    # Calculate deviation
    guidance_threshold = config.get_int("planetpoi_guidance_threshold", default=4)
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
    
    # Update widgets
    try:
        # Update left arrows
        left_arrows = "<" * num_arrows if deviation < -guidance_threshold else ""
        GUIDANCE_LEFT_LABEL.config(text=left_arrows)
        
        # Update center text and color
        if unit == "m":
            center_text = f"{round(bearing)}°/ {round(show_dist)}{unit}"
        else:
            center_text = f"{round(bearing)}°/ {show_dist:.1f}{unit}"
        if on_course:
            GUIDANCE_CENTER_LABEL.config(text=center_text, foreground="#00aa00")
        else:
            # Reset to default foreground by explicitly removing the custom color
            try:
                temp_label = tk.Label()
                default_fg = temp_label.cget("foreground")
                temp_label.destroy()
                GUIDANCE_CENTER_LABEL.config(text=center_text, foreground=default_fg)
            except:
                # Fallback: use empty string to reset to default
                GUIDANCE_CENTER_LABEL.config(text=center_text, foreground="")
                theme.update(GUIDANCE_CENTER_LABEL)
        
        # Update right arrows
        right_arrows = ">" * num_arrows if deviation > guidance_threshold else ""
        GUIDANCE_RIGHT_LABEL.config(text=right_arrows)
        
        # Update first POI label with bearing/distance if it exists
        if FIRST_POI_LABEL:
            poi_desc = first_active_poi.get("description", "")
            if not poi_desc:
                if poi_lat is not None and poi_lon is not None:
                    poi_desc = f"{poi_lat:.4f}, {poi_lon:.4f}"
                else:
                    poi_desc = "(No description)"
            
            if unit == "m":
                display_text = f"{poi_desc} - {round(bearing)}°/ {round(show_dist)}{unit}"
            else:
                display_text = f"{poi_desc} - {round(bearing)}°/ {show_dist:.1f}{unit}"
            FIRST_POI_LABEL.config(text=display_text)
        
        return True  # Successfully updated
    except Exception as e:
        print(f"PPOI: Error updating guidance widgets: {e}")
        return "rebuild"  # Failed to update - trigger rebuild
