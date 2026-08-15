output "arn" {
  description = "ARN of the private process-knowledge bucket."
  value       = aws_s3_bucket.this.arn
}

output "name" {
  description = "Name of the private process-knowledge bucket."
  value       = aws_s3_bucket.this.id
}

output "documents_prefix" {
  description = "S3 key prefix ingested by the managed Knowledge Base connector."
  value       = var.documents_prefix
}
