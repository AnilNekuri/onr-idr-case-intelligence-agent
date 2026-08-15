variable "name" {
  description = "Name of the Bedrock Managed Knowledge Base."
  type        = string

  validation {
    condition     = can(regex("^[0-9A-Za-z](?:[0-9A-Za-z_-]?[0-9A-Za-z])*$", var.name)) && length(var.name) <= 48
    error_message = "name must use letters, numbers, underscores, or hyphens and be at most 48 characters."
  }
}

variable "description" {
  description = "Description of the process-guidance Knowledge Base."
  type        = string
  default     = "Curated public ONR/IDR process guidance for the case-intelligence demo."
}

variable "aws_account_id" {
  description = "AWS account that owns the Knowledge Base and source bucket."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must contain exactly 12 digits."
  }
}

variable "aws_region" {
  description = "AWS Region containing the Knowledge Base and source bucket."
  type        = string
}

variable "bucket_arn" {
  description = "ARN of the S3 bucket containing process-guidance documents."
  type        = string
}

variable "bucket_name" {
  description = "Name of the S3 bucket containing process-guidance documents."
  type        = string
}

variable "documents_prefix" {
  description = "S3 key prefix included by the managed connector."
  type        = string
  default     = "documents/"

  validation {
    condition = (
      length(var.documents_prefix) > 1 &&
      endswith(var.documents_prefix, "/") &&
      !startswith(var.documents_prefix, "/")
    )
    error_message = "documents_prefix must be relative, non-empty, and end with a slash."
  }
}

variable "tags" {
  description = "Tags to apply to taggable Knowledge Base resources."
  type        = map(string)
  default     = {}
}
