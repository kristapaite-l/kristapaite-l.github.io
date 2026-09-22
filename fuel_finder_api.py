import os
import pandas as pd
import requests

CLIENT_ID = os.environ.get("FUEL_CLIENT_ID")
CLIENT_SECRET = os.environ.get("FUEL_CLIENT_SECRET")

BASE_URL = "https://developer.fuel-finder.service.gov.uk"
TOKEN_URL = f"{BASE_URL}/oauth/token"
PRICES_ENDPOINT = f"{BASE_URL}/api/v1/prices"

payload = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": "fuelfinder.read",
}
headers = {"Content-Type": "application/x-www-form-urlencoded"}

response = requests.post(TOKEN_URL, data=payload, headers=headers)
response.raise_for_status()

token = response.json()["access_token"]

api_headers = {"Authorization": f"Bearer {token}"}
data_res = requests.get(
    PRICES_ENDPOINT, headers=api_headers, params={"fuel_type": "unleaded"}
)
data_res.raise_for_status()

df = pd.json_normalize(data_res.json())
df.to_csv("fuel_prices.csv", index=False)
print("Successfully generated fuel_prices.csv in cloud!")