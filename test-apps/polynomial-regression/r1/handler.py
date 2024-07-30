import json
import numpy as np
from numpy.polynomial import Polynomial
from aws_xray_sdk.core import patch_all, xray_recorder
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.logging import correlation_paths
from datetime import datetime

# Initialize Powertools Logger, Tracer, and Metrics
logger = Logger(service="polynomial-regression")
tracer = Tracer(service="polynomial-regression")
metrics = Metrics(namespace="PolynomialRegression")

# Patch all supported libraries for AWS X-Ray
patch_all()

# Track if the function is experiencing a cold start
cold_start = True

@tracer.capture_method
def polynomial_regression(x, y, degree):
    logger.info("Fitting polynomial of degree %d to data", degree)
    
    # Fit polynomial regression
    coefficients = np.polyfit(x, y, degree)
    polynomial = Polynomial(coefficients)
    
    logger.info("Polynomial coefficients: %s", coefficients)
    
    return polynomial

@tracer.capture_lambda_handler
@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
def lambda_handler(event, context):
    global cold_start

    # Add cold start annotation to X-Ray subsegment
    subsegment = xray_recorder.current_subsegment()
    subsegment.put_annotation("ColdStart", cold_start)

    if cold_start:
        cold_start = False

    logger.info("Received event: %s", json.dumps(event))
    
    # Extract query parameters from the event
    params = event.get('queryStringParameters', {})
    x_str = params.get('x')
    y_str = params.get('y')
    degree_str = params.get('degree')
    
    # Convert comma-separated strings to lists
    x = list(map(float, x_str.split(',')))
    y = list(map(float, y_str.split(',')))
    degree = int(degree_str)
    
    logger.info("Input data: x=%s, y=%s, degree=%d", x, y, degree)
    
    try:
        # Perform polynomial regression
        polynomial = polynomial_regression(x, y, degree)
        coefficients = polynomial.coef.tolist()
        
        # Prepare response body
        response_body = {
            'coefficients': coefficients
        }
        
        # Return success response
        return {
            'statusCode': 200,
            'body': json.dumps(response_body)
        }
    except Exception as e:
        # Log error and return error response
        logger.error("An error occurred: %s", str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal Server Error'})
        }

# For local testing, you can simulate the lambda handler
if __name__ == "__main__":
    event = {
        'queryStringParameters': {
            'x': '1,2,3,4,5',
            'y': '2,3,5,7,11',
            'degree': '2'
        }
    }
    context = {}
    print(lambda_handler(event, context))
