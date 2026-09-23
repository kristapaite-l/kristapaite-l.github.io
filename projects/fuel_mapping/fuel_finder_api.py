import os
import sys
import pandas as pd
from curl_cffi import requests
from dotenv import load_dotenv

# Load variables from .env file into environment
load_dotenv()

CLIENT_ID = os.environ.get("FUEL_CLIENT_ID")
CLIENT_SECRET = os.environ.get("FUEL_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("Error: FUEL_CLIENT_ID or FUEL_CLIENT_SECRET missing.")
    sys.exit(1)

# 2. Production Domain and Endpoints
BASE_URL = "https://www.fuel-finder.service.gov.uk"
TOKEN_URL = f"{BASE_URL}/oauth/token"
PRICES_ENDPOINT = f"{BASE_URL}/api/v1/prices"

# 3. Headers required to satisfy Cloudflare firewall routing
headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-GB,en;q=0.9",
    "Referer": "https://www.fuel-finder.service.gov.uk/",
    "Origin": "https://www.fuel-finder.service.gov.uk"
}

payload = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID.strip(),
    "client_secret": CLIENT_SECRET.strip(),
    "scope": "fuelfinder.read"
}

print(f"Requesting token from: {TOKEN_URL}...")

try:
    token_res = requests.post(
        TOKEN_URL, 
        data=payload, 
        headers=headers, 
        impersonate="chrome120", 
        timeout=15
    )
    
    print(f"Token Response Status: {token_res.status_code}")
    
    if token_res.status_code != 200:
        print(f"Token generation failed ({token_res.status_code}): {token_res.text}")
        sys.exit(1)
        
    res_data = token_res.json()
    # Handle both wrapped response objects and root-level tokens
    access_token = res_data.get("access_token") or res_data.get("data", {}).get("access_token")
    
    if not access_token:
        print(f"Token missing from response payload: {res_data}")
        sys.exit(1)
        
    print("Successfully retrieved access token!")

    # 4. Fetch Price Data
    api_headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Referer": "https://www.fuel-finder.service.gov.uk/"
    }

    print(f"Fetching fuel prices from: {PRICES_ENDPOINT}...")
    data_res = requests.get(
        PRICES_ENDPOINT, 
        headers=api_headers, 
        impersonate="chrome120", 
        timeout=30
    )

    print(f"Data Response Status: {data_res.status_code}")

    if data_res.status_code != 200:
        print(f"API Data fetch failed ({data_res.status_code}): {data_res.text}")
        sys.exit(1)

    raw_json = data_res.json()
    
    # Handle direct root-level arrays vs nested objects
    if isinstance(raw_json, dict) and "data" in raw_json:
        df = pd.json_normalize(raw_json["data"])
    else:
        df = pd.json_normalize(raw_json)

    df.to_csv("fuel_prices.csv", index=False)
    print(f"Successfully exported {len(df)} records to fuel_prices.csv!")

except Exception as err:
    print(f"Execution Error: {err}")
    sys.exit(1)