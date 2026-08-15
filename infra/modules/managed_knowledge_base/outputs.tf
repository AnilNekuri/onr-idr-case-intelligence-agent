output "knowledge_base_arn" {
  description = "ARN of the Bedrock Managed Knowledge Base."
  value       = aws_bedrockagent_knowledge_base.this.arn
}

output "knowledge_base_id" {
  description = "ID used by the Bedrock Agent Runtime Retrieve API."
  value       = aws_bedrockagent_knowledge_base.this.id
}

output "data_source_id" {
  description = "ID used when starting and inspecting ingestion jobs."
  value       = aws_bedrockagent_data_source.s3.data_source_id
}

output "service_role_arn" {
  description = "ARN of the dedicated Knowledge Base service role."
  value       = aws_iam_role.this.arn
}

output "retrieval_policy_arn" {
  description = "ARN of the least-privilege policy to attach to application runtimes."
  value       = aws_iam_policy.retrieve.arn
}
