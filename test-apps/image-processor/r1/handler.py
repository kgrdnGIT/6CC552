import os
import json
import boto3
from PIL import Image
import numpy as np
from datetime import datetime
from aws_xray_sdk.core import patch_all, xray_recorder

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.logging import correlation_paths

logger = Logger(service="enhanced-image-processing-app")
tracer = Tracer(service="enhanced-image-processing-app")
metrics = Metrics(namespace="ImageProcessing")

s3 = boto3.client('s3')
rekognition = boto3.client('rekognition')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
app = APIGatewayRestResolver()
cold_start = True
patch_all()

@tracer.capture_method
def detect_objects(image_key):
    try:
        logger.info(f"Detecting objects in image: {image_key}")
        
        with xray_recorder.in_subsegment("RekognitionCall"):
            start_time = datetime.now()
            response = rekognition.detect_labels(
                Image={'S3Object': {'Bucket': 'resized-images-python-kg001', 'Name': image_key}},
                MaxLabels=10,
                MinConfidence=70
            )
            labels = [label['Name'] for label in response['Labels']]
            
        duration = (datetime.now() - start_time).total_seconds() * 1000
        metrics.add_metric(name="RekognitionCallDuration", unit=MetricUnit.Milliseconds, value=duration)
        
        logger.debug(f"Objects detected: {labels}")
        return labels
    except Exception as e:
        logger.exception(f"Error detecting objects in image: {e}")
        raise

@tracer.capture_method
def store_metadata(image_key, img_shape, detected_objects):
    try:
        logger.info("Storing image metadata and detected objects in DynamoDB")
        
        with xray_recorder.in_subsegment("DynamoDBCall"):
            start_time = datetime.now()
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            timestamped_image_key = f"{image_key}_{timestamp}"
            
            table.put_item(Item={'image_key': timestamped_image_key, 'image_shape': img_shape, 'detected_objects': detected_objects})
            
        duration = (datetime.now() - start_time).total_seconds() * 1000
        metrics.add_metric(name="DynamoDBCallDuration", unit=MetricUnit.Milliseconds, value=duration)
        
        logger.info("Image metadata and detected objects stored in DynamoDB")
    except Exception as e:
        logger.exception(f"Error storing metadata in DynamoDB: {e}")
        raise

@app.get("/process-image")
@tracer.capture_method
@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
def process_image(event, context):
    global cold_start

    subsegment = xray_recorder.current_subsegment()
    subsegment.put_annotation(key="ColdStart", value=cold_start)

    if cold_start:
        cold_start = False

    try:
        body = json.loads(event['body'])
        image_key = body['image_key']
        bucket_name = 'resized-images-python-kg001'

        logger.info(f"Processing image: {image_key}")
        
        with xray_recorder.in_subsegment("S3DownloadCall"):
            start_time = datetime.now()
            s3.download_file(bucket_name, image_key, '/tmp/image.jpg')
            duration = (datetime.now() - start_time).total_seconds() * 1000
            metrics.add_metric(name="S3DownloadDuration", unit=MetricUnit.Milliseconds, value=duration)
        
        with Image.open('/tmp/image.jpg') as img:
            img_array = np.array(img)
            img_shape = img_array.shape
        logger.info(f"Image processed: shape={img_shape}")

        detected_objects = detect_objects(image_key)
        logger.info(f"Objects detected: {detected_objects}")

        store_metadata(image_key, img_shape, detected_objects)

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Image processed, objects detected, and metadata stored successfully'})
        }
    except Exception as e:
        logger.exception(f"Error processing image: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Error processing image'})
        }
