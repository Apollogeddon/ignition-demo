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
  description = "ignition-failover chart version, from the chart repository; ignored when chart_path is set"
  type        = string
  default     = "5.1.1"
  validation {
    condition     = can(regex("^[0-9]+\\.[0-9]+\\.[0-9]+", var.chart_version))
    error_message = "chart_version must be a chart version such as 5.1.0."
  }
}

variable "chart_path" {
  description = "A local ignition-failover chart directory to install instead of chart_version from the repository, to test an unreleased chart; null uses the repository"
  type        = string
  default     = null
}

variable "timeout" {
  description = "Seconds the chart's install or upgrade may take until every gateway is Ready: a redundant pair's first start (the Backup synced in about 5 minutes on k3s), or a rolling upgrade restarting both, with headroom for a slow image pull"
  type        = number
  default     = 900

  validation {
    condition     = var.timeout >= 300
    error_message = "timeout must be at least 300 seconds: a redundant pair takes about 5 minutes to report Ready."
  }
}

variable "atomic" {
  description = "Uninstall a first install that fails or times out, and roll back a failed upgrade, so the next apply starts clean. false keeps a failed release's pods and events to debug, but the next apply then fails on the name still in use until you helm uninstall it (cluster/README.md)"
  type        = bool
  default     = true
}

variable "accept_eula" {
  description = <<-EOT
    Accept the Ignition End User License Agreement, which the chart then passes to
    the gateway (its acceptEula value). Read it first:
    https://inductiveautomation.com/ignition/license
  EOT
  type        = bool

  validation {
    condition     = var.accept_eula
    error_message = "Set accept_eula = true once you have read and accepted the Ignition EULA (https://inductiveautomation.com/ignition/license); the gateway does not start without it."
  }
}

variable "image_repository" {
  description = "Gateway image repository (built from gateway/Dockerfile)"
  type        = string
}

variable "image_tag" {
  description = "Gateway image tag; one tag fully describes the projects it runs"
  type        = string

  validation {
    condition     = var.image_tag != "" && var.image_tag != "latest"
    error_message = "image_tag must name a release, not latest: a moving tag changes the gateway on any restart."
  }
}

variable "image_digest" {
  description = "Image digest (sha256:...) to pin image_tag to, as tag@digest, so a re-pushed tag can't change the gateway; null for the tag alone"
  type        = string
  default     = null

  validation {
    condition     = var.image_digest == null || can(regex("^sha256:[0-9a-f]{64}$", var.image_digest))
    error_message = "image_digest must be sha256: followed by 64 lower-case hex digits."
  }
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

variable "license_key" {
  description = "Ignition license key, which the gateway activates on start (IGNITION_LICENSE_KEY); null to license it by hand or run a trial"
  type        = string
  default     = null
  sensitive   = true
}

variable "activation_token" {
  description = "Activation token for a leased license key (IGNITION_ACTIVATION_TOKEN); null for none"
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
  description = "Ingress for the gateway web UI; null for none. namespace is the ingress controller's, which the gateways' NetworkPolicy lets in (kube-system for k3s's Traefik, ingress-nginx for ingress-nginx, and so on)"
  type = object({
    host        = string
    class_name  = optional(string, "")
    tls_secret  = optional(string)
    namespace   = string
    annotations = optional(map(string), {})
  })
  default = null

  validation {
    condition     = var.ingress == null || can(regex("^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?$", var.ingress.namespace))
    error_message = "ingress.namespace must be the ingress controller's namespace, a DNS label such as kube-system or ingress-nginx."
  }
}

variable "persistence" {
  description = "The gateways' data volumes (the chart's ignition.persistence). A StatefulSet's volumes can't be changed in place: set these before the first apply"
  type = object({
    size          = optional(string, "3Gi")
    storage_class = optional(string)
  })
  default  = {}
  nullable = false
}

variable "backup" {
  description = <<-EOT
    A CronJob (8.3) that downloads a gateway backup (.gwbk) from the gateway's REST
    API (GET /data/api/v1/backup) with the module's API key, into a volume of its
    own, keeping retention_days of them; null for none. url defaults to the
    ingress's HTTPS URL, or with api_token_require_tls = false the in-cluster HTTP
    one. The ingress's TLS Secret's ca.crt, when it has one, verifies the gateway.
  EOT
  type = object({
    schedule       = optional(string, "47 2 * * *")
    retention_days = optional(number, 7)
    storage        = optional(string, "5Gi")
    storage_class  = optional(string)
    url            = optional(string)
    # the chart's own helper image, which has sh and curl
    image = optional(string, "docker.io/alpine/kubectl:1.37.1")
  })
  default = {}

  validation {
    condition     = var.backup == null || try(var.backup.retention_days >= 1, false)
    error_message = "backup.retention_days must be at least 1."
  }
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

variable "ignition_version" {
  description = "Ignition major.minor of the image (8.1 or 8.3): 8.3 gets an API key for the resources module, 8.1 a seed environment"
  type        = string
  default     = "8.3"
  validation {
    condition     = contains(["8.1", "8.3"], var.ignition_version)
    error_message = "ignition_version must be 8.1 or 8.3."
  }
}

variable "api_token_name" {
  description = "Name of the generated API key (8.3); OpenTofu's ignition provider authenticates with it"
  type        = string
  default     = "iac"

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+$", var.api_token_name)) && !contains([".", ".."], var.api_token_name)
    error_message = "api_token_name may only hold letters, digits, '.', '_' and '-'."
  }
}

variable "api_token_require_tls" {
  description = <<-EOT
    Accept the API key over HTTPS only (8.3). With an ingress, the ingress's TLS
    counts, through the X-Forwarded-Proto header the gateway then trusts: a pod
    that can reach the gateway's HTTP port could send that header itself, and the
    NetworkPolicy admits the ingress's namespace and the release's own. Keep other
    workloads out of the namespace; the platform module's database can't call out.
  EOT
  type        = bool
  default     = true
}

variable "seed_environment" {
  description = <<-EOT
    Environment variables for the gateway's seed spec (gateway/seed/seed.json),
    which the 8.1 startup event applies: connection URLs, users' passwords and
    so on. Ignored on 8.3, where the resources module configures the gateway.
  EOT
  type        = map(string)
  default     = {}
  sensitive   = true
}
