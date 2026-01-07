
import json
import os
import boto3
import decimal
from datetime import datetime

# --- Helper Class to serialize DynamoDB Decimal types ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

# --- Initialize Clients (outside handler for reuse) ---
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('DYNAMODB_TABLE_NAME')
issues_table = dynamodb.Table(table_name)

# --- CORS Headers ---
headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "PUT,OPTIONS" # Allow PUT for updates
}

def lambda_handler(event, context):
    try:
        # Get the IssueID from the URL path (e.g., /issues/1234abcd)
        issue_id = event['pathParameters']['issueId']
        
        # Get the new data from the request body
        body = json.loads(event['body'])
        new_status = body.get('Status')
        new_date = body.get('ExpectedCompletionDate')

        if not new_status or not new_date:
            raise ValueError("Status and ExpectedCompletionDate are required.")
        current_time_int = int(datetime.now().timestamp())
        # Update the item in DynamoDB
        response = issues_table.update_item(
    Key={'IssueID': issue_id},
    
    # CRITICAL: Removed the problematic #ts update.
    # We use #lmt (StatusLastModified) for tracking changes.
    UpdateExpression="SET #s = :s, #ecd = :ecd, #lmt = :lmt",
    
    ExpressionAttributeNames={
        '#s': 'Status',
        '#ecd': 'ExpectedCompletionDate',
        '#lmt': 'StatusLastModified' 
        # Removed '#ts': 'Timestamp'
    },
    ExpressionAttributeValues={
        ':s': new_status,
        ':ecd': new_date,
        ':lmt': current_time_int  # StatusLastModified is updated here
        # Removed ':ts_val': current_time_int
    },
    ReturnValues="ALL_NEW" 
)

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response.get('Attributes', {}), cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({"error": str(e)})
        }
