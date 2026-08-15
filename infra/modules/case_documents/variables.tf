variable "bucket_name" {
  description = "Globally unique name of the private case-document bucket."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.bucket_name))
    error_message = "bucket_name must be a valid 3-63 character lowercase S3 bucket name."
  }
}

variable "force_destroy" {
  description = "Whether Terraform may delete the bucket and all contained object versions during destroy."
  type        = bool
  default     = false
}

variable "versioning_enabled" {
  description = "Whether S3 object versioning is enabled."
  type        = bool
  default     = false
}

variable "temporary_prefix" {
  description = "Object-key prefix whose objects are treated as temporary demo documents."
  type        = string
  default     = "temporary/"

  validation {
    condition     = length(var.temporary_prefix) > 1 && endswith(var.temporary_prefix, "/")
    error_message = "temporary_prefix must be non-empty and end with a slash."
  }
}

variable "temporary_document_expiration_days" {
  description = "Number of days to retain objects under the temporary prefix."
  type        = number
  default     = 30

  validation {
    condition     = var.temporary_document_expiration_days >= 1
    error_message = "temporary_document_expiration_days must be at least 1."
  }
}

variable "cors_allowed_origins" {
  description = "Browser origins allowed to call S3 directly. Leave empty for server-side uploads."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags to apply to the S3 bucket."
  type        = map(string)
  default     = {}
}
