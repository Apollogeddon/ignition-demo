# Changelog

## [2.0.1](https://github.com/Apollogeddon/ignition-demo/compare/v2.0.0...v2.0.1) (2026-10-16)


### Bug Fixes

* **deps:** Bump the apollogeddon group across 2 directories with 1 update ([#57](https://github.com/Apollogeddon/ignition-demo/issues/57)) ([3b907fd](https://github.com/Apollogeddon/ignition-demo/commit/3b907fd45ed5bae49a6d91a088cf377152bab0ba))

## [2.0.0](https://github.com/Apollogeddon/ignition-demo/compare/v1.2.3...v2.0.0) (2026-10-16)


### ⚠ BREAKING CHANGES

* secure API key defaults, Dependabot for Ignition and providers, test the published image ([#46](https://github.com/Apollogeddon/ignition-demo/issues/46))

### Bug Fixes

* **ci:** Lower-case the owner in the published image's reference ([#53](https://github.com/Apollogeddon/ignition-demo/issues/53)) ([be13d1a](https://github.com/Apollogeddon/ignition-demo/commit/be13d1a9fc10354fd9a81c78abef5cd07ec22b6d))
* **deps:** Bump astro ([#47](https://github.com/Apollogeddon/ignition-demo/issues/47)) ([8a96306](https://github.com/Apollogeddon/ignition-demo/commit/8a963061ef51c27879b680a515f35596fe87ef81))
* **deps:** Bump the apollogeddon group across 2 directories with 1 update ([#48](https://github.com/Apollogeddon/ignition-demo/issues/48)) ([9e9ca2a](https://github.com/Apollogeddon/ignition-demo/commit/9e9ca2acab3fb8a945855e69094d9f00c9e7bd6d))
* **deps:** Bump the providers group across 3 directories with 1 update ([#49](https://github.com/Apollogeddon/ignition-demo/issues/49)) ([025dba2](https://github.com/Apollogeddon/ignition-demo/commit/025dba20f809d00a6c857377c8b358e019fee21e))
* **deps:** Take ignition-failover 4.2.6, the ignition provider 1.2.4 and forgepy 1.0.0 ([#56](https://github.com/Apollogeddon/ignition-demo/issues/56)) ([8f54d66](https://github.com/Apollogeddon/ignition-demo/commit/8f54d661183bbaac65acbd09378b784047779b15))
* Restart the trial reset backoff when the trial runs again, and drop an unneeded forwarded-header flag ([#52](https://github.com/Apollogeddon/ignition-demo/issues/52)) ([a3638aa](https://github.com/Apollogeddon/ignition-demo/commit/a3638aaf075efad2d87fa79844de2d0a4c5692f5))
* Review 4 findings (trial keepalive JSON and backoff, forwarded-header trust, lock files, forgepy, OpenTofu pin) ([#51](https://github.com/Apollogeddon/ignition-demo/issues/51)) ([ac72a04](https://github.com/Apollogeddon/ignition-demo/commit/ac72a042b0643dcc09ff010a85390791452b7946))
* Secure API key defaults, Dependabot for Ignition and providers, test the published image ([#46](https://github.com/Apollogeddon/ignition-demo/issues/46)) ([adc551b](https://github.com/Apollogeddon/ignition-demo/commit/adc551bae59bd44703dd0066977420a2b203b325))

## [1.2.3](https://github.com/Apollogeddon/ignition-demo/compare/v1.2.2...v1.2.3) (2026-10-12)


### Bug Fixes

* **cluster:** Deploy ignition-failover 4.2.5 and take ignition provider releases from 1.2.3 ([81184b8](https://github.com/Apollogeddon/ignition-demo/commit/81184b80fe3154381ac549e9fc8d70af27d95bb3))
* **cluster:** Deploy ignition-failover 4.2.5, which bundles ignition-common 3.3.2 ([fc1280d](https://github.com/Apollogeddon/ignition-demo/commit/fc1280d1ccceb2295400bf10a0dff19509a9c60a))
* **cluster:** Take ignition provider patch releases from 1.2.3, which shows cleared fields as drift ([17ed7e5](https://github.com/Apollogeddon/ignition-demo/commit/17ed7e5862348593c8b677c06b671c76ef639924))

## [1.2.2](https://github.com/Apollogeddon/ignition-demo/compare/v1.2.1...v1.2.2) (2026-10-12)


### Bug Fixes

* **develop:** Publish the gateway and database ports on 127.0.0.1 only ([#42](https://github.com/Apollogeddon/ignition-demo/issues/42)) ([489b252](https://github.com/Apollogeddon/ignition-demo/commit/489b252e691b86ef287371d59ffc61e6abbaf3fa))

## [1.2.1](https://github.com/Apollogeddon/ignition-demo/compare/v1.2.0...v1.2.1) (2026-10-12)


### Bug Fixes

* **cluster:** Deploy ignition-failover 4.2.3, and pin the ignition provider to 1.2 patch releases ([f3f1368](https://github.com/Apollogeddon/ignition-demo/commit/f3f1368a521012efd4593a7973d1187a47f0c5b9))
* **cluster:** Deploy ignition-failover 4.2.3, which redoes an interrupted data volume seed ([381b54c](https://github.com/Apollogeddon/ignition-demo/commit/381b54c8ab8ab46220159488ae20c144bcc152e3))
* **cluster:** Take ignition provider patch releases from 1.2.2, with the shared module stating its minimum ([584889a](https://github.com/Apollogeddon/ignition-demo/commit/584889a120ddd6accd2f7d7f72362ac2882fa59c))

## [1.2.0](https://github.com/Apollogeddon/ignition-demo/compare/v1.1.3...v1.2.0) (2026-10-11)


### Features

* **cluster:** Give the database startup and liveness probes beside its readiness probe ([c0de8ae](https://github.com/Apollogeddon/ignition-demo/commit/c0de8ae896a01a27aaaad22183925ff695a5956f))
* **cluster:** Probe every workload and close the chart's helper pods to ingress ([5ea2cf7](https://github.com/Apollogeddon/ignition-demo/commit/5ea2cf74a83b5e762b0b534520ebd44c23f5b9c4))
* **cluster:** State the gateway's probes and close the chart's helper pods to ingress ([953f238](https://github.com/Apollogeddon/ignition-demo/commit/953f2380fd538c6a9b8966fc609192abc6cea741))


### Bug Fixes

* **deps:** Override smol-toml to 1.9 past markdownlint-cli2's exact pin ([#39](https://github.com/Apollogeddon/ignition-demo/issues/39)) ([0430fa9](https://github.com/Apollogeddon/ignition-demo/commit/0430fa9aa9bb3a5bfbe0c256ae39fc41b540b781))
* **webpage:** Meet WCAG 2.2 AA and check the site's links and accessibility in CI ([#38](https://github.com/Apollogeddon/ignition-demo/issues/38)) ([c50cc83](https://github.com/Apollogeddon/ignition-demo/commit/c50cc83754d6b9dc2ee8f685ca82105e11f4b16e))

## [1.1.3](https://github.com/Apollogeddon/ignition-demo/compare/v1.1.2...v1.1.3) (2026-10-10)


### Bug Fixes

* **deps:** Bump @apollogeddon/forgejs ([#28](https://github.com/Apollogeddon/ignition-demo/issues/28)) ([837b058](https://github.com/Apollogeddon/ignition-demo/commit/837b058de31ad20767e9a683f54a84fbab90dc8d))

## [1.1.2](https://github.com/Apollogeddon/ignition-demo/compare/v1.1.1...v1.1.2) (2026-10-10)


### Bug Fixes

* **deps:** Bump forgejs to 4.0.0 and let Dependabot update it ([114c8d0](https://github.com/Apollogeddon/ignition-demo/commit/114c8d0084fc97e5e167389f679b118ba225a53b))
* **deps:** Bump forgejs to 4.0.0, which bundles with tsdown instead of tsup ([7d486f0](https://github.com/Apollogeddon/ignition-demo/commit/7d486f0d8e344d3dbf283ff831fd9b473931fb22))
* **deps:** Bump the dependencies group across 1 directory with 2 updates ([#23](https://github.com/Apollogeddon/ignition-demo/issues/23)) ([2999aac](https://github.com/Apollogeddon/ignition-demo/commit/2999aacdd642eb8d36a2fcb2e5eb6466d039e9bc))

## [1.1.1](https://github.com/Apollogeddon/ignition-demo/compare/v1.1.0...v1.1.1) (2026-10-10)


### Bug Fixes

* **deps:** Override katex to a patched version ([#20](https://github.com/Apollogeddon/ignition-demo/issues/20)) ([b280938](https://github.com/Apollogeddon/ignition-demo/commit/b280938f27b5f42be3f0ca4ac19ae7d168b78451))

## [1.1.0](https://github.com/Apollogeddon/ignition-demo/compare/v1.0.0...v1.1.0) (2026-10-09)


### Features

* **tofu:** Require ignition provider ~&gt; 1.1 and install it from a release ([bd7b3f7](https://github.com/Apollogeddon/ignition-demo/commit/bd7b3f75ae1d65c01c7e79fe88e218bdd0c0bc1e))

## 1.0.0 (2026-10-08)


### Features

* Check the projects with forgepy and version the gateway images ([c99717e](https://github.com/Apollogeddon/ignition-demo/commit/c99717e6287eb12b641fa7d10c4663b68369f1e8))
