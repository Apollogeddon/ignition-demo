variable "kubeconfig" {
  description = "kubeconfig file"
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "kubeconfig context of the k3s cluster"
  type        = string
  default     = "Ubuntu-k3s"
}

variable "namespace" {
  description = "Namespace for the demo"
  type        = string
  default     = "ignition"
}

variable "image_repository" {
  description = "Gateway image repository"
  type        = string
  default     = "localhost/ignition-gateway"
}

variable "image_tag" {
  description = "Gateway image tag"
  type        = string
}

variable "image_pull_policy" {
  description = "Never when the image is imported into k3s directly (see deploy/README.md)"
  type        = string
  default     = "Never"
}

variable "hostname" {
  description = "Host name for the gateway web UI (through traefik)"
  type        = string
}

variable "issuer_name" {
  description = "cert-manager ClusterIssuer for the gateway and ingress certificates"
  type        = string
  default     = "ignition-cluster-issuer"
}

variable "redundancy" {
  description = "Run a redundant Master/Backup pair"
  type        = bool
  default     = true
}
