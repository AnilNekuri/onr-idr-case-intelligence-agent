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

variable "case_table_arn" {
  description = "DynamoDB case table the runtime may read."
  type        = string
}

variable "case_table_name" {
  description = "DynamoDB case table supplied to the application environment."
  type        = string
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
