---
name: bump-ignition
description: Move the repository to a new Ignition patch release on the 8.1 or 8.3 line (Dockerfile pins, every file naming the release, examples, tests, the API stubs), or finish a Dependabot pull request that moved a gateway/base pin. Use when asked to bump, upgrade or update the Ignition version.
---

`gateway/base/<line>/Dockerfile` (`FROM docker.io/inductiveautomation/ignition:<release>`) is the pin. Dependabot moves it, and `scripts/check-ignition-versions.sh` lists every other tracked file still naming that line's old release.

1. **Pin.** Set the new release in `gateway/base/<line>/Dockerfile`, unless Dependabot already did. Check that the tag exists: `docker manifest inspect docker.io/inductiveautomation/ignition:<release>` (or ask the user).
2. **List the rest:** `scripts/check-ignition-versions.sh`. It skips the changelog, the npm manifests and lockfiles, `projects/uv.lock`, `projects/pyproject.toml` and its own test.
3. **Update each listed place**, typically:
   - `gateway/Dockerfile`: `ARG IGNITION_VERSION` (the 8.3 default) and the 8.1 example in the header;
   - `develop/.env.example` and `develop/docker-compose.yml`: the `${IGNITION_VERSION:-…}` defaults;
   - `.github/workflows/.index.yml`: the docker matrix's `version`, and `docker.yml`'s comments;
   - `scripts/generate-event-scripts.sh`: `IGNITION_81_VERSION`, for 8.1;
   - the 8.3 image tags in `k3s.example.tfvars`, `cluster/README.md` and its webpage mirror, the k3s `variables.tf` messages and the `*.tftest.hcl` files. Those name a *release* tag (`8.3.10-2.0.1`), so move them only once a release image on the new version exists, or keep each file consistent with its tests;
   - `gateway/tests/*_test.sh`.
4. **API stubs.** `ignition-api-stubs` follows its own releases. If one exists for the new release, update the `ignition81`/`ignition83` group in `projects/pyproject.toml` and its comment, then `cd projects && uv lock`. If none exists, leave the group and update the comment.
5. **Validate:** run `scripts/check-ignition-versions.sh` until it prints `Ignition versions match gateway/base`, then `bash scripts/tests/check-ignition-versions_test.sh` and `bash gateway/tests/*_test.sh`, and `tofu test` in `cluster/modules/gateway` and `cluster/environments/k3s/infra` if tftest files changed. Run the projects' checks if the stubs moved (see `/validate`). The image itself is smoke-tested by CI's `docker / test`, or locally with `gateway/tests/smoke.sh` when asked.
6. **Commit:** `fix(gateway): move ignition 8.3 to 8.3.11, so the image runs the latest patch release` (stage the files by name).
