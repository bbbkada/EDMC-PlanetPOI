"""
POI Manager module for EDMC-PlanetPOI
Handles loading, saving, and manipulation of POI data structures
"""

import json
import os


# POI file path - will be initialized by calling code
POI_FILE = os.path.join(os.path.dirname(__file__), "poi.json")


def set_poi_file(file_path):
    """Set the POI file path"""
    global POI_FILE
    POI_FILE = file_path


def load_pois():
    """Load POIs from JSON file and return them"""
    if not os.path.exists(POI_FILE):
        return []
    try:
        with open(POI_FILE, "r", encoding="utf8") as f:
            data = json.load(f)
            # Handle migration of old format to new format with separate system/body
            if data and isinstance(data, list):
                migrated = False
                for item in data:
                    # Check if POI needs migration (has old "body" field but not "system" field)
                    if item.get("type") == "poi" and "body" in item and "system" not in item:
                        # Old format: {"body": "HIP 36601 C 3 b"}
                        # New format: {"system": "HIP 36601", "body": "C 3 b"}
                        full_body = item.get("body", "")
                        system_name, body_part = split_system_and_body(full_body)
                        item["system"] = system_name
                        item["body"] = body_part
                        migrated = True
                        print(f"Migrated POI: {full_body} -> system={system_name}, body={body_part}")
                    # Also ensure old non-typed POIs get type field
                    elif "type" not in item:
                        item["type"] = "poi"
                        if "body" in item and "system" not in item:
                            full_body = item.get("body", "")
                            system_name, body_part = split_system_and_body(full_body)
                            item["system"] = system_name
                            item["body"] = body_part
                            migrated = True
                
                if migrated:
                    print("Saving migrated POI format...")
                    save_pois(data)  # Save migrated format
                
                return data
            else:
                return []
    except Exception as ex:
        print(f"Error loading POIs: {ex}")
        return []


def save_pois(all_pois):
    """Save POIs to JSON file"""
    try:
        print("saving pois")
        with open(POI_FILE, "w", encoding="utf8") as f:
            json.dump(all_pois, f, indent=2, ensure_ascii=False)
    except Exception as ex:
        print(f"Error saving POIs: {ex}")


def split_system_and_body(full_body_name):
    """
    Split full body name into system and body parts.
    Example: "HIP 36601 C 3 a b" -> ("HIP 36601", "C 3 a b")
    """
    if not full_body_name:
        return "", ""
    
    parts = full_body_name.split()
    if len(parts) < 3:
        return full_body_name, ""
    
    # Find where body designation starts (first part that's a single char or number)
    for i, part in enumerate(parts):
        if len(part) == 1 or (len(part) == 2 and part[1].isdigit()):
            system_name = " ".join(parts[:i])
            body_name = " ".join(parts[i:])
            return system_name, body_name
    
    # If no clear body designation, treat first 2 parts as system
    if len(parts) >= 2:
        return " ".join(parts[:2]), " ".join(parts[2:])
    
    return full_body_name, ""


def get_full_body_name(poi):
    """Get full body name from POI (combines system + body)."""
    system = poi.get("system", "")
    body = poi.get("body", "")
    if body:
        return f"{system} {body}"
    return system


def get_all_pois_flat(items):
    """Get flat list of all POIs (not folders) from tree structure."""
    pois = []
    def traverse(children):
        for item in children:
            if item.get("type") == "poi":
                pois.append(item)
            elif item.get("type") == "folder":
                traverse(item.get("children", []))
    traverse(items)
    return pois


def find_poi_by_id(items, poi_id):
    """Find POI by ID in tree structure."""
    def search(children, path=None, parents=None):
        if path is None:
            path = []
        if parents is None:
            parents = []
        for item in children:
            if item.get("id") == poi_id:
                return item, path, parents
            if item.get("type") == "folder":
                result = search(item.get("children", []), path + [item.get("name")], parents + [item])
                if result:
                    return result
        return None
    return search(items)


def create_folder(all_pois, parent_children, folder_name):
    """Create new folder."""
    new_folder = {
        "type": "folder",
        "name": folder_name,
        "children": []
    }
    parent_children.append(new_folder)
    save_pois(all_pois)
    return new_folder


def delete_item(all_pois, items, target_item):
    """Delete item (POI or folder) from tree."""
    def remove_from(children):
        for idx, item in enumerate(children):
            if item is target_item:
                children.pop(idx)
                return True
            if item.get("type") == "folder":
                if remove_from(item.get("children", [])):
                    return True
        return False
    if remove_from(items):
        save_pois(all_pois)
        return True
    return False


def move_item(all_pois, items, target_item, new_parent_children):
    """Move item to new parent folder."""
    # First remove from current location
    if delete_item(all_pois, items, target_item):
        # Then add to new location
        new_parent_children.append(target_item)
        save_pois(all_pois)
        return True
    return False


def count_folder_contents(folder):
    """Count total subfolders and POIs in a folder recursively."""
    subfolder_count = 0
    poi_count = 0
    
    def count_recursive(children):
        nonlocal subfolder_count, poi_count
        for item in children:
            if item.get("type") == "folder":
                subfolder_count += 1
                count_recursive(item.get("children", []))
            elif item.get("type") == "poi":
                poi_count += 1
    
    count_recursive(folder.get("children", []))
    return subfolder_count, poi_count


def get_item_location_path(items, target_item, path=""):
    """Get the folder path where an item is located."""
    for item in items:
        if item is target_item:
            return path if path else "(Root level)"
        if item.get("type") == "folder":
            folder_name = item.get("name", "Unnamed")
            new_path = f"{path} > {folder_name}" if path else folder_name
            children = item.get("children", [])
            result = get_item_location_path(children, target_item, new_path)
            if result:
                return result
    return None
