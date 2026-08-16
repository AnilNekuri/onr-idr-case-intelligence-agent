locals {
  name_prefix                  = "${var.project_name}-${var.environment}"
  agentcore_runtime_name       = "${replace(local.name_prefix, "-", "_")}_agent"
  claim_agentcore_runtime_name = "${replace(local.name_prefix, "-", "_")}_claim_intake"

  common_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    },
    var.additional_tags,
  )
}
