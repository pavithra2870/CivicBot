import json
import os
import decimal
import time
from twilio.rest import Client
from datetime import datetime
import logging # <-- REQUIRED IMPORT

# Initialize the logger object globally
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- CONFIGURATION (Reads from Environment Variables) ---
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID').strip()
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN').strip()
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER').strip() # Twilio Sandbox Number
# --- END CONFIGURATION ---

# Initialize Twilio Client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
def build_notification_message(new_record, old_record):
    """Determines the type of change and builds a user-friendly message."""
    issue_id = new_record['IssueID']['S']
    new_status = new_record['Status']['S']
    old_status = old_record.get('Status', {}).get('S')
    old_date = old_record.get('ExpectedCompletionDate', {}).get('S')
    new_date = new_record.get('ExpectedCompletionDate', {}).get('S')
    # 1. Status Change (New -> Processing/Completed)
    if new_status != old_status:
        if new_status == 'Processing':
            return f"🛠️ UPDATE: Issue {issue_id} is now *PROCESSING*. A crew has been dispatched."
        elif new_status == 'Completed':
            # This triggers the Rating Request (Feature 8)
            return (f"✅ RESOLVED: Issue {issue_id} has been *COMPLETED*! "
                    f"Please respond with 'Rate Service' to give 1-5 star feedback.")
    
    # 2. Expected Completion Date Change (Official Review)
    if new_status != old_status and new_status == 'Processing' and new_date and (new_date != old_date):
        return (f"🗓️ REVIEWED: Issue {issue_id} has an expected completion date of **{new_date}**. "
                f"We will notify you of further progress.")
    
    return None # No significant change to notify user about

def send_whatsapp_notification(recipient_waid, message):
    """Sends the actual outbound message via Twilio."""
    try:
        # Note: 'To' must include the whatsapp: prefix and the user's phone number
        # We assume the user's phone number (WaId) is stored in the record.
        # For POC, we assume the user's phone number is included in the event or retrieved from UserSessions
        
        # In a real app, the full number (including +country code) would be passed from the main table.
        # Since we don't have that field, we'll use a placeholder variable for the recipient.
        
        twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message,
            to='whatsapp:+XXXXXXXXXXXX' # logic to get the whatsapp number from dynamodb table
        )
        logger.info(f"Notification sent successfully. Twilio SID: {message_resource.sid}")
    except Exception as e:
        logger.error(f"Twilio send failed: {e}")

def lambda_handler(event, context):
    """Processes records from the DynamoDB Stream."""
    logger.info(f"Received {len(event['Records'])} records from stream.")
    
    for record in event['Records']:
        if record['eventName'] in ('INSERT', 'MODIFY'):
            
            # DynamoDB Stream data is nested under 'dynamodb' and encoded in strings (S) or numbers (N)
            new_record = record['dynamodb']['NewImage']
            old_record = record['dynamodb'].get('OldImage', {})
            
            # The user's phone number (WaId) must be present in the record to send a message back.
            # We assume it is stored in the record under a field like 'UserID' or 'WaId'.
            # For this code, we'll assume it's stored under a field named 'WaId' (string type)
            recipient_waid = new_record.get('UserID', {}).get('S') # Get the user's phone number
            if not recipient_waid:
                logger.warning("Record skipped: Missing WaId for notification.")
                continue
            if recipient_waid.startswith('+'): 
                    e164_number = recipient_waid
            else:
                    e164_number = f"+{recipient_waid}"
            RECIPIENT_PHONE_NUMBER = f"whatsapp:{e164_number}"
            notification_message = build_notification_message(new_record, old_record)
            if notification_message:
                send_whatsapp_notification(RECIPIENT_PHONE_NUMBER, notification_message)
    
    return {'statusCode': 200, 'body': 'Stream processing complete.'}
