import requests
import pandas as pd
import json
import base64

def get_user_id_from_token(token):
    try:
        payload_part = token.split('.')[1]
        payload_part += '=' * (-len(payload_part) % 4)
        payload = json.loads(base64.b64decode(payload_part))
        return payload.get('user_id')
    except Exception:
        return None

# Load token
with open(".token", "r") as f:
    token = f.read().strip()

user_id = get_user_id_from_token(token)
url = "https://6t.kreedo.solutions/api"

# Load one child to get IDs
df = pd.read_excel("child/children.xlsx", sheet_name="Children")
child = df.iloc[0]
child_id = child["id"]

# Extract academic session
# The excel might have flattened it as string, need to parse or find the column
# In previous step, we saw 'academic_session_data' column
import ast
academic_session_id = None
try:
    session_data_str = child["academic_session_data"]
    session_data = ast.literal_eval(session_data_str)
    if session_data and isinstance(session_data, list):
        academic_session_id = session_data[0]["academic_session"]["id"]
except Exception as e:
    print(f"Error parsing session: {e}")

print(f"Child ID: {child_id}, Session ID: {academic_session_id}, User ID: {user_id}")

if academic_session_id:
    subject_url = f"{url}/plan/subject_list_by_child"
    payload = {
        "academic_session": int(academic_session_id),
        "child": int(child_id),
        "plan": "true",
        "type": "school_associate",
        "user_id": int(user_id),
        "web": "true"
    }
    headers = {"Authorization": f"JWT {token}"}
    
    # Fetch subjects first to get a valid subject ID
    response = requests.post(subject_url, json=payload, headers=headers)
    print(f"Subject List Status: {response.status_code}")
    
    try:
        data = response.json()
        subjects = []
        if isinstance(data, list):
            subjects = data
        elif isinstance(data, dict) and "data" in data:
            subjects = data["data"]
            
        if subjects:
            first_subject = subjects[0]
            subject_id = first_subject.get("id")
            print(f"First Subject ID: {subject_id}")
            
            # Now call flag_based_activity
            activity_url = f"{url}/activity/flag_based_activity?offset=0&limit=10"
            activity_payload = {
                "flag": "completed",
                "subject": int(subject_id),
                "academic_session": int(academic_session_id),
                "start": "",
                "end": "",
                "child": int(child_id)
            }
            print(f"Calling {activity_url} with payload: {activity_payload}")
            
            act_response = requests.post(activity_url, json=activity_payload, headers=headers)
            print(f"Activity Status: {act_response.status_code}")
            
            try:
                act_data = act_response.json()
                # print(json.dumps(act_data, indent=2))
                
                if "data" in act_data:
                    act_data = act_data["data"]
                    
                results = act_data.get("results", [])
                if results:
                    print("First Activity Object:")
                    print(json.dumps(results[0], indent=2))
                else:
                    print("No activities found in response.")
            except Exception as e:
                print(f"Error parsing activity response: {e}")
                print(act_response.text)
            
        else:
            print("No subjects found.")
            
    except Exception as e:
        print(f"Error: {e}")
        if 'act_response' in locals():
            print(act_response.text)
        else:
            print(response.text)
