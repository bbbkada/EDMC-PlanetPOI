# overlay.py
import sys

# Store module reference - works regardless of whether imported as "overlay" or "PlanetPOI.overlay"
this = sys.modules[__name__]

# Initialize module-level variables
overlay = None
overlay_available = False
_connection_attempted = False  # Track if we've tried to connect

def _try_connect():
    """Attempt to connect to EDMCOverlay - called lazily on first use"""
    global overlay, overlay_available, _connection_attempted, this
    
    if _connection_attempted:
        return overlay_available
    
    _connection_attempted = True
    
    try:
        from edmcoverlay import Overlay
        overlay = Overlay()
        overlay.connect()
        overlay_available = True
        # Also set on this for backward compatibility
        this.overlay = overlay
        this.overlay_available = True
        return True
    except Exception as e:
        print(f"Unable to load EDMCOverlay: {e}")
        overlay = None
        overlay_available = False
        this.overlay = None
        this.overlay_available = False
        return False

try:
    import myNotebook as nb
    from config import config
except ImportError:
    config = {}

ROW_Y_START = 2        # pixel-y for first row
ROW_Y_STEP = 24        # distance between rows

OVERLAY_MAX_ROWS = 10
OVERLAY_LEFT_MARGIN = 500

# New helper for overlay settings
def get_overlay_settings():
    try:
        max_rows = int(config.get_int("planetpoi_max_overlay_rows", 5))
    except Exception:
        max_rows = 10
    try:
        leftmargin = int(config.get_int("planetpoi_overlay_leftmargin", 500))
    except Exception:
        leftmargin = 500
    return max_rows, leftmargin

def set_overlay_settings(rows, margin):
    global OVERLAY_MAX_ROWS, OVERLAY_LEFT_MARGIN
    OVERLAY_MAX_ROWS = int(rows)
    OVERLAY_LEFT_MARGIN = int(margin)

def show_poi_rows(poi_texts, color="#ff7100"):
    global OVERLAY_MAX_ROWS, OVERLAY_LEFT_MARGIN, overlay
    """
    Shows one row in overlay for each POI (max rows and left alignment from settings).
    Clears excess old rows.
    """
    if not ensure_overlay():
        return

    if len(poi_texts) > OVERLAY_MAX_ROWS:
        poi_texts = poi_texts[:OVERLAY_MAX_ROWS]

    for idx, text in enumerate(poi_texts):
        y_pos = ROW_Y_START + idx * ROW_Y_STEP
        message_id = f"poi_{idx}"
        overlay.send_message(
            msgid=message_id,
            text=text,
            color=color,
            x=OVERLAY_LEFT_MARGIN,
            y=y_pos,
            ttl=30,  # TTL = 30 seconds (keeps overlay visible)
            size="large"
        )
 
    # Clear old overlays if there are fewer rows than before
    for idx in range(len(poi_texts), OVERLAY_MAX_ROWS):
        y_pos = ROW_Y_START + idx * ROW_Y_STEP
        message_id = f"poi_{idx}"
        overlay.send_message(
            msgid=message_id,
            text="",
            color="#000000",
            x=OVERLAY_LEFT_MARGIN,
            y=y_pos,
            ttl=8,  # TTL = 30 seconds (keeps overlay visible)
            size="large"
        )

def show_poi_rows_with_colors(poi_texts_with_colors):
    global OVERLAY_MAX_ROWS, OVERLAY_LEFT_MARGIN, overlay
    """
    Shows POI rows with different colors. First POI (target) is orange, rest are gray.
    
    Args:
        poi_texts_with_colors: List of tuples (text, is_target) where is_target is True for target POI
    """
    if not ensure_overlay():
        return

    if len(poi_texts_with_colors) > OVERLAY_MAX_ROWS:
        poi_texts_with_colors = poi_texts_with_colors[:OVERLAY_MAX_ROWS]

    for idx, (text, is_target) in enumerate(poi_texts_with_colors):
        y_pos = ROW_Y_START + idx * ROW_Y_STEP
        message_id = f"poi_{idx}"
        # Target POI is orange, others are gray
        color = "#ff7100" if is_target else "#888888"
        overlay.send_message(
            msgid=message_id,
            text=text,
            color=color,
            x=OVERLAY_LEFT_MARGIN,
            y=y_pos,
            ttl=30,
            size="large"
        )
 
    # Clear old overlays if there are fewer rows than before
    for idx in range(len(poi_texts_with_colors), OVERLAY_MAX_ROWS):
        y_pos = ROW_Y_START + idx * ROW_Y_STEP
        message_id = f"poi_{idx}"
        overlay.send_message(
            msgid=message_id,
            text="",
            color="#000000",
            x=OVERLAY_LEFT_MARGIN,
            y=y_pos,
            ttl=8,
            size="large"
        )

def show_message(message_id, text, color="#ff7100", x=2, y=2, size=8, font_weight="normal"):
    """
    Send any overlay row (for advanced custom overlays).
    """
    global overlay
    if ensure_overlay():
        overlay.send_message(
            msgid=message_id,
            text=text,
            color=color,
            x=x,
            y=y,
            ttl=size,  # TTL = 30 seconds (keeps overlay visible)
            size="large"
        )



def clear_all_poi_rows():
    global OVERLAY_MAX_ROWS, OVERLAY_LEFT_MARGIN
    """
    Clears all POI rows in overlay.
    """
    for idx in range(OVERLAY_MAX_ROWS):
        y_pos = ROW_Y_START + idx * ROW_Y_STEP
        message_id = f"poi_{idx}"
        if ensure_overlay():
         this.overlay.send_message(
            msgid=message_id,
            text="",
            color="#000000",
            x=OVERLAY_LEFT_MARGIN,
            y=y_pos,
            ttl=8,  # TTL = 30 seconds (keeps overlay visible)
            size="large"
        )

def ensure_overlay():
    global overlay, overlay_available, _connection_attempted
    
    # First time - try lazy connection
    if not _connection_attempted:
        return _try_connect()
    
    # Already tried - check if it's available
    if overlay_available:
        return True
    
    # Not available - try to reconnect
    try:
        from edmcoverlay import Overlay
        overlay = Overlay()
        overlay.connect()
        overlay_available = True
        this.overlay = overlay
        this.overlay_available = True
        if hasattr(this, "_overlay_warned"):
            del this._overlay_warned   # Reset warning if we successfully reconnected!
        print("EDMCOverlay: Reconnected successfully!")
        return True
    except Exception as e:
        if not hasattr(this, "_overlay_warned") or not this._overlay_warned:
            print(f"Unable to load EDMCOverlay: {e}")
            this._overlay_warned = True
        overlay = None
        overlay_available = False
        this.overlay = None
        this.overlay_available = False
        return False
