import requests
import csv
import os
import logging

logger = logging.getLogger(__name__)

def fetch_children(auth, url, school_id):
    """
    Fetches all children for a given school ID using pagination.
    """
    children = []
    offset = 0
    limit = 100 # Fetch more per page to reduce requests
    
    base_url = f"{url}/child/child_list_create"
    
    while True:
        logger.info(f"Fetching children offset={offset} limit={limit}...")
        params = {
            "offset": offset,
            "limit": limit,
            "school": school_id,
            "active_academic_calender": "true"
        }
        
        try:
            # auth.session already has the Authorization header
            response = auth.session.get(base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Check structure of response
            # Based on typical pagination, it might be a list or a dict with 'results'
            # The user provided curl output didn't show response, but let's assume standard DRF or similar
            # If data is a list, we append. If it's a dict, we look for results.
            
            results = []
            if isinstance(data, list):
                results = data
            elif isinstance(data, dict) and "results" in data:
                results = data["results"]
            elif isinstance(data, dict) and "data" in data: # Kreedo style might be nested
                 if isinstance(data["data"], list):
                     results = data["data"]
                 elif isinstance(data["data"], dict) and "results" in data["data"]:
                     results = data["data"]["results"]
            
            if not results:
                break
                
            children.extend(results)
            
            if len(results) < limit:
                break
                
            offset += limit
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch children: {e}")
            break
            
    logger.info(f"Fetched {len(children)} children from list. Now fetching details...")
    
    # Get user_id from token for subject fetching
    token = auth.session.headers.get("Authorization", "").split(" ")[1]
    user_id = get_user_id_from_token(token)
    
    # Fetch details for each child
    for i, child in enumerate(children):
        child_id = child.get("id")
        if child_id:
            if i % 10 == 0:
                logger.info(f"Fetching details for child {i+1}/{len(children)}...")
                
            detail_url = f"{url}/child/child_retrive_update_delete/{child_id}"
            try:
                response = auth.session.get(detail_url)
                response.raise_for_status()
                details = response.json()
                
                # Handle potential nesting
                if isinstance(details, dict) and "data" in details:
                    details = details["data"]
                    
                if isinstance(details, dict):
                    child.update(details)
                    
                # Fetch assigned subjects
                # Need academic_session id
                academic_session_id = None
                if "academic_session_data" in child and isinstance(child["academic_session_data"], list):
                     if len(child["academic_session_data"]) > 0:
                         # Try to find active one or just take first
                         # Assuming structure: [{'academic_session': {'id': ...}, ...}]
                         session_data = child["academic_session_data"][0]
                         if "academic_session" in session_data and "id" in session_data["academic_session"]:
                             academic_session_id = session_data["academic_session"]["id"]
                
                if academic_session_id and user_id:
                    subject_url = f"{url}/plan/subject_list_by_child"
                    payload = {
                        "academic_session": academic_session_id,
                        "child": child_id,
                        "plan": "true",
                        "type": "school_associate",
                        "user_id": user_id,
                        "web": "true"
                    }
                    try:
                        sub_response = auth.session.post(subject_url, json=payload)
                        sub_response.raise_for_status()
                        sub_data = sub_response.json()
                        
                        # Handle response structure
                        # Assuming list of subjects or dict with data
                        subjects = []
                        if isinstance(sub_data, list):
                            subjects = sub_data
                        elif isinstance(sub_data, dict) and "data" in sub_data:
                            subjects = sub_data["data"]
                            
                        child["assigned_subjects"] = subjects
                        
                    except requests.exceptions.RequestException as e:
                        logger.error(f"Failed to fetch subjects for child {child_id}: {e}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch details for child {child_id}: {e}")

    logger.info(f"Finished fetching details.")
    return children

import pandas as pd
import base64
import json

def get_user_id_from_token(token):
    try:
        # JWT is header.payload.signature
        payload_part = token.split('.')[1]
        # Pad base64 string
        payload_part += '=' * (-len(payload_part) % 4)
        payload = json.loads(base64.b64decode(payload_part))
        return payload.get('user_id')
    except Exception as e:
        logger.error(f"Failed to decode token: {e}")
        return None

def save_children_to_excel(children, output_dir="child"):
    """
    Saves the list of children to an Excel file with flattening.
    Main sheet contains child details.
    Separate sheets for lists (e.g., parents, subjects).
    """
    if not children:
        logger.warning("No children to save.")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    filepath = os.path.join(output_dir, "children.xlsx")
    
    # Prepare data containers
    main_data = []
    parents_data = []
    subjects_data = []
    
    for child in children:
        # Create a flat copy for the main sheet
        flat_child = child.copy()
        child_id = child.get("id")
        
        # Extract and remove 'parents' list
        if "parents" in flat_child:
            parents = flat_child.pop("parents")
            if isinstance(parents, list):
                for parent in parents:
                    if isinstance(parent, dict):
                        parent["child_id"] = child_id # Link back to child
                        parents_data.append(parent)
        
        # Extract and remove 'parent' dict
        if "parent" in flat_child:
             parent = flat_child.pop("parent")
             if isinstance(parent, dict):
                 parent["child_id"] = child_id
                 parents_data.append(parent)

        # Extract and remove 'assigned_subjects'
        if "assigned_subjects" in flat_child:
            subjects = flat_child.pop("assigned_subjects")
            if isinstance(subjects, list):
                for subject in subjects:
                    if isinstance(subject, dict):
                        subject["child_id"] = child_id
                        subjects_data.append(subject)

        # Flatten other potential lists or complex objects
        for key, value in flat_child.items():
            if isinstance(value, (dict, list)):
                flat_child[key] = str(value)
                
        main_data.append(flat_child)
        
    try:
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Write main sheet
            df_main = pd.DataFrame(main_data)
            df_main.to_excel(writer, sheet_name='Children', index=False)
            
            # Write parents sheet
            if parents_data:
                df_parents = pd.DataFrame(parents_data)
                df_parents.to_excel(writer, sheet_name='Parents', index=False)
            
            # Write subjects sheet
            if subjects_data:
                df_subjects = pd.DataFrame(subjects_data)
                df_subjects.to_excel(writer, sheet_name='Subjects', index=False)
                
        logger.info(f"Saved children data to {filepath}")
    except Exception as e:
        logger.error(f"Failed to write Excel: {e}")

import ast
import re

def fetch_child_activities(auth, url, input_file="child/children.xlsx", child_name_filter=None):
    """
    Reads children and subjects from Excel, fetches plan details for each subject,
    and extracts activities.
    Returns a dictionary: {child_id: [activity_records]}
    """
    if not os.path.exists(input_file):
        logger.error(f"Input file {input_file} not found.")
        return {}, {}

    try:
        df_children = pd.read_excel(input_file, sheet_name="Children")
        df_subjects = pd.read_excel(input_file, sheet_name="Subjects")
    except Exception as e:
        logger.error(f"Failed to read Excel file: {e}")
        return {}, {}

    # Create a map of child_id to child_name for sheet naming
    child_map = {}
    for _, row in df_children.iterrows():
        name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
        child_map[row['id']] = name

    # Filter children if name filter is provided
    if child_name_filter and child_name_filter.lower() != 'all':
        logger.info(f"Filtering children by name: {child_name_filter}")
        # Case-insensitive partial match on full name
        # We need to reconstruct full name for filtering since it's not a single column usually
        # Or we can use the map we just built
        
        filtered_ids = []
        for child_id, name in child_map.items():
            if child_name_filter.lower() in name.lower():
                filtered_ids.append(child_id)
        
        if not filtered_ids:
            logger.warning(f"No children found matching '{child_name_filter}'")
            return {}, {}
            
        # Filter the subjects dataframe to only include these children
        df_subjects = df_subjects[df_subjects['child_id'].isin(filtered_ids)]
        logger.info(f"Found {len(filtered_ids)} matching children.")

    activities_by_child = {}

    # Group subjects by child
    subjects_by_child = df_subjects.groupby('child_id')

    total_children = len(subjects_by_child)
    logger.info(f"Fetching activities for {total_children} children...")

    for i, (child_id, subjects) in enumerate(subjects_by_child):
        if i % 5 == 0:
             logger.info(f"Processing child {i+1}/{total_children}...")
             
        child_activities = []
        
        # Get academic session from the first subject row (assuming same for all subjects of a child)
        # The excel might have it in 'academic_session_data' or we might need to rely on what we have.
        # Actually, the 'Subjects' sheet might not have academic_session_id directly if we didn't save it.
        # But we saved 'assigned_subjects' which came from 'subject_list_by_child'.
        # Let's check if we can get academic_session from the child info in 'Children' sheet.
        
        academic_session_id = None
        child_row = df_children[df_children['id'] == child_id]
        if not child_row.empty:
            # Try to parse academic_session_data
            try:
                raw_session = child_row.iloc[0].get('academic_session_data')
                if pd.notna(raw_session):
                    parsed_session = ast.literal_eval(str(raw_session))
                    if isinstance(parsed_session, list) and len(parsed_session) > 0:
                        academic_session_id = parsed_session[0].get('academic_session', {}).get('id')
            except:
                pass
        
        if not academic_session_id:
            logger.warning(f"Could not find academic_session_id for child {child_id}")
            continue

        for _, subject in subjects.iterrows():
            subject_id = subject.get("id")
            if not subject_id:
                continue
                
            # Fetch completed activities for this subject
            offset = 0
            limit = 50
            while True:
                activity_url = f"{url}/activity/flag_based_activity?offset={offset}&limit={limit}"
                payload = {
                    "flag": "completed",
                    "subject": int(subject_id),
                    "academic_session": int(academic_session_id),
                    "start": "",
                    "end": "",
                    "child": int(child_id)
                }
                
                try:
                    response = auth.session.post(activity_url, json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        if "data" in data:
                            data = data["data"]
                            
                        results = data.get("results", [])
                        if not results:
                            break
                            
                        for act in results:
                            child_activities.append({
                                "Activity ID": act.get("id"),
                                "Activity Name": act.get("name"),
                                "Activity Description": act.get("description"),
                                "Subject": subject.get("subject_label"),
                                "Status": "Completed",
                                "Completed Date": act.get("created_at")
                            })
                        
                        if len(results) < limit:
                            break
                        offset += limit
                    else:
                        logger.warning(f"Failed to fetch activities for child {child_id}, subject {subject_id}: {response.status_code}")
                        break
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Error fetching activities: {e}")
                    break
                
        if child_activities:
            activities_by_child[child_id] = child_activities
            
    return activities_by_child, child_map


def save_activities_to_excel(activities_by_child, child_map, output_dir="child"):
    """
    Saves activities to an Excel file with a separate sheet for each child.
    """
    if not activities_by_child:
        logger.warning("No activities to save.")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    filepath = os.path.join(output_dir, "child_activities.xlsx")
    
    try:
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            for child_id, activities in activities_by_child.items():
                child_name = child_map.get(child_id, f"Child_{child_id}")
                
                # Sanitize sheet name (max 31 chars, no invalid chars)
                sheet_name = re.sub(r'[\\/*?:\[\]]', '', child_name)
                sheet_name = sheet_name[:30] # Truncate to 30 to be safe
                
                # Ensure unique sheet names if truncation causes collision
                # (Simple handling: append ID if needed, but for now just use name)
                
                df = pd.DataFrame(activities)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
        logger.info(f"Saved child activities to {filepath}")
    except Exception as e:
        logger.error(f"Failed to write Activities Excel: {e}")
