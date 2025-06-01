import base64
import gzip
import json
import streamlit as st
import io


def decode_save_file(file_content):
    # Decode the base64 encoded gzip data
    decoded_data = base64.b64decode(file_content)
    # Decode the second base64 layer
    decoded_data = base64.b64decode(decoded_data)
    # Decompress the gzip data
    decompressed_data = gzip.decompress(decoded_data)
    # Load the JSON content
    save_json = json.loads(decompressed_data.decode('utf-8'))
    return save_json


def encode_save_file(json_data):
    # Convert the JSON content to string
    json_str = json.dumps(json_data)
    # Compress the JSON string
    compressed_data = gzip.compress(json_str.encode('utf-8'))
    # Encode the compressed data in base64 twice
    encoded_data = base64.b64encode(base64.b64encode(compressed_data))
    return encoded_data


def find_resources_path(json_obj, path=""):
    """Find the path to resources in the JSON structure."""
    if isinstance(json_obj, dict):
        if "resources" in json_obj:
            return path, json_obj
        for key, value in json_obj.items():
            if isinstance(value, dict):
                result = find_resources_path(value, f"{path}.{key}" if path else key)
                if result[0] is not None:
                    return result
    return None, None


def find_buildings_path(json_obj, path=""):
    """Find the path to buildings in the JSON structure."""
    if isinstance(json_obj, dict):
        if "buildings" in json_obj:
            return path, json_obj
        for key, value in json_obj.items():
            if isinstance(value, dict):
                result = find_buildings_path(value, f"{path}.{key}" if path else key)
                if result[0] is not None:
                    return result
    return None, None


def find_inventory_path(json_obj, path=""):
    """Find the path to inventory in the JSON structure."""
    if isinstance(json_obj, dict):
        if "inventory" in json_obj and isinstance(json_obj["inventory"], list):
            return path, json_obj
        for key, value in json_obj.items():
            if isinstance(value, dict):
                result = find_inventory_path(value, f"{path}.{key}" if path else key)
                if result[0] is not None:
                    return result
    return None, None


def find_equipment_path(json_obj, path=""):
    """Find the path to equipment in the JSON structure."""
    if isinstance(json_obj, dict):
        if "equipment" in json_obj and isinstance(json_obj["equipment"], dict):
            return path, json_obj
        for key, value in json_obj.items():
            if isinstance(value, dict):
                result = find_equipment_path(value, f"{path}.{key}" if path else key)
                if result[0] is not None:
                    return result
    return None, None


def edit_resources(save_json):
    """Edit resource values in the save file."""
    st.header("Resources Editor")
    
    # Find the resources in the JSON structure
    resources_path, container = find_resources_path(save_json)
    
    if not container or "resources" not in container:
        st.error("No resources found in the save file!")
        st.json(save_json)  # Display the JSON structure to help debug
        return save_json
    
    resources = container.get("resources", {})
    modified = False
    
    # Create columns for a more compact layout
    col1, col2 = st.columns(2)
    
    # Create a dictionary to store the new values
    updated_resources = {}
    
    # Display input fields for each resource
    for i, (resource_name, value) in enumerate(resources.items()):
        # Alternate between columns
        current_col = col1 if i % 2 == 0 else col2
        
        with current_col:
            # Determine if value is integer or float
            is_int = isinstance(value, int)
            
            if is_int:
                new_value = st.number_input(
                    f"{resource_name}", 
                    value=int(value),
                    step=100,
                    key=f"resource_{resource_name}"
                )
            else:
                new_value = st.number_input(
                    f"{resource_name}", 
                    value=float(value),
                    format="%.2f",
                    step=100.0,
                    key=f"resource_{resource_name}"
                )
                
            updated_resources[resource_name] = new_value
            
            if new_value != value:
                modified = True
    
    # Update the save_json with the new values
    if modified and container:
        container["resources"] = updated_resources
    
    return save_json


def edit_buildings(save_json):
    """Edit building values in the save file."""
    st.header("Buildings Editor")
    
    # Find the buildings in the JSON structure
    buildings_path, container = find_buildings_path(save_json)
    
    if not container or "buildings" not in container:
        st.error("No buildings found in the save file!")
        return save_json
    
    buildings = container.get("buildings", {})
    modified = False
    
    # Create columns for a more compact layout
    col1, col2 = st.columns(2)
    
    # Create a dictionary to store the new values
    updated_buildings = {}
    
    # Display input fields for each building
    for i, (building_name, building_data) in enumerate(buildings.items()):
        # Alternate between columns
        current_col = col1 if i % 2 == 0 else col2
        
        with current_col:
            st.subheader(building_name)
            
            # Initialize the building data
            updated_building = {}
            
            # Edit current value
            current = st.number_input(
                f"{building_name} - Current", 
                value=int(building_data.get("current", 0)),
                step=1,
                key=f"building_{building_name}_current"
            )
            updated_building["current"] = current
            
            # Edit turnedOn value
            turned_on = st.number_input(
                f"{building_name} - Turned On", 
                value=int(building_data.get("turnedOn", 0)),
                step=1,
                key=f"building_{building_name}_turnedOn"
            )
            updated_building["turnedOn"] = turned_on
            
            # Check if values have changed
            if (current != building_data.get("current") or 
                turned_on != building_data.get("turnedOn")):
                modified = True
                
            updated_buildings[building_name] = updated_building
    
    # Update the save_json with the new values
    if modified and container:
        container["buildings"] = updated_buildings
    
    return save_json


def edit_inventory(save_json):
    """Edit inventory item amounts and qualities."""
    st.header("Inventory Editor")
    
    # Find the inventory in the JSON structure
    inventory_path, container = find_inventory_path(save_json)
    
    if not container or "inventory" not in container:
        st.error("No inventory found in the save file!")
        return save_json
    
    inventory = container.get("inventory", [])
    modified = False
    
    # Group items by ID for more organized display
    # This helps when the same item appears multiple times with different qualities
    item_groups = {}
    
    for idx, item in enumerate(inventory):
        if "itemOccurrence" in item and "itemId" in item["itemOccurrence"]:
            item_id = item["itemOccurrence"]["itemId"]
            quality = item["itemOccurrence"].get("params", {}).get("itemQuality", 0)
            
            # Create a unique key for this item+quality combination
            group_key = f"{item_id}_{quality}"
            
            if group_key not in item_groups:
                item_groups[group_key] = {
                    "name": item_id,
                    "quality": quality,
                    "items": []
                }
            
            item_groups[group_key]["items"].append((idx, item))
    
    # Create a search box for filtering items
    search_term = st.text_input("Search items", "")
    
    # Filter items based on search term if provided
    if search_term:
        filtered_groups = {k: v for k, v in item_groups.items() if search_term.lower() in v["name"].lower()}
        if not filtered_groups:
            st.warning(f"No items found matching '{search_term}'")
            filtered_groups = item_groups
    else:
        filtered_groups = item_groups
    
    # Display items in expandable sections grouped by name
    for group_key, group_data in filtered_groups.items():
        item_name = group_data["name"]
        quality = group_data["quality"]
        items = group_data["items"]
        
        # Create an expander for each item type
        quality_text = f" (Quality: {quality})" if quality else ""
        with st.expander(f"{item_name}{quality_text} - {len(items)} item(s)"):
            for idx, (item_idx, item) in enumerate(items):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"Item ID: {item_name}")
                    if quality:
                        st.write(f"Quality: {quality}")
                
                with col2:
                    # Edit amount
                    new_amount = st.number_input(
                        "Amount",
                        value=int(item.get("amount", 1)),
                        min_value=1,
                        step=1,
                        key=f"inventory_amount_{item_idx}"
                    )
                    
                    # Edit quality if params exist
                    if "params" in item["itemOccurrence"] and "itemQuality" in item["itemOccurrence"]["params"]:
                        new_quality = st.number_input(
                            "Quality",
                            value=int(item["itemOccurrence"]["params"].get("itemQuality", 1)),
                            min_value=1,
                            step=1,
                            key=f"inventory_quality_{item_idx}"
                        )
                        
                        # Check if quality changed
                        if new_quality != item["itemOccurrence"]["params"].get("itemQuality", 1):
                            item["itemOccurrence"]["params"]["itemQuality"] = new_quality
                            modified = True
                    
                    # Check if amount changed
                    if new_amount != item.get("amount", 1):
                        item["amount"] = new_amount
                        modified = True
    
    # Update the save_json with the modified inventory
    if modified:
        # No need to reassign as we modified the items in place
        pass
    
    return save_json


def edit_equipment(save_json):
    """Edit equipped items."""
    st.header("Equipment Editor")
    
    # Find the equipment in the JSON structure
    equipment_path, container = find_equipment_path(save_json)
    
    if not container or "equipment" not in container:
        st.error("No equipment found in the save file!")
        return save_json
    
    equipment = container.get("equipment", {})
    modified = False
    
    # Create tabs for each equipment slot
    slot_tabs = st.tabs(list(equipment.keys()))
    
    for i, slot_name in enumerate(equipment.keys()):
        with slot_tabs[i]:
            st.subheader(f"{slot_name} Slot")
            
            slot_items = equipment[slot_name]
            
            # Display each equipped item
            for idx, item in enumerate(slot_items):
                with st.expander(f"Item {idx+1}: {item.get('itemId', 'Unknown')}"):
                    st.write(f"Item ID: {item.get('itemId', 'Unknown')}")
                    
                    # Edit quality if it exists
                    if "params" in item and "itemQuality" in item["params"]:
                        new_quality = st.number_input(
                            "Quality",
                            value=int(item["params"].get("itemQuality", 1)),
                            min_value=1,
                            step=1,
                            key=f"equipment_{slot_name}_{idx}_quality"
                        )
                        
                        # Check if quality changed
                        if new_quality != item["params"].get("itemQuality", 1):
                            item["params"]["itemQuality"] = new_quality
                            modified = True
    
    # No need to reassign equipment as we modified it in place
    
    return save_json


def view_raw_json(save_json):
    """View and edit the raw JSON of the save file."""
    st.header("Raw JSON Editor")
    
    json_editor = st.text_area(
        "Edit the raw JSON content",
        value=json.dumps(save_json, indent=4),
        height=400
    )
    
    try:
        updated_json = json.loads(json_editor)
        return updated_json
    except json.JSONDecodeError:
        st.error("Invalid JSON! Changes won't be saved.")
        return save_json


st.title("Magic Research 2 Save File Editor")

uploaded_file = st.file_uploader("Upload your .sav file", type=["sav"])

if uploaded_file is not None:
    save_json = decode_save_file(uploaded_file.getvalue())
    st.write("Save file loaded successfully!")
    
    # Debug: Show the top-level structure of the save file
    st.expander("Debug: Save File Structure").json({k: type(v).__name__ for k, v in save_json.items()})
    
    # Create tabs for different editing sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Resources", "Buildings", "Inventory", "Equipment", "Raw JSON"])
    
    with tab1:
        save_json = edit_resources(save_json)
    
    with tab2:
        save_json = edit_buildings(save_json)
    
    with tab3:
        save_json = edit_inventory(save_json)
    
    with tab4:
        save_json = edit_equipment(save_json)
    
    with tab5:
        save_json = view_raw_json(save_json)
    
    if st.button("Save Changes"):
        try:
            modified_save_file = encode_save_file(save_json)

            st.download_button(
                label="Download Modified Save File",
                data=modified_save_file,
                file_name="modified_save.sav",
                mime="application/octet-stream"
            )
            st.success("Changes saved successfully! Download the modified save file.")
        except Exception as e:
            st.error(f"Error saving changes: {str(e)}")