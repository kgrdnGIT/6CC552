import boto3
import json
import xmltodict
from aws_lambda_powertools import Logger

logger = Logger(service="file-conversion-service")

s3_client = boto3.client('s3')

def convert_json_to_xml(data):
    return xmltodict.unparse(json.loads(data))

def convert_xml_to_json(data):
    return json.dumps(xmltodict.parse(data))

@logger.inject_lambda_context
def lambda_handler(event, context):
    print(event)
    try:
        bucket = event['queryStringParameters']['bucket']
        input_key = event['queryStringParameters']['key']
        output_format = event['queryStringParameters']['format']

        response = s3_client.get_object(Bucket=bucket, Key=input_key)
        file_content = response['Body'].read().decode('utf-8')

        if output_format == 'xml':
            converted_data = convert_json_to_xml(file_content)
            output_key = f'converted_{input_key}.xml'
        elif output_format == 'json':
            converted_data = convert_xml_to_json(file_content)
            output_key = f'converted_{input_key}.json'
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid output format specified'})
            }

        s3_client.put_object(Bucket=bucket, Key=output_key, Body=converted_data)
        uri = f's3://{bucket}/{output_key}'

        try:
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': output_key},
                ExpiresIn=3600
            )
        except Exception as e:
            logger.error(f"Error generating pre-signed URL: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }

        return {
            'statusCode': 200,
            'body': json.dumps({'uri': uri, 'presigned_url': url})
        }
    except Exception as e:
        logger.error(f"Error handling request: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal Server Error'})
        }
