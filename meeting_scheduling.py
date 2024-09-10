from datetime import datetime, timedelta
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import json
import pytz
import re
import os
import pickle
import time

# Google Calendar API credentials and scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']
TOKEN_FILE = 'token.pickle'
CREDENTIALS_FILE = 'cred.json'

# Google Gemini API credentials
GOOGLE_API_KEY = 'AIzaSyAYGPqPfgB65M3874J25J4IBYyT3KEJ2jk'
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

def generate_answer(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error generating answer: {e}")
        return None

def extract_meeting_details(text):
    prompt = f"""
    Extract the following details from the text:
    - Date of the meeting (in DD/MM/YYYY format or 'today' or 'tomorrow')
    - Time of the meeting (in 12-hour format HH:MM AM/PM)
    - List of attendees (as a list of email addresses)
    - Summary of the meeting

    Provide the extracted details as a JSON object with the following keys:
    - "date": The date of the meeting.
    - "time": The time of the meeting.
    - "attendees": A list of email addresses.
    - "summary": A brief summary of the meeting.

    Text: "{text}"
    """
    answer = generate_answer(prompt)
    print(f'Gemini response: "{answer}"')  # Include quotes for better visibility

    if not answer:
        print('No response from Gemini.')
        return None

    # Clean the response
    cleaned_answer = re.sub(r'^```json', '', answer)  # Remove start code block delimiter
    cleaned_answer = re.sub(r'```$', '', cleaned_answer)  # Remove end code block delimiter
    cleaned_answer = cleaned_answer.strip()
    print(f'Cleaned response: "{cleaned_answer}"')  # Debugging line

    try:
        details = json.loads(cleaned_answer)
        if not isinstance(details, dict):
            raise ValueError("Response is not a JSON object")
        print(f'Parsed details: {details}')  # Debugging line
        return details
    except json.JSONDecodeError as e:
        print(f'JSON decoding error: {e}')
        return None
    except ValueError as e:
        print(f'Value error: {e}')
        return None

# Authentication for OAuth2 installed application flow
def authenticate_google_calendar():
    creds = None
    # Check if token.pickle exists (stored token for re-use)
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # If there are no valid credentials available, prompt the user to log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service

def convert_date_and_time(date_str, time_str):
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    
    if date_str.lower() == "today":
        meeting_date = now.date()
    elif date_str.lower() == "tomorrow":
        meeting_date = now.date() + timedelta(days=1)
    else:
        try:
            meeting_date = datetime.strptime(date_str, '%d/%m/%Y').date()
        except ValueError:
            print(f'Invalid date format: {date_str}')
            return None, None
    
    try:
        meeting_time = datetime.strptime(time_str, '%I:%M %p').strftime('%H:%M')
    except ValueError:
        print(f'Invalid time format: {time_str}')
        return None, None
    
    start_time = datetime.combine(meeting_date, datetime.strptime(meeting_time, '%H:%M').time())
    end_time = start_time + timedelta(hours=1)
    
    print(f'Converted start time: {start_time.isoformat()}')
    print(f'Converted end time: {end_time.isoformat()}')
    
    return start_time.isoformat(), end_time.isoformat()

def schedule_meeting(service, start_time, end_time, attendees, summary="Meeting"):
    event = {
        'summary': summary,
        'start': {
            'dateTime': start_time,
            'timeZone': 'Asia/Kolkata',  # Change this to your timezone
        },
        'end': {
            'dateTime': end_time,
            'timeZone': 'Asia/Kolkata',  # Change this to your timezone
        },
        'attendees': [{'email': email} for email in attendees],
        'reminders': {
            'useDefault': True,
        },
    }

    event = service.events().insert(calendarId='primary', body=event).execute()
    print(f'Event created: {event.get("htmlLink")}')

def main():
    user_input = "Schedule meeting @10:30 AM 10/09/2024 with gowsrini2004@gmail.com,idhikaprabakaran@gmail.com, forfungowtham@gmail.com, cowara987@gmail.com about SIH INTERNAL HACAKTHON"
    
    # Extract meeting details using Gemini
    details = extract_meeting_details(user_input)
    
    if details:
        print(f'Extracted details: {details}')  # Debugging line
        
        # Use correct keys from the parsed JSON
        meeting_date = details.get('date') or details.get('meeting_date')
        meeting_time = details.get('time') or details.get('meeting_time')
        attendees = details.get('attendees', [])
        summary = details.get('summary', "Meeting")
        
        if not meeting_date or not meeting_time:
            print('Date or time information missing.')
            return
        
        start_time, end_time = convert_date_and_time(meeting_date, meeting_time)
        
        if start_time and end_time:
            # Authenticate
            service = authenticate_google_calendar()
            
            # Retry loop for scheduling the meeting
            max_retries = 5
            retry_delay = 5  # seconds
            for attempt in range(max_retries):
                try:
                    schedule_meeting(service, start_time, end_time, attendees, summary)
                    print('Event created successfully.')
                    break  # Exit loop if successful
                except Exception as e:
                    print(f'Error creating event: {e}')
                    if attempt < max_retries - 1:
                        print(f'Retrying in {retry_delay} seconds...')
                        time.sleep(retry_delay)
                    else:
                        print('Failed to create event after multiple attempts.')
        else:
            print('Failed to convert date and time.')
    else:
        print('Failed to extract meeting details.')

if __name__ == '__main__':
    main()