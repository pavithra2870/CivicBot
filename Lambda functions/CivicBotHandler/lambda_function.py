import json
import logging
import os
import uuid
from datetime import datetime
import boto3
import requests # Requires Lambda Layer: used for simulating external API calls
import decimal # Add this import at the top

# Add this class definition below your imports:
class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal types from DynamoDB."""
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            # Check if it's an integer and return int, otherwise float
            return int(o) if o == int(o) else float(o)
        return super(DecimalEncoder, self).default(o)

# --- CONFIGURATION (MUST BE UPDATED) ---
REGION = 'us-east-1' # N. Virginia
DYNAMODB_ISSUES_TABLE = 'CivicIssues' # <-- VERIFY
DYNAMODB_SESSIONS_TABLE = 'UserSessions' # <-- VERIFY
S3_BUCKET_NAME = 'civicbot-media-reports'
# SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:123456789012:HighPriorityAlert' 
# The SNS line above is now COMMENTED OUT for Lex testing.

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name=REGION)
bedrock_rt = boto3.client('bedrock-runtime', region_name=REGION)
# sns_client = boto3.client('sns', region_name=REGION) # SNS Client commented out
translate_client = boto3.client('translate', region_name=REGION) 

# --- HELPER FUNCTIONS ---

def get_slot_value(slots, slot_name):
    """Safely extracts the interpreted value from a Lex V2 slot structure."""
    try:
        return slots.get(slot_name, {}).get('value', {}).get('interpretedValue')
    except AttributeError:
        return None

import json
import decimal # Must be imported at the top

import json
import decimal

def handle_welcome_intent(intent_request):
    """
    Handles the WelcomeIntent. Since the menu message is set in Lex's Initial Response,
    this function simply tells Lex to close the conversation, allowing the initial 
    Lex message to be displayed.
    """
    # NOTE: The actual menu is defined in the Lex Console.
    return close_dialog(intent_request, 'Fulfilled', 'Displaying main menu.')
def handle_retrieve_id(intent_request):
    """
    Handles forgotten Issue ID retrieval using only robust keyword filtering 
    (Bypassing Titan Embeddings model due to persistent errors).
    """
    slots = intent_request['sessionState']['intent']['slots']
    issue_keyword = get_slot_value(slots, 'IssueKeyword')
    user_location = get_slot_value(slots, 'UserLocation')

    if not issue_keyword or not user_location:
        return close_dialog(intent_request, 'Failed', "Please provide both the issue keyword and location to search.")

    try:
        # --- REMOVED: Titan Embeddings Invocation ---
        # No model call is made. The code proceeds directly to search.
        
        search_keyword = issue_keyword.lower().strip()
        search_location = user_location.lower().strip()
        
        issues_table = dynamodb.Table(DYNAMODB_ISSUES_TABLE)
        response = issues_table.scan()
        items = response.get('Items', [])
        
        found_reports = []
        
        for item in items:
            db_issue = item.get('IssueType', '').lower()
            db_location = item.get('UserLocation', '').lower()
            
            # Non-AI Search: Check if any major search term is contained in the stored issue/location text.
            # This is a robust keyword check that simulates similarity.
            
            # Check if the user's issue description is contained in the stored DB issue text:
            issue_match = all(word in db_issue for word in search_keyword.split()) 
            
            # Check if the user's location keyword is contained in the stored DB location text:
            location_match = (search_location in db_location)
            
            if issue_match and location_match:
                found_reports.append(item)
                break # Found the closest match
            
        # --- 2. RESPONSE ---
        if found_reports:
            report = found_reports[0]
            message = (
                f"✅ **Found Report - ID: {report['IssueID']}**\n\n"
                f"Your issue was found based on your description:\n"
                f"**Issue Type:** {report['IssueType']}\n"
                f"**Location:** {report['UserLocation']}\n"
                f"**Status:** {report['Status']}\n"
                f"You can now use this ID for tracking."
            )
        else:
            message = (
                "❌ I could not find a matching active report based on those keywords and location. "
                "Please ensure the issue description and location are accurate."
            )

        return close_dialog(intent_request, 'Fulfilled', message)

    except Exception as e:
        logger.error(f"ID Retrieval (Non-AI) failed: {e}")
        return close_dialog(intent_request, 'Failed', "An internal error occurred during the database search.")
def get_issue_priority(issue_text):
    """Uses Bedrock (Titan Text Express) with the simplest possible prompt structure."""
    try:
        # --- 1. ATOMIC INSTRUCTION PROMPT ---
        # Instruction is flattened to one line to eliminate newline errors.
        prompt_instruction = (
            "Classify the following issue as one word: HIGH, MEDIUM, or LOW. "
            "HIGH is for health/safety crises (e.g., sewage leak, road collapse). "
            "MEDIUM is for non-critical safety/service (e.g., flickering light, minor debris). "
            "LOW is for aesthetic/maintenance only (e.g., faded paint, small weeds). "
            f"Issue: {issue_text} Priority:"
        )
        
        # --- 2. CRITICAL FIX: ENFORCE PREFIXING WITHOUT COMPLEX F-STRINGS ---
        titan_input_text = "User: " + prompt_instruction.strip() + " Assistant:"
        
        # --- 3. INVOKE MODEL ---
        response = bedrock_rt.invoke_model(
            modelId='amazon.titan-text-express-v1',
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                "inputText": titan_input_text, 
                "textGenerationConfig": {
                    "maxTokenCount": 5, # We only need one word
                    "temperature": 0.0,
                    # We remove "stopSequences" as we no longer need complex JSON parsing
                }
            })
        )
        
        # --- 4. NEW PARSING LOGIC: Extract the first word ---
        response_body = json.loads(response.get('body').read())
        
        # The LLM is asked to output only the priority word, so we grab the first word.
        priority_word = response_body.get('results', [{}])[0].get('outputText', 'MEDIUM').split()[0].upper().strip()
        
        return priority_word if priority_word in ['HIGH', 'MEDIUM', 'LOW'] else 'MEDIUM'
        
    except Exception as e:
        # This will now only catch critical failures outside the API call itself.
        logger.error(f"Bedrock priority classification failed: {e}")
        return 'MEDIUM'
def get_similar_issues(issue_text):
    """Uses Titan Embeddings for vector search simulation (Feature 7)."""
    try:
        # Note: This step requires a live Vector DB (e.g., OpenSearch) for a full RAG system.
        # Here, we only test the ability to call the Titan Embeddings model.
        
        bedrock_rt.invoke_model(
            modelId='amazon.titan-embed-text-v1',
            contentType='application/json',
            accept='application/json',
            body=json.dumps({"inputText": issue_text})
        )
        # If the model call succeeds, we simulate finding a match
        if "pothole" in issue_text.lower() and "main street" in issue_text.lower():
             return ["A similar Pothole report (ID: 12345) found nearby. Upvote instead?"]
             
        return []
        
    except Exception as e:
        logger.error(f"Bedrock embedding model call succeeded but search is simulated: {e}")
        return []
        
def get_contextual_suggestion(issue_type):
    """Simulates Feature 9: Context-Aware Suggestions (using simple logic)."""
    if 'garbage' in issue_type.lower():
        # Simulating a call to a dummy weather API
        try:
            requests.get('http://dummy.weather.com')
            return "Note: Due to a reported heavy rain forecast, garbage pickup may be delayed."
        except:
            pass
    return ""

def generate_admin_summary(timeframe, report_type):
    """Uses Bedrock (Nova Premier) for complex data synthesis (Feature 10)."""
    try:
        issues_table = dynamodb.Table(DYNAMODB_ISSUES_TABLE)
        # Fetch mock data (or real data if available)
        response = issues_table.scan(Limit=10) # Fetch recent 10 items for a small demo
        issue_data = json.dumps(response.get('Items', []), cls=DecimalEncoder)

        # Update the 'prompt' variable inside generate_admin_summary
        prompt = f"""TASK: As a data analyst, summarize the following JSON data of civic reports for {timeframe}. Instructions: 
1. Identify the top 2 IssueType entries by count.
2. For those top 2, state the Count and the highest observed Priority (HIGH/MEDIUM/LOW).
3. **CRITICAL GUARDRAIL: Only report issues present in the JSON data.** If there is less than two issues, only report the ones that exist.
4. Format the output as a numbered list.
JSON Data: {issue_data}"""

        # Using Nova Premier for high-quality, complex summarization
        response = bedrock_rt.invoke_model(
            modelId='amazon.titan-text-express-v1',
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 1000,
                    "temperature": 0.1,
                }
            })
        )
        
        summary = json.loads(response.get('body').read()).get('results', [{}])[0].get('outputText', 'Error').strip()
        return summary
        
    except Exception as e:
        logger.error(f"Admin summary generation failed: {e}")
        return "Error generating summary. Please ensure Nova Premier access is granted."

# --- LEX INTENT HANDLERS ---
def handle_report_issue(intent_request):
    """Handles core report submission, retrieves location from Session Attributes, and saves to DynamoDB."""
    slots = intent_request['sessionState']['intent']['slots']
    session_attributes = intent_request['sessionState'].get('sessionAttributes', {})
    wa_id = intent_request.get('sessionId')
    # --- 1. DATA EXTRACTION AND VALIDATION ---
    issue_type_slot = get_slot_value(slots, 'IssueType')
    location_slot_text = get_slot_value(slots, 'UserLocation') # This captures text address or "report location"
    
    # Retrieve Location from Session Attributes (Passed by WhatsApp_Connector for shared location)
    gps_data = session_attributes.get('LocationData') # Format: "LAT:X|LONG:Y"
    
    # Determine the final location string for the DB
    if gps_data:
        # Prioritize GPS data if available (user shared pin)
        final_location = f"GPS Coordinates: {gps_data}" 
    elif location_slot_text:
        # Use the text address if no GPS data
        final_location = location_slot_text
    else:
        # This is the fail-safe if both inputs are missing (should not happen with a good flow)
        return close_dialog(intent_request, 'Failed', 'Error: Location data is required and was not provided.')

    # Check that the core issue description is present (Lex should ensure this is not None)
    if not issue_type_slot:
         return close_dialog(intent_request, 'Failed', 'Error: Please provide a description of the issue.')

    # --- 2. AI PROCESSING ---
    priority = get_issue_priority(issue_type_slot)
    similar_issues = get_similar_issues(issue_type_slot) # Community Validation check
    
    if similar_issues:
        msg_core = f"A similar issue was found nearby: {similar_issues[0]}. We'll link your report to it to avoid duplicates."
    else:
        msg_core = "Thank you for reporting. Your issue is new."
        
    # --- 3. DATABASE WRITE (CRITICAL STEP) ---
    issue_id = str(uuid.uuid4())[:8]
    issues_table = dynamodb.Table(DYNAMODB_ISSUES_TABLE)
    
    # Save the complete, structured report to DynamoDB
    issues_table.put_item(Item={
        'IssueID': issue_id,
        'Timestamp': int(datetime.now().timestamp()),
        'UserLocation': final_location,  # <-- ATTACHED LOCATION HERE
        'IssueType': issue_type_slot,
        'Priority': priority,
        'Status': 'New',
        'ExpectedCompletionDate': 'Under Review', # Default for new reports
        'UserID': wa_id
    })
    if wa_id:
        sessions_table = dynamodb.Table(DYNAMODB_SESSIONS_TABLE)
        sessions_table.put_item(Item={
            'UserID': wa_id, # Partition Key
            'LastIssueID': issue_id, # Save the ID of the new report
            'Timestamp': int(datetime.now().timestamp()),
        })
        logger.info(f"User session updated for WaId: {wa_id} with LastIssueID: {issue_id}")

    # --- 4. RESPONSE CONSTRUCTION ---
    # Construct the clear, user-friendly confirmation message
    response_msg = (
        f"✅ *Report Confirmed - ID: {issue_id}*\n\n"
        f"{msg_core}\n"
        f"*Issue:* {issue_type_slot}\n"
        f"*Location:* {final_location}\n"
        f"*Priority:* {priority}\n"
        f"*Expected Resolution:* Under Review (Notification will be sent when scheduled)."
    )

    # Note: SNS alert logic would be inserted here, if enabled.

    return close_dialog(intent_request, 'Fulfilled', response_msg)

    
    # 4. Critical Alert - SNS CALL IS OMITTED HERE FOR LEX TESTING
    
    # 5. Contextual Suggestion
    suggestion = get_contextual_suggestion(issue_type)
    
    response_msg = (
        f"{msg_core} Your report (ID: **{issue_id}**) has been logged as **{priority}** priority. "
        f"We will notify the relevant team."
    )
    if suggestion:
        response_msg += f" {suggestion}"

    return close_dialog(intent_request, 'Fulfilled', response_msg)
def handle_track_status(intent_request):
    """
    Handles tracking status.
    Directly fetches TrackingID from slots and looks up in DynamoDB.
    """
    logger.info("Starting handle_track_status intent...")
    
    # Get all slots from the incoming request
    slots = intent_request['sessionState']['intent']['slots']
    issues_table = dynamodb.Table(DYNAMODB_ISSUES_TABLE)
    
    # Get the specific 'TrackingID' slot value
    tracking_id = get_slot_value(slots, 'TrackingID')
    
    # --- 1. Check if an ID was provided at all ---
    if not tracking_id:
        logger.warning("Intent triggered, but 'TrackingID' slot is empty.")
        # We must fail here because the user didn't provide an ID
        return close_dialog(
            intent_request, 
            'Failed', 
            "I can't seem to find the ID. Please tell me the 8-digit tracking ID for your report, for example: 'What is the status of 1234abcd?'"
        )
    
    logger.info(f"Looking up status for ID: {tracking_id}")
    
    # --- 2. Try to find the ID in DynamoDB ---
    try:
        response = issues_table.get_item(Key={'IssueID': tracking_id})
        item = response.get('Item')
        
        # --- 3. Check if the item was found ---
        if item:
            # SUCCESS: We found the item!
            logger.info(f"Successfully found item for ID: {tracking_id}")
            
            # Format the user-friendly response
            completion_date = item.get('ExpectedCompletionDate', 'Under Review')
            message = (
                f"🚨 *Civic Report Status* 🚨\n\n"
                f"*ID:* {item['IssueID']}\n"
                f"*Issue:* {item.get('IssueType', 'N/A')}\n"
                f"*Current Status:* {item['Status'].upper()}\n"
                f"*Priority:* {item.get('Priority', 'N/A')}\n"
                f"*Expected Completion:* {completion_date}"
            )
            return close_dialog(intent_request, 'Fulfilled', message)
        
        else:
            # FAILURE: ID was valid, but not in our database
            logger.warning(f"No item found for ID: {tracking_id}")
            return close_dialog(
                intent_request, 
                'Failed', 
                f"Sorry, I could not find a report with the ID **{tracking_id}**. Please double-check the ID."
            )
            
    except Exception as e:
        # FAILURE: A database error occurred
        logger.error(f"Error getting item from DynamoDB: {e}")
        return close_dialog(
            intent_request, 
            'Failed', 
            "I'm sorry, I ran into an error trying to look up that ID. Please try again in a moment."
        )
def handle_rate_service(intent_request):
    """Handles service feedback and rating (Feature 8)."""
    rating = get_slot_value(intent_request['sessionState']['intent']['slots'], 'RatingScore')
    
    try:
        rating_val = int(rating)
    except (ValueError, TypeError):
        return close_dialog(intent_request, 'Failed', "Please provide a valid numeric rating between 1 and 5.")

    if 1 <= rating_val <= 5:
        # In production, you would associate this rating with a specific issue ID/User ID.
        feedback_msg = "Thank you for your feedback! Your rating helps us improve service quality."
        if rating_val <= 2:
            feedback_msg += " We are sorry the service was poor and will review this with the team."
        
        return close_dialog(intent_request, 'Fulfilled', feedback_msg)
    else:
        return close_dialog(intent_request, 'Failed', "Please rate service on a scale of 1 to 5.")


def handle_admin_summary(intent_request):
    """Handles admin requests for data analysis (Feature 10)."""
    slots = intent_request['sessionState']['intent']['slots']
    timeframe = get_slot_value(slots, 'Timeframe') or 'Last Week'
    report_type = get_slot_value(slots, 'ReportType') or 'Top Issues'
    
    # In a real system, a security check would go here to confirm Admin privileges
    
    summary_text = generate_admin_summary(timeframe, report_type)
    
    return close_dialog(intent_request, 'Fulfilled', f"**Admin Insight:**\n{summary_text}")

def delegate_dialog(intent_request):
    """Instructs Lex to continue the conversation based on its internal flow."""
    return {
        'sessionState': {
            'sessionAttributes': intent_request.get('sessionAttributes', {}),
            'dialogAction': {
                'type': 'Delegate'  # <-- Tells Lex: "I'm done, follow your flow chart."
            },
            'intent': intent_request['sessionState']['intent']
        },
        'requestAttributes': intent_request.get('requestAttributes')
    }
def dispatch(intent_request):
    """Routes the request to the correct intent handler."""
    intent_name = intent_request['sessionState']['intent']['name']
    # Log incoming intent for debugging
    logger.info(f"Dispatching intent: {intent_name}")
    if intent_name == 'ReportIssue':
        return handle_report_issue(intent_request)
    elif intent_name == 'TrackStatus':
        return handle_track_status(intent_request)
    elif intent_name == 'RateService':
        return handle_rate_service(intent_request)
    elif intent_name == 'AdminSummary':
        return handle_admin_summary(intent_request)
    elif intent_name == 'WelcomeIntent':
        return handle_welcome_intent(intent_request) 
    elif intent_name == 'RetrieveID': 
        return handle_retrieve_id(intent_request)
    elif intent_name == 'ForgotIdTrigger' or intent_name == 'StartReport': 
        # Since these intents have NO SLOTS and are fulfilled entirely by Lex routing,
        # we delegate control back immediately, letting Lex execute the Next Step 
        # (which is eliciting the first slot of the next intent).
        logger.info(f"Trigger Intent matched: {intent_name}. Delegating to Lex flow.")
        return delegate_dialog(intent_request)
    # Fallback/Default intents (like AMAZON.FallbackIntent) are handled by Lex default actions

    raise Exception('Intent with name ' + intent_name + ' not supported by Lambda dispatcher.')

# --- RESPONSE BUILDING FUNCTIONS ---

# --- REVISED RESPONSE BUILDING FUNCTION ---

def close_dialog(intent_request, fulfillment_state, message):
    """
    Constructs the final, complete JSON response required by Amazon Lex V2.
    This structure is highly sensitive and must be exactly correct for Lex to accept the message.
    """
    
    # 1. Get the current intent object and update its state
    current_intent = intent_request['sessionState']['intent']
    current_intent['state'] = fulfillment_state 
    
    # 2. Get sessionAttributes safely (to ensure the object is returned)
    session_attributes = intent_request['sessionState'].get('sessionAttributes', {})
    
    # 3. Construct the final Lex V2 response structure
    response = {
        # --- TOP LEVEL KEYS ---
        'sessionState': {
            'dialogAction': {
                'type': 'Close'
            },
            'intent': current_intent,
            'sessionAttributes': session_attributes 
        },
        'messages': [{
            'contentType': 'PlainText',
            'content': message
        }],
        # Ensure requestAttributes is included, even if empty
        'requestAttributes': intent_request.get('requestAttributes')
    }

    return response
# --- NEW UTILITY FUNCTION ---

# --- MAIN HANDLER ---

def lambda_handler(event, context):
    """
    The entry point for the Lambda function invoked by Amazon Lex V2.
    """
    logger.info(f"Received event: {json.dumps(event)}")
    # Lex V2 sends the entire conversation state; we dispatch based on the recognized intent
    response = dispatch(event)
    logger.info(f"Sending response: {json.dumps(response)}")
    return response
