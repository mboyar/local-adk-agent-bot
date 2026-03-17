import os
import sys
import time
import hmac
import hashlib
import base64
import json
import requests
import urllib3
from dotenv import load_dotenv, set_key

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=env_path, override=True)

APP_ID = os.environ.get("EWELINK_APPID")
APP_SECRET = os.environ.get("EWELINK_APPSECRET")
EMAIL = os.environ.get("EWELINK_EMAIL")
PASSWORD = os.environ.get("EWELINK_PASSWORD")
REGION = os.environ.get("EWELINK_REGION", "as")
REDIRECT_URL = os.environ.get("EWELINK_REDIRECT_URL", "http://localhost:8722")

REGION_URLS = {
    "as": "https://as-apia.coolkit.cc",
    "us": "https://us-apia.coolkit.cc",
    "eu": "https://eu-apia.coolkit.cc",
    "cn": "https://cn-apia.coolkit.cn"
}

BASE_URL = REGION_URLS.get(REGION, REGION_URLS["as"])


def sign(secret: str, message: bytes) -> str:
    """HMAC-SHA256 sign the message bytes with the secret, return base64."""
    sig = hmac.new(secret.encode('utf-8'), message, hashlib.sha256).digest()
    return base64.b64encode(sig).decode('utf-8')


def get_nonce():
    import uuid
    return str(uuid.uuid4())[:8]


# ── Authentication ───────────────────────────────────────────────────────

def login_via_oauth_code():
    """
    Get an OAuth authorization code directly via API (no browser needed),
    then exchange it for an access token.
    
    Replicates the exact request the browser OAuth page makes to
    /v2/user/oauth/code.
    """
    global BASE_URL
    if not EMAIL or not PASSWORD:
        print("Error: EWELINK_EMAIL and EWELINK_PASSWORD must be set in .env", file=sys.stderr)
        return None

    seq = str(int(time.time() * 1000))
    nonce = get_nonce()

    # The authorization value is Sign(AppSecret, "clientId_seq") — same as URL param
    auth_signature = sign(APP_SECRET, f"{APP_ID}_{seq}".encode('utf-8'))

    # Build the exact payload the browser sends
    payload = {
        "password": PASSWORD,
        "clientId": APP_ID,
        "state": nonce,
        "redirectUrl": REDIRECT_URL,
        "authorization": f"Sign {auth_signature}",
        "nonce": nonce,
        "seq": seq,
        "grantType": "authorization_code",
        "email": EMAIL,
    }

    # The Authorization header is the SAME Sign value from URL params, NOT a body signature
    headers = {
        "authorization": f"Sign {auth_signature}",
        "x-ck-appid": APP_ID,
        "x-ck-nonce": nonce,
        "x-ck-seq": seq,
        "Content-Type": "application/json; charset=utf-8",
    }

    # Try all possible endpoints
    code_endpoints = [
        f"{BASE_URL}/v2/user/oauth/code",
        "https://apia.coolkit.cc/v2/user/oauth/code",
        "https://apia.coolkit.cn/v2/user/oauth/code",
    ]

    code = None
    for url in code_endpoints:
        try:
            print(f"Trying: {url}", file=sys.stderr)
            response = requests.post(url, json=payload, headers=headers, verify=False, timeout=10)
            resp = response.json()
            print(f"  Response: error={resp.get('error')}, msg={resp.get('msg')}", file=sys.stderr)

            if resp.get("error") == 0:
                # The response may contain redirectUrl with ?code=XXX&region=YY
                redirect_data = resp.get("data", {})
                code = redirect_data.get("code")
                # Sometimes the code is in the redirectUrl itself
                redirect_url = redirect_data.get("redirectUrl", "")
                if not code and "code=" in redirect_url:
                    from urllib.parse import urlparse, parse_qs
                    parsed = urlparse(redirect_url)
                    params = parse_qs(parsed.query)
                    code = params.get("code", [None])[0]
                if code:
                    print(f"  Got authorization code!", file=sys.stderr)
                    # Check if region changed
                    region = redirect_data.get("region") or (
                        parse_qs(urlparse(redirect_url).query).get("region", [None])[0]
                        if redirect_url else None
                    )
                    if region:
                        BASE_URL = REGION_URLS.get(region, BASE_URL)
                        if region != os.environ.get("EWELINK_REGION"):
                            set_key(env_path, "EWELINK_REGION", region)
                            os.environ["EWELINK_REGION"] = region
                            print(f"Updated region to {region} in .env", file=sys.stderr)
                    break
        except Exception as e:
            print(f"  Failed: {e}", file=sys.stderr)

    if not code:
        print("Could not obtain authorization code via any endpoint.", file=sys.stderr)
        return None

    # Exchange code for token
    return exchange_code_for_token(code)


def login_direct():
    """
    Try direct login via /v2/user/login.
    This may fail with error 407 if the APPID doesn't support it.
    """
    global BASE_URL
    if not EMAIL or not PASSWORD:
        print("Error: EWELINK_EMAIL and EWELINK_PASSWORD must be set in .env", file=sys.stderr)
        return None

    payload = {
        "password": PASSWORD,
        "countryCode": "+90"
    }
    if "@" in EMAIL:
        payload["email"] = EMAIL
    else:
        payload["phoneNumber"] = EMAIL

    data = json.dumps(payload).encode('utf-8')
    signature = sign(APP_SECRET, data)

    headers = {
        "Authorization": f"Sign {signature}",
        "Content-Type": "application/json",
        "X-CK-Appid": APP_ID,
    }

    try:
        response = requests.post(
            f"{BASE_URL}/v2/user/login",
            data=data,
            headers=headers,
            verify=False,
            timeout=10
        )
        resp = response.json()

        # Handle wrong region redirect
        if resp.get("error") == 10004:
            new_region = resp.get("data", {}).get("region")
            if new_region:
                BASE_URL = REGION_URLS.get(new_region, BASE_URL)
                set_key(env_path, "EWELINK_REGION", new_region)
                os.environ["EWELINK_REGION"] = new_region
                print(f"Updated region to {new_region} in .env", file=sys.stderr)
                response = requests.post(
                    f"{BASE_URL}/v2/user/login",
                    data=data, headers=headers, verify=False, timeout=10
                )
                resp = response.json()

        if resp.get("error") != 0:
            print(f"Direct login: {resp.get('msg')} (Code: {resp.get('error')})", file=sys.stderr)
            return None

        at = resp.get("data", {}).get("at")
        rt = resp.get("data", {}).get("rt")
        if at:
            set_key(env_path, "EWELINK_ACCESSTOKEN", at)
            os.environ["EWELINK_ACCESSTOKEN"] = at
            if rt:
                set_key(env_path, "EWELINK_REFRESHTOKEN", rt)
                os.environ["EWELINK_REFRESHTOKEN"] = rt
            print("Direct login successful!", file=sys.stderr)
            return at
        return None
    except Exception as e:
        print(f"Direct login failed: {e}", file=sys.stderr)
        return None


def exchange_code_for_token(code: str):
    """Exchange the OAuth authorization code for an access token."""
    body = {
        "code": code,
        "redirectUrl": REDIRECT_URL,
        "grantType": "authorization_code"
    }

    # Use compact JSON for consistency
    data = json.dumps(body, sort_keys=True, separators=(',', ':')).encode('utf-8')
    signature = sign(APP_SECRET, data)
    nonce = get_nonce()

    headers = {
        "X-CK-Appid": APP_ID,
        "X-CK-Nonce": nonce,
        "Authorization": f"Sign {signature}",
        "Content-Type": "application/json",
    }

    print(f"Exchanging code for token at {BASE_URL}/v2/user/oauth/token...", file=sys.stderr)
    try:
        response = requests.post(
            f"{BASE_URL}/v2/user/oauth/token",
            data=data, headers=headers, verify=False, timeout=10
        )
        resp = response.json()
        print(f"Token exchange response: {resp}", file=sys.stderr)

        if resp.get("error") != 0:
            print(f"Token exchange failed: {resp.get('msg')} (Code: {resp.get('error')})", file=sys.stderr)
            return None

        token_data = resp.get("data", {})
        at = token_data.get("at") or token_data.get("accessToken")
        rt = token_data.get("rt") or token_data.get("refreshToken")

        if at:
            set_key(env_path, "EWELINK_ACCESSTOKEN", at)
            os.environ["EWELINK_ACCESSTOKEN"] = at
            print("Access token saved!", file=sys.stderr)
        if rt:
            set_key(env_path, "EWELINK_REFRESHTOKEN", rt)
            os.environ["EWELINK_REFRESHTOKEN"] = rt
            print("Refresh token saved!", file=sys.stderr)

        return at
    except Exception as e:
        print(f"Token exchange failed: {e}", file=sys.stderr)
        return None


def refresh_token():
    """Refresh the access token using the stored refresh token."""
    rt = os.environ.get("EWELINK_REFRESHTOKEN")
    if not rt:
        return None

    body = {"rt": rt}
    data = json.dumps(body).encode('utf-8')
    signature = sign(APP_SECRET, data)
    nonce = get_nonce()

    headers = {
        "X-CK-Appid": APP_ID,
        "X-CK-Nonce": nonce,
        "Authorization": f"Sign {signature}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            f"{BASE_URL}/v2/user/refresh",
            data=data, headers=headers, verify=False, timeout=10
        )
        resp = response.json()

        if resp.get("error") != 0:
            return None

        token_data = resp.get("data", {})
        at = token_data.get("at")
        rt_new = token_data.get("rt")

        if at:
            set_key(env_path, "EWELINK_ACCESSTOKEN", at)
            os.environ["EWELINK_ACCESSTOKEN"] = at
        if rt_new:
            set_key(env_path, "EWELINK_REFRESHTOKEN", rt_new)
            os.environ["EWELINK_REFRESHTOKEN"] = rt_new

        print("Token refreshed!", file=sys.stderr)
        return at
    except Exception as e:
        return None


def get_thing(device_id):
    """Retrieves details for a specific device ID."""
    headers = get_bearer_headers()
    if not headers:
        return None

    body = {
        "thingList": [
            {"itemType": 1, "id": device_id}
        ]
    }

    try:
        response = requests.post(
            f"{BASE_URL}/v2/device/thing",
            headers=headers,
            json=body,
            verify=False, timeout=10
        )
        resp = response.json()
        print(f"Get thing response: {resp}", file=sys.stderr)
        return resp
    except Exception as e:
        print(f"Get thing request failed: {e}", file=sys.stderr)
        return None


def get_user_profile():
    """Retrieves the user profile information."""
    headers = get_bearer_headers()
    if not headers:
        return None

    try:
        response = requests.get(
            f"{BASE_URL}/v2/user/profile",
            headers=headers,
            verify=False, timeout=10
        )
        resp = response.json()
        print(f"User profile response: {resp}", file=sys.stderr)
        return resp
    except Exception as e:
        print(f"User profile request failed: {e}", file=sys.stderr)
        return None


def list_homepage():
    """Retrieves the full home page dashboard state."""
    headers = get_bearer_headers()
    if not headers:
        return None

    try:
        response = requests.post(
            f"{BASE_URL}/v2/homepage",
            headers=headers,
            json={},
            verify=False, timeout=10
        )
        resp = response.json()
        print(f"Homepage response: {resp}", file=sys.stderr)
        return resp
    except Exception as e:
        print(f"Homepage request failed: {e}", file=sys.stderr)
        return None


def list_messages():
    """Lists recent eWeLink messages (including share invites)."""
    headers = get_bearer_headers()
    if not headers:
        return None

    try:
        response = requests.get(
            f"{BASE_URL}/v2/message/read",
            headers=headers,
            verify=False, timeout=10
        )
        resp = response.json()
        print(f"List messages response: {resp}", file=sys.stderr)
        return resp
    except Exception as e:
        print(f"List messages failed: {e}", file=sys.stderr)
        return None


def permit_share(device_id, family_id=None):
    """Approves a share request for a specific device."""
    headers = get_bearer_headers()
    if not headers:
        return None

    body = {"deviceid": device_id}
    if family_id:
        body["familyid"] = family_id

    try:
        response = requests.post(
            f"{BASE_URL}/v2/device/share/permit",
            headers=headers,
            json=body,
            verify=False, timeout=10
        )
        resp = response.json()
        print(f"Permit share response: {resp}", file=sys.stderr)
        return resp
    except Exception as e:
        print(f"Permit share failed: {e}", file=sys.stderr)
        return None


def list_families():
    """Lists all eWeLink families associated with the account."""
    headers = get_bearer_headers()
    if not headers:
        return None

    try:
        response = requests.get(
            f"{BASE_URL}/v2/family",
            headers=headers,
            verify=False, timeout=10
        )
        resp = response.json()

        # If token invalid or region mismatch, force re-login
        if resp.get("error") in [401, 402, 407, 10004]:
            print(f"Token invalid or region error ({resp.get('error')}), forcing re-login...", file=sys.stderr)
            headers = get_bearer_headers(force_refresh=True)
            if headers:
                response = requests.get(
                    f"{BASE_URL}/v2/family",
                    headers=headers,
                    verify=False, timeout=10
                )
                resp = response.json()

        print(f"List families response: {resp}", file=sys.stderr)
        return resp
    except Exception as e:
        print(f"List families failed: {e}", file=sys.stderr)
        return None


# ── Bearer Token Management ──────────────────────────────────────────────

def get_bearer_headers(force_refresh=False):
    """Get headers with Bearer token. Tries: cached token → refresh → login."""
    token = os.environ.get("EWELINK_ACCESSTOKEN") if not force_refresh else None

    if not token:
        token = refresh_token()

    if not token:
        print("No valid session. Attempting login...", file=sys.stderr)
        # Try direct login first
        token = login_direct()

    if not token:
        # Direct login failed, try OAuth flow
        print("Direct login unavailable. Trying automated OAuth code flow...", file=sys.stderr)
        token = login_via_oauth_code()

    if not token:
        print("All authentication methods failed.", file=sys.stderr)
        return None

    return {
        "Authorization": f"Bearer {token}",
        "X-CK-Appid": APP_ID,
        "Content-Type": "application/json",
    }


# ── Device Operations ────────────────────────────────────────────────────

def list_devices():
    """Lists all eWeLink devices associated with the account."""
    headers = get_bearer_headers()
    if not headers:
        return "Error: Authentication failed."

    # First, get the families to make sure we check everywhere
    families_resp = list_families()
    if not families_resp or families_resp.get("error") != 0:
        family_ids = [None] # Try without familyid as fallback
    else:
        family_ids = [f["id"] for f in families_resp.get("data", {}).get("familyList", [])]
        if not family_ids:
            family_ids = [None]

    all_devices = []
    seen_device_ids = set()

    for fid in family_ids:
        # Try multiple endpoints
        endpoints = [
            f"{BASE_URL}/v2/device/thing",
            f"{BASE_URL}/v2/device/all-thing",
            f"{BASE_URL}/v2/family/room/thing"
        ]
        for endpoint in endpoints:
            params = {"num": 100}
            if fid and "all-thing" not in endpoint:
                params["familyid"] = fid
            
            try:
                response = requests.get(
                    endpoint,
                    headers=headers,
                    params=params,
                    verify=False, timeout=10
                )
                resp = response.json()
                if resp.get("error") != 0:
                    continue

                thing_list = resp.get("data", {}).get("thingList", [])
                for thing in thing_list:
                    item = thing.get("itemData", {})
                    did = item.get("deviceid")
                    if did and did not in seen_device_ids:
                        seen_device_ids.add(did)
                        device_info = {
                            "name": item.get("name"),
                            "deviceid": did,
                            "online": item.get("online"),
                            "brandName": item.get("brandName"),
                            "productModel": item.get("productModel"),
                            "familyid": fid
                        }
                        params_data = item.get("params", {})
                        if "switch" in params_data:
                            device_info["switch"] = params_data["switch"]
                        all_devices.append(device_info)
            except Exception as e:
                print(f"Request failed for {endpoint} with family {fid}: {str(e)}", file=sys.stderr)

    return all_devices


def control_device(device_id, state):
    """Controls an eWeLink device. state: 'on' or 'off'."""
    headers = get_bearer_headers()
    if not headers:
        return "Error: Authentication failed."

    body = {"type": 1, "id": device_id, "params": {"switch": state}}

    # List of shards to try
    shards = [BASE_URL] + list(REGION_URLS.values())
    # Remove duplicates
    shards = list(dict.fromkeys(shards))

    last_error = "Unknown error"
    
    for shard_url in shards:
        try:
            print(f"Trying to control device on {shard_url}...", file=sys.stderr)
            response = requests.post(
                f"{shard_url}/v2/device/thing/status",
                headers=headers, json=body, verify=False, timeout=10
            )
            resp = response.json()

            if resp.get("error") == 0:
                return f"Successfully turned {state} device {device_id} (via {shard_url})"
            
            # If token expired, refresh once and retry this shard
            if resp.get("error") in [401, 402]:
                new_token = refresh_token()
                if new_token:
                    headers["Authorization"] = f"Bearer {new_token}"
                    response = requests.post(
                        f"{shard_url}/v2/device/thing/status",
                        headers=headers, json=body, verify=False, timeout=10
                    )
                    resp = response.json()
                    if resp.get("error") == 0:
                        return f"Successfully turned {state} device {device_id} (via {shard_url})"

            last_error = f"API error: {resp.get('msg')} (Code: {resp.get('error')}) on {shard_url}"
            # If 405 or 406, continue to next shard
            if resp.get("error") not in [405, 406]:
                # If it's a "real" error, stop and report? 
                # Actually, eWeLink often gives 406 for wrong region.
                pass
                
        except Exception as e:
            last_error = f"Request failed for {shard_url}: {str(e)}"

    return last_error


# ── CLI ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python ewelink_tool.py list           # List all devices")
        print("  python ewelink_tool.py on [device_id] # Turn device on")
        print("  python ewelink_tool.py off [device_id] # Turn device off")
        sys.exit(1)

    command = sys.argv[1]

    if command == "list":
        result = list_devices()
        print(json.dumps(result, indent=2))
    elif command == "families":
        result = list_families()
        print(json.dumps(result, indent=2))
    elif command == "profile":
        result = get_user_profile()
        print(json.dumps(result, indent=2))
    elif command == "thing":
        if len(sys.argv) < 3:
            print("Error: device_id required")
            sys.exit(1)
        result = get_thing(sys.argv[2])
        print(json.dumps(result, indent=2))
    elif command == "homepage":
        result = list_homepage()
        print(json.dumps(result, indent=2))
    elif command == "messages":
        result = list_messages()
        print(json.dumps(result, indent=2))
    elif command == "permit":
        if len(sys.argv) < 3:
            print("Usage: python ewelink_tool.py permit [device_id] [family_id (optional)]")
            sys.exit(1)
        fid = sys.argv[3] if len(sys.argv) > 3 else None
        result = permit_share(sys.argv[2], fid)
        print(json.dumps(result, indent=2))
    elif command in ["on", "off"]:
        if len(sys.argv) < 3:
            device_id = os.environ.get("EWELINK_DEVICEID")
            if not device_id:
                print("Error: device_id required or set EWELINK_DEVICEID in .env")
                sys.exit(1)
        else:
            device_id = sys.argv[2]
        result = control_device(device_id, command)
        print(result)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
