"""
Test script to verify overlay functionality
Run this to test if EDMCOverlay is working
"""

import sys
import os

# Add plugin directory to path
plugin_dir = os.path.dirname(__file__)
sys.path.insert(0, plugin_dir)

import overlay

print("Testing overlay connectivity...")
print(f"Overlay available: {overlay.this.overlay_available}")

if overlay.ensure_overlay():
    print("✓ Overlay connected successfully!")
    
    # Test sending a message
    overlay.show_message("test_msg", "TEST MESSAGE FROM EDMC-PlanetPOI", "#00ff00", 500, 100)
    print("✓ Test message sent")
    
    # Test POI rows
    test_pois = [
        ("Test POI 1 - 45° / 1.2km", True),
        ("Test POI 2 - 90° / 3.5km", False),
        ("Test POI 3 - 180° / 5.0km", False)
    ]
    overlay.show_poi_rows_with_colors(test_pois)
    print("✓ Test POI rows sent")
    
    print("\nOverlay test complete! Check in-game for messages.")
    print("Messages should appear at x=500, starting at y=2")
    
else:
    print("✗ Could not connect to overlay!")
    print("\nTroubleshooting:")
    print("1. Make sure EDMCOverlay.exe is running")
    print("2. Check if EDMCOverlay plugin is installed in EDMC")
    print("3. Try restarting EDMC")

input("\nPress Enter to clear test messages and exit...")

if overlay.ensure_overlay():
    overlay.clear_all_poi_rows()
    overlay.show_message("test_msg", "", "#000000", 500, 100)
    print("Test messages cleared")
