# The k3s infra stage's image validations and HTTPS-only ingress, against mock
# providers: tofu -chdir=cluster/environments/k3s/infra test

mock_provider "helm" {}
mock_provider "kubernetes" {}
mock_provider "random" {}

variables {
  state_passphrase = "a passphrase for tests only"
  accept_eula      = true
  image_tag        = "8.3.10-2.0.1"
  hostname         = "ignition.192.0.2.10.nip.io"
}

run "redirects_http_to_https" {
  command = plan
  assert {
    condition     = output.gateway_url == "https://ignition.192.0.2.10.nip.io"
    error_message = "The gateway is not served over HTTPS."
  }
  assert {
    condition     = kubernetes_ingress_v1.http_redirect[0].metadata[0].annotations["traefik.ingress.kubernetes.io/router.entrypoints"] == "web"
    error_message = "The redirect Ingress is not on the web entrypoint."
  }
  assert {
    condition     = kubernetes_manifest.https_redirect[0].manifest.spec.redirectScheme.scheme == "https"
    error_message = "The Middleware does not redirect to HTTPS."
  }
}

run "no_redirect_when_off" {
  command = plan
  variables {
    http_redirect = false
  }
  assert {
    condition     = length(kubernetes_ingress_v1.http_redirect) == 0 && length(kubernetes_manifest.https_redirect) == 0
    error_message = "http_redirect = false still routes port 80."
  }
}

run "reads_8_1_from_the_tag" {
  command = plan
  variables {
    image_tag = "8.1-dev"
  }
  assert {
    condition     = output.api_token == null
    error_message = "An 8.1 tag must deploy an 8.1 gateway, which has no API key."
  }
}

run "no_main_tag" {
  command = plan
  variables {
    image_tag = "8.3.10-main"
  }
  expect_failures = [var.image_tag]
}

run "no_latest_tag" {
  command = plan
  variables {
    image_tag = "latest"
  }
  expect_failures = [var.image_tag]
}

run "tag_must_name_its_ignition_version" {
  command = plan
  variables {
    image_tag = "dev"
  }
  expect_failures = [var.image_tag]
}

run "passphrase_of_16_characters" {
  command = plan
  variables {
    state_passphrase = "too short"
  }
  expect_failures = [var.state_passphrase]
}
