import os
import json
import boto3
from PIL import Image
from io import BytesIO
from aws_lambda_powertools import Logger

logger = Logger(service="image-resizing-python")

s3 = boto3.client('s3')

def resized_image_url(resized_key, bucket, region):
    return f"https://s3-{region}.amazonaws.com/{bucket}/{resized_key}"

def resize_image(bucket_name, key, size):
    try:
        size_split = size.split('x')
        
        obj = s3.get_object(Bucket=bucket_name, Key=key)
        obj_body = obj['Body'].read()
        img = Image.open(BytesIO(obj_body))
        
        img = img.resize((int(size_split[0]), int(size_split[1])), Image.LANCZOS)
        buffer = BytesIO()
        img.save(buffer, 'JPEG')
        buffer.seek(0)

        resized_key = f"{size}_{key}"
        
        s3.put_object(Bucket=bucket_name, Key=resized_key, Body=buffer, ContentType='image/jpeg')

        resized_url = resized_image_url(resized_key, bucket_name, os.environ["AWS_REGION"])
        return resized_url
    except Exception as e:
        logger.error(f"Error resizing image: {e}")
        raise

@logger.inject_lambda_context
def process_image(event, context):
    try:
        key = event["pathParameters"]["image"]
        size = event["pathParameters"]["size"]
        
        result_url = resize_image(os.environ["BUCKET"], key, size)
        
        return {
            "statusCode": 301,
            "headers": {
                "Location": result_url
            }
        }
    except Exception as e:
        logger.error(f"Error handling request: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Error processing image"})
        }
