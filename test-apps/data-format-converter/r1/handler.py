import boto3
import json
import logging
import xmltodict
from aws_xray_sdk.core import patch_all, xray_recorder
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit
from datetime import datetime

# Initialize Powertools Logger, Tracer, and Metrics
logger = Logger(service="file-conversion-service")
tracer = Tracer(service="file-conversion-service")
metrics = Metrics(namespace="FileConversion")

# Patch all supported libraries for AWS X-Ray
patch_all()

# Track if the function is experiencing a cold start
cold_start = True

s3_client = boto3.client('s3')

@tracer.capture_method
def convert_json_to_xml(data):
    # Convert JSON to XML using xmltodict library
    xml_data = xmltodict.unparse(json.loads(data))
    return xml_data

@tracer.capture_method
def convert_xml_to_json(data):
    # Convert XML to JSON using xmltodict library
    json_data = json.dumps(xmltodict.parse(data))
    return json_data

@tracer.capture_lambda_handler
@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
def lambda_handler(event, context):
    global cold_start

    # Add cold start annotation to X-Ray subsegment
    subsegment = xray_recorder.current_subsegment()
    subsegment.put_annotation("ColdStart", cold_start)

    if cold_start:
        cold_start = False

    # Log the incoming event
    logger.info("Received event: %s", json.dumps(event))

    # Parse request parameters
    bucket = event['queryStringParameters']['bucket']
    input_key = event['queryStringParameters']['key']
    output_format = event['queryStringParameters']['format']

    # Retrieve file from S3
    with xray_recorder.in_subsegment("S3GetObjectCall"):
        start_time = datetime.now()
        response = s3_client.get_object(Bucket=bucket, Key=input_key)
        duration = (datetime.now() - start_time).total_seconds() * 1000
        metrics.add_metric(name="S3GetObjectDuration", unit=MetricUnit.Milliseconds, value=duration)
        
    file_content = response['Body'].read().decode('utf-8')

    # Perform file conversion
    if output_format == 'xml':
        converted_data = convert_json_to_xml(file_content)
        output_key = f'converted_{input_key}.xml'
    elif output_format == 'json':
        converted_data = convert_xml_to_json(file_content)
        output_key = f'converted_{input_key}.json'
    else:
        # Log invalid output format
        logger.error("Invalid output format specified: %s", output_format)
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid output format specified'})
        }

    # Upload converted file back to S3
    with xray_recorder.in_subsegment("S3PutObjectCall"):
        start_time = datetime.now()
        s3_client.put_object(Bucket=bucket, Key=output_key, Body=converted_data)
        duration = (datetime.now() - start_time).total_seconds() * 1000
        metrics.add_metric(name="S3PutObjectDuration", unit=MetricUnit.Milliseconds, value=duration)

    # Generate URI for the converted object
    uri = f's3://{bucket}/{output_key}'

    # Log the URI of the converted object
    logger.info("URI of the converted object: %s", uri)

    # Generate pre-signed URL for accessing the converted object
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': output_key},
            ExpiresIn=3600  # URL expiration time in seconds (1 hour)
        )

        # Log the generated pre-signed URL
        logger.info("Generated pre-signed URL: %s", url)
    except Exception as e:
        # Log error if unable to generate pre-signed URL
        logger.error("Error generating pre-signed URL: %s", str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

    # Return URI and pre-signed URL in the response
    return {
        'statusCode': 200,
        'body': json.dumps({'uri': uri, 'presigned_url': url})
    }
