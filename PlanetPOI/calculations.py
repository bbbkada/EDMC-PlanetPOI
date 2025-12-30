"""
Calculations module for EDMC-PlanetPOI
Handles mathematical calculations for navigation, distance, bearing, and formatting
"""

import math


def calculate_bearing_and_distance(lat1, lon1, lat2, lon2, planet_radius_m, alt1=0, alt2=0, calc_with_altitude=False):
    """
    Calculate bearing and distance between two coordinates on a sphere
    
    Args:
        lat1, lon1: Starting position (degrees)
        lat2, lon2: Target position (degrees)
        planet_radius_m: Planet radius in meters
        alt1, alt2: Altitudes in meters (optional)
        calc_with_altitude: If True, calculate 3D distance including altitude
        
    Returns:
        tuple: (distance_meters, bearing_degrees)
    """
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


def format_distance_with_unit(distance_meters):
    """
    Format distance with appropriate unit (m, km, Mm)
    
    Args:
        distance_meters: Distance in meters
        
    Returns:
        tuple: (value, unit)
    """
    unit = "m"
    show_dist = distance_meters
    
    if distance_meters > 1_000:
        show_dist = distance_meters / 1_000
        unit = "km"
    
    if show_dist > 1_000:
        show_dist = show_dist / 1_000
        unit = "Mm"
    
    return show_dist, unit


def get_ui_scale():
    """Get UI scale factor from EDMC config (default 100%)"""
    try:
        from config import config
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


def safe_int(val, fallback):
    """Safely convert value to int with fallback"""
    try:
        return int(val)
    except Exception:
        return fallback
