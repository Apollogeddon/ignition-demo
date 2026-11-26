# Copy to terraform.tfvars (git-ignored) and adjust.

# Read the Ignition End User License Agreement before you set this:
# https://inductiveautomation.com/ignition/license
accept_eula = true

# a tag CI published to ghcr.io/apollogeddon/ignition-gateway: <ignition version>-<branch|sha-<commit>|release>
image_tag = "8.3.10-main"
# any name resolving to the k3s node; nip.io maps <ip>.nip.io to <ip>, so use your node's IP
hostname = "ignition.192.0.2.10.nip.io"

# only for a private GHCR package
# ghcr_username = "<github user>"
# ghcr_token    = "<token with read:packages>"
