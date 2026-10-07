variable "namespace" {
  description = "Namespace to install into (created by the platform module)"
  type        = string
}

variable "name" {
  description = "Gateway name: the chart's applicationName, used for its resources and pod labels"
  type        = string
  default     = "ignition"
}

variable "chart_version" {
  description = "ignition-failover chart version"
  type        = string
  default     = "4.2.1"
}

variable "image_repository" {
  description = "Gateway image repository (built from gateway/Dockerfile)"
  type        = string
}

variable "image_tag" {
  description = "Gateway image tag; one tag fully describes the projects it runs"
  type        = string
}

variable "image_pull_policy" {
  description = "Image pull policy; Never for images imported straight into the nodes"
  type        = string
  default     = "IfNotPresent"
}

variable "image_pull_secrets" {
  description = "Pull secret names for a private registry"
  type        = list(string)
  default     = []
}

variable "admin_password" {
  description = "Gateway admin password; generated when null"
  type        = string
  default     = null
  sensitive   = true
}

variable "redundancy" {
  description = "Run a Master/Backup pair with active routing and certificate-renewal restarts"
  type        = bool
  default     = true
}

variable "issuer" {
  description = "cert-manager issuer for the Gateway Network and web certificates"
  type = object({
    name = string
    kind = optional(string, "ClusterIssuer")
  })
}

variable "ingress" {
  description = "Ingress for the gateway web UI; null for none"
  type = object({
    host        = string
    class_name  = optional(string, "")
    tls_secret  = optional(string)
    namespace   = optional(string, "kube-system")
    annotations = optional(map(string), {})
  })
  default = null
}

variable "memory_mb" {
  description = "Gateway JVM max heap in MB; the container limit is set to twice this"
  type        = number
  default     = 1024
}

variable "values" {
  description = "Extra chart values, merged last (see the chart's values.yaml)"
  type        = any
  default     = {}
}
