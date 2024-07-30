import os
import boto3
import json
import time
import uuid
from decimal import Decimal
from aws_lambda_powertools import Logger

logger = Logger(service="todos-service")

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj)
        return super(DecimalEncoder, self).default(obj)

dynamodb = boto3.resource('dynamodb')

@logger.inject_lambda_context
def api(event, context):
    print(event)
    http_method = event['requestContext']['http']['method']
    path = event['requestContext']['http']['path']
    
    try:
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
            return {
                "statusCode": 404,
                "body": json.dumps({"message": "Not Found"})
            }
    except Exception as e:
        logger.error(f"Error handling request: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }

def create(event):
    data = json.loads(event['body'])
    if 'text' not in data or 'checked' not in data:
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
            return {
                "statusCode": 200,
                "body": json.dumps(result['Item'], cls=DecimalEncoder)
            }
        else:
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
