import boto3
import json
import os
import time
import sys
import subprocess
from PIL import Image
import io

# AWS Configuration
ASU_ID = "1233384011"  # Replace with your actual ASU ID
REGION = "us-east-1"
REQUEST_QUEUE = f"{ASU_ID}-req-queue"
RESPONSE_QUEUE = f"{ASU_ID}-resp-queue"
INPUT_BUCKET = f"{ASU_ID}-in-bucket"
OUTPUT_BUCKET = f"{ASU_ID}-out-bucket"

# Path to the model directory
MODEL_DIR = "./CSE546-SPRING-2025-model"
FACE_RECOGNITION_SCRIPT = os.path.join(MODEL_DIR, "face_recognition.py")
DATA_PT_PATH = os.path.join(MODEL_DIR, "data.pt")

# Initialize AWS services
s3_client = boto3.client('s3', region_name=REGION)
sqs_client = boto3.client('sqs', region_name=REGION)

# Get queue URLs
req_queue_url = sqs_client.get_queue_url(QueueName=REQUEST_QUEUE)['QueueUrl']
resp_queue_url = sqs_client.get_queue_url(QueueName=RESPONSE_QUEUE)['QueueUrl']

def process_message(message):
    """Process a single message from the request queue"""
    try:
        # Parse message body
        body = json.loads(message['Body'])
        filename = body.get('filename')
        print(f"Processing request for {filename}")
        
        # Extract the base filename without extension
        base_filename = os.path.splitext(filename)[0]
        
        # Download the image from S3
        response = s3_client.get_object(
            Bucket=INPUT_BUCKET,
            Key=filename
        )
        image_bytes = response['Body'].read()
        
        # Save the image locally for processing
        local_image_path = f"/tmp/{filename}"
        with open(local_image_path, 'wb') as f:
            f.write(image_bytes)
        
        # Call the face recognition script as a subprocess
        try:
            result = subprocess.run(
                ["python3", FACE_RECOGNITION_SCRIPT, local_image_path],
                capture_output=True,
                text=True,
                check=True
            )
            prediction = result.stdout.strip()
            print(f"Recognition result for {filename}: {prediction}")
        except subprocess.CalledProcessError as e:
            print(f"Error during face recognition: {e}")
            prediction = "Unknown"
        
        # Clean up temporary file
        os.remove(local_image_path)
        
        # Store result in S3 output bucket
        s3_client.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=base_filename,
            Body=prediction
        )
        
        # Send result to response queue
        response_message = json.dumps({
            'filename': base_filename,
            'result': prediction
        })
        
        sqs_client.send_message(
            QueueUrl=resp_queue_url,
            MessageBody=response_message
        )
        
        # Delete the message from the request queue
        sqs_client.delete_message(
            QueueUrl=req_queue_url,
            ReceiptHandle=message['ReceiptHandle']
        )
        
        print(f"Completed processing for {filename}")
        return True
        
    except Exception as e:
        print(f"Error processing message: {e}")
        return False

def main():
    print("Starting application tier instance...")
    
    # Verify that the face recognition script exists
    if not os.path.exists(FACE_RECOGNITION_SCRIPT):
        print(f"Error: Face recognition script not found at {FACE_RECOGNITION_SCRIPT}")
        return
    
    # Verify that data.pt exists
    if not os.path.exists(DATA_PT_PATH):
        print(f"Error: data.pt not found at {DATA_PT_PATH}")
        return
    
    print("Model files verified")
    
    # Process one message
    while True:
        # Poll for messages
        response = sqs_client.receive_message(
            QueueUrl=req_queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5
        )
        
        messages = response.get('Messages', [])
        
        if not messages:
            print("No messages in queue. Exiting.")
            break
        
        # Process the message
        message = messages[0]
        process_message(message)
    
    print("Application tier instance shutting down.")

if __name__ == '__main__':
    main()