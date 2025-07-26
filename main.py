import datetime
import base64
import json
import os
from flask import Flask, jsonify
from flask_cors import CORS
import google.generativeai as genai
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar.readonly'
]

TOKEN_PATH = 'token.json'

def authenticate_google_user():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token_file:
            token_file.write(creds.to_json())
    return creds

def decode_base64(data):
    if not data:
        return ""
    decoded_bytes = base64.urlsafe_b64decode(data.encode('UTF-8'))
    return decoded_bytes.decode('utf-8', errors='ignore')

def get_email_body(message):
    payload = message.get('payload', {})
    parts = payload.get('parts', [])

    if not parts:
        body_data = payload.get('body', {}).get('data', '')
        return decode_base64(body_data)

    for part in parts:
        if part.get('mimeType') == 'text/plain':
            body_data = part.get('body', {}).get('data', '')
            return decode_base64(body_data)
    return ""

def fetch_gmail_emails(creds, max_results=50):
    service = build('gmail', 'v1', credentials=creds)
    
    # Fetch unread messages specifically
    results = service.users().messages().list(
        userId='me', 
        labelIds=['UNREAD'],
        maxResults=max_results
    ).execute()
    messages = results.get('messages', [])

    emails = []
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        headers = msg_data['payload'].get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown Sender)')
        body = get_email_body(msg_data)
        
        # Include more context for better summarization
        email_content = f"From: {sender}\nSubject: {subject}\nBody: {body}"
        emails.append(email_content)
    
    return emails

def fetch_calendar_events(creds, max_results=5):
    service = build('calendar', 'v3', credentials=creds)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    events_result = service.events().list(
        calendarId='primary',
        timeMin=now,
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    event_descriptions = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        summary = event.get('summary', '(No Title)')
        event_descriptions.append(f"{summary} at {start}")
    return event_descriptions

def generate_todo_list(prompt_text):
    genai.configure(api_key="AIzaSyAMGyvbj5VpkBm5fNKm2PyW6yioSk-zyZM")  # Replace with your API key
    model = genai.GenerativeModel("models/gemini-2.5-pro")  # Use an available model

    response = model.generate_content(prompt_text)
    return response.text

@app.route('/todos')
def todos():
    creds = authenticate_google_user()

    emails = fetch_gmail_emails(creds)
    calendar_events = fetch_calendar_events(creds)

    combined_text = "\n".join(
        ["Unread Emails:"] + emails + ["", "Calendar Events:"] + calendar_events + ["", 
         "First, provide a brief summary of the key points from the unread emails above. " +
         "Then, based on both the email summary and calendar events, generate a concise to-do list. " +
         "Return ONLY a valid JSON array of strings, where each string is a single task. " +
         "Example format: [\"Task 1\", \"Task 2\", \"Task 3\"]. " +
         "Do not include any other text, just the JSON array."]
    )

    todo_text = generate_todo_list(combined_text)

    try:
        # Clean the response to extract just the JSON array
        todo_text = todo_text.strip()
        
        # Remove any markdown code blocks if present
        if todo_text.startswith('```json'):
            todo_text = todo_text[7:]
        if todo_text.startswith('```'):
            todo_text = todo_text[3:]
        if todo_text.endswith('```'):
            todo_text = todo_text[:-3]
        
        todo_text = todo_text.strip()
        
        # Parse the JSON
        tasks = json.loads(todo_text)
        
        # Ensure it's a list of strings
        if isinstance(tasks, list):
            tasks = [str(task).strip() for task in tasks if task and str(task).strip()]
        else:
            tasks = []
            
    except Exception as e:
        print(f"JSON parse error: {e}")
        print(f"Raw response: {todo_text}")
        # Fallback: split by newlines and clean up
        tasks = []
        for line in todo_text.split('\n'):
            line = line.strip()
            if line and not line.startswith('[') and not line.startswith(']') and not line.startswith('{') and not line.startswith('}'):
                # Remove quotes and commas if present
                line = line.strip('"\'')
                line = line.rstrip(',')
                if line:
                    tasks.append(line)

    return jsonify(tasks)

if __name__ == '__main__':
    app.run(debug=True)
