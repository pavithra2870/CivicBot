import json
import os
import urllib.parse
import boto3
import uuid
import mimetypes
import urllib.request
# Import MessagingResponse for building the XML response
from twilio.twiml.messaging_response import MessagingResponse 
# Import Twilio client (optional for outbound, but good practice)
from twilio.rest import Client 

# --- CONFIGURATION (Reads from Environment Variables) ---
REGION = 'us-east-1' 
LEX_BOT_ID = os.environ.get('LEX_BOT_ID')
LEX_ALIAS_ID = os.environ.get('LEX_ALIAS_ID')
LEX_LOCALE_ID = os.environ.get('LEX_LOCALE_ID')
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
DDB_TABLE_NAME = os.environ.get('DDB_TABLE_NAME')
# --- END CONFIGURATION ---
s3_client = boto3.client('s3')
dynamo_resource = boto3.resource('dynamodb')
ddb_table = dynamo_resource.Table(DDB_TABLE_NAME)
# Global client initialization
lex_client = boto3.client('lexv2-runtime', region_name=REGION)

def invoke_lex(user_id, text_input, session_attributes={}):
    """Sends the user's message to the Lex Bot and retrieves the response."""
    try:
        response = lex_client.recognize_text(
            botId=LEX_BOT_ID,
            botAliasId=LEX_ALIAS_ID,
            localeId=LEX_LOCALE_ID,
            sessionId=user_id,
            text=text_input,
            sessionState={'sessionAttributes': session_attributes}
        )
        # Extract the final message content
        messages = response.get('messages', [])
        if messages:
            return messages[0].get('content', 'Sorry, I had trouble processing that request.')
        return 'Bot did not return a message.'
        
    except Exception as e:
        print(f"Error invoking Lex: {e}")
        return "The bot's AI brain encountered an error."
def handle_media_upload(user_id, media_url, content_type):
    """Downloads media from Twilio, uploads to S3, and updates DynamoDB."""
    try:
        # 1. Download media from Twilio's URL
        print(f"Downloading media from: {media_url}")
        with urllib.request.urlopen(media_url) as response:
            media_data = response.read()
            
        # 2. Generate a unique S3 key (filename)
        # Guess the file extension (e.g., .jpg) from the content type (e.g., image/jpeg)
        extension = mimetypes.guess_extension(content_type)
        if not extension:
            extension = '.bin' # Default to binary if type is unknown
            
        # Create a unique path: uploads/USER_ID/UNIQUE_ID.extension
        s3_key = f"uploads/{user_id}/{uuid.uuid4()}{extension}"
        
        # 3. Upload to S3
        print(f"Uploading to S3 Bucket: {S3_BUCKET_NAME}, Key: {s3_key}")
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=media_data,
            ContentType=content_type
        )
        
        # 4. Generate the S3 URL
        # This is the standard S3 URL format
        s3_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
        
        # 5. Update DynamoDB
        print(f"Updating DynamoDB table: {DDB_TABLE_NAME} for user: {user_id}")
        ddb_table.update_item(
            Key={'UserId': user_id}, # Assumes your Primary Key is 'UserId'
            UpdateExpression="SET MediaAttached = :url", # Set the column
            ExpressionAttributeValues={
                ':url': s3_url
            },
            ReturnValues="NONE" # No need to return the updated item
        )
        
        # 6. Return a success message for the user
        return "Thank you, I've received your media."
        
    except Exception as e:
        print(f"Error handling media upload: {e}")
        return "Sorry, I had a problem saving your media file."

def lambda_handler(event, context):
    """Handles incoming POST requests from Twilio."""
    try:
        # Twilio sends data as URL-encoded form data in the body
        body_str = event.get('body', '')
        
        # Parse the form data sent by Twilio
        data = urllib.parse.parse_qs(body_str)
        
        # --- INBOUND DATA EXTRACTION ---
        # The 'WaId' is Twilio's unique user ID for WhatsApp
        user_id = data.get('WaId', ['N/A'])[0] 
        # The 'Body' contains the text message
        num_media = int(data.get('NumMedia', ['0'])[0])
        if num_media > 0:
            # --- MEDIA PROCESSING ---
            media_url = data.get('MediaUrl0', [''])[0]
            content_type = data.get('MediaContentType0', ['application/octet-stream'])[0]
            
            if media_url:
                response_text = handle_media_upload(user_id, media_url, content_type)
            else:
                response_text = "I see you tried to send media, but I couldn't find it."
        else:
            # --- TEXT PROCESSING (Original Flow) ---
            text_input = data.get('Body', [''])[0].strip()
            if not text_input:
                response_text = "Please send a message."
            else:
                response_text = invoke_lex(user_id, text_input)

        # --- OUTBOUND RESPONSE (TwiML) ---
        twiml = MessagingResponse()
        twiml.message(response_text)
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'text/xml'},
            'body': str(twiml)
        }

    except Exception as e:
        print(f"Full Lambda error: {e}")
        # Send a generic failure message back to the user via TwiML
        twiml = MessagingResponse()
        twiml.message("I'm sorry, an internal server error occurred.")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'text/xml'},
            'body': str(twiml)
        }
