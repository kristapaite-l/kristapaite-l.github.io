import os
import sys
from dotenv import load_dotenv
from curl_cffi import requests

load_dotenv()

CLIENT_ID = os.environ.get("FUEL_CLIENT_ID")
CLIENT_SECRET = os.environ.get("FUEL_CLIENT_SECRET")

# Dagiti opisial a nga path ti authentication
CANDIDATE_PATHS = [
    "https://developer.fuel-finder.service.gov.uk/oauth/token",
    "https://developer.fuel-finder.service.gov.uk/fuel-finder/apis-ifr/access-token",
    "https://developer.fuel-finder.service.gov.uk/api/v1/prices",
]

headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
}

payload = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID.strip() if CLIENT_ID else "",
    "client_secret": CLIENT_SECRET.strip() if CLIENT_SECRET else "",
    "scope": "fuelfinder.read",
}

for url in CANDIDATE_PATHS:
    print(f"Testing endpoint: {url}")
    try:
        # Usaren ti chrome110 wenno edge101 no ag-error ti chrome120
        res = requests.post(
            url, 
            data=payload, 
            headers=headers, 
            impersonate="chrome110", 
            verify=False, 
            timeout=10
        )
        print(f"  Status: {res.status_code}")
        print(f"  Response preview: {res.text[:150]}\n")
    except Exception as e:
        print(f"  Error: {e}\n")