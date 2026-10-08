#!/usr/bin/env bash
# Install the image's assets into the gateway's data volume, before the gateway
# starts (entrypoint.sh runs this on every start). The data volume outlives the
# image, so each start makes it match the image again: assets are copied (not
# symlinked: a dangling symlink in data/ breaks redundancy state transfer), and
# assets a previous image installed that this one no longer has are removed.
#
#   assets/icons/<library>.svg   Perspective icon library, referenced in views
#                                as <library>/<icon id>
#     8.1: data/modules/com.inductiveautomation.perspective/icons/<library>.svg
#     8.3: an icon library resource in the external config collection
#   assets/certs/*.crt|cer|pem   trusted by the gateway's outgoing connections
#     data/certificates/supplemental/ on both versions
#
# Web files (gateway/assets/web) need nothing at start: the Dockerfile puts
# them in webserver/webapps/main, which is in the image, not the data volume.
#
# Env: IGNITION_HOME (default /usr/local/bin/ignition)
set -euo pipefail
shopt -s nullglob

home="${IGNITION_HOME:-/usr/local/bin/ignition}"
assets="${home}/assets"
data="${home}/data"
manifest="${data}/.image-assets"

log() { echo "assets   | $(date '+%Y/%m/%d %H:%M:%S') | $*"; }

data_files=("${data}"/*)
if [ ${#data_files[@]} -eq 0 ]; then
  log "WARNING: the data volume is empty (not seeded); skipping asset installation"
  exit 0
fi

version=$(sed -n 's/^gateway\.version=//p' "${home}/lib/install-info.txt" 2>/dev/null || true)
case "${version}" in
  8.1.*) layout=81 ;;
  8.3.* | 8.[4-9].* | 9.*) layout=83 ;;
  *)
    log "WARNING: unknown Ignition version '${version}'; skipping asset installation"
    exit 0
    ;;
esac

icons81="${data}/modules/com.inductiveautomation.perspective/icons"
icons83="${data}/config/resources/external/com.inductiveautomation.perspective/icons"
certs="${data}/certificates/supplemental"

installed=()

for svg in "${assets}"/icons/*.svg; do
  library=$(basename "${svg}" .svg)
  if [ "${layout}" = 81 ]; then
    mkdir -p "${icons81}"
    cp "${svg}" "${icons81}/${library}.svg"
    installed+=("${icons81}/${library}.svg")
  else
    dir="${icons83}/${library}"
    mkdir -p "${dir}"
    cp "${svg}" "${dir}/library.svg"
    printf '{\n  "svgFileName": "library.svg"\n}\n' > "${dir}/config.json"
    cat > "${dir}/resource.json" <<'EOF'
{
  "scope": "A",
  "version": 1,
  "restricted": false,
  "overridable": true,
  "files": [
    "config.json",
    "library.svg"
  ],
  "attributes": {
    "enabled": true
  }
}
EOF
    installed+=("${dir}")
  fi
done

for cert in "${assets}"/certs/*.crt "${assets}"/certs/*.cer "${assets}"/certs/*.pem; do
  mkdir -p "${certs}"
  cp "${cert}" "${certs}/$(basename "${cert}")"
  installed+=("${certs}/$(basename "${cert}")")
done

# remove what an earlier image installed and this one does not have; only
# paths under the folders this script manages are ever removed
removed=0
if [ -f "${manifest}" ]; then
  while IFS= read -r old; do
    [ -n "${old}" ] || continue
    case "${old}" in
      "${icons81}"/* | "${icons83}"/* | "${certs}"/*) ;;
      *) continue ;;
    esac
    keep=false
    for path in "${installed[@]}"; do
      [ "${path}" = "${old}" ] && keep=true && break
    done
    if ! ${keep} && [ -e "${old}" ]; then
      rm -rf -- "${old}"
      removed=$((removed + 1))
    fi
  done < "${manifest}"
fi
printf '%s\n' "${installed[@]}" > "${manifest}"

log "Ignition ${version}: installed ${#installed[@]} assets, removed ${removed}"
