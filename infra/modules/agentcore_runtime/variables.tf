variable "name" {
  description = "AgentCore runtime name."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z][A-Za-z0-9_]{0,47}$", var.name))
    error_message = "name must start with a letter and contain at most 48 letters, numbers, or underscores."
  }
}

variable "aws_account_id" {
  description = "AWS account that owns the runtime and its dependencies."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must contain exactly 12 digits."
  }
}

variable "aws_region" {
  description = "AWS Region containing the runtime and its dependencies."
  type        = string
}

variable "deployment_bucket_name" {
  description = "Globally unique private bucket for the direct-deploy ZIP."
  type        = string
}

variable "deployment_package_path" {
  description = "Absolute or root-relative path to the built AgentCore ZIP."
  type        = string
}

variable "use_source_hash" {
  description = "Use multipart-safe source hashing for artifact changes."
  type        = bool
  default     = false
}

variable "entry_point" {
  description = "Python entry-point file inside the deployment ZIP."
  type        = string
  default     = "agentcore_main.py"
}

variable "runtime_description" {
  description = "Description applied to the AgentCore runtime."
  type        = string
  default     = "Grounded ONR/IDR case intelligence agent."
}

variable "endpoint_description" {
  description = "Description applied to the stable runtime endpoint."
  type        = string
  default     = "Stable endpoint for deployment and invocation checks."
}

variable "case_table_arn" {
  description = "DynamoDB case table the runtime may read."
  type        = string
}

variable "case_table_name" {
  description = "DynamoDB case table supplied to the application environment."
  type        = string
}

variable "allow_case_writes" {
  description = "Allow the runtime to create or replace confirmed cases."
  type        = bool
  default     = false
}

variable "claim_intake_table_arn" {
  description = "Optional DynamoDB table ARN for durable intake-session state."
  type        = string
  default     = null
  nullable    = true
}

variable "claim_intake_table_name" {
  description = "Optional DynamoDB table name supplied to the runtime."
  type        = string
  default     = null
  nullable    = true
}

variable "case_documents_bucket_arn" {
  description = "Optional case-document bucket ARN for temporary PDF reads."
  type        = string
  default     = null
  nullable    = true
}

variable "case_documents_bucket_name" {
  description = "Optional case-document bucket name supplied to the runtime."
  type        = string
  default     = null
  nullable    = true
}

variable "enable_textract" {
  description = "Allow asynchronous Textract document analysis."
  type        = bool
  default     = false
}

variable "additional_environment_variables" {
  description = "Additional non-secret environment variables for the runtime."
  type        = map(string)
  default     = {}
}

variable "knowledge_base_arn" {
  description = "Managed Knowledge Base the runtime may retrieve from."
  type        = string
}

variable "knowledge_base_id" {
  description = "Managed Knowledge Base ID supplied to the application environment."
  type        = string
}

variable "bedrock_model_id" {
  description = "Bedrock Mantle model ID supplied to the application environment."
  type        = string

  validation {
    condition     = length(trimspace(var.bedrock_model_id)) > 0
    error_message = "bedrock_model_id must not be empty."
  }
}

variable "endpoint_name" {
  description = "Stable AgentCore endpoint qualifier."
  type        = string
  default     = "live"

  validation {
    condition     = can(regex("^[A-Za-z][A-Za-z0-9_]{0,47}$", var.endpoint_name))
    error_message = "endpoint_name must start with a letter and contain at most 48 letters, numbers, or underscores."
  }
}

variable "idle_runtime_session_timeout" {
  description = "Seconds before an idle development session stops."
  type        = number
  default     = 300
}

variable "max_lifetime" {
  description = "Maximum runtime session lifetime in seconds."
  type        = number
  default     = 900
}

variable "force_destroy_deployment_bucket" {
  description = "Whether Terraform may delete the development artifact bucket and its versions."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to taggable runtime resources."
  type        = map(string)
  default     = {}
}
