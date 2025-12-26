# overlay.py
import sys

this = sys.modules[__name__]

try:
    from edmcoverlay import Overlay
    this.overlay = Overlay()
    this.overlay.connect()
    this.overlay_available = True
except Exception as e:
    print(f"Unable to load EDMCOverlay: {e}")
    this.overlay = None
    this.overlay_available = False

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
    global OVERLAY_MAX_ROWS, OVERLAY_LEFT_MARGIN
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
        this.overlay.send_message(
            message_id,
            text,
            color,
            OVERLAY_LEFT_MARGIN, y_pos, 30,  # TTL = 30 seconds (keeps overlay visible)
            "large"
        )

    # Clear old overlays if there are fewer rows than before
    for idx in range(len(poi_texts), OVERLAY_MAX_ROWS):
        y_pos = ROW_Y_START + idx * ROW_Y_STEP
        message_id = f"poi_{idx}"
        this.overlay.send_message(
            message_id,
            "",
            "#000000",
            OVERLAY_LEFT_MARGIN, y_pos, 8,
            "large"
        )

def show_message(message_id, text, color="#ff7100", x=2, y=2, size=8, font_weight="normal"):
    """
    Send any overlay row (for advanced custom overlays).
    """
    if ensure_overlay():
        this.overlay.send_message(
            message_id,
            text,
            color,
            x, y, size,
            font_weight
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
                message_id,
                "",
                "#000000",
                OVERLAY_LEFT_MARGIN, y_pos, 8,
                "large"
            )

def ensure_overlay():
    if getattr(this, "overlay_available", False):
        return True
    try:
        from edmcoverlay import Overlay
        this.overlay = Overlay()
        this.overlay.connect()
        this.overlay_available = True
        if hasattr(this, "_overlay_warned"):
            del this._overlay_warned   # Reset warning if we successfully reconnected!
        print("EDMCOverlay: Reconnected successfully!")
        return True
    except Exception as e:
        if not hasattr(this, "_overlay_warned") or not this._overlay_warned:
            print(f"Unable to load EDMCOverlay: {e}")
            this._overlay_warned = True
        this.overlay = None
        this.overlay_available = False
        return False
