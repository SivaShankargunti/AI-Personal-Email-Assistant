import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# SCOPES define the level of access.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def generate_token():
    # --- FIXED PATH LOGIC ---
    # This gets the exact folder where THIS script is saved
    project_folder = os.path.dirname(os.path.abspath(__file__))
    credentials_path = os.path.join(project_folder, 'credentials.json')
    token_path = os.path.join(project_folder, 'token.json')
    
    creds = None
    
    # Check if token.json exists
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If no valid credentials, trigger the login flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Check if credentials.json actually exists before trying to open it
            if not os.path.exists(credentials_path):
                print(f"❌ ERROR: 'credentials.json' NOT FOUND at: {credentials_path}")
                print("Please ensure you downloaded it and renamed it correctly in that folder.")
                return

            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the token to the absolute path
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
            print(f"✅ SUCCESS: 'token.json' created at: {token_path}")

if __name__ == "__main__":
    generate_token()