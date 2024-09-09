import imaplib
import email
from email.header import decode_header
import time

# Function to connect to Gmail and fetch emails
def connect_to_gmail(username, password):
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(username, password)
    return mail

# Function to fetch emails from the "Cletocite" label without marking them as "seen"
def fetch_emails_from_label(mail, processed_emails, label="Cletocite"):
    # Select the "Cletocite" label (Gmail labels are accessed as folders)
    mail.select(f'"{label}"')
    
    status, messages = mail.search(None, 'ALL')  # Fetch all emails with the label

    email_ids = messages[0].split()

    for num in email_ids:
        if num in processed_emails:
            continue
        
        status, msg_data = mail.fetch(num, "(BODY.PEEK[])")  # Use PEEK to avoid marking as seen
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else "utf-8")
                from_ = msg.get("From")
                print(f"From: {from_}")
                print(f"Subject: {subject}")
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode("utf-8")
                            print(f"Body:\n{body}")
                else:
                    body = msg.get_payload(decode=True).decode("utf-8")
                    print(f"Body:\n{body}")

        # Add email ID to the processed_emails set
        processed_emails.add(num)

        # After processing the email, remove the label "Cletocite" from the email
        # This effectively deletes it from the label but keeps it in the inbox
        mail.store(num, '+FLAGS', '\\Deleted')

    mail.expunge()  # Permanently remove the emails with the "Deleted" flag from the "Cletocite" label

# Function to keep checking emails live from the "Cletocite" label
def live_email_check(username, password, interval=5, label="Cletocite"):
    mail = connect_to_gmail(username, password)
    processed_emails = set()  # Store processed email IDs to avoid duplicates
    while True:
        fetch_emails_from_label(mail, processed_emails, label)
        print(f"Checking {label} label again in {interval} seconds...")
        time.sleep(interval)

# Your Gmail credentials
username = "cletocite@gmail.com"
password = "dxkbhzyaqaqcgrrq"  # Use your app password

# Start live email check for the "Cletocite" label
live_email_check(username, password)