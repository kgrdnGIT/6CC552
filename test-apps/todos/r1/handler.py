import os
import boto3
import json
import time
import uuid
import logging
from decimal import Decimal
from aws_xray_sdk.core import patch_all, xray_recorder
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit

# Configure logging
logger = Logger(service="todo-service")
tracer = Tracer(service="todo-service")
metrics = Metrics(namespace="TodoService")

# Patch all supported libraries for X-Ray
patch_all()

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')

# Track cold start
cold_start = True

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj)
        return super(DecimalEncoder, self).default(obj)

@tracer.capture_method
def api(event, context):
    global cold_start

    subsegment = xray_recorder.current_subsegment()
    subsegment.put_annotation(key="ColdStart", value=cold_start)
    cold_start = False

    logger.info(f"Received event: {json.dumps(event)}")

    http_method = event['requestContext']['http']['method']
    path = event['requestContext']['http']['path']

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

@tracer.capture_method
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
        with xray_recorder.in_subsegment("DynamoDBCall"):
            start_time = time.time()
            table.put_item(Item=item)
            duration = (time.time() - start_time) * 1000
            metrics.add_metric(name="DynamoDBPutItemDuration", unit=MetricUnit.Milliseconds, value=duration)
        
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

@tracer.capture_method
def list_todos(event):
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

    try:
        with xray_recorder.in_subsegment("DynamoDBCall"):
            start_time = time.time()
            result = table.scan()
            duration = (time.time() - start_time) * 1000
            metrics.add_metric(name="DynamoDBScanDuration", unit=MetricUnit.Milliseconds, value=duration)

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

@tracer.capture_method
def get(event):
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

    try:
        with xray_recorder.in_subsegment("DynamoDBCall"):
            start_time = time.time()
            result = table.get_item(
                Key={
                    'id': event['pathParameters']['id']
                }
            )
            duration = (time.time() - start_time) * 1000
            metrics.add_metric(name="DynamoDBGetItemDuration", unit=MetricUnit.Milliseconds, value=duration)

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

@tracer.capture_method
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
        with xray_recorder.in_subsegment("DynamoDBCall"):
            start_time = time.time()
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
            duration = (time.time() - start_time) * 1000
            metrics.add_metric(name="DynamoDBUpdateItemDuration", unit=MetricUnit.Milliseconds, value=duration)

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

@tracer.capture_method
def delete(event):
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

    try:
        with xray_recorder.in_subsegment("DynamoDBCall"):
            start_time = time.time()
            table.delete_item(
                Key={
                    'id': event['pathParameters']['id']
                }
            )
            duration = (time.time() - start_time) * 1000
            metrics.add_metric(name="DynamoDBDeleteItemDuration", unit=MetricUnit.Milliseconds, value=duration)

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
