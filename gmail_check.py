import os
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# This permission level allows the app to read and modify emails
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_gmail_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens.
    # It is created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Ensure your 'credentials.json' from Google Cloud is in this folder!
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def test_fetch():
    service = get_gmail_service()
    # Fetch 5 most recent unread emails
    results = service.users().messages().list(userId='me', q="is:unread", maxResults=5).execute()
    messages = results.get('messages', [])

    if not messages:
        print('No unread messages found.')
    else:
        print("Successfully connected! Here are your latest 5 unread emails:")
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            print(f"- {msg['snippet'][:50]}...")

if __name__ == '__main__':
    test_fetch()