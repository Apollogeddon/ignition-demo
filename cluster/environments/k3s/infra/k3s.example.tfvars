# Copy to terraform.tfvars (git-ignored) and adjust.

# Read the Ignition End User License Agreement before you set this:
# https://inductiveautomation.com/ignition/license
# accept_eula = true

# A release's tag in ghcr.io/apollogeddon/ignition-gateway: <ignition version>-<release version>.
# Not <ignition version>-main, which CI re-pushes on every merge.
image_tag = "8.3.10-2.0.1"
# Optionally pin the tag to its digest, from the release's images-<version>.txt or
#   docker buildx imagetools inspect ghcr.io/apollogeddon/ignition-gateway:8.3.10-2.0.1
# image_digest = "sha256:<64 hex digits>"
# any name resolving to the k3s node; nip.io maps <ip>.nip.io to <ip>, so use your node's IP
hostname = "ignition.192.0.2.10.nip.io"

# only for a private GHCR package
# ghcr_username = "<github user>"
# ghcr_token    = "<token with read:packages>"
