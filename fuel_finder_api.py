import os
import sys
import pandas as pd
import requests

CLIENT_ID = os.environ.get("FUEL_CLIENT_ID")
CLIENT_SECRET = os.environ.get("FUEL_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
  print("Error: FUEL_CLIENT_ID or FUEL_CLIENT_SECRET missing.")
  sys.exit(1)

TOKEN_URL = "https://www.fuel-finder.service.gov.uk/oauth/token"
PRICES_ENDPOINT = "https://www.fuel-finder.service.gov.uk/api/v1/prices"

# 1. Standard OAuth 2.0 payload
payload = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": "fuelfinder.read",
}

# 2. Complete header set to satisfy Cloudflare/GOV.UK firewall
headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:123.0) Gecko/20100101"
        " Firefox/123.0"
    ),
}

print(f"Requesting token from: {TOKEN_URL}...")

response = requests.post(
    TOKEN_URL, data=payload, headers=headers, timeout=15
)

if response.status_code != 200:
  print(f"Token Generation Failed ({response.status_code}): {response.text}")
  sys.exit(1)

token_data = response.json()
access_token = token_data.get("access_token")
print("Successfully retrieved access token!")

api_headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json",
    "User-Agent": headers["User-Agent"],
}

data_response = requests.get(PRICES_ENDPOINT, headers=api_headers, timeout=30)

if data_response.status_code != 200:
  print(
      f"API Fetch Failed ({data_response.status_code}): {data_response.text}"
  )
  sys.exit(1)

df = pd.json_normalize(data_response.json())
df.to_csv("fuel_prices.csv", index=False)
print(f"Saved {len(df)} records to fuel_prices.csv")