# background_service.py
import imaplib
import email
import time
import os
import traceback
from email.header import decode_header
from dotenv import load_dotenv
from openai import OpenAI
from agents.jira_agent import create_jira_issue, create_jira_ticket

# Load environment variables
load_dotenv()

# Configuration
EMAIL_HOST = "imap.gmail.com"
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
POLL_INTERVAL = 60  # seconds
LOG_FILE = "email_processing_log.txt"

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


def connect_inbox():
    """Connect to the email inbox using IMAP"""
    mail = imaplib.IMAP4_SSL(EMAIL_HOST)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")
    return mail


def fetch_unseen_emails(mail):
    """Fetch and yield all unseen emails from the inbox"""
    status, messages = mail.search(None, 'UNSEEN')
    email_ids = messages[0].split()
    print(f"📩 Found {len(email_ids)} unseen emails")

    for eid in email_ids:
        status, data = mail.fetch(eid, '(RFC822)')
        msg = email.message_from_bytes(data[0][1])
        yield parse_email(msg)


def parse_email(msg):
    """Parse an email message into a structured format with attachments"""
    # Extract and decode subject
    subject, encoding = decode_header(msg["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding or "utf-8")

    # Get sender
    from_ = msg.get("From")

    # Extract body text and attachments
    body = ""
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            # Get the body text
            if content_type == "text/plain" and "attachment" not in content_disposition:
                body = part.get_payload(decode=True).decode(errors="ignore")

            # Get attachments
            elif "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    # Decode filename if needed
                    if decode_header(filename)[0][1] is not None:
                        filename = decode_header(filename)[0][0]
                        if isinstance(filename, bytes):
                            filename = filename.decode()

                    # Save attachment to temp directory
                    attachment_dir = os.path.join(os.getcwd(), "temp_attachments")
                    os.makedirs(attachment_dir, exist_ok=True)
                    filepath = os.path.join(attachment_dir, filename)

                    # Save the file
                    with open(filepath, "wb") as f:
                        f.write(part.get_payload(decode=True))

                    attachments.append({
                        "filename": filename,
                        "path": filepath,
                        "content_type": content_type
                    })
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")

    return {
        "from": from_,
        "subject": subject,
        "body": body,
        "attachments": attachments,
        "raw": msg
    }


def process_email_with_gpt(email_data):
    """Process an email to generate structured Jira ticket content using GPT"""
    prompt = f"""
From: {email_data['from']}
Subject: {email_data['subject']}
Body: {email_data['body']}

You are an AI assistant that processes emails to generate structured Jira ticket content.
Extract the following fields from the email:
1. Summary (title of the issue)
2. Description (detailed explanation)
3. Priority (High, Medium, Low)
4. Tags (comma-separated keywords)

If information is missing, infer based on context or leave it blank.
Format your response as:

```jira
Summary: [extracted summary]
Description: [extracted description]
Priority: [extracted priority]
Tags: [extracted tags]
```
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system",
                "content": "You are a helpful assistant that processes emails into structured Jira tickets. Make sure all the details from the email are captured in the description."},
                {"role": "user", "content": prompt}
            ]
        )
        # Return the response content
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Error calling OpenAI API: {e}")
        traceback.print_exc()
        return None


def process_email_and_create_ticket(email_data):
    """Process email and create Jira ticket using the JiraAgent"""
    try:
        print("🔍 Processing email with GPT...")
        # Process with GPT
        structured_data = process_email_with_gpt(email_data)

        print("\n✅ GPT Output:")
        print("-----------------------------------------------")
        print(structured_data)
        print("-----------------------------------------------\n")

        # Log the processed output
        with open(LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(f"\n\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            log_file.write(f"EMAIL:\nFrom: {email_data['from']}\nSubject: {email_data['subject']}\n")
            log_file.write(f"\nEXTRACTED OUTPUT:\n{structured_data}\n")

        # Check if we got valid data from GPT before trying to create a ticket
        if not structured_data:
            print("⚠️ No valid data received from GPT, cannot create ticket")
            return None

        # Use the JiraAgent to create a ticket
        print("🎫 Creating Jira ticket...")
        ticket_result = create_jira_ticket(structured_data, email_data.get("attachments"))

        # Log the Jira ticket creation result
        with open(LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(f"\nJIRA TICKET: {ticket_result}\n")
            log_file.write("=" * 80)

        print(f"📝 Results saved to {LOG_FILE}")

        # Clean up temporary attachment files
        cleanup_attachments(email_data.get("attachments"))

        return ticket_result

    except Exception as e:
        print(f"❌ Error processing email and creating ticket: {e}")
        traceback.print_exc()

        # Still clean up attachments on error
        cleanup_attachments(email_data.get("attachments"))

        return None


def cleanup_attachments(attachments):
    """Remove temporary attachment files after processing"""
    if not attachments:
        return

    for attachment in attachments:
        filepath = attachment.get("path")
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
                print(f"🗑️ Removed temporary file: {filepath}")
            except Exception as e:
                print(f"⚠️ Failed to remove temporary file {filepath}: {e}")

def run_background_service():
    print("📬 Email listener started...")
    mail = connect_inbox()

    while True:
        try:
            for email_data in fetch_unseen_emails(mail):
                print(f"\n\n===============================================")
                print(f"📨 NEW EMAIL RECEIVED")
                print(f"From: {email_data['from']}")
                print(f"Subject: {email_data['subject']}")
                print(f"Body Preview: {email_data['body'][:150]}...")
                print(f"===============================================\n")

                ticket_result = process_email_and_create_ticket(email_data)

                if ticket_result:
                    print(f"🎫 Jira ticket created successfully: {ticket_result}")
                else:
                    print("⚠️ Failed to create Jira ticket.")

            # Reconnect to make sure we don't lose the connection over time
            try:
                mail.noop()  # Keep connection alive
            except:
                print("🔄 Reconnecting to email server...")
                mail = connect_inbox()

        except Exception as e:
            print(f"⚠️ Error in main loop: {e}")
            import traceback
            traceback.print_exc()

        print(f"\n💤 Waiting {POLL_INTERVAL} seconds before checking again...")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    run_background_service()