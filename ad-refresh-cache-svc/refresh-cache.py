import os
import requests
import time

# Read Ad Manager URL from environment variable
AD_MANAGER_URL = os.getenv("AD_MANAGER_URL")
if AD_MANAGER_URL is None:
    print("Error: Please set the AD_MANAGER_URL environment variable.")
    exit(1)

# Define API endpoints
CAMPAIGNS_API = f"{AD_MANAGER_URL}/cache/campaigns"
ADS_API = f"{AD_MANAGER_URL}/cache/ads"
CREATIVES_API = f"{AD_MANAGER_URL}/cache/creatives"

# Function to call API endpoints
def call_api(url):
    print(f"Calling {url}")
    response = requests.get(url)
    # Check if the request was successful
    if response.status_code == 200:
        print("API call successful")
    else:
        print(f"API call failed with status code: {response.status_code}")

# Call API endpoints
while True:
    call_api(CAMPAIGNS_API)
    call_api(ADS_API)
    call_api(CREATIVES_API)
    time.sleep(15) 