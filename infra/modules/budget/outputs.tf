output "arn" {
  description = "ARN of the AWS budget."
  value       = aws_budgets_budget.this.arn
}

output "id" {
  description = "Terraform identifier of the AWS budget."
  value       = aws_budgets_budget.this.id
}

output "name" {
  description = "Name of the AWS budget."
  value       = aws_budgets_budget.this.name
}

output "limit_usd" {
  description = "Configured monthly budget limit in US dollars."
  value       = var.limit_usd
}
