import os
import boto3
import json
import time
import uuid
import logging
from decimal import Decimal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj)
        return super(DecimalEncoder, self).default(obj)

dynamodb = boto3.resource('dynamodb')

def api(event, context):
    http_method = event['requestContext']['http']['method']
    path = event['requestContext']['http']['path']

    logger.info(f"Received request: {http_method} {path}")

    if path == '/todos' and http_method == 'POST':
        return create(event)
    elif path == '/todos' and http_method == 'GET':
        return list_todos(event)
    elif path.startswith('/todos/') and http_method == 'GET':
        return get(event)
    elif path.startswith('/todos/') and http_method == 'PUT':
        return update(event)
    elif path.startswith('/todos/') and http_method == 'DELETE':
        return delete(event)
    else:
        logger.warning(f"Request not found: {http_method} {path}")
        return {
            "statusCode": 404,
            "body": json.dumps({"message": "Not Found"})
        }

def create(event):
    data = json.loads(event['body'])
    if 'text' not in data or 'checked' not in data:
        logger.error("Validation Failed: 'text' and 'checked' are required")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Validation Failed: 'text' and 'checked' are required"})
        }

    timestamp = int(time.time() * 1000)
    item = {
        'id': str(uuid.uuid1()),
        'text': data['text'],
        'checked': data['checked'],
        'createdAt': timestamp,
        'updatedAt': timestamp,
    }

    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

    try:
        table.put_item(Item=item)
        logger.info(f"Item created: {item}")
        return {
            "statusCode": 200,
            "body": json.dumps(item, cls=DecimalEncoder)
        }
    except Exception as e:
        logger.error(f"Error creating item: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

def list_todos(event):
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

    try:
        result = table.scan()
        logger.info("Items fetched successfully")
        return {
            "statusCode": 200,
            "body": json.dumps(result['Items'], cls=DecimalEncoder)
        }
    except Exception as e:
        logger.error(f"Error fetching items: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

def get(event):
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

    try:
        result = table.get_item(
            Key={
                'id': event['pathParameters']['id']
            }
        )
        if 'Item' in result:
            logger.info(f"Item fetched: {result['Item']}")
            return {
                "statusCode": 200,
                "body": json.dumps(result['Item'], cls=DecimalEncoder)
            }
        else:
            logger.warning("Item not found")
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Item not found"})
            }
    except Exception as e:
        logger.error(f"Error fetching item: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

def update(event):
    data = json.loads(event['body'])
    if 'text' not in data or 'checked' not in data:
        logger.error("Validation Failed: 'text' and 'checked' are required")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Validation Failed: 'text' and 'checked' are required"})
        }

    timestamp = int(time.time() * 1000)

    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

    try:
        result = table.update_item(
            Key={
                'id': event['pathParameters']['id']
            },
            ExpressionAttributeNames={
                '#todo_text': 'text',
            },
            ExpressionAttributeValues={
                ':text': data['text'],
                ':checked': data['checked'],
                ':updatedAt': timestamp,
            },
            UpdateExpression='SET #todo_text = :text, '
                             'checked = :checked, '
                             'updatedAt = :updatedAt',
            ReturnValues='ALL_NEW',
        )
        logger.info(f"Item updated: {result['Attributes']}")
        return {
            "statusCode": 200,
            "body": json.dumps(result['Attributes'], cls=DecimalEncoder)
        }
    except Exception as e:
        logger.error(f"Error updating item: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

def delete(event):
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

    try:
        table.delete_item(
            Key={
                'id': event['pathParameters']['id']
            }
        )
        logger.info(f"Item deleted: {event['pathParameters']['id']}")
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Item deleted"})
        }
    except Exception as e:
        logger.error(f"Error deleting item: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
