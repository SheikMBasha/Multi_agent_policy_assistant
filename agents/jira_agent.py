from autogen import AssistantAgent
from shared.llm_config import llm_config
import requests
from requests.auth import HTTPBasicAuth
import json
import os
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Jira configuration
JIRA_URL = os.getenv("JIRA_URL")  # e.g., "https://your-domain.atlassian.net"
JIRA_PROJECT = os.getenv("JIRA_PROJECT")  # e.g., "PROJ"
JIRA_USER = os.getenv("JIRA_USER")  # Jira email
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")  # API token


def create_jira_issue(ticket_data, attachments=None):
    """Create a Jira issue using the provided ticket data"""
    # Extract ticket data
    summary = ticket_data.get("Summary", "New Issue")
    description = ticket_data.get("Description", "")
    priority = ticket_data.get("Priority", "Medium").capitalize()
    raw_tags = ticket_data.get("Tags", "").split(",")
    # Process each tag: strip whitespace, replace spaces with hyphens, remove empty tags
    processed_tags = []
    for tag in raw_tags:
        tag = tag.strip()
        if tag:
            # Replace spaces with hyphens for Jira compatibility
            tag = tag.replace(" ", "-")
            processed_tags.append(tag)

    # Create issue payload
    issue_data = {
        "fields": {
            "project": {
                "key": JIRA_PROJECT
            },
            "summary": summary,
            "description": description,
            "issuetype": {
                "name": "Task"  # Can be customized
            }
        }
    }

    # Only add labels if we have valid ones
    if processed_tags:
        issue_data["fields"]["labels"] = processed_tags

    # Create the issue
    auth = HTTPBasicAuth(JIRA_USER, JIRA_API_TOKEN)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    response = requests.post(
        f"{JIRA_URL}/rest/api/2/issue",
        auth=auth,
        headers=headers,
        data=json.dumps(issue_data)
    )

    if response.status_code != 201:
        raise Exception(f"Failed to create Jira issue: {response.text}")

    issue_key = response.json().get("key")
    print(f"✅ Created Jira issue: {issue_key}")

    # If we have attachments, upload them
    if attachments and issue_key:
        for attachment in attachments:
            upload_attachment(issue_key, attachment)

    return issue_key


def upload_attachment(issue_key, attachment):
    """Upload an attachment to a Jira issue"""
    filepath = attachment.get("path")
    if not filepath or not os.path.exists(filepath):
        print(f"⚠️ Attachment not found: {filepath}")
        return

    headers = {
        "X-Atlassian-Token": "no-check"
    }

    auth = HTTPBasicAuth(JIRA_USER, JIRA_API_TOKEN)

    with open(filepath, "rb") as file:
        files = {
            "file": (os.path.basename(filepath), file, attachment.get("content_type", "application/octet-stream"))
        }

        response = requests.post(
            f"{JIRA_URL}/rest/api/2/issue/{issue_key}/attachments",
            headers=headers,
            auth=auth,
            files=files
        )

        if response.status_code == 200 or response.status_code == 201:
            print(f"✅ Uploaded attachment '{os.path.basename(filepath)}' to {issue_key}")
        else:
            print(f"⚠️ Failed to upload attachment: {response.text}")


def parse_jira_ticket_format(ticket_text):
    """Parse Jira ticket format from text"""
    # Check if ticket_text is None or empty
    if not ticket_text:
        return {}
        
    # Extract ticket data from the formatted text
    ticket_data = {}

    # Find the content between ```jira and ```
    import re
    jira_content = re.search(r"```jira\s*(.*?)```", ticket_text, re.DOTALL)

    if jira_content:
        content = jira_content.group(1)

        # Extract each field
        fields = ["Summary", "Description", "Priority", "Tags"]
        for field in fields:
            pattern = rf"{field}:\s*(.*?)(?=\n[A-Za-z]+:|$)"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                ticket_data[field] = match.group(1).strip()

    return ticket_data


def create_jira_ticket(ticket_text, attachments=None):
    """Process structured ticket text and create a Jira ticket"""
    # Parse the ticket data
    ticket_data = parse_jira_ticket_format(ticket_text)

    if not ticket_data:
        return "Failed to parse ticket data from text"

    try:
        # Create the Jira issue
        issue_key = create_jira_issue(ticket_data, attachments)
        return f"Successfully created Jira ticket: {issue_key}"
    except Exception as e:
        return f"Error creating Jira ticket: {str(e)}"


# Create the Jira agent
JiraAgent = AssistantAgent(
    name="JiraAgent",
    llm_config=llm_config,
    system_message="""
You are a specialized agent that creates Jira tickets from structured data.
You can create tickets and upload attachments to Jira.

When you receive formatted Jira ticket data, you will create the ticket in Jira and return the ticket ID.
""",
    function_map={
        "create_jira_ticket": create_jira_ticket
    }
)