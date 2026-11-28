output "name" {
  description = "Gateway name (the chart's applicationName)"
  value       = var.name
}

output "pod_labels" {
  description = "Labels selecting the gateway pods (e.g. for database NetworkPolicies)"
  value       = { "app.kubernetes.io/name" = var.name, "app.kubernetes.io/instance" = var.name }
}

output "service" {
  description = "Service routing to the Active gateway"
  value       = var.redundancy ? "${var.name}-active" : var.name
}

output "internal_url" {
  description = "In-cluster URL of the Active gateway"
  value       = "http://${var.redundancy ? "${var.name}-active" : var.name}.${var.namespace}.svc:8088"
}

output "pod_urls" {
  description = "In-cluster URL of each gateway pod (through the headless Service)"
  value = [
    for i in range(var.redundancy ? 2 : 1) :
    "http://${var.name}-${i}.${var.name}-headless.${var.namespace}.svc:8088"
  ]
}

output "url" {
  description = "External URL of the gateway web UI, when an ingress is configured"
  value       = var.ingress == null ? null : "${var.ingress.tls_secret == null ? "http" : "https"}://${var.ingress.host}"
}

output "admin_password" {
  description = "Gateway admin password"
  value       = local.admin_password
  sensitive   = true
}

output "api_token" {
  description = "API key (name:secret) for the ignition provider; null on 8.1"
  value       = local.api_token
  sensitive   = true
}

output "backup_claim" {
  description = "PersistentVolumeClaim holding the gateway backups (.gwbk); null without them (8.1, or backup = null)"
  value       = try(kubernetes_persistent_volume_claim_v1.backup[0].metadata[0].name, null)
}

output "release" {
  description = "The chart's Helm release: its name and namespace (for helm status, history and uninstall), and how a failed install or upgrade is handled (atomic, timeout)"
  value = {
    name      = helm_release.gateway.name
    namespace = helm_release.gateway.namespace
    atomic    = helm_release.gateway.atomic
    timeout   = helm_release.gateway.timeout
  }
}
