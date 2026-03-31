import os
import requests
from dotenv import load_dotenv

load_dotenv()

def exchange_code():
    # Correct values from the prompt
    client_id = os.getenv("ZOHO_CLIENT_ID")
    client_secret = os.getenv("ZOHO_CLIENT_SECRET")
    redirect_uri = os.getenv("ZOHO_REDIRECT_URI")
    # Extract code properly
    pasted_value = os.getenv("ZOHO_REFRESH_TOKEN")
    if "code=" in pasted_value:
        auth_code = pasted_value.split("code=")[1].split("&")[0]
    else:
        
        auth_code = pasted_value.replace("1000.your", "1000.") if "1000.your" in pasted_value else pasted_value
    
    print(f"Exchanging code: {auth_code}...")
    
    url = "https://accounts.zoho.com/oauth/v2/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code": auth_code
    }
    
    response = requests.post(url, data=payload)
    print(f"Response Status: {response.status_code}")
    
    try:
        data = response.json()
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        print(f"Raw Response: {response.text}")
        return
    
    if "refresh_token" in data:
        print("\n SUCCESS!")
        refresh_token = data["refresh_token"]
        print(f"New Refresh Token: {refresh_token}")
        
        # Update .env file automatically
        with open(".env", "r") as f:
            lines = f.readlines()
        
        with open(".env", "w") as f:
            for line in lines:
                if line.startswith("ZOHO_REFRESH_TOKEN="):
                    f.write(f"ZOHO_REFRESH_TOKEN=\"{refresh_token}\"\n")
                elif line.startswith("ZOHO_ACCESS_TOKEN="):
                    f.write(f"ZOHO_ACCESS_TOKEN=\"{data['access_token']}\"\n")
                else:
                    f.write(line)
        print("Updated .env file with REAL tokens.")
    else:
        print("\n FAILED")
        print(data)

if __name__ == "__main__":
    exchange_code()
