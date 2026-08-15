output "arn" {
  description = "ARN of the DynamoDB case table."
  value       = aws_dynamodb_table.this.arn
}

output "name" {
  description = "Name of the DynamoDB case table."
  value       = aws_dynamodb_table.this.name
}
