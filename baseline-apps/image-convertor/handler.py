import datetime
import json
import os
from io import BytesIO
import logging

import boto3
import PIL
from PIL import Image

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def resized_image_url(resized_key, bucket, region):
    return "https://s3-{region}.amazonaws.com/{bucket}/{resized_key}".format(
        bucket=bucket, region=region, resized_key=resized_key
    )

def resize_image(bucket_name, key, size):
    s3 = boto3.resource('s3')
    
    try:
        size_split = size.split('x')
        obj = s3.Object(bucket_name=bucket_name, key=key)
        obj_body = obj.get()['Body'].read()
        img = Image.open(BytesIO(obj_body))
        img = img.resize((int(size_split[0]), int(size_split[1])), PIL.Image.LANCZOS)
        buffer = BytesIO()
        img.save(buffer, 'JPEG')
        buffer.seek(0)

        resized_key = "{size}_{key}".format(size=size, key=key)
        obj = s3.Object(bucket_name=bucket_name, key=resized_key)
        obj.put(Body=buffer, ContentType='image/jpeg')

        resized_url = resized_image_url(resized_key, bucket_name, os.environ["AWS_REGION"])
        logger.info("Image resized successfully. Original Key: %s, Resized Key: %s", key, resized_key)
        
        return resized_url
    except Exception as e:
        logger.error("Error resizing image: %s", e)
        raise e

def call(event, context):
    key = event["pathParameters"]["image"]
    size = event["pathParameters"]["size"]

    try:
        result_url = resize_image(os.environ["BUCKET"], key, size)
        
        response = {
            "statusCode": 301,
            "body": "",
            "headers": {
                "location": result_url
            }
        }
        return response
    except Exception as e:
        logger.error("Error handling request: %s", e)
        raise e
