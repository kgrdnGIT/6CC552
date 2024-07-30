import json
import numpy as np
from numpy.polynomial import Polynomial
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def polynomial_regression(x, y, degree):
    logger.info("Fitting polynomial of degree %d to data", degree)
    
    # Fit polynomial regression
    coefficients = np.polyfit(x, y, degree)
    polynomial = Polynomial(coefficients)
    
    logger.info("Polynomial coefficients: %s", coefficients)
    
    return polynomial

def lambda_handler(event, context):
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

