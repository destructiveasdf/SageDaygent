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

def fetch_gmail_emails(creds, max_results=5):
    service = build('gmail', 'v1', credentials=creds)
    results = service.users().messages().list(userId='me', maxResults=max_results).execute()
    messages = results.get('messages', [])

    emails = []
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        headers = msg_data['payload'].get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
        body = get_email_body(msg_data)
        snippet = (body[:500] + '...') if len(body) > 500 else body
        emails.append(f"Subject: {subject}\nBody: {snippet}")
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
        ["Emails:"] + emails + ["", "Calendar Events:"] + calendar_events + ["", "Generate a concise to-do list as a JSON array of tasks, each task a string."]
    )

    todo_text = generate_todo_list(combined_text)

    try:
        tasks = json.loads(todo_text)
    except Exception as e:
        print(f"JSON parse error: {e}")
        tasks = [task.strip() for task in todo_text.split('\n') if task.strip()]

    return jsonify(tasks)

if __name__ == '__main__':
    app.run(debug=True)
