import os
import json
from typing import TypedDict, List
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from langgraph.graph import StateGraph, START, END

# Use the updated Ollama import for version 1.0.1
from langchain_ollama import ChatOllama

# 1. Define the Shared State (Assistant's Memory)
class AgentState(TypedDict):
    emails: List[dict]
    analysis: str
    confirmed: bool

# 2. Node: Fetch Emails (Reads from your actual Gmail)
def fetch_node(state: AgentState):
    print("--- 📥 FETCHING RECENT EMAILS ---")
    creds = Credentials.from_authorized_user_file('token.json')
    service = build('gmail', 'v1', credentials=creds)
    
    # Get 3 most recent unread emails
    results = service.users().messages().list(userId='me', q="is:unread", maxResults=5).execute()
    messages = results.get('messages', [])
    
    email_list = []
    for m in messages:
        msg = service.users().messages().get(userId='me', id=m['id']).execute()
        # Wrap the generator expression in its own parentheses
        subject = next((h['value'] for h in msg['payload']['headers'] if h['name'] == 'Subject'), "No Subject")
        email_list.append({"id": m['id'], "subject": subject, "snippet": msg['snippet']})
    
    return {"emails": email_list}

# 3. Node: Categorize with Ollama (Family, Shopping, Junk, etc.)
def analyze_node(state: AgentState):
    print("--- 🤖 OLLAMA CATEGORIZING EMAILS ---")
    llm = ChatOllama(model="llama3")
    
    email_text = "\n".join([f"Subj: {e['subject']} | Snippet: {e['snippet']}" for e in state['emails']])
    prompt = f"""Categorize these emails into: Family, Friends, job opportunities, Shopping, or Junk. 
    Identify if any are 'High Priority' or 'Reply Required'.
    Emails:
    {email_text}"""
    
    response = llm.invoke(prompt)
    return {"analysis": response.content}

# 4. Node: Human Review (Human-in-the-loop)
def review_node(state: AgentState):
    print(f"\n--- 📋 ANALYSIS REPORT ---\n{state['analysis']}")
    # This pauses the graph until you provide input
    answer = input("\nDo you approve these actions? (yes/no): ")
    return {"confirmed": answer.lower() == "yes"}

# 5. Node: Store Data (Saves to a local file for processing)
def store_node(state: AgentState):
    if state["confirmed"]:
        print("--- 💾 STORING ANALYSIS TO FILE ---")
        with open("processed_emails.json", "w") as f:
            json.dump({"report": state["analysis"]}, f)
    else:
        print("--- ❌ ACTIONS REJECTED BY USER ---")
    return state

# BUILD THE GRAPH
builder = StateGraph(AgentState)
builder.add_node("fetcher", fetch_node)
builder.add_node("analyzer", analyze_node)
builder.add_node("reviewer", review_node)
builder.add_node("storage", store_node)

builder.add_edge(START, "fetcher")
builder.add_edge("fetcher", "analyzer")
builder.add_edge("analyzer", "reviewer")
builder.add_edge("reviewer", "storage")
builder.add_edge("storage", END)

app = builder.compile()

if __name__ == "__main__":
    app.invoke({"emails": [], "analysis": "", "confirmed": False})