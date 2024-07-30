import os
import json
import boto3
from PIL import Image
from datetime import datetime
from io import BytesIO
from aws_xray_sdk.core import patch_all, xray_recorder

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.logging import correlation_paths

logger = Logger(service="image-resizing-python")
tracer = Tracer(service="image-resizing-python")
metrics = Metrics(namespace="ImageResizing")

app = APIGatewayRestResolver()
cold_start = True
patch_all()

s3 = boto3.client('s3')

@tracer.capture_method
def resized_image_url(resized_key, bucket, region):
    logger.info(f"Bucket URL: https://s3-{region}.amazonaws.com/{bucket}/{resized_key}")
    return f"https://s3-{region}.amazonaws.com/{bucket}/{resized_key}"

@tracer.capture_method
def resize_image(bucket_name, key, size):
    try:
        size_split = size.split('x')
        
        with xray_recorder.in_subsegment("S3DownloadCall"):
            obj = s3.get_object(Bucket=bucket_name, Key=key)
            obj_body = obj['Body'].read()
            img = Image.open(BytesIO(obj_body))
        
        with xray_recorder.in_subsegment("ImageProcessingCall"):
            img = img.resize((int(size_split[0]), int(size_split[1])), Image.LANCZOS)
            buffer = BytesIO()
            img.save(buffer, 'JPEG')
            buffer.seek(0)

        resized_key = f"{size}_{key}"
        
        with xray_recorder.in_subsegment("S3UploadCall"):
            s3.put_object(Bucket=bucket_name, Key=resized_key, Body=buffer, ContentType='image/jpeg')

        resized_url = resized_image_url(resized_key, bucket_name, os.environ["AWS_REGION"])
        logger.info(f"Image resized successfully. Original Key: {key}, Resized Key: {resized_key}")

        return resized_url
    except Exception as e:
        logger.error(f"Error resizing image: {e}")
        raise e

@app.get("/resize-image/{image}/{size}")
@tracer.capture_method
@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
def process_image(event, context):
    global cold_start

    subsegment = xray_recorder.current_subsegment()
    subsegment.put_annotation(key="ColdStart", value=cold_start)

    if cold_start:
        cold_start = False

    try:
        key = event["pathParameters"]["image"]
        size = event["pathParameters"]["size"]
        logger.info(f"Processing image: {key} with size: {size}")
        
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
