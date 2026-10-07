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
