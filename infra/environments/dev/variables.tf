variable "aws_region" {
  description = "AWS region used for development resources. AWS Budgets itself is account-scoped."
  type        = string
  default     = "us-east-1"

  validation {
    condition     = can(regex("^[a-z]{2}(-[a-z]+)+-[0-9]+$", var.aws_region))
    error_message = "aws_region must look like a valid AWS region, for example us-east-1."
  }
}

variable "aws_profile" {
  description = "Optional shared AWS configuration profile. Leave null to use the normal AWS credential chain."
  type        = string
  default     = null
  nullable    = true
}

variable "project_name" {
  description = "Short lowercase project identifier used in names and tags."
  type        = string
  default     = "onr-idr-case-intelligence"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,31}$", var.project_name))
    error_message = "project_name must be 3-32 lowercase letters, numbers, or hyphens and start with a letter."
  }
}

variable "environment" {
  description = "Deployment environment name. This root module is restricted to development."
  type        = string
  default     = "dev"

  validation {
    condition     = var.environment == "dev"
    error_message = "The infra/environments/dev root module only accepts environment = \"dev\"."
  }
}

variable "budget_limit_usd" {
  description = "Low monthly development budget limit in US dollars."
  type        = number
  default     = 10

  validation {
    condition     = var.budget_limit_usd >= 1 && var.budget_limit_usd <= 100
    error_message = "budget_limit_usd must be between 1 and 100 for the development environment."
  }
}

variable "budget_alert_email" {
  description = "Email address that receives AWS budget alerts. Supply it in terraform.tfvars or TF_VAR_budget_alert_email."
  type        = string
  sensitive   = true

  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.budget_alert_email))
    error_message = "budget_alert_email must be a valid email address."
  }
}

variable "case_table_point_in_time_recovery_enabled" {
  description = "Whether the development case table has continuous point-in-time recovery enabled."
  type        = bool
  default     = false
}

variable "case_documents_versioning_enabled" {
  description = "Whether object versioning is enabled for development case documents."
  type        = bool
  default     = false
}

variable "case_documents_force_destroy" {
  description = "Whether Terraform may empty and delete the development document bucket during destroy."
  type        = bool
  default     = true
}

variable "temporary_document_expiration_days" {
  description = "Retention period for temporary development documents."
  type        = number
  default     = 30

  validation {
    condition     = var.temporary_document_expiration_days >= 1 && var.temporary_document_expiration_days <= 365
    error_message = "temporary_document_expiration_days must be between 1 and 365."
  }
}

variable "case_documents_cors_allowed_origins" {
  description = "Origins allowed to upload directly from a browser. Empty because the current app uploads server-side."
  type        = list(string)
  default     = []
}

variable "knowledge_documents_versioning_enabled" {
  description = "Whether object versioning is enabled for development process-knowledge documents."
  type        = bool
  default     = false
}

variable "knowledge_documents_force_destroy" {
  description = "Whether Terraform may empty and delete the development process-knowledge bucket during destroy."
  type        = bool
  default     = true
}

variable "knowledge_documents_prefix" {
  description = "S3 prefix ingested by the Managed Knowledge Base connector."
  type        = string
  default     = "documents/"

  validation {
    condition = (
      length(var.knowledge_documents_prefix) > 1 &&
      endswith(var.knowledge_documents_prefix, "/") &&
      !startswith(var.knowledge_documents_prefix, "/")
    )
    error_message = "knowledge_documents_prefix must be relative, non-empty, and end with a slash."
  }
}

variable "enable_agentcore_runtime" {
  description = "Create the paid AgentCore runtime only after the local agent and deployment ZIP are verified."
  type        = bool
  default     = false
}

variable "enable_claim_intake_agentcore_runtime" {
  description = "Create the separate paid conversational claim-intake runtime."
  type        = bool
  default     = false
}

variable "agentcore_bedrock_model_id" {
  description = "Bedrock Mantle model ID used by the deployed AgentCore runtime."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition = (
      !(var.enable_agentcore_runtime || var.enable_claim_intake_agentcore_runtime) ||
      (var.agentcore_bedrock_model_id != null && length(trimspace(var.agentcore_bedrock_model_id)) > 0)
    )
    error_message = "agentcore_bedrock_model_id is required when either AgentCore runtime is enabled."
  }
}

variable "agentcore_deployment_package_path" {
  description = "Path from this Terraform root to the built Linux ARM64 direct-deploy ZIP."
  type        = string
  default     = "../../../output/agentcore/deployment_package.zip"
}

variable "claim_intake_agentcore_deployment_package_path" {
  description = "Path from this Terraform root to the claim-intake runtime ZIP."
  type        = string
  default     = "../../../output/agentcore/claim_intake_deployment_package.zip"
}

variable "agentcore_deployment_bucket_force_destroy" {
  description = "Whether Terraform may delete every version of the development AgentCore artifact."
  type        = bool
  default     = true
}

variable "agentcore_idle_runtime_session_timeout" {
  description = "Seconds before an idle development AgentCore session stops."
  type        = number
  default     = 300

  validation {
    condition     = var.agentcore_idle_runtime_session_timeout >= 60 && var.agentcore_idle_runtime_session_timeout <= 28800
    error_message = "agentcore_idle_runtime_session_timeout must be between 60 and 28800 seconds."
  }
}

variable "agentcore_max_lifetime" {
  description = "Maximum AgentCore runtime session lifetime in seconds."
  type        = number
  default     = 900

  validation {
    condition     = var.agentcore_max_lifetime >= 60 && var.agentcore_max_lifetime <= 28800
    error_message = "agentcore_max_lifetime must be between 60 and 28800 seconds."
  }
}

variable "enable_agentcore_transaction_search" {
  description = "Manage the account-level CloudWatch Transaction Search destination and 1% index."
  type        = bool
  default     = false
}

variable "agentcore_trace_indexing_percentage" {
  description = "Percentage of AgentCore traces indexed by CloudWatch Transaction Search."
  type        = number
  default     = 1

  validation {
    condition     = var.agentcore_trace_indexing_percentage >= 0 && var.agentcore_trace_indexing_percentage <= 100
    error_message = "agentcore_trace_indexing_percentage must be between 0 and 100."
  }
}

variable "additional_tags" {
  description = "Additional common tags merged with Project, Environment, and ManagedBy."
  type        = map(string)
  default = {
    Workload = "case-intelligence-demo"
  }

  validation {
    condition = alltrue([
      for key in keys(var.additional_tags) :
      !contains(["Project", "Environment", "ManagedBy"], key)
    ])
    error_message = "additional_tags cannot replace the required Project, Environment, or ManagedBy tags."
  }
}
