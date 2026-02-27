import boto3
import time
import os

ec2 = boto3.client('ec2', region_name="us-east-1")
def get_instance_ids(states):
    get_instance = ec2.describe_instances(Filters=[{'Name': 'image-id', 'Values': ['ami-088f07f4e1b2b18e8']},{'Name': 'instance-state-name', 'Values': states}])
    return [i['InstanceId'] for r in get_instance['Reservations'] for i in r['Instances']]

sqs = boto3.client('sqs', region_name="us-east-1") 
def get_queue_size():
    response = sqs.get_queue_attributes(QueueUrl="https://sqs.us-east-1.amazonaws.com/221082179934/1233384011-req-queue", AttributeNames=['ApproximateNumberOfMessages'])
    return int(response['Attributes'].get('ApproximateNumberOfMessages', 0))

def scale_instances():
    while True:
        queue_size = get_queue_size()
        running_instances = get_instance_ids(["running"])
        stopped_instances = get_instance_ids(["stopped"])

        if queue_size == 0 and running_instances:
            print("No pending requests, stopping all instances.")
            ec2.stop_instances(InstanceIds=running_instances)
        elif queue_size > 0:
            required_instances = min(queue_size, 15)
            if len(running_instances) < required_instances:
                to_start = stopped_instances[:required_instances - len(running_instances)]
                if to_start:
                    print(f"Starting {len(to_start)} instances to match queue demand.")
                    ec2.start_instances(InstanceIds=to_start)
        
        time.sleep(3)

if __name__ == "__main__":
    scale_instances()
