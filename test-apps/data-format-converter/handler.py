import boto3
import json
import logging
import xmltodict

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')

def convert_json_to_xml(data):
    # Convert JSON to XML using xmltodict library
    xml_data = xmltodict.unparse(json.loads(data))
    return xml_data

def convert_xml_to_json(data):
    # Convert XML to JSON using xmltodict library
    json_data = json.dumps(xmltodict.parse(data))
    return json_data

def lambda_handler(event, context):
    # Log the incoming event
    logger.info("Received event: %s", json.dumps(event))

    # Parse request parameters
    bucket = event['queryStringParameters']['bucket']
    input_key = event['queryStringParameters']['key']
    output_format = event['queryStringParameters']['format']

    # Retrieve file from S3
    response = s3_client.get_object(Bucket=bucket, Key=input_key)
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
    s3_client.put_object(Bucket=bucket, Key=output_key, Body=converted_data)

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

