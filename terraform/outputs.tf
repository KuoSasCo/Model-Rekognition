output "s3_bucket_name" {
  value = aws_s3_bucket.image_bucket.id
}

output "sqs_queue_url" {
  value = aws_sqs_queue.s3_event_queue.id
}

output "iot_endpoint" {
  value = data.aws_iot_endpoint.iot_data.endpoint_address
}

output "raspberry_access_key_id" {
  value = aws_iam_access_key.raspberry_keys.id
}

output "raspberry_secret_access_key" {
  value     = aws_iam_access_key.raspberry_keys.secret
  sensitive = true
}
output "backend_access_key_id" {
  value = aws_iam_access_key.backend_keys.id
}

output "backend_secret_access_key" {
  value     = aws_iam_access_key.backend_keys.secret
  sensitive = true
}
