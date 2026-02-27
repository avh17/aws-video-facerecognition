# Elastic Face Recognition Application on AWS

This project implements an elastic face recognition application leveraging Amazon Web Services (AWS) Infrastructure as a Service (IaaS) resources. The application is designed to dynamically scale based on demand, processing face recognition requests from users efficiently.

## Architecture

The application follows a multi-tiered cloud architecture consisting of a Web Tier and an Application Tier, utilizing AWS services like EC2, S3, and SQS for scalability and persistence.

<img width="1928" height="808" alt="image" src="https://github.com/user-attachments/assets/0184ef0c-1448-46bb-b202-639b34324732" />

## Components

### 1. Web Tier

The Web Tier acts as the front-end, handling user requests and orchestrating the communication with the Application Tier. It runs on a single EC2 instance.

* **Program Name**: `server.py`
* **EC2 Instance Name**: `web-instance`
* **Static IP**: The web tier instance is assigned a static Elastic IP address.
* **HTTP POST Requests**: Handles HTTP POST requests to the root endpoint (`/`) on port 8000.
    * The HTTP payload key for the input file is `"inputFile"`.
* **S3 Integration**: Stores received images in an S3 Input Bucket for persistence.
    * **Input Bucket Naming Convention**: `<ASU ID>-in-bucket` (e.g., `1225754101-in-bucket`).
    * **Object Key**: The input file's name (e.g., `test_000.jpg`).
* **SQS Integration (Request Queue)**: Forwards face recognition requests to the Application Tier via an SQS queue.
    * **Request Queue Naming Convention**: `<ASU ID>-req-queue` (e.g., `1225754101-req-queue`).
    * **Message Size**: Maximum message size for the request queue is set to 1KB to prevent sending image data directly. Only request metadata (e.g., image file name) is sent.
* **SQS Integration (Response Queue)**: Receives face recognition results from the Application Tier via an SQS queue.
    * **Response Queue Naming Convention**: `<ASU ID>-resp-queue` (e.g., `1225754101-resp-queue`).
* **Result Return**: Returns the recognition result as a plain text response to the original HTTP request.
    * **Output Format**: `<filename>:<prediction_results>` (e.g., `test_000:Paul`).

### 2. Application Tier

The Application Tier performs the core face recognition task using a deep learning model. Multiple instances of this tier can run concurrently to handle varying workloads.

* **Program Name**: `backend.py`
* **EC2 Instance Naming Convention**: `app-tier-instance-<instance#>`
* **AMI Creation**: A custom Amazon Machine Image (AMI) is created for launching application tier instances. This AMI includes:
    * A base EC2 instance (AWS Linux or Ubuntu AMI).
    * Required Python packages: `torch`, `torchvision`, `torchaudio` (installed from `https://download.pytorch.org/whl/cpu`).
    * Provided deep learning model code and model weights.
* **Request Processing**: For every request in the SQS request queue:
    1.  Retrieves the request from `<ASU ID>-req-queue`.
    2.  Fetches the corresponding image from the S3 Input Bucket.
    3.  Performs face recognition using the deep learning model.
    4.  Stores the recognition result in the S3 Output Bucket.
        * **Output Bucket Naming Convention**: `<ASU ID>-out-bucket` (e.g., `1225754101-out-bucket`).
        * **Object Key**: `image_image` (e.g., `test_000`).
        * **Value**: Classification result (e.g., `"Paul"`).
    5.  Pushes the recognition result to the SQS response queue (`<ASU ID>-resp-queue`).

### 3. Autoscaling Controller

The Web Tier also includes an autoscaling controller (`controller.py`) responsible for dynamically managing the number of Application Tier instances. This is a custom implementation and does not use the AWS Auto Scaling service.

* **Autoscaling Policies**:
    * The number of Application Tier instances is 0 when there are no requests being processed or waiting.
    * The maximum number of Application Tier instances is 15 (due to free tier resource limits).
    * Each Application Tier instance processes only one request at a time.
    * An Application Tier instance stops immediately after processing a request if no more pending requests exist; otherwise, it continues to process the next request.
    * Application Tier instances can be initialized in a "stopped" state to reduce startup overhead.

## AWS Resource Naming Conventions and Region

To ensure consistency and facilitate deployment, all resources adhere to specific naming conventions and are deployed in a single AWS region.

* **AWS Region**: `US-East-1`
* **S3 Input Bucket**: `<ASU ID>-in-bucket`
* **S3 Output Bucket**: `<ASU ID>-out-bucket`
* **SQS Request Queue**: `<ASU ID>-req-queue`
* **SQS Response Queue**: `<ASU ID>-resp-queue`
* **Web Tier EC2 Instance**: `web-instance`
* **App Tier EC2 Instances**: `app-tier-instance-<instance#>`

## Setup and Deployment

1.  **AWS Account**: Ensure you have an AWS account with access to EC2, S3, and SQS services in the `US-East-1` region.
2.  **IAM User**: Create an IAM user with appropriate permissions for this project.
3.  **AMI Creation**: Follow the steps outlined in the project description to create the custom AMI for the Application Tier instances. This involves launching a base EC2 instance, installing dependencies, copying model files, and then creating an AMI from it.
4.  **Web Tier Deployment**: Launch a single EC2 instance named `web-instance` and assign it an Elastic IP address. Deploy `server.py` and `controller.py` to this instance.
5.  **S3 Buckets and SQS Queues**: Create the S3 input and output buckets, and the SQS request and response queues, adhering to the specified naming conventions and SQS message size limit.
6.  **Application Tier Deployment**: The `controller.py` will manage the launching and termination of `backend.py` instances based on the autoscaling logic.
