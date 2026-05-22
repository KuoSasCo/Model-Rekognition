# AWS Infrastructure

All resources are defined in `terraform/main.tf` and provisioned via `terraform apply`.

## Resources

### S3 Bucket — `sigr-detection-bucket-2026`
Stores uploaded images under the `uploads/` prefix.

- `force_destroy = true` — allows `terraform destroy` to remove a non-empty bucket.
- S3 event notifications send `ObjectCreated` events on `uploads/*` to the SQS queue.

### SQS Queue — `sigr-s3-delivery-queue`
Buffers S3 upload events for the Raspberry Pi.

- Visibility timeout: 30 s
- Message retention: 24 h
- Queue policy allows `s3.amazonaws.com` (source bucket ARN) to call `sqs:SendMessage`.

### IAM User — `sigr-flask-backend`
Used by the Flask API running on Railway.

**Permissions (`sigr-backend-iot-sign-policy`):**
```json
[
  { "Action": "s3:PutObject",
    "Resource": "arn:aws:s3:::<bucket>/uploads/*" },
  { "Action": ["iot:Connect", "iot:Subscribe", "iot:Receive"],
    "Resource": ["...client/*", "...topicfilter/sigr/results", "...topic/sigr/results"] }
]
```

### IAM User — `sigr-raspberry-pi-edge`
Used by the Raspberry Pi edge device.

**Permissions (`sigr-edge-execution-policy`):**
```json
[
  { "Action": ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"],
    "Resource": "<queue-arn>" },
  { "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::<bucket>/uploads/*" },
  { "Action": "rekognition:DetectCustomLabels",
    "Resource": "arn:aws:rekognition:us-east-1:*:project/*" },
  { "Action": "iot:Publish",   "Resource": "...topic/sigr/results" },
  { "Action": "iot:Connect",   "Resource": "...client/*" },
  { "Action": "iot:Subscribe", "Resource": "...topicfilter/sigr/results" },
  { "Action": "iot:Receive",   "Resource": "...topic/sigr/results" }
]
```

### IoT Core Endpoint
Retrieved dynamically via `data "aws_iot_endpoint"` with type `iot:Data-ATS`.

```bash
terraform output iot_endpoint
```

---

## Using a Different S3 Bucket

If you use a bucket not managed by Terraform (e.g. `test-image-dataset-01234`), configure manually:

### 1. SQS queue policy — allow the bucket as a source

```bash
aws sqs set-queue-attributes \
  --profile <profile> \
  --queue-url https://sqs.us-east-1.amazonaws.com/<account>/sigr-s3-delivery-queue \
  --attributes '{
    "Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"s3.amazonaws.com\"},\"Action\":\"sqs:SendMessage\",\"Resource\":\"arn:aws:sqs:us-east-1:<account>:sigr-s3-delivery-queue\",\"Condition\":{\"ArnLike\":{\"aws:SourceArn\":[\"arn:aws:s3:::sigr-detection-bucket-2026\",\"arn:aws:s3:::test-image-dataset-01234\"]}}}]}"
  }'
```

### 2. S3 event notification on the bucket

```bash
aws s3api put-bucket-notification-configuration \
  --profile <profile> \
  --bucket test-image-dataset-01234 \
  --notification-configuration '{
    "QueueConfigurations": [{
      "QueueArn": "arn:aws:sqs:us-east-1:<account>:sigr-s3-delivery-queue",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {"Key": {"FilterRules": [{"Name": "prefix", "Value": "uploads/"}]}}
    }]
  }'
```

### 3. IAM policy — update both users to the new bucket ARN

```bash
# Flask backend
aws iam put-user-policy --user-name sigr-flask-backend \
  --policy-name sigr-backend-iot-sign-policy \
  --policy-document '{ ... "Resource": "arn:aws:s3:::test-image-dataset-01234/uploads/*" ... }'

# Raspberry Pi
aws iam put-user-policy --user-name sigr-raspberry-pi-edge \
  --policy-name sigr-edge-execution-policy \
  --policy-document '{ ... "Resource": "arn:aws:s3:::test-image-dataset-01234/uploads/*" ... }'
```

---

## Terraform Outputs

| Output | Description |
|---|---|
| `s3_bucket_name` | S3 bucket name |
| `sqs_queue_url` | SQS queue URL for the Pi |
| `iot_endpoint` | IoT Core ATS data endpoint |
| `raspberry_access_key_id` | Pi IAM access key ID |
| `raspberry_secret_access_key` | Pi IAM secret (sensitive) |
| `backend_access_key_id` | Flask backend IAM access key ID |
| `backend_secret_access_key` | Flask backend IAM secret (sensitive) |
