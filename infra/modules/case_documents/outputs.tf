output "arn" {
  description = "ARN of the private case-document bucket."
  value       = aws_s3_bucket.this.arn
}

output "name" {
  description = "Name of the private case-document bucket."
  value       = aws_s3_bucket.this.id
}

output "temporary_prefix" {
  description = "Prefix subject to the temporary-document lifecycle rule."
  value       = var.temporary_prefix
}
