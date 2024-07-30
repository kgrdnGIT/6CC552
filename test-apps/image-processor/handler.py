import os
import json
import boto3
import logging
from PIL import Image
import numpy as np
from datetime import datetime

# Initialize AWS services
s3 = boto3.client('s3')
rekognition = boto3.client('rekognition')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Set logging level to DEBUG

def detect_objects(image_key):
    try:
        # Detect objects in the image using Rekognition
        response = rekognition.detect_labels(
            Image={'S3Object': {'Bucket': 'resized-images-python-kg001', 'Name': image_key}},
            MaxLabels=10,
            MinConfidence=70
        )
        labels = [label['Name'] for label in response['Labels']]
        return labels
    except Exception as e:
        logger.error(f"Error detecting objects in image: {e}")
        raise

def process_image(event, context):

    try:
        # Placeholder for image processing logic
        body = json.loads(event['body'])
        image_key = body['image_key']
        bucket_name = 'resized-images-python-kg001'

        # Log image key and bucket name
        logger.debug(f"Image key: {image_key}, Bucket name: {bucket_name}")
        
        # Download image from S3
        s3.download_file(bucket_name, image_key, '/tmp/image.jpg')
        logger.info(f"Image downloaded from S3: {image_key}")
        
        # Open and process the image
        # Open and process the image
        with Image.open('/tmp/image.jpg') as img:
            img_array = np.array(img)
            img_shape = img_array.shape
        logger.info(f"Image processed: shape={img_shape}")

        # Detect objects in the image
        detected_objects = detect_objects(image_key)
        logger.info(f"Objects detected: {detected_objects}")

        # Generate a timestamp and append it to the image_key
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        timestamped_image_key = f"{image_key}_{timestamp}"
        
        # Store image metadata and detected objects in DynamoDB
        table.put_item(Item={'image_key': timestamped_image_key, 'image_shape': img_shape, 'detected_objects': detected_objects})
        logger.info("Image metadata and detected objects stored in DynamoDB")

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Image processed, objects detected, and metadata stored successfully'})
        }
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Error processing image'})
        }

