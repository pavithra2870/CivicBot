import json
import os
import boto3
import decimal
from boto3.dynamodb.conditions import Key

# --- Helper Class to serialize DynamoDB Decimal types ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

# --- Initialize Clients (outside handler for reuse) ---
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('DYNAMODB_TABLE_NAME')
index_name = os.environ.get('GSI_NAME')
issues_table = dynamodb.Table(table_name)

# --- CORS Headers ---
headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,OPTIONS"
}

def lambda_handler(event, context):
    try:
        # Check for optional query parameter ?status=New
        params = event.get('queryStringParameters')
        status_filter = None
        if params and 'status' in params:
            status_filter = params['status']
            
        if status_filter:
            # Use the GSI to find all issues with a specific status
            response = issues_table.query(
                IndexName=index_name,
                KeyConditionExpression=Key('Status').eq(status_filter),
                ScanIndexForward=False # Sort by timestamp, newest first
            )
        else:
            # If no filter, scan the whole table (less efficient, ok for small data)
            response = issues_table.scan(Limit=500)

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response.get('Items', []), cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({"error": str(e)})
        }
