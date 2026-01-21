import streamlit as st
import json
import os
import base64
import pandas as pd
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.message import EmailMessage
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

# --- GOOGLE AUTH CONFIGURATION ---
# Note: If you see a scope error, delete your local token.json file!
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify', 
    'https://www.googleapis.com/auth/calendar.events'
]

# --- LLM CONFIGURATION (GROQ) ---
llm = ChatGroq(
    model="llama-3.1-8b-instant", 
    temperature=0, 
    api_key=os.getenv("GROQ_API_KEY")
)

# --- UI STYLING ---
st.set_page_config(page_title="AI Executive Assistant", layout="wide")
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #1E2A38; color: white; }
    
    /* Unified Orange Download Buttons */
    .stDownloadButton > button {
        background-color: #FF8C00 !important;
        color: white !important;
        font-weight: bold !important;
        border-radius: 10px;
        border: none;
        width: 100%;
        margin-bottom: 10px;
    }
    
    /* Priority Colors */
    .p-high { color: #FF4B4B; font-weight: bold; }
    .p-medium { color: #FFA500; font-weight: bold; }
    .p-low { color: #008000; font-weight: bold; }
    
    .stExpander { border: 1px solid #e6e9ef; border-radius: 8px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- GOOGLE SERVICES HELPERS ---
def get_credentials():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def send_reply(to, subject, body, thread_id):
    service = build('gmail', 'v1', credentials=get_credentials())
    msg = EmailMessage()
    msg.set_content(body)
    msg['To'] = to
    msg['Subject'] = f"Re: {subject}"
    encoded_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={'raw': encoded_msg, 'threadId': thread_id}).execute()

def add_calendar_event(summary, description):
    service = build('calendar', 'v3', credentials=get_credentials())
    start_time = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0)
    event = {
        'summary': summary,
        'description': description,
        'start': {'dateTime': start_time.isoformat(), 'timeZone': 'UTC'},
        'end': {'dateTime': (start_time + timedelta(hours=1)).isoformat(), 'timeZone': 'UTC'},
    }
    service.events().insert(calendarId='primary', body=event).execute()

# --- MAIN ANALYSIS LOGIC ---
def fetch_and_analyze_unread(limit):
    service = build('gmail', 'v1', credentials=get_credentials())
    # 1. GET ONLY UNREAD MAIL
    results = service.users().messages().list(userId='me', q="is:unread", maxResults=limit).execute()
    messages = results.get('messages', [])
    data = []

    for m in messages:
        msg = service.users().messages().get(userId='me', id=m['id']).execute()
        headers = msg['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
        sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown")
        snippet = msg['snippet']
        
        # 2. AI CATEGORY & PRIORITY & REPLY
        prompt = f"""
        Analyze this email:
        Sender: {sender} | Subject: {subject} | Snippet: {snippet}
        
        Tasks:
        1. Category: (Work, Social, Promotion, Finance, or Personal)
        2. Priority: (High, Medium, or Low)
        3. Meeting: Is this a meeting/event request? (Yes/No)
        4. Reply: Draft a 2-sentence professional response.

        Return ONLY JSON: 
        {{"category": "string", "priority": "High/Medium/Low", "meeting": "Yes/No", "reply": "string"}}
        """
        try:
            ai_res = json.loads(llm.invoke(prompt).content)
        except:
            ai_res = {"category": "Other", "priority": "Medium", "meeting": "No", "reply": "Thanks for the email."}

        data.append({
            "ID": m['id'], "Subject": subject, "From": sender, 
            "Category": ai_res['category'], "Priority": ai_res['priority'],
            "Meeting": ai_res['meeting'], "Reply": ai_res['reply'], "Snippet": snippet
        })
    return data

# --- UI LAYOUT ---
with st.sidebar:
    st.title("⚙️ AI Controls")
    email_limit = st.number_input("Number of unread emails:", 1, 30, 5)
    st.markdown("---")
    st.subheader("📥 Export Results")
    dl_json_placeholder = st.empty()
    dl_txt_placeholder = st.empty()

st.title("📧 Agentic Email Assistant")
st.write("Smart Triage: Categories, Priority, Replies, and Calendar Sync.")

if st.button("🚀 Sync & Analyze Unread Messages"):
    with st.spinner("Agent is reading your inbox..."):
        emails = fetch_and_analyze_unread(email_limit)
        st.session_state['emails'] = emails

if 'emails' in st.session_state:
    for i, email in enumerate(st.session_state['emails']):
        # Assign color based on priority
        p_color = "p-high" if email['Priority'] == "High" else "p-medium" if email['Priority'] == "Medium" else "p-low"
        
        with st.expander(f"{email['Subject']} — [{email['Category']}]"):
            st.markdown(f"**From:** {email['From']}")
            st.markdown(f"**Priority:** <span class='{p_color}'>{email['Priority']}</span>", unsafe_allow_html=True)
            st.write(f"**Context:** {email['Snippet']}")
            st.divider()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🤖 Suggested Reply")
                final_reply = st.text_area("Refine AI Draft:", email['Reply'], key=f"txt_{i}")
                if st.button("📧 Send This Reply", key=f"send_{i}"):
                    send_reply(email['From'], email['Subject'], final_reply, email['ID'])
                    st.success("Reply Sent via Gmail!")
            
            with col2:
                if email['Meeting'] == "Yes":
                    st.subheader("📅 Event Detected")
                    st.warning("This email looks like a meeting request.")
                    if st.button("🗓️ Add to Google Calendar", key=f"cal_{i}"):
                        add_calendar_event(email['Subject'], email['Snippet'])
                        st.success("Added to Calendar (Tomorrow 10 AM)!")
                else:
                    st.info("No calendar event detected.")

    # Sidebar Download Buttons (Orange)
    report_json = json.dumps(st.session_state['emails'], indent=4)
    dl_json_placeholder.download_button("📥 Download JSON", report_json, "email_report.json")
    
    report_txt = "EMAIL TRIAGE REPORT\n" + "="*20 + "\n"
    for e in st.session_state['emails']:
        report_txt += f"Subject: {e['Subject']}\nPriority: {e['Priority']}\nCategory: {e['Category']}\n---\n"
    dl_txt_placeholder.download_button("📥 Download TXT", report_txt, "email_report.txt")