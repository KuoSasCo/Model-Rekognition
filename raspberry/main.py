import os
import json
import boto3
from dotenv import load_dotenv

load_dotenv()

sqs = boto3.client('sqs', region_name='us-east-1')
rekognition = boto3.client('rekognition', region_name='us-east-1')
iot_data = boto3.client(
    'iot-data',
    region_name='us-east-1',
    endpoint_url=f"https://{os.getenv('AWS_IOT_ENDPOINT')}"
)

QUEUE_URL = os.getenv('SQS_QUEUE_URL')
MODEL_ARN = os.getenv('MODEL_ARN')


def process_and_publish(bucket, photo):
    print(f"\n[EXECUTION] Processing file: {photo}")

    response = rekognition.detect_custom_labels(
        Image={'S3Object': {'Bucket': bucket, 'Name': photo}},
        MinConfidence=80,
        ProjectVersionArn=MODEL_ARN
    )

    print(f"[LOCAL TERMINAL LOGS]: {json.dumps(response['CustomLabels'], indent=2)}")

    payload = {
        "photo": photo,
        "detections": response['CustomLabels']
    }

    iot_data.publish(
        topic='sigr/results',
        qos=1,
        payload=json.dumps(payload)
    )
    print("[AWS IoT] Metrics dispatched successfully to frontend UI channel.")


def listen_loop():
    print("SIGR System running — Awaiting real-time message events...")
    while True:
        messages = sqs.receive_message(
            QueueUrl=QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20
        )

        if 'Messages' in messages:
            for msg in messages['Messages']:
                body = json.loads(msg['Body'])

                if 'Records' in body:
                    s3_data = body['Records'][0]['s3']
                    bucket_name = s3_data['bucket']['name']
                    object_key = s3_data['object']['key']
                    process_and_publish(bucket_name, object_key)

                sqs.delete_message(
                    QueueUrl=QUEUE_URL,
                    ReceiptHandle=msg['ReceiptHandle']
                )


if __name__ == '__main__':
    listen_loop()
