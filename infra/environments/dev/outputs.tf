output "aws_region" {
  description = "AWS region configured for development resources."
  value       = var.aws_region
}

output "environment" {
  description = "Name of this deployment environment."
  value       = var.environment
}

output "name_prefix" {
  description = "Prefix for resources added in later steps."
  value       = local.name_prefix
}

output "common_tags" {
  description = "Common tags inherited by taggable AWS resources."
  value       = local.common_tags
}

output "budget_arn" {
  description = "ARN of the development AWS budget."
  value       = module.budget.arn
}

output "budget_name" {
  description = "Name of the development AWS budget."
  value       = module.budget.name
}

output "budget_limit_usd" {
  description = "Monthly development budget limit in US dollars."
  value       = module.budget.limit_usd
}

output "case_table_arn" {
  description = "ARN of the development DynamoDB case table."
  value       = module.case_table.arn
}

output "case_table_name" {
  description = "Name of the development DynamoDB case table."
  value       = module.case_table.name
}

output "case_documents_bucket_arn" {
  description = "ARN of the development case-document bucket."
  value       = module.case_documents.arn
}

output "case_documents_bucket_name" {
  description = "Name of the development case-document bucket."
  value       = module.case_documents.name
}

output "case_documents_temporary_prefix" {
  description = "Prefix whose objects expire under the demo lifecycle rule."
  value       = module.case_documents.temporary_prefix
}

output "knowledge_documents_bucket_arn" {
  description = "ARN of the private process-knowledge bucket."
  value       = module.knowledge_documents.arn
}

output "knowledge_documents_bucket_name" {
  description = "Name of the private process-knowledge bucket."
  value       = module.knowledge_documents.name
}

output "knowledge_documents_prefix" {
  description = "Prefix ingested by the Managed Knowledge Base connector."
  value       = module.knowledge_documents.documents_prefix
}

output "bedrock_knowledge_base_arn" {
  description = "ARN of the Bedrock Managed Knowledge Base."
  value       = module.managed_knowledge_base.knowledge_base_arn
}

output "bedrock_knowledge_base_id" {
  description = "ID supplied to the Bedrock Agent Runtime Retrieve API."
  value       = module.managed_knowledge_base.knowledge_base_id
}

output "bedrock_knowledge_data_source_id" {
  description = "ID supplied when starting and inspecting ingestion jobs."
  value       = module.managed_knowledge_base.data_source_id
}

output "bedrock_knowledge_base_service_role_arn" {
  description = "ARN of the dedicated Managed Knowledge Base service role."
  value       = module.managed_knowledge_base.service_role_arn
}

output "bedrock_knowledge_retrieval_policy_arn" {
  description = "ARN of the policy granting retrieval from this Knowledge Base."
  value       = module.managed_knowledge_base.retrieval_policy_arn
}

output "agentcore_runtime_arn" {
  description = "ARN accepted by InvokeAgentRuntime, or null when AgentCore is disabled."
  value       = try(module.agentcore_runtime[0].runtime_arn, null)
}

output "agentcore_runtime_id" {
  description = "AgentCore control-plane runtime ID, or null when disabled."
  value       = try(module.agentcore_runtime[0].runtime_id, null)
}

output "agentcore_runtime_version" {
  description = "Deployed AgentCore runtime version, or null when disabled."
  value       = try(module.agentcore_runtime[0].runtime_version, null)
}

output "agentcore_endpoint_name" {
  description = "Stable invocation qualifier, or null when AgentCore is disabled."
  value       = try(module.agentcore_runtime[0].endpoint_name, null)
}

output "agentcore_endpoint_arn" {
  description = "ARN of the stable AgentCore endpoint, or null when disabled."
  value       = try(module.agentcore_runtime[0].endpoint_arn, null)
}

output "agentcore_execution_role_arn" {
  description = "Runtime IAM role with case-read, retrieval, Mantle, and telemetry access."
  value       = try(module.agentcore_runtime[0].execution_role_arn, null)
}

output "agentcore_deployment_bucket_name" {
  description = "Private direct-deploy artifact bucket, or null when disabled."
  value       = try(module.agentcore_runtime[0].deployment_bucket_name, null)
}

output "agentcore_cloudwatch_log_group_name" {
  description = "AgentCore service log group name, or null when disabled."
  value       = try(module.agentcore_runtime[0].cloudwatch_log_group_name, null)
}
