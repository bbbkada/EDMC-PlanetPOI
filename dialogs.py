"""
Dialogs module for EDMC-PlanetPOI
Contains all dialog windows (add POI, move, delete, share, etc.)
"""

import tkinter as tk
import tkinter.messagebox as mb
from calculations import scale_geometry, format_body_name
from poi_manager import split_system_and_body
from AutoCompleter import AutoCompleter
import functools
import l10n

plugin_tl = functools.partial(l10n.translations.tl, context=__file__)

# External dependencies - will be set by load.py
get_globals = None
get_callbacks = None


def init_dialogs(globals_getter, callbacks_getter):
    """Initialize dialogs with getters for external dependencies"""
    global get_globals, get_callbacks
    get_globals = globals_getter
    get_callbacks = callbacks_getter


def show_add_poi_dialog(parent_frame, prefill_system=None, edit_poi=None, parent_children=None):
    """Show dialog to add a new POI or edit existing POI"""
    g = get_globals()
    cb = get_callbacks()
    
    ALL_POIS = g['ALL_POIS']
    CURRENT_SYSTEM = g['CURRENT_SYSTEM']
    last_body = g['last_body']
    last_lat = g['last_lat']
    last_lon = g['last_lon']
    
    dialog = tk.Toplevel(parent_frame)
    is_edit_mode = edit_poi is not None
    
    if parent_children is None:
        parent_children = ALL_POIS
    
    dialog.title("Edit POI" if is_edit_mode else "Add New POI")
    dialog.geometry(scale_geometry(550, 650))
    dialog.transient(parent_frame)
    dialog.grab_set()
    
    # Center the dialog
    dialog.update_idletasks()
    screen_width = dialog.winfo_screenwidth()
    screen_height = dialog.winfo_screenheight()
    dialog_width = dialog.winfo_width()
    dialog_height = dialog.winfo_height()
    
    x = parent_frame.winfo_rootx() + (parent_frame.winfo_width() // 2) - (dialog_width // 2)
    y = parent_frame.winfo_rooty() + (parent_frame.winfo_height() // 2) - (dialog_height // 2)
    
    x = max(0, min(x, screen_width - dialog_width))
    y = max(0, min(y, screen_height - dialog_height))
    
    dialog.geometry(f"+{x}+{y}")
    
    # Determine auto-fill values
    auto_system = CURRENT_SYSTEM or ""
    auto_body = ""
    auto_lat = ""
    auto_lon = ""
    auto_desc = ""
    auto_notes = ""
    
    if is_edit_mode:
        auto_system = edit_poi.get("system", "")
        auto_body = edit_poi.get("body", "")
        lat_val = edit_poi.get("lat", "")
        lon_val = edit_poi.get("lon", "")
        auto_lat = str(lat_val) if lat_val not in ["", None] else ""
        auto_lon = str(lon_val) if lon_val not in ["", None] else ""
        auto_desc = edit_poi.get("description", "")
        auto_notes = edit_poi.get("notes", "")
    else:
        if last_body:
            system_part, body_part = split_system_and_body(last_body)
            auto_system = system_part
            auto_body = body_part
            if last_lat is not None and last_lon is not None:
                auto_lat = str(last_lat)
                auto_lon = str(last_lon)
        
        if prefill_system:
            system_part, body_part = split_system_and_body(prefill_system)
            auto_system = system_part if system_part else prefill_system
            if body_part and not auto_body:
                auto_body = body_part
    
    dialog.grid_columnconfigure(1, weight=1)
    
    row = 0
    
    paste_btn = tk.Button(dialog, text="📋 Paste shared link", width=18)
    paste_btn.grid(row=row, column=1, sticky="e", padx=(10, 20), pady=(5, 10))
    row += 1
    
    tk.Label(dialog, text="System Name:").grid(row=row, column=0, sticky="w", padx=10, pady=5)
    system_entry = AutoCompleter(dialog, "System Name", width=30)
    system_entry.grid(row=row, column=1, padx=(10, 20), pady=5, sticky="ew")
    
    if auto_system:
        system_entry.set_text(auto_system, placeholder_style=False)
    
    system_var = system_entry.var
    row += 2
    
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
    desc_var = tk.StringVar(value=auto_desc)
    desc_entry = tk.Entry(dialog, textvariable=desc_var, width=30)
    desc_entry.grid(row=row, column=1, padx=(10, 20), pady=5, sticky="ew")
    row += 1
    
    tk.Label(dialog, text="Notes:").grid(row=row, column=0, sticky="nw", padx=10, pady=5)
    notes_text = tk.Text(dialog, width=40, height=8, wrap=tk.WORD, font="TkDefaultFont")
    notes_text.grid(row=row, column=1, padx=(10, 20), pady=5, sticky="ew")
    if auto_notes:
        notes_text.insert("1.0", auto_notes)
    row += 1
    
    status_label = tk.Label(dialog, text="", fg="red")
    status_label.grid(row=row, column=0, columnspan=2, pady=(2, 5))
    row += 1
    
    def paste_from_clipboard():
        try:
            clipboard_text = dialog.clipboard_get().strip()
            poi_data = cb['parse_share_url'](clipboard_text)
            
            if poi_data:
                system_name = poi_data.get('system', '')
                body_part = poi_data.get('body', '')
                
                system_entry.set_text(system_name, placeholder_style=False)
                body_var.set(body_part)
                lat_var.set(str(poi_data.get('lat', '')))
                lon_var.set(str(poi_data.get('lon', '')))
                desc_var.set(poi_data.get('description', ''))
                notes_text.delete("1.0", tk.END)
                notes_text.insert("1.0", poi_data.get('notes', ''))
                
                status_label.config(text="✓ Loaded from shared link", fg="green")
            else:
                status_label.config(text="No valid link found in clipboard", fg="red")
        except Exception:
            status_label.config(text="No link found in clipboard", fg="red")
    
    paste_btn.config(command=paste_from_clipboard)
    
    def on_paste(event):
        widget = event.widget
        dialog.after(10, lambda: check_for_share_link(widget))
    
    def check_for_share_link(widget):
        try:
            text = widget.get()
            if 'github.io/EDMC-PlanetPOI' in text or '#' in text:
                poi_data = cb['parse_share_url'](text)
                if poi_data:
                    if widget == system_entry:
                        system_entry.set_text("", placeholder_style=False)
                    elif hasattr(widget, 'delete'):
                        widget.delete(0, tk.END)
                    
                    system_name = poi_data.get('system', '')
                    body_part = poi_data.get('body', '')
                    
                    system_entry.set_text(system_name, placeholder_style=False)
                    body_var.set(body_part)
                    lat_var.set(str(poi_data.get('lat', '')))
                    lon_var.set(str(poi_data.get('lon', '')))
                    desc_var.set(poi_data.get('description', ''))
                    notes_text.delete("1.0", tk.END)
                    notes_text.insert("1.0", poi_data.get('notes', ''))
                    
                    status_label.config(text="✓ Auto-loaded from shared link", fg="green")
        except Exception:
            pass
    
    system_entry.bind('<Control-v>', on_paste)
    body_entry.bind('<Control-v>', on_paste)
    lat_entry.bind('<Control-v>', on_paste)
    lon_entry.bind('<Control-v>', on_paste)
    desc_entry.bind('<Control-v>', on_paste)
    notes_text.bind('<Control-v>', on_paste)
    
    def save_and_close():
        system = system_var.get().strip()
        body = body_var.get().strip()
        
        if not system:
            status_label.config(text="System name is required!", fg="red")
            return
        
        if body:
            formatted_body = format_body_name(body)
        else:
            formatted_body = ""
        
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
            lat = ""
            lon = ""
        
        desc = desc_var.get().strip()
        notes = notes_text.get("1.0", tk.END).strip()
        
        if is_edit_mode:
            edit_poi["system"] = system
            edit_poi["body"] = formatted_body
            edit_poi["lat"] = lat
            edit_poi["lon"] = lon
            edit_poi["description"] = desc
            edit_poi["notes"] = notes
        else:
            new_poi = {
                "type": "poi",
                "system": system,
                "body": formatted_body,
                "lat": lat,
                "lon": lon,
                "description": desc,
                "notes": notes,
                "active": True
            }
            parent_children.append(new_poi)
        
        cb['save_pois']()
        cb['redraw_plugin_app']()
        cb['update_overlay_for_current_position']()
        
        dialog.destroy()
    
    button_frame = tk.Frame(dialog)
    button_frame.grid(row=row, column=1, sticky="e", padx=(10, 20), pady=(5, 20))
    
    tk.Button(button_frame, text="Cancel", command=dialog.destroy, width=10).pack(side="left", padx=(0, 5))
    tk.Button(button_frame, text="Save", command=save_and_close, width=10).pack(side="left")
    
    desc_entry.focus()


def show_add_folder_dialog(frame, parent_children):
    """Show dialog to add new folder"""
    cb = get_callbacks()
    
    popup = tk.Toplevel()
    popup.title(plugin_tl("Add Folder"))
    popup.geometry(scale_geometry(400, 150))
    
    tk.Label(popup, text=plugin_tl("Folder name:")).pack(pady=10)
    
    name_var = tk.StringVar()
    entry = tk.Entry(popup, textvariable=name_var, width=40)
    entry.pack(pady=10, padx=20)
    entry.focus()
    
    def save_and_close(event=None):
        folder_name = name_var.get().strip()
        if folder_name:
            cb['create_folder'](parent_children, folder_name)
            cb['redraw_plugin_app']()
            popup.destroy()
    
    entry.bind("<Return>", save_and_close)
    popup.bind("<Return>", save_and_close)
    
    tk.Button(popup, text=plugin_tl("Add"), command=save_and_close).pack(pady=10)


def show_move_dialog(frame, item, item_type, is_prefs=False):
    """Show dialog to move POI or folder to different parent"""
    g = get_globals()
    cb = get_callbacks()
    
    ALL_POIS = g['ALL_POIS']
    
    in_config_dialog = False
    try:
        toplevel = frame.winfo_toplevel()
        if toplevel.winfo_class() == 'Toplevel' and 'Configuration' in str(toplevel.title()):
            in_config_dialog = True
            is_prefs = True
    except Exception:
        pass
    
    if is_prefs:
        parent = frame.winfo_toplevel()
    else:
        parent = frame
    
    popup = tk.Toplevel()
    popup.title(plugin_tl(f"Move {item_type}"))
    popup.geometry(scale_geometry(500, 450))
    
    if is_prefs:
        popup.transient(parent)
    
    tk.Label(popup, text=plugin_tl("Select destination folder:")).pack(pady=(10, 5), padx=10)
    
    listbox_frame = tk.Frame(popup)
    listbox_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
    
    scrollbar = tk.Scrollbar(listbox_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    listbox = tk.Listbox(listbox_frame, width=50, yscrollcommand=scrollbar.set)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=listbox.yview)
    
    folder_map = {0: ALL_POIS}
    current_parent = None
    current_index = None
    
    listbox.insert(tk.END, "(Root level)")
    
    def find_parent(items, target, parent=None):
        for it in items:
            if it is target:
                return parent
            if it.get("type") == "folder":
                result = find_parent(it.get("children", []), target, it)
                if result is not None:
                    return result
        return None
    
    current_parent = find_parent(ALL_POIS, item)
    
    if current_parent is None and item in ALL_POIS:
        current_index = 0
    
    def add_folders(items, indent=0):
        nonlocal current_index
        for it in items:
            if it.get("type") == "folder" and it is not item:
                idx = listbox.size()
                folder_map[idx] = it.get("children", [])
                prefix = "  " * indent + "📁 "
                listbox.insert(tk.END, f"{prefix}{it.get('name', 'Unnamed')}")
                
                if it is current_parent:
                    current_index = idx
                
                add_folders(it.get("children", []), indent + 1)
    
    add_folders(ALL_POIS)
    
    if current_index is not None:
        listbox.selection_set(current_index)
        listbox.activate(current_index)
        listbox.see(current_index)
    
    def move_and_close():
        selection = listbox.curselection()
        if selection:
            idx = selection[0]
            target_children = folder_map.get(idx, ALL_POIS)
            if cb['move_item'](ALL_POIS, item, target_children):
                cb['save_pois']()
                if is_prefs:
                    popup.grab_release()
                popup.destroy()
                if not in_config_dialog:
                    cb['redraw_plugin_app']()
                    if is_prefs:
                        try:
                            frame.after(10, lambda: cb['redraw_prefs'](frame))
                        except Exception:
                            pass
    
    def cancel_and_close():
        if is_prefs:
            popup.grab_release()
        popup.destroy()
    
    button_frame = tk.Frame(popup)
    button_frame.pack(side=tk.BOTTOM, pady=10, padx=10)
    tk.Button(button_frame, text=plugin_tl("Move"), command=move_and_close, width=15).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text=plugin_tl("Cancel"), command=cancel_and_close, width=15).pack(side=tk.LEFT, padx=5)
    
    popup.focus_set()
    if is_prefs:
        popup.grab_set()


def confirm_delete_item(frame, item, item_type):
    """Confirm and delete item"""
    g = get_globals()
    cb = get_callbacks()
    
    ALL_POIS = g['ALL_POIS']
    
    try:
        item_name = item.get("description", "") if item_type == "poi" else item.get("name", "")
        
        if item_type == "folder":
            subfolder_count, poi_count = cb['count_folder_contents'](item)
            if subfolder_count > 0 or poi_count > 0:
                message = plugin_tl(f"Are you sure you want to delete this folder?\n\n{item_name}\n\n")
                message += plugin_tl("This will also delete:\n")
                if subfolder_count > 0:
                    message += plugin_tl(f"• {subfolder_count} subfolder(s)\n")
                if poi_count > 0:
                    message += plugin_tl(f"• {poi_count} POI(s)")
            else:
                message = plugin_tl(f"Are you sure you want to delete this {item_type}?\n\n{item_name}")
        else:
            message = plugin_tl(f"Are you sure you want to delete this {item_type}?\n\n{item_name}")
        
        if mb.askyesno(
            plugin_tl(f"Delete {item_type}"),
            message
        ):
            if cb['delete_item'](ALL_POIS, item):
                cb['redraw_plugin_app']()
    except Exception as ex:
        print(f"Error deleting item: {ex}")


def show_share_popup(parent, poi):
    """Show popup dialog with shareable URL and copy button"""
    cb = get_callbacks()
    
    share_url = cb['generate_share_url'](poi)
    
    popup = tk.Toplevel(parent)
    popup.title(plugin_tl("Share POI"))
    popup.geometry(scale_geometry(500, 170))
    popup.resizable(False, False)
    popup.transient(parent)
    
    popup.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (popup.winfo_width() // 2)
    y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (popup.winfo_height() // 2)
    popup.geometry(f"+{x}+{y}")
    
    label = tk.Label(popup, text=plugin_tl("Copy this link to share the POI:"))
    label.pack(pady=(10, 5), padx=10)
    
    url_var = tk.StringVar(value=share_url)
    url_entry = tk.Entry(popup, textvariable=url_var, width=60)
    url_entry.pack(pady=5, padx=10, fill=tk.X)
    url_entry.select_range(0, tk.END)
    url_entry.focus()
    
    def copy_to_clipboard():
        popup.clipboard_clear()
        popup.clipboard_append(share_url)
        popup.destroy()
    
    copy_btn = tk.Button(popup, text=plugin_tl("Copy to clipboard"), command=copy_to_clipboard)
    copy_btn.pack(pady=10)
    
    def close_popup(event=None):
        popup.destroy()
    
    popup.bind("<Escape>", close_popup)
    popup.bind("<FocusOut>", lambda e: popup.after(100, lambda: popup.destroy() if not popup.focus_get() else None))
    
    popup.grab_set()
