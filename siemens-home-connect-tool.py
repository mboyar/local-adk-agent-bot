import os
import sys
import requests
from dotenv import load_dotenv, set_key

def get_headers():
    token = os.environ.get("HOME_CONNECT_ACCESSTOKEN")
    if not token:
        raise ValueError("HOME_CONNECT_ACCESSTOKEN environment variable not set")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.bsh.sdk.v1+json"
    }

def refresh_access_token():
    client_id = os.environ.get("HOME_CONNECT_CLIENTID")
    refresh_token = os.environ.get("HOME_CONNECT_REFRESHTOKEN")
    if not client_id or not refresh_token:
        print("Cannot refresh token: Missing CLIENTID or REFRESHTOKEN.", file=sys.stderr)
        return False
        
    url = "https://api.home-connect.com/security/oauth/token"
    data = {"grant_type": "refresh_token", "refresh_token": refresh_token, "client_id": client_id}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        tokens = response.json()
        new_access_token = tokens.get("access_token")
        new_refresh_token = tokens.get("refresh_token")
        
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if new_access_token:
            set_key(env_path, "HOME_CONNECT_ACCESSTOKEN", new_access_token)
            os.environ["HOME_CONNECT_ACCESSTOKEN"] = new_access_token
        if new_refresh_token:
            set_key(env_path, "HOME_CONNECT_REFRESHTOKEN", new_refresh_token)
            os.environ["HOME_CONNECT_REFRESHTOKEN"] = new_refresh_token
        return True
    except Exception as e:
        print(f"Failed to refresh token: {e}", file=sys.stderr)
        return False

def make_request(url):
    response = requests.get(url, headers=get_headers())
    if response.status_code == 401:
        if refresh_access_token():
            response = requests.get(url, headers=get_headers())
    response.raise_for_status()
    return response.json()

def get_appliances():
    url = "https://api.home-connect.com/api/homeappliances"
    data = make_request(url)
    return data.get("data", {}).get("homeappliances", [])

def get_appliance_status(ha_id):
    url = f"https://api.home-connect.com/api/homeappliances/{ha_id}/status"
    data = make_request(url)
    return data.get("data", {}).get("status", [])

def get_door_status():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(dotenv_path=env_path, override=True)
    
    haid_dishwasher = os.environ.get("HOME_CONNECT_HAID_DISHWASHER")
    haid_fridge = os.environ.get("HOME_CONNECT_HAID_FRIDGEFREEZER")
    
    appliances_to_check = []
    
    if haid_dishwasher or haid_fridge:
        if haid_dishwasher:
            appliances_to_check.append({
                "haId": haid_dishwasher,
                "name": "Dishwasher",
                "type": "Dishwasher"
            })
        if haid_fridge:
            appliances_to_check.append({
                "haId": haid_fridge,
                "name": "FridgeFreezer",
                "type": "FridgeFreezer"
            })
    else:
        try:
            appliances_to_check = get_appliances()
            if not appliances_to_check:
                print("No appliance found.")
                return
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error fetching appliances: {e.response.status_code} - {e.response.text}")
            return
        except Exception as e:
            print(f"Error fetching appliances: {e}")
            return

    for app in appliances_to_check:
        ha_id = app.get("haId")
        name = app.get("name", "Unknown Name")
        app_type = app.get("type", "Unknown Type")
        
        try:
            status_list = get_appliance_status(ha_id)
            door_state = "Unknown"
            for status in status_list:
                if status.get("key") == "BSH.Common.Status.DoorState":
                    door_state = status.get("value", "").split(".")[-1]
                    break
            
            print(f"Device: {name} ({app_type})")
            print(f"HAID: {ha_id}")
            print(f"Door Status: {door_state}")
            print("-" * 30)
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                print(f"Failed to fetch status for {name} ({ha_id}) - HTTP {e.response.status_code}: {e.response.text}")
            else:
                print(f"Failed to fetch status for {name} ({ha_id}): {e}")
            print("-" * 30)

if __name__ == "__main__":
    get_door_status()
