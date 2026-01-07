import json
import os
import boto3
import decimal
import collections

# --- Helper Class to serialize DynamoDB Decimal types ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

# --- Initialize Clients (outside handler for reuse) ---
dynamodb = boto3.resource('dynamodb')
bedrock_rt = boto3.client('bedrock-runtime', region_name=os.environ.get('REGION'))
table_name = os.environ.get('DYNAMODB_TABLE_NAME')
model_id = os.environ.get('BEDROCK_MODEL_ID')
issues_table = dynamodb.Table(table_name)

# --- CORS Headers ---
headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "GET,OPTIONS"
}

def get_ai_insight(items_json):
    """Calls Bedrock for a high-level summary."""
    try:
        prompt_instruction = (
            "You are a city operations analyst. Based on this JSON list of open civic issues, "
            "write a 2-sentence executive summary identifying the most critical trend. "
            f"DATA: {items_json}"
        )
        
        titan_input_text = f"User: {prompt_instruction.strip()} Assistant:"
        
        response = bedrock_rt.invoke_model(
            modelId=model_id,
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                "inputText": titan_input_text,
                "textGenerationConfig": {"maxTokenCount": 200, "temperature": 0.1}
            })
        )
        body = json.loads(response.get('body').read())
        return body.get('results', [{}])[0].get('outputText', 'No insight generated.').strip()
    except Exception as e:
        print(f"Bedrock insight failed: {e}")
        return "AI insight is currently unavailable."


def lambda_handler(event, context):
    try:
        # --- 1. Get All Data ---
        # Scan is acceptable here as analytics needs all data
        response = issues_table.scan()
        items = response.get('Items', [])

        # --- 2. Python-based Aggregation (for Charts) ---
        status_counts = collections.defaultdict(int)
        priority_counts = collections.defaultdict(int)
        total_pending = 0

        for item in items:
            status = item.get('Status', 'Unknown')
            priority = item.get('Priority', 'Unknown')
            
            status_counts[status] += 1
            priority_counts[priority] += 1
            
            if status.lower() in ['new', 'processing']:
                total_pending += 1

        # --- 3. Bedrock AI Insight ---
        # Get AI insight based on the first 20 items (to avoid huge Bedrock payload)
        ai_summary = get_ai_insight(json.dumps(items[:20], cls=DecimalEncoder))

        # --- 4. Format the Dashboard Payload ---
        dashboard_data = {
            "keyMetrics": {
                "totalPending": total_pending,
                "highPriority": priority_counts.get('HIGH', 0),
                "totalCompleted": status_counts.get('Completed', 0)
            },
            "byStatus": [{"name": k, "value": v} for k, v in status_counts.items()],
            "byPriority": [{"name": k, "value": v} for k, v in priority_counts.items()],
            "aiExecutiveSummary": ai_summary
        }

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(dashboard_data)
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({"error": str(e)})
        }
