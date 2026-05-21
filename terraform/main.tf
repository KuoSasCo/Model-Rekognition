provider "aws" {
  region = var.aws_region
}

# 1. S3 Bucket for Image Storage
resource "aws_s3_bucket" "image_bucket" {
  bucket        = var.bucket_name
  force_destroy = true
}

# 2. SQS Queue for Raspberry Pi Event Ingestion
resource "aws_sqs_queue" "s3_event_queue" {
  name                       = "sigr-s3-delivery-queue"
  visibility_timeout_seconds = 30
  message_retention_seconds  = 86400
}

# 3. SQS Access Policy allowing S3 to Publish Messages
resource "aws_sqs_queue_policy" "allow_s3_publish" {
  queue_url = aws_sqs_queue.s3_event_queue.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "s3.amazonaws.com" }
        Action    = "sqs:SendMessage"
        Resource  = aws_sqs_queue.s3_event_queue.arn
        Condition = {
          ArnEquals = { "aws:SourceArn" = aws_s3_bucket.image_bucket.arn }
        }
      }
    ]
  })
}

# 4. Bind S3 ObjectCreated events to SQS
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.image_bucket.id

  queue {
    queue_arn     = aws_sqs_queue.s3_event_queue.arn
    events        = ["s3:ObjectCreated:*"]
    filter_prefix = "uploads/"
  }

  depends_on = [aws_sqs_queue_policy.allow_s3_publish]
}

# 5. IAM Privileges for the Raspberry Pi Edge Device
resource "aws_iam_user" "raspberry_user" {
  name = "sigr-raspberry-pi-edge"
}

resource "aws_iam_access_key" "raspberry_keys" {
  user = aws_iam_user.raspberry_user.name
}

resource "aws_iam_user_policy" "raspberry_policy" {
  name = "sigr-edge-execution-policy"
  user = aws_iam_user.raspberry_user.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.s3_event_queue.arn
      },
      {
        Effect = "Allow"
        Action = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.image_bucket.arn}/uploads/*"
      },
      {
        Effect = "Allow"
        Action = ["rekognition:DetectCustomLabels"]
        Resource = "arn:aws:rekognition:${var.aws_region}:*:project/*"
      },
      {
        Effect = "Allow"
        Action = ["iot:Publish"]
        Resource = "arn:aws:iot:${var.aws_region}:*:topic/sigr/results"
      }
    ]
  })
}

# 6. Fetch AWS IoT Endpoint dynamically
data "aws_iot_endpoint" "iot_data" {
  endpoint_type = "iot:Data-ATS"
}
