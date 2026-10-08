# Security policy

## Supported versions

Only the latest commit on `main`, and the gateway images built from it, receive security fixes.

## Reporting a vulnerability

Report security vulnerabilities privately through [GitHub's private vulnerability reporting](https://github.com/Apollogeddon/ignition-demo/security/advisories/new). Don't open a public issue.

You can expect an initial response within a few days. If the issue is confirmed, the fix is committed to `main` and credited in the advisory unless you ask otherwise.

Vulnerabilities in Ignition itself should be reported to Inductive Automation, not here.

## Automated security tooling

CI runs these checks on pull requests and on pushes to `main`:

- **Gitleaks** scans the repository for committed secrets.
- **OSV-Scanner** scans the project tooling's `uv.lock` and the documentation site's dependencies for known vulnerabilities. On `main`, it upgrades vulnerable packages and commits the patched lock files.
- **Trivy** scans the OpenTofu code, the Compose file and the Dockerfile for high and critical misconfigurations.

**Dependabot** proposes dependency updates with a 3-day cooldown, which gives a compromised release time to be caught and yanked upstream.
