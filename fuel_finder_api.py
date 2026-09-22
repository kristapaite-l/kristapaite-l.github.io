import os
import sys
import pandas as pd
import requests

# 1. Retrieve credentials from environment variables
CLIENT_ID = os.environ.get("FUEL_CLIENT_ID")
CLIENT_SECRET = os.environ.get("FUEL_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
  print("Error: Missing FUEL_CLIENT_ID or FUEL_CLIENT_SECRET environment variable.")
  sys.exit(1)

# 2. Base domain
BASE_URL = "https://developer.fuel-finder.service.gov.uk"

# Potential token endpoint paths on the GOV.UK developer portal
TOKEN_ENDPOINTS = [
    f"{BASE_URL}/oauth/token",
    f"{BASE_URL}/fuel-finder/apis-ifr/access-token",
    f"{BASE_URL}/api/v1/oauth/token"
]

PRICES_ENDPOINT = f"{BASE_URL}/api/v1/prices"

headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

payload = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID.strip(),
    "client_secret": CLIENT_SECRET.strip(),
    "scope": "fuelfinder.read"
}

access_token = None

# Iterate through possible token endpoints
for token_url in TOKEN_ENDPOINTS:
    print(f"Trying token endpoint: {token_url}...")
    try:
        res = requests.post(token_url, data=payload, headers=headers, timeout=15)
        print(f"Response ({res.status_code}): {res.text[:200]}")
        
        if res.status_code == 200:
            access_token = res.json().get("access_token")
            print("Successfully acquired access token!")
            break
    except Exception as err:
        print(f"Endpoint failed: {err}")

if not access_token:
    print("Could not retrieve access token from any candidate endpoint.")
    sys.exit(1)

# 3. Fetch data using the access token
api_headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json",
    "User-Agent": headers["User-Agent"]
}

print(f"Fetching fuel prices from: {PRICES_ENDPOINT}...")
data_res = requests.get(PRICES_ENDPOINT, headers=api_headers, timeout=30)

print(f"Data Fetch Response Status: {data_res.status_code}")

if data_res.status_code != 200:
    print(f"Data Fetch Failed: {data_res.text}")
    sys.exit(1)

df = pd.json_normalize(data_res.json())
df.to_csv("fuel_prices.csv", index=False)
print(f"Successfully saved {len(df)} records to fuel_prices.csv!")