variable "name" {
  description = "Name of the conversational claim-intake session table."
  type        = string
}

variable "point_in_time_recovery_enabled" {
  description = "Whether continuous point-in-time recovery is enabled."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags applied to the table."
  type        = map(string)
  default     = {}
}
