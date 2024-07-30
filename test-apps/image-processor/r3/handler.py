import os
import json
import boto3
from PIL import Image
import numpy as np
from datetime import datetime

from aws_lambda_powertools import Logger

logger = Logger(service="enhanced-image-processing-app")

s3 = boto3.client('s3')
rekognition = boto3.client('rekognition')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

def detect_objects(image_key):
    try:
        
       start_time = datetime.now()
       response = rekognition.detect_labels(
            Image={'S3Object': {'Bucket': 'resized-images-python-kg001', 'Name': image_key}},
            MaxLabels=10,
            MinConfidence=70
       )
       labels = [label['Name'] for label in response['Labels']]
            
       return labels
    except Exception as e:
        logger.exception(f"Error detecting objects in image: {e}")
        raise

def store_metadata(image_key, img_shape, detected_objects):
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    timestamped_image_key = f"{image_key}_{timestamp}"
    try:
        table.put_item(Item={'image_key': timestamped_image_key, 'image_shape': img_shape, 'detected_objects': detected_objects})
            
    except Exception as e:
        logger.exception(f"Error storing metadata in DynamoDB: {e}")
        raise

def process_image(event, context):
    try:
        body = json.loads(event['body'])
        image_key = body['image_key']
        bucket_name = 'resized-images-python-kg001'

        s3.download_file(bucket_name, image_key, '/tmp/image.jpg')
        
        with Image.open('/tmp/image.jpg') as img:
            img_array = np.array(img)
            img_shape = img_array.shape

            detected_objects = detect_objects(image_key)
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
