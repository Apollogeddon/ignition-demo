# The gateway module's validations and the chart values it renders, against mock
# providers: tofu -chdir=cluster/modules/gateway test

mock_provider "helm" {}
mock_provider "kubernetes" {}
mock_provider "random" {}

variables {
  namespace        = "ignition"
  image_repository = "ghcr.io/apollogeddon/ignition-gateway"
  image_tag        = "8.3.10-2.0.1"
  issuer           = { name = "cluster-issuer" }
  accept_eula      = true
  ingress = {
    host       = "ignition.example.com"
    class_name = "traefik"
    namespace  = "kube-system"
    tls_secret = "ignition-ingress-tls"
  }
}

run "renders_the_chart_values" {
  command = plan

  assert {
    condition     = yamldecode(helm_release.gateway.values[0]).acceptEula == true
    error_message = "acceptEula is not passed to the chart."
  }
  assert {
    condition     = yamldecode(helm_release.gateway.values[0]).image.tag == "8.3.10-2.0.1"
    error_message = "The image tag is not the tag alone without a digest."
  }
  assert {
    condition     = yamldecode(helm_release.gateway.values[0]).ignition.persistence == { size = "3Gi", storageClassName = "" }
    error_message = "The data volume does not keep the chart's defaults."
  }
  assert {
    condition     = helm_release.gateway.repository == "https://apollogeddon.github.io/ignition-helm" && helm_release.gateway.chart == "ignition-failover" && helm_release.gateway.version == "5.0.0"
    error_message = "The chart does not come from the repository."
  }
  assert {
    condition     = contains(yamldecode(helm_release.gateway.values[0]).ignition.args, "gateway.useProxyForwardedHeader=true")
    error_message = "With an ingress, the gateway must trust X-Forwarded-Proto."
  }
  assert {
    condition     = yamldecode(helm_release.gateway.values[0]).ignition.networkPolicy.extraIngress[0].from[0].namespaceSelector.matchLabels["kubernetes.io/metadata.name"] == "kube-system"
    error_message = "The NetworkPolicy does not let the ingress controller's namespace in."
  }
  assert {
    condition     = output.url == "https://ignition.example.com"
    error_message = "The URL is not the ingress's HTTPS one."
  }
}

run "pins_a_digest_on_the_tag" {
  command = plan
  variables {
    image_digest = "sha256:174fb4d8c640a6439baec35540bdf15169f850f6f849a1ae80dcb91bbe66b119"
  }
  assert {
    condition     = yamldecode(helm_release.gateway.values[0]).image.tag == "8.3.10-2.0.1@sha256:174fb4d8c640a6439baec35540bdf15169f850f6f849a1ae80dcb91bbe66b119"
    error_message = "The digest is not rendered as tag@digest."
  }
}

run "takes_storage_for_the_data_volumes" {
  command = plan
  variables {
    persistence = { size = "10Gi", storage_class = "longhorn" }
  }
  assert {
    condition     = yamldecode(helm_release.gateway.values[0]).ignition.persistence == { size = "10Gi", storageClassName = "longhorn" }
    error_message = "persistence is not passed to the chart."
  }
}

run "chart_4_renders_its_own_secret" {
  variables {
    chart_version    = "4.2.6"
    license_key      = "license-key"
    activation_token = "activation-token"
  }
  assert {
    condition     = length(kubernetes_secret_v1.gateway) == 0
    error_message = "Chart 4 has no existingSecret, so the module must not create the Secret."
  }
  assert {
    condition = alltrue([
      for key in ["GATEWAY_ADMIN_PASSWORD", "IGNITION_GAN_KEYSTORE_PASSWORD", "IGNITION_WEB_KEYSTORE_PASSWORD", "GATEWAY_API_TOKEN"] :
      nonsensitive(yamldecode(helm_release.gateway.values[1]).ignition.secrets[key] != "")
    ])
    error_message = "The chart's Secret lacks a generated password or the API key."
  }
  assert {
    condition     = nonsensitive(yamldecode(helm_release.gateway.values[1]).ignition.secrets.IGNITION_LICENSE_KEY == "license-key" && yamldecode(helm_release.gateway.values[1]).ignition.secrets.IGNITION_ACTIVATION_TOKEN == "activation-token")
    error_message = "The license key and activation token are not in the chart's Secret."
  }
}

run "no_licensing_unless_set" {
  assert {
    condition     = !nonsensitive(contains(keys(kubernetes_secret_v1.gateway[0].data), "IGNITION_LICENSE_KEY"))
    error_message = "IGNITION_LICENSE_KEY is set without a license key."
  }
}

run "a_local_chart_takes_the_modules_secret" {
  variables {
    chart_path  = "tests/fixtures/base/charts/failover"
    license_key = "license-key"
  }
  assert {
    condition     = helm_release.gateway.chart == "tests/fixtures/base/charts/failover" && helm_release.gateway.repository == null
    error_message = "chart_path does not replace the repository chart."
  }
  assert {
    condition     = nonsensitive(yamldecode(helm_release.gateway.values[1])) == { ignition = { existingSecret = "ignition-gateway" } }
    error_message = "A local chart must take the module's Secret through existingSecret, and no secrets."
  }
  assert {
    condition     = nonsensitive(kubernetes_secret_v1.gateway[0].data.IGNITION_LICENSE_KEY) == "license-key" && kubernetes_secret_v1.gateway[0].metadata[0].name == "ignition-gateway"
    error_message = "The module's Secret does not hold the gateway's environment."
  }
  assert {
    condition     = length(kubernetes_annotations.secret_checksum[0].template_annotations["checksum/secret"]) == 64
    error_message = "A changed Secret would not roll the gateways."
  }
}

# The fixtures stand in for an ignition-helm checkout (charts/failover beside
# charts/common), at the same chart versions: base, then the same with a change
# to the common library, and with changes only to files Helm doesn't render
run "a_local_chart_is_upgraded_when_its_files_change" {
  command = plan
  variables {
    chart_path = "tests/fixtures/base/charts/failover"
  }
  assert {
    condition     = helm_release.gateway.description == "chart_path sha256:1dd86fde515e8d67c2ea059b1126c5a2a8bd4192e762c6ad338c11b602b56e78"
    error_message = "The release's description is not the hash of the local chart and its common dependency (recompute it if the base fixture changed)."
  }
  assert {
    condition     = helm_release.gateway.dependency_update == true
    error_message = "A local chart must build its file:// dependencies, so an edit to charts/common deploys."
  }
}

run "a_local_chart_is_upgraded_when_its_dependency_changes" {
  command = plan
  variables {
    chart_path = "tests/fixtures/edited-common/charts/failover"
  }
  assert {
    condition     = startswith(helm_release.gateway.description, "chart_path sha256:") && helm_release.gateway.description != "chart_path sha256:1dd86fde515e8d67c2ea059b1126c5a2a8bd4192e762c6ad338c11b602b56e78"
    error_message = "An edit to the chart's file:// dependency (charts/common) does not change the release's description, so it would not upgrade."
  }
}

run "a_local_chart_ignores_files_helm_does_not_render" {
  command = plan
  variables {
    chart_path = "tests/fixtures/edited-unrendered/charts/failover"
  }
  assert {
    condition     = helm_release.gateway.description == "chart_path sha256:1dd86fde515e8d67c2ea059b1126c5a2a8bd4192e762c6ad338c11b602b56e78"
    error_message = "Changes to charts/, Chart.lock, tests/ or ci/ alone must not upgrade the release."
  }
}

run "a_published_chart_builds_no_dependencies" {
  command = plan
  assert {
    condition     = helm_release.gateway.dependency_update == false
    error_message = "A published chart is upgraded by its version and ships its dependencies: no dependency build."
  }
}

run "chart_path_must_be_a_chart" {
  command = plan
  variables {
    chart_path = "tests/fixtures/missing"
  }
  expect_failures = [helm_release.gateway]
}

run "a_failed_install_is_undone" {
  command = plan
  assert {
    condition     = helm_release.gateway.atomic == true && helm_release.gateway.cleanup_on_fail == true && helm_release.gateway.timeout == 900
    error_message = "A failed or timed-out install must be uninstalled (atomic), so the next apply can install again, within a timeout sized to a redundant pair's first start."
  }
}

run "a_failed_install_can_be_kept_to_debug" {
  command = plan
  variables {
    atomic  = false
    timeout = 1800
  }
  assert {
    condition     = helm_release.gateway.atomic == false && helm_release.gateway.timeout == 1800
    error_message = "atomic and timeout are not passed to the release."
  }
}

run "timeout_covers_a_first_start" {
  command = plan
  variables {
    timeout = 60
  }
  expect_failures = [var.timeout]
}

run "chart_5_takes_the_modules_secret" {
  command = plan
  variables {
    chart_version = "5.0.0"
  }
  assert {
    condition     = length(kubernetes_secret_v1.gateway) == 1
    error_message = "Chart 5 must take the module's Secret."
  }
}

run "backs_up_through_the_ingress" {
  command = plan
  assert {
    condition     = kubernetes_cron_job_v1.backup[0].spec[0].job_template[0].spec[0].template[0].spec[0].container[0].env[0].value == "https://ignition.example.com"
    error_message = "The backup job does not reach the gateway through the ingress's HTTPS."
  }
  assert {
    condition     = kubernetes_cron_job_v1.backup[0].spec[0].job_template[0].spec[0].template[0].spec[0].container[0].env[1].value_from[0].secret_key_ref[0].name == "ignition-gateway"
    error_message = "The backup job does not take the API key from the module's Secret."
  }
  assert {
    condition     = strcontains(kubernetes_cron_job_v1.backup[0].spec[0].job_template[0].spec[0].template[0].spec[0].container[0].command[2], "-mmin +10080")
    error_message = "The backup job does not keep 7 days of backups."
  }
}

run "backs_up_in_cluster_without_tls" {
  command = plan
  variables {
    ingress               = null
    api_token_require_tls = false
    redundancy            = false
  }
  assert {
    condition     = kubernetes_cron_job_v1.backup[0].spec[0].job_template[0].spec[0].template[0].spec[0].container[0].env[0].value == "http://ignition.ignition.svc:8088"
    error_message = "Without TLS required, the backup job should use the in-cluster HTTP URL."
  }
}

run "no_backup_url" {
  command = plan
  variables {
    ingress = null
  }
  expect_failures = [kubernetes_cron_job_v1.backup]
}

run "no_backup_on_8_1" {
  command = plan
  variables {
    ignition_version = "8.1"
    image_tag        = "8.1.55-2.0.1"
  }
  assert {
    condition     = length(kubernetes_cron_job_v1.backup) == 0 && output.api_token == null
    error_message = "8.1 has no REST API: no backup job and no API key."
  }
}

run "no_backup_when_null" {
  command = plan
  variables {
    backup = null
  }
  assert {
    condition     = length(kubernetes_cron_job_v1.backup) == 0 && length(kubernetes_persistent_volume_claim_v1.backup) == 0
    error_message = "backup = null still creates the backup job."
  }
}

run "eula_must_be_accepted" {
  command = plan
  variables {
    accept_eula = false
  }
  expect_failures = [var.accept_eula]
}

run "no_latest_tag" {
  command = plan
  variables {
    image_tag = "latest"
  }
  expect_failures = [var.image_tag]
}

run "digest_must_be_sha256" {
  command = plan
  variables {
    image_digest = "8.3.10-2.0.1"
  }
  expect_failures = [var.image_digest]
}

run "ingress_namespace_must_be_a_namespace" {
  command = plan
  variables {
    ingress = {
      host      = "ignition.example.com"
      namespace = "Kube System"
    }
  }
  expect_failures = [var.ingress]
}

run "api_key_over_an_ingress_without_tls" {
  command = plan
  variables {
    ingress = {
      host      = "ignition.example.com"
      namespace = "kube-system"
    }
    backup = null
  }
  expect_failures = [helm_release.gateway]
}

run "plain_http_when_tls_is_not_required" {
  command = plan
  variables {
    ingress = {
      host      = "ignition.example.com"
      namespace = "kube-system"
    }
    api_token_require_tls = false
  }
  assert {
    condition     = output.url == "http://ignition.example.com"
    error_message = "Without TLS required, an ingress without TLS is allowed."
  }
}
