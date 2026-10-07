# The gateway image: Ignition with this repository's projects baked in.
#
# Build from the repository root so the projects are in the context:
#   docker build -f gateway/Dockerfile -t ignition-gateway .
#
# The projects are copied outside the data volume, to assets/projects, and the
# gateway is pointed at them with -Dignition.projects.dir (see the gateway
# module's Helm values). The image is then the only source of project
# contents: a new image tag ships new projects, and both gateways of a
# redundant pair always run the same ones. Designer edits made on a deployed
# gateway are not kept; develop against local/ instead.
ARG IGNITION_VERSION=8.3.10
FROM docker.io/inductiveautomation/ignition:${IGNITION_VERSION}

WORKDIR /usr/local/bin/ignition

# Third-party modules (.modl), if any: drop them in gateway/modules/
COPY --chown=ignition:ignition --chmod=u=rwX,go=rX gateway/modules/ user-lib/modules/

# One folder per project, named as the gateway knows it (project.json's parent
# refers to these names)
COPY --chown=ignition:ignition --chmod=u=rwX,go=rX projects/library/src/ assets/projects/library/
COPY --chown=ignition:ignition --chmod=u=rwX,go=rX projects/project/src/ assets/projects/project/

LABEL org.opencontainers.image.title="ignition-gateway" \
      org.opencontainers.image.description="Ignition with the demo projects baked in"
