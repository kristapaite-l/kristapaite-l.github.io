import os
import sys
import pandas as pd
import requests

CLIENT_ID = os.environ.get("FUEL_CLIENT_ID")
CLIENT_SECRET = os.environ.get("FUEL_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
  print("Error: FUEL_CLIENT_ID or FUEL_CLIENT_SECRET environment variable missing.")
  sys.exit(1)

# Exact domain and endpoint structure from the GOV.UK documentation
BASE_URL = "https://api.fuelfinder.service.gov.uk"
TOKEN_URL = f"{BASE_URL}/oauth/token"
PRICES_ENDPOINT = f"{BASE_URL}/v1/prices"

headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

payload = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID.strip(),
    "client_secret": CLIENT_SECRET.strip(),
    "scope": "fuelfinder.read"
}

print(f"Requesting token from: {TOKEN_URL}...")
token_res = requests.post(TOKEN_URL, data=payload, headers=headers, timeout=15)

print(f"Token Response Status: {token_res.status_code}")

if token_res.status_code != 200:
    print(f"Token error details: {token_res.text}")
    sys.exit(1)

access_token = token_res.json().get("access_token")
print("Successfully retrieved access token!")

api_headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json",
    "User-Agent": headers["User-Agent"]
}

print(f"Fetching fuel prices from: {PRICES_ENDPOINT}...")
data_res = requests.get(PRICES_ENDPOINT, headers=api_headers, timeout=30)

print(f"Data Response Status: {data_res.status_code}")

if data_res.status_code != 200:
    print(f"Data fetch error details: {data_res.text}")
    sys.exit(1)

json_data = data_res.json()
df = pd.json_normalize(json_data)
df.to_csv("fuel_prices.csv", index=False)
print(f"Successfully saved {len(df)} fuel price records to fuel_prices.csv!")