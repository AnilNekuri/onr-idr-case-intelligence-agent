output "arn" {
  description = "ARN of the claim-intake session table."
  value       = aws_dynamodb_table.this.arn
}

output "name" {
  description = "Name of the claim-intake session table."
  value       = aws_dynamodb_table.this.name
}
