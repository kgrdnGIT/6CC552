import json
import numpy as np
from numpy.polynomial import Polynomial
from aws_lambda_powertools import Logger

logger = Logger(service="polynomial-regression")

def polynomial_regression(x, y, degree):
    try:
        coefficients = np.polyfit(x, y, degree)
        polynomial = Polynomial(coefficients)
        return polynomial
    except Exception as e:
        logger.error(f"Error fitting polynomial regression: {e}")
        raise

@logger.inject_lambda_context
def lambda_handler(event, context):
    try:
        params = event.get('queryStringParameters', {})
        x_str = params.get('x')
        y_str = params.get('y')
        degree_str = params.get('degree')
        
        x = list(map(float, x_str.split(',')))
        y = list(map(float, y_str.split(',')))
        degree = int(degree_str)
        
        polynomial = polynomial_regression(x, y, degree)
        coefficients = polynomial.coef.tolist()
        
        response_body = {
            'coefficients': coefficients
        }
        
        return {
            'statusCode': 200,
            'body': json.dumps(response_body)
        }
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal Server Error'})
        }
