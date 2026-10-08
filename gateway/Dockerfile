# The gateway image: Ignition with this repository's projects and assets baked
# in. Works for Ignition 8.1 and 8.3:
#
#   docker build -f gateway/Dockerfile -t ignition-gateway .
#   docker build -f gateway/Dockerfile --build-arg IGNITION_VERSION=8.1.55 -t ignition-gateway:8.1 .
#
# Build from the repository root so the projects are in the context.
#
# The projects are copied outside the data volume, to assets/projects, and the
# gateway is pointed at them with -Dignition.projects.dir (see the gateway
# module's Helm values). The image is then the only source of project
# contents: a new image tag ships new projects, and both gateways of a
# redundant pair always run the same ones. Designer edits made on a deployed
# gateway are not kept; develop against develop/ instead.
ARG IGNITION_VERSION=8.3.10
FROM docker.io/inductiveautomation/ignition:${IGNITION_VERSION}

WORKDIR /usr/local/bin/ignition

# Third-party modules (.modl), if any: drop them in gateway/modules/
COPY --chown=ignition:ignition gateway/modules/ user-lib/modules/

# Static files served by the gateway's web server at /<file> (manuals, sounds,
# guides); webserver/ is part of the image, not the data volume
COPY --chown=ignition:ignition gateway/assets/web/ webserver/webapps/main/

# Icon libraries and certificates, installed into the data volume on every
# start by install-assets.sh (the data volume outlives the image)
COPY --chown=ignition:ignition gateway/assets/icons/ assets/icons/
COPY --chown=ignition:ignition gateway/assets/certs/ assets/certs/
COPY --chown=ignition:ignition gateway/install-assets.sh gateway/entrypoint.sh gateway/api-token.sh gateway/api_token_grant.py gateway/trial-keepalive.sh assets/

# Ignition 8.1 gateway configuration, applied by the startup event (library.seed)
COPY --chown=ignition:ignition gateway/seed/ assets/seed/

# One folder per project, named as the gateway knows it (project.json's parent
# refers to these names)
COPY --chown=ignition:ignition projects/library/src/ assets/projects/library/
COPY --chown=ignition:ignition projects/project/src/ assets/projects/project/

# checkouts on Windows give everything mode 777; make it owner-writable only,
# with the two scripts executable
RUN chmod -R a-x,u=rwX,go=rX assets user-lib/modules webserver/webapps/main \
    && chmod 0755 assets/install-assets.sh assets/entrypoint.sh assets/api-token.sh assets/trial-keepalive.sh

ENTRYPOINT ["/usr/local/bin/ignition/assets/entrypoint.sh"]

LABEL org.opencontainers.image.title="ignition-gateway" \
      org.opencontainers.image.description="Ignition with the demo projects and assets baked in"
