import requests
import json

def call_lambda_function(image_key):
    # Endpoint URL of the Lambda function
    endpoint_url = "https://23pqj6a60j.execute-api.eu-west-1.amazonaws.com/dev/process-image"

    # Payload data for the POST request
    payload = {
        "image_key": image_key
    }

    # Convert payload to JSON format
    payload_json = json.dumps(payload)

    try:
        # Make HTTP POST request to the Lambda function
        response = requests.post(endpoint_url, data=payload_json)

        # Check if request was successful (status code 200)
        if response.status_code == 200:
            print("Lambda function call successful")
            print("Response:", response.json())
        else:
            print("Error:", response.text)
    except Exception as e:
        print("Error making request:", e)

if __name__ == "__main__":
    # Example image key
    image_key = "100x100_google-skateboard.jpg"
    
    # Call the Lambda function
    call_lambda_function(image_key)

