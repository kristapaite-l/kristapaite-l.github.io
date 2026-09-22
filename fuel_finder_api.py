import os
import sys
import pandas as pd
import requests

# 1. Fetch credentials from environment variables set in GitHub Actions / local environment
CLIENT_ID = os.environ.get("FUEL_CLIENT_ID")
CLIENT_SECRET = os.environ.get("FUEL_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
  print(
      "Error: FUEL_CLIENT_ID or FUEL_CLIENT_SECRET environment variables missing."
  )
  sys.exit(1)

# 2. Correct GOV.UK Fuel Finder production domains
BASE_URL = "https://www.fuel-finder.service.gov.uk"
TOKEN_URL = f"{BASE_URL}/oauth/token"
PRICES_ENDPOINT = f"{BASE_URL}/api/v1/prices"

# 3. Headers required by the GOV.UK CloudFront distribution
headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
}

token_payload = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": "fuelfinder.read",
}

print(f"Requesting token from: {TOKEN_URL}...")

try:
  token_response = requests.post(
      TOKEN_URL, data=token_payload, headers=headers, timeout=15
  )

  if token_response.status_code != 200:
    print(
        f"Token Generation Failed ({token_response.status_code}):"
        f" {token_response.text}"
    )
    sys.exit(1)

  access_token = token_response.json().get("access_token")
  print("Successfully retrieved access token!")

  api_headers = {
      "Authorization": f"Bearer {access_token}",
      "User-Agent": headers["User-Agent"],
  }

  print(f"Fetching fuel prices from: {PRICES_ENDPOINT}...")
  data_response = requests.get(
      PRICES_ENDPOINT, headers=api_headers, timeout=30
  )

  if data_response.status_code != 200:
    print(
        f"API Fetch Failed ({data_response.status_code}):"
        f" {data_response.text}"
    )
    sys.exit(1)

  raw_data = data_response.json()

  # Parse the array returned by the API
  df = pd.json_normalize(raw_data)
  df.to_csv("fuel_prices.csv", index=False)
  print(
      f"Successfully fetched and saved {len(df)} records to fuel_prices.csv!"
  )

except Exception as e:
  print(f"Execution Error: {e}")
  sys.exit(1)