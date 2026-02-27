import boto3
import os
import time
from fastapi import FastAPI, UploadFile
import uvicorn
 
app = FastAPI()
s3 = boto3.client('s3', region_name='us-east-1')
sqs = boto3.client('sqs', region_name='us-east-1')
 
REQ_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/221082179934/1233384011-resp-queue'
RESP_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/221082179934/1233384011-resp-queue'
IN_BUCKET = '1233384011-in-bucket'
 
@app.post("/")
async def recognize(inputFile: UploadFile):
   content = await inputFile.read()
   s3.put_object(Bucket=IN_BUCKET, Key=inputFile.filename, Body=content)
 
   sqs.send_message(QueueUrl=REQ_QUEUE_URL, MessageBody=inputFile.filename)
 
   while True:
       response = sqs.receive_message(QueueUrl=RESP_QUEUE_URL, MaxNumberOfMessages=1, WaitTimeSeconds=10)
       if "Messages" in response:
           msg = response['Messages'][0]  
           filename, prediction = msg['Body'].split(':', 1)  
           sqs.delete_message(QueueUrl=RESP_QUEUE_URL, ReceiptHandle=msg['ReceiptHandle'])
           result = f"{filename}:{prediction}"
           return Response(content=result, media_type="text/plain")
 
if __name__ == "__main__":
   uvicorn.run(app, host="0.0.0.0", port=8000)