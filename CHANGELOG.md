# Changelog

## [3.0.0](https://github.com/Apollogeddon/ignition-demo/compare/v2.0.1...v3.0.0) (2026-11-28)


### ⚠ BREAKING CHANGES

* **cluster:** require the ingress controller's namespace, prefix the platform's names with an optional name, and create none of the optional gateway resources by default
* **cluster:** pin the k3s example to a release tag, take an image digest, and read the ignition version from a validated tag
* **cluster:** keep the k3s state in a kubernetes secret, locked by a lease and encrypted with a passphrase, and read infra's through the same backend
* **cluster:** require accept_eula, passed as the chart's acceptEula, and take a local chart_path to test an unreleased chart

### Features

* A deployable k3s environment, a deploy test in ci, and the demo waterworks sample project ([32f1dae](https://github.com/Apollogeddon/ignition-demo/commit/32f1daef3fad02f6938127a3a2c97f86d0be1095))
* **ci:** Deploy the k3s environment to a throwaway k3d cluster in ci, so a provider or chart change the cluster refuses fails a check ([f7fa529](https://github.com/Apollogeddon/ignition-demo/commit/f7fa52970fffc2a41bbb0dc6625b935220929ff1))
* **ci:** Run tofu tests of the modules and the k3s infra stage, and deploy k3s by a manual run that applies a reviewed, encrypted plan ([5f88e38](https://github.com/Apollogeddon/ignition-demo/commit/5f88e38223edcc80e32bcba7ca2f83309fdf68e6))
* **cluster:** Back up the database with a nightly pg_dump and the 8.3 gateway through its backup api, pin postgres to 17.12, and size the gateway volumes ([418d9e3](https://github.com/Apollogeddon/ignition-demo/commit/418d9e3e902038cf2477a8e7b64a46a581f72265))
* **cluster:** Give 8.3 a sql historian for the udts' tag history, so history works on both lines ([0120787](https://github.com/Apollogeddon/ignition-demo/commit/01207879f1e2d0e2f2cc6bcaeb83e6f5aafddb1c))
* **cluster:** Keep the k3s state in a kubernetes secret, locked by a lease and encrypted with a passphrase, and read infra's through the same backend ([11baa24](https://github.com/Apollogeddon/ignition-demo/commit/11baa24babc58fb0f08fb84efc0cb46b8d8939f4))
* **cluster:** Pass a license key and activation token through the gateway secret, and own that secret in opentofu for charts with existingSecret ([ecfa047](https://github.com/Apollogeddon/ignition-demo/commit/ecfa047e623ce72d075db0df4d37c08444da7646))
* **cluster:** Pin the k3s example to a release tag, take an image digest, and read the ignition version from a validated tag ([f7900af](https://github.com/Apollogeddon/ignition-demo/commit/f7900af9fd68684c8ed8048b3391abdc9ee442f0))
* **cluster:** Require accept_eula, passed as the chart's acceptEula, and take a local chart_path to test an unreleased chart ([63347d0](https://github.com/Apollogeddon/ignition-demo/commit/63347d018d7ced02202384557dc8fc8b15d467c7))
* **cluster:** Require the ingress controller's namespace, prefix the platform's names with an optional name, and create none of the optional gateway resources by default ([11dad2d](https://github.com/Apollogeddon/ignition-demo/commit/11dad2d2dc109a450fa655196c5db8bc898d2963))
* **cluster:** Take chart_path in the k3s infra stage, to deploy an unreleased ignition-failover chart ([8f5c918](https://github.com/Apollogeddon/ignition-demo/commit/8f5c9180961f76f82c8efb085b5057d8f1a6869f))
* **database:** Add asset readings, events, online state, units and area order, seeding three days of readings, so the views have trends and an event log on a fresh stack ([0692e9b](https://github.com/Apollogeddon/ignition-demo/commit/0692e9b5b7c131f3bd790d6813b39de8e320e44f))
* **database:** Give each asset a rated capacity, so gauges and load bars have a scale to measure readings against ([c23a3c1](https://github.com/Apollogeddon/ignition-demo/commit/c23a3c1bf5ab7caa5839f80b878eb7491fe82c6c))
* **projects:** Add an alarms page and a tag history chart, so operators acknowledge the udts' alarms and see the historian's trends ([b6c031e](https://github.com/Apollogeddon/ignition-demo/commit/b6c031e742df7ad2f40fe0db02268288972119a0))
* **projects:** Add plant and analytics pages with a symbol schematic, equipment popup, gauges, xy chart and heatmap, so the demo shows perspective's process and analytics components on 8.1 and 8.3 ([317b0bb](https://github.com/Apollogeddon/ignition-demo/commit/317b0bb3f364da8a46d8057b7e0dc5d5e52b36c4))
* **projects:** Add the plant and analytics script modules and an hourly readings query, so the new pages' symbol states, gauges, chart and heatmap are shaped and tested outside the gateway ([4b74bb0](https://github.com/Apollogeddon/ignition-demo/commit/4b74bb0273d3fb4194762a0170d91da6aaf3c464))
* **projects:** Add the recordEvent gateway message handler and the overview, asset and event scripts and named queries behind the views, tested outside the gateway ([e8e319f](https://github.com/Apollogeddon/ignition-demo/commit/e8e319fb0944f7525fe542a7f8fb2f21615c8358))
* **projects:** Drive the asset tags from a gateway timer's plant model, so the views show a live process the operator can start and stop ([c3bce2a](https://github.com/Apollogeddon/ignition-demo/commit/c3bce2af9fa5600d23bf0da9a9b37b992399e81a))
* **projects:** Generate 8.1 gateway message handlers from ignition/message/*/handleMessage.py, so a handler is written once for both lines ([ca1f9ce](https://github.com/Apollogeddon/ignition-demo/commit/ca1f9ce46921cd177b1b705bb97ac6135374aac8))
* **projects:** Put the alarm tables in tabs and restyle them, so each gets the card's full height and matches the app ([68de9cd](https://github.com/Apollogeddon/ignition-demo/commit/68de9cdec5e9beea3faf27dd6d1450f3ef143948))
* **projects:** Replace the home view with overview, assets and events pages under a docked header, with kpi cards, charts and message-driven panels ([ad8148f](https://github.com/Apollogeddon/ignition-demo/commit/ad8148fa2c25f899d2d36154c2a02b9f32098839))


### Bug Fixes

* **ci:** Skip npm manifests in the ignition version check, and let patch (projects) open its pr ([9482f8a](https://github.com/Apollogeddon/ignition-demo/commit/9482f8ac35cd8be17e16ed062d3b9074764d6f6a))
* **ci:** Unblock the version check, the patch PR and the stuck /projects bumps ([6e33be6](https://github.com/Apollogeddon/ignition-demo/commit/6e33be69154a51b0ce235c21632fe09e1c877400))
* **cluster:** Allow ignition provider 1.3 in the config stages, so they can use the historian resource ([574134f](https://github.com/Apollogeddon/ignition-demo/commit/574134f17db67f37b8e10152206fc7dab49fbdbe))
* **cluster:** Install ignition-failover 5.0.0, so the gateways pair, route and load the 8.3 jdbc drivers ([adb0369](https://github.com/Apollogeddon/ignition-demo/commit/adb03694ac64ce772fab0b10c2f46f71780b1a2a))
* **cluster:** Install ignition-failover 5.1.0 and pass the secret hash through podannotations, so a first install no longer restarts the pair under the config stage ([11b537f](https://github.com/Apollogeddon/ignition-demo/commit/11b537fc7edbb85591775e2270cd1694ecf107dc))
* **cluster:** Install ignition-failover 5.1.1, so a backup that stays active and out of sync beside its master is restarted and pairs again ([05561bd](https://github.com/Apollogeddon/ignition-demo/commit/05561bdd0fa32a0a3046d8a930988bc71b50fec2))
* **cluster:** Install the gateway atomically and hash chart_path into the release, so a timed-out install retries and a local chart edit upgrades ([4586834](https://github.com/Apollogeddon/ignition-demo/commit/458683484c887e55ea337d54978e04794b599247))
* **cluster:** Lock the ignition provider at 1.3.0, so the config stages install the release that adds the historian provider ([240ae99](https://github.com/Apollogeddon/ignition-demo/commit/240ae99de1e1497e5eb21e0621a1df32baab943b))
* **cluster:** Require whole months of historian pruning, so a fraction fails validation rather than the plan ([0e63206](https://github.com/Apollogeddon/ignition-demo/commit/0e63206c73cc27eaf5b5e12cce5e0c994c402a82))
* **cluster:** Roll the gateways when the secret they take through existingSecret changes, as the chart has no pod annotations ([78bf060](https://github.com/Apollogeddon/ignition-demo/commit/78bf06009ac749df57303e812eb1fa742fcfd8c4))
* **cluster:** Serve the k3s ingress on websecure only with an http redirect, and fail the plan when the api key needs tls the ingress lacks ([234996f](https://github.com/Apollogeddon/ignition-demo/commit/234996f9cb4982573c237d363e5e379ae135fd82))
* **cluster:** Set runAsNonRoot on every container, as kubernetes provider 3.5 sends it unset as false and pod security rejects the database ([ef2ed3f](https://github.com/Apollogeddon/ignition-demo/commit/ef2ed3f67748156a050cbf302620b94d6d99de8c))
* **cluster:** Ship the k3s example with accept_eula commented out, so copying it doesn't accept the eula for the user ([5d9ef9c](https://github.com/Apollogeddon/ignition-demo/commit/5d9ef9cc63d5886d5671b5b349e3895ca991a6d5))
* **cluster:** Wait for the database and retry the gateway backup, so a backup job's new pod survives the seconds before its network policy admits it ([9d246fb](https://github.com/Apollogeddon/ignition-demo/commit/9d246fb63f206f53e4227642ff28e7a1496fd56e))
* **deps:** Bump astro ([#75](https://github.com/Apollogeddon/ignition-demo/issues/75)) ([d57ccdb](https://github.com/Apollogeddon/ignition-demo/commit/d57ccdbeeb8d0a9234bda2d298d4676be0b6b0b6))
* **deps:** Bump astro ([#78](https://github.com/Apollogeddon/ignition-demo/issues/78)) ([437d63b](https://github.com/Apollogeddon/ignition-demo/commit/437d63b135836860e334eaf884c01f4fdc088963))
* **deps:** Bump dompurify from 3.4.16 to 3.4.17 in /webpage ([#70](https://github.com/Apollogeddon/ignition-demo/issues/70)) ([f5c8d0b](https://github.com/Apollogeddon/ignition-demo/commit/f5c8d0bcca97ec0a9c1b5e1895695e45017b7e4d))
* **deps:** Bump fast-uri from 3.1.8 to 3.1.9 ([#71](https://github.com/Apollogeddon/ignition-demo/issues/71)) ([9bf277b](https://github.com/Apollogeddon/ignition-demo/commit/9bf277b1f3ad2a37da1aad43d4f875a3b3258c8a))
* **deps:** Bump fast-uri from 3.1.8 to 3.1.9 in /webpage ([#72](https://github.com/Apollogeddon/ignition-demo/issues/72)) ([c6f66c9](https://github.com/Apollogeddon/ignition-demo/commit/c6f66c986645f72f02d8d2b450a1179b7f9ed2f3))
* **deps:** Bump filelock, virtualenv and vermin in /projects together, past their advisories ([ec627b9](https://github.com/Apollogeddon/ignition-demo/commit/ec627b99bafc743b48ab12580ddc1398bc0a220e))
* **deps:** Bump forgepy[toolchain] from v1.0.0 to 1.1.1 in /projects ([#84](https://github.com/Apollogeddon/ignition-demo/issues/84)) ([6a3ae40](https://github.com/Apollogeddon/ignition-demo/commit/6a3ae40307ec8e2b9aea1d1fa2194617e1779489))
* **deps:** Bump hashicorp/kubernetes ([#63](https://github.com/Apollogeddon/ignition-demo/issues/63)) ([b9e8cec](https://github.com/Apollogeddon/ignition-demo/commit/b9e8cec7aa6f04b220abc95899ee4456d656ce74))
* **deps:** Bump hashicorp/kubernetes ([#77](https://github.com/Apollogeddon/ignition-demo/issues/77)) ([104af99](https://github.com/Apollogeddon/ignition-demo/commit/104af9960f9d4e78011d9bba1f9de0f277975539))
* **deps:** Bump markdownlint-cli2 ([#85](https://github.com/Apollogeddon/ignition-demo/issues/85)) ([b9f6069](https://github.com/Apollogeddon/ignition-demo/commit/b9f6069c710584b3cd253ead04c254299eea2441))
* **deps:** Bump the apollogeddon group across 2 directories with 1 update ([#60](https://github.com/Apollogeddon/ignition-demo/issues/60)) ([cd50dc2](https://github.com/Apollogeddon/ignition-demo/commit/cd50dc288acdec745547058a1b79ccc165c06760))
* **deps:** Bump the apollogeddon group across 2 directories with 1 update ([#73](https://github.com/Apollogeddon/ignition-demo/issues/73)) ([578b069](https://github.com/Apollogeddon/ignition-demo/commit/578b069f186f4d1620f0bda44d88c57160d17b95))
* **deps:** Bump the apollogeddon group across 2 directories with 1 update ([#82](https://github.com/Apollogeddon/ignition-demo/issues/82)) ([cbc8483](https://github.com/Apollogeddon/ignition-demo/commit/cbc848317ab07ffe9ed4e637019ecb4c43be536d))
* **deps:** Bump the dependencies group across 1 directory with 2 updates ([#61](https://github.com/Apollogeddon/ignition-demo/issues/61)) ([72fc1e1](https://github.com/Apollogeddon/ignition-demo/commit/72fc1e1fe4cb0e17f1353b8084d54055654bb1d5))
* **deps:** Bump the dependencies group across 1 directory with 2 updates ([#76](https://github.com/Apollogeddon/ignition-demo/issues/76)) ([2daf084](https://github.com/Apollogeddon/ignition-demo/commit/2daf08453bcdf0eb5842d6eaa480ce6281ed0420))
* **deps:** Bump the dependencies group across 1 directory with 3 updates ([#68](https://github.com/Apollogeddon/ignition-demo/issues/68)) ([5498bb5](https://github.com/Apollogeddon/ignition-demo/commit/5498bb5b2e514532a6ed7c30489d684fa7bc2add))
* **deps:** Bump the dependencies group across 1 directory with 3 updates ([#80](https://github.com/Apollogeddon/ignition-demo/issues/80)) ([c242588](https://github.com/Apollogeddon/ignition-demo/commit/c242588f4a9fcb5f5bc61f1325f09be75fefd031))
* **deps:** Bump the dependencies group across 2 directories with 3 updates ([#74](https://github.com/Apollogeddon/ignition-demo/issues/74)) ([a0be711](https://github.com/Apollogeddon/ignition-demo/commit/a0be7115062edb37e5dc1550400ddca2aad0315c))
* **deps:** Bump the dependencies group across 2 directories with 3 updates ([#79](https://github.com/Apollogeddon/ignition-demo/issues/79)) ([3f190b7](https://github.com/Apollogeddon/ignition-demo/commit/3f190b77a4be27051a34afc394896b7c6527ac28))
* **docs:** Darken light-mode links and mermaid's dark labels, so both clear 4.5:1 contrast ([aefbcb7](https://github.com/Apollogeddon/ignition-demo/commit/aefbcb71ba2e5f40d5c2d09ca558073b3fb60868))
* **docs:** Keep the navbar, hero and docs tables inside a phone's width, so mobile browsers don't zoom the pages out ([df5bf7e](https://github.com/Apollogeddon/ignition-demo/commit/df5bf7ec366b519cd757418cde8d96fa8b7b09a0))
* **projects:** Create the asset instances from the process timer once the database answers, so a new 8.3 gateway gets them after its config stage ([e5ff8cc](https://github.com/Apollogeddon/ignition-demo/commit/e5ff8cc8af59c330eef15f3a089ebcd1a39a1a6a))
* **projects:** Drop the heatmap's numbers on tablets too, so its narrow cells don't overlap ([306fefe](https://github.com/Apollogeddon/ignition-demo/commit/306fefe76ba38cb8f3f57384207ab2f675e4aa9b))
* **projects:** Keep an operator's reset, retry a failed reading log and disable start until the state is known, so the live process never undoes an operator ([3a8a8c5](https://github.com/Apollogeddon/ignition-demo/commit/3a8a8c5723c91aea41c10e4fe9e60f0f485ce53d))
* **projects:** Narrow the page links on phones, so all six fit the header ([a932d55](https://github.com/Apollogeddon/ignition-demo/commit/a932d55c737ee02e642453aafdaaea23cbe8306a))
* **projects:** Split the plant schematic into a container per stage and wrap kpi cards below desktop width, so neither bunches up on a tablet or phone ([ad79999](https://github.com/Apollogeddon/ignition-demo/commit/ad79999efe7ba12cf91d46101e9aea208bcb4362))
* **projects:** Stack the views on phones and keep the plant schematic scrollable, so every page fits a small screen ([00bdfe4](https://github.com/Apollogeddon/ignition-demo/commit/00bdfe4ed379e7de635f73878bc5b8a0121e50a7))
* **projects:** Start tank levels empty rather than at zero, so a new gateway records no false low level ([aeaf46e](https://github.com/Apollogeddon/ignition-demo/commit/aeaf46ecedd971e0016c6d32e8608e456ae3e42c))

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
