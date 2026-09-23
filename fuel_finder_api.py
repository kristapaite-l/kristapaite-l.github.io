import os
import sys
import pandas as pd
from curl_cffi import requests

# 1. Credentials from Environment Variables
CLIENT_ID = os.environ.get("FUEL_CLIENT_ID")
CLIENT_SECRET = os.environ.get("FUEL_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("Error: FUEL_CLIENT_ID or FUEL_CLIENT_SECRET environment variable is missing.")
    sys.exit(1)

# 2. Correct GOV.UK API Endpoints
# Public API gateway host uses hyphens: api.fuel-finder.service.gov.uk
BASE_URL = "https://api.fuel-finder.service.gov.uk"
TOKEN_URL = f"{BASE_URL}/oauth/token"
PRICES_ENDPOINT = f"{BASE_URL}/v1/prices"

headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json"
}

payload = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID.strip(),
    "client_secret": CLIENT_SECRET.strip(),
    "scope": "fuelfinder.read"
}

print(f"Requesting token from: {TOKEN_URL}...")

try:
    # impersonate="chrome120" bypasses the SSL handshake failure triggered by Cloudflare/GOV.UK
    token_res = requests.post(
        TOKEN_URL, 
        data=payload, 
        headers=headers, 
        impersonate="chrome120", 
        timeout=15
    )
    
    print(f"Token Status Code: {token_res.status_code}")
    
    if token_res.status_code != 200:
        print(f"Token generation error: {token_res.text}")
        sys.exit(1)
        
    access_token = token_res.json().get("access_token")
    print("Successfully retrieved access token!")

    # 3. Fetch Price Data
    api_headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    print(f"Fetching fuel prices from: {PRICES_ENDPOINT}...")
    data_res = requests.get(
        PRICES_ENDPOINT, 
        headers=api_headers, 
        impersonate="chrome120", 
        timeout=30
    )

    print(f"Data Fetch Status Code: {data_res.status_code}")

    if data_res.status_code != 200:
        print(f"Data fetch error: {data_res.text}")
        sys.exit(1)

    json_data = data_res.json()
    df = pd.json_normalize(json_data)
    df.to_csv("fuel_prices.csv", index=False)
    print(f"Successfully saved {len(df)} records to fuel_prices.csv!")

except Exception as err:
    print(f"Execution Error: {err}")
    sys.exit(1)