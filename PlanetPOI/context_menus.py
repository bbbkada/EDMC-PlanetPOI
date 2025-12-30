"""
Context Menu module for EDMC-PlanetPOI
Handles right-click menus for POI tree items
"""

import tkinter as tk
from tkinter import ttk

# References to load.py globals (set by init function)
get_poi_manager = None
get_callbacks = None


def init_context_menus(poi_getter, callbacks_getter):
    """Initialize context menus with getters for external dependencies"""
    global get_poi_manager, get_callbacks
    get_poi_manager = poi_getter
    get_callbacks = callbacks_getter


def show_poi_context_menu(event, tree, item, poi_or_folder):
    """Show context menu for POI tree item"""
    from PlanetPOI.poi_manager import get_all_pois_flat, ALL_POIS
    
    callbacks = get_callbacks()
    
    menu = tk.Menu(tree, tearoff=0)
    
    is_folder = poi_or_folder.get("type") == "folder"
    
    if is_folder:
        # Folder menu
        menu.add_command(label="Add POI", command=lambda: callbacks['show_add_poi_dialog'](poi_or_folder))
        menu.add_command(label="Add Subfolder", command=lambda: callbacks['show_add_folder_dialog'](poi_or_folder))
        menu.add_separator()
        menu.add_command(label="Rename", command=lambda: callbacks['show_rename_folder_dialog'](poi_or_folder))
        menu.add_command(label="Move...", command=lambda: callbacks['show_move_dialog'](poi_or_folder))
        menu.add_separator()
        menu.add_command(label="Delete", command=lambda: callbacks['confirm_delete_item'](poi_or_folder))
    else:
        # POI menu
        menu.add_command(label="Edit", command=lambda: callbacks['show_edit_poi_dialog'](poi_or_folder))
        menu.add_command(label="Move...", command=lambda: callbacks['show_move_dialog'](poi_or_folder))
        menu.add_separator()
        
        # Add "Set as Active" option
        is_active = poi_or_folder.get("active", True)
        if is_active:
            menu.add_command(label="Deactivate", command=lambda: toggle_poi_active(poi_or_folder, tree))
        else:
            menu.add_command(label="Set as Active", command=lambda: toggle_poi_active(poi_or_folder, tree))
        
        menu.add_separator()
        menu.add_command(label="Delete", command=lambda: callbacks['confirm_delete_item'](poi_or_folder))
    
    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()


def toggle_poi_active(poi, tree):
    """Toggle active state of POI"""
    from PlanetPOI.poi_manager import save_pois, ALL_POIS
    
    poi["active"] = not poi.get("active", True)
    save_pois(ALL_POIS)
    
    callbacks = get_callbacks()
    if callbacks.get('redraw_prefs'):
        callbacks['redraw_prefs']()


def show_menu_dropdown(event, tree, menu_button):
    """Show dropdown menu for menu button at top of tree"""
    callbacks = get_callbacks()
    
    menu = tk.Menu(menu_button, tearoff=0)
    menu.add_command(label="Add POI at Root", command=lambda: callbacks['show_add_poi_dialog'](None))
    menu.add_command(label="Add Folder at Root", command=lambda: callbacks['show_add_folder_dialog'](None))
    menu.add_separator()
    menu.add_command(label="Share POIs...", command=callbacks['show_share_popup'])
    menu.add_command(label="Import POIs...", command=callbacks['show_import_dialog'])
    menu.add_separator()
    menu.add_command(label="Expand All", command=lambda: expand_all(tree))
    menu.add_command(label="Collapse All", command=lambda: collapse_all(tree))
    
    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()


def expand_all(tree):
    """Recursively expand all tree items"""
    def expand_recursive(item):
        tree.item(item, open=True)
        for child in tree.get_children(item):
            expand_recursive(child)
    
    for item in tree.get_children():
        expand_recursive(item)


def collapse_all(tree):
    """Recursively collapse all tree items"""
    def collapse_recursive(item):
        tree.item(item, open=False)
        for child in tree.get_children(item):
            collapse_recursive(child)
    
    for item in tree.get_children():
        collapse_recursive(item)
