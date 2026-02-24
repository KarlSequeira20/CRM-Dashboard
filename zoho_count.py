import os
import requests
from dotenv import load_dotenv

# Load credentials from backend/.env
env_path = os.path.join('backend', '.env')
load_dotenv(dotenv_path=env_path)

CLIENT_ID = os.getenv('ZOHO_CLIENT_ID')
CLIENT_SECRET = os.getenv('ZOHO_CLIENT_SECRET')
REFRESH_TOKEN = os.getenv('ZOHO_REFRESH_TOKEN')

# Note: Using .in domain as seen in the backend implementation
AUTH_URL = "https://accounts.zoho.in/oauth/v2/token"
API_DOMAIN = "https://www.zohoapis.in/crm/v3"

def get_access_token():
    """Refresh the Zoho access token."""
    params = {
        'refresh_token': REFRESH_TOKEN,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'refresh_token'
    }
    response = requests.post(AUTH_URL, params=params)
    data = response.json()
    
    if 'access_token' not in data:
        print(f"Error refreshing token: {data}")
        exit(1)
        
    return data['access_token']

def get_module_count(module_name, access_token):
    """Get the total record count for a specific Zoho CRM module."""
    url = f"{API_DOMAIN}/{module_name}/actions/count"
    headers = {
        'Authorization': f'Zoho-oauthtoken {access_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(url, headers=headers)
    
    # Check if the count endpoint is available (v3+)
    if response.status_code == 200:
        data = response.json()
        if 'count' in data:
            return data['count']
    
    # Fallback/Error handling
    print(f"Error fetching count for {module_name}: {response.status_code} - {response.text}")
    return "Error"

def main():
    print("--- Zoho CRM Row Counter ---")
    
    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        print("Error: Missing ZOHO credentials in backend/.env")
        return

    print("Refreshing access token...")
    access_token = get_access_token()
    
    print("Fetching record counts...")
    leads_count = get_module_count("Leads", access_token)
    deals_count = get_module_count("Deals", access_token)
    
    print("-" * 30)
    print(f"Total Leads: {leads_count}")
    print(f"Total Deals: {deals_count}")
    print("-" * 30)

if __name__ == "__main__":
    main()
