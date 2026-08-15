output "runtime_arn" {
  description = "ARN accepted by InvokeAgentRuntime."
  value       = aws_bedrockagentcore_agent_runtime.this.agent_runtime_arn
}

output "runtime_id" {
  description = "ID accepted by AgentCore control-plane APIs."
  value       = aws_bedrockagentcore_agent_runtime.this.agent_runtime_id
}

output "runtime_version" {
  description = "Immutable AgentCore runtime version serving the endpoint."
  value       = aws_bedrockagentcore_agent_runtime.this.agent_runtime_version
}

output "endpoint_name" {
  description = "Qualifier accepted by InvokeAgentRuntime."
  value       = aws_bedrockagentcore_agent_runtime_endpoint.this.name
}

output "endpoint_arn" {
  description = "ARN of the stable AgentCore endpoint."
  value       = aws_bedrockagentcore_agent_runtime_endpoint.this.agent_runtime_endpoint_arn
}

output "execution_role_arn" {
  description = "Least-privilege IAM role assumed by AgentCore Runtime."
  value       = aws_iam_role.runtime.arn
}

output "deployment_bucket_name" {
  description = "Private versioned bucket holding the direct-deploy ZIP."
  value       = aws_s3_bucket.deployment.id
}

output "cloudwatch_log_group_name" {
  description = "Service-created log group used by this runtime endpoint."
  value       = "/aws/bedrock-agentcore/runtimes/${aws_bedrockagentcore_agent_runtime.this.agent_runtime_id}-${aws_bedrockagentcore_agent_runtime_endpoint.this.name}"
}
