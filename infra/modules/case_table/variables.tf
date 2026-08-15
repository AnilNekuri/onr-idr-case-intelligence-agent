variable "name" {
  description = "Name of the DynamoDB table that stores authoritative case records."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]{3,255}$", var.name))
    error_message = "name must be a valid 3-255 character DynamoDB table name."
  }
}

variable "point_in_time_recovery_enabled" {
  description = "Whether continuous point-in-time recovery is enabled for the table."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to the DynamoDB table."
  type        = map(string)
  default     = {}
}
