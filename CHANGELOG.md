# Changelog

All notable changes to Agentic Trader will be recorded here.

This file is maintained by `python-semantic-release` from conventional commits on
`main`.

<!-- version list -->

## v0.12.3 (2026-05-25)

### Bug Fixes

- Enforce release changelog coverage
  ([`5beddec`](https://github.com/ogiboy/agentic-trader/commit/5beddec2df62a7800830fad11babe14d50442b26))


## v0.12.2 (2026-05-25)

### Bug Fixes

- Restore changelog generation
  ([`3b621e0`](https://github.com/ogiboy/agentic-trader/commit/3b621e038ad9eedb648ea7cec04222420ec3f2e5))


## v0.12.1 (2026-05-25)

### Bug Fixes

- Align CI with Python 3.13
  ([`8e788d7`](https://github.com/ogiboy/agentic-trader/commit/8e788d7d6232d6c8cd006338796698f5623d539e))

- Stabilize CI and document Next apps
  ([`864c32c`](https://github.com/ogiboy/agentic-trader/commit/864c32c56c679ebe9897cbcc70d342140ce652a3))

### Refactors

- Refactor control room localization
  ([`d219801`](https://github.com/ogiboy/agentic-trader/commit/d2198014f8d5bd5cb8f804e40bfd4a278699ffaf))

### Chores

- Improve V1 readiness and strict QA gates
  ([`b33a07f`](https://github.com/ogiboy/agentic-trader/commit/b33a07f7f9198f38e9d494b4e6c17bb988f3068b))


## v0.12.0 (2026-05-20)

### Features

- Align V1 trading readiness
  ([`199eb30`](https://github.com/ogiboy/agentic-trader/commit/199eb30))
- Replay research cycle memory
  ([`2f6cb23`](https://github.com/ogiboy/agentic-trader/commit/2f6cb23))
- Refresh broker proposal truth
  ([`07d6cdd`](https://github.com/ogiboy/agentic-trader/commit/07d6cdd))
- Add proposal candidate promotion
  ([`d15cdbb`](https://github.com/ogiboy/agentic-trader/commit/d15cdbb))
- Enrich proposal candidate evidence
  ([`94a3e1e`](https://github.com/ogiboy/agentic-trader/commit/94a3e1e))
- Add SEC companyfacts fundamentals
  ([`f9e4940`](https://github.com/ogiboy/agentic-trader/commit/f9e4940))
- Harden proposal and broker audit flows
  ([`ffb64ab`](https://github.com/ogiboy/agentic-trader/commit/ffb64ab))

### Bug Fixes

- Persist proposal position plans
  ([`eae6962`](https://github.com/ogiboy/agentic-trader/commit/eae6962))
- Flag unmanaged open positions
  ([`9f1909d`](https://github.com/ogiboy/agentic-trader/commit/9f1909d))
- Surface exit plan coverage
  ([`651d021`](https://github.com/ogiboy/agentic-trader/commit/651d021))
- Require proposal exit controls
  ([`e697394`](https://github.com/ogiboy/agentic-trader/commit/e697394))
- Repair missing paper exit plans
  ([`ee3a1e9`](https://github.com/ogiboy/agentic-trader/commit/ee3a1e9))
- Allow Alpaca paper readiness
  ([`c90d1cf`](https://github.com/ogiboy/agentic-trader/commit/c90d1cf))
- Use Alpaca paper account state
  ([`2024dfd`](https://github.com/ogiboy/agentic-trader/commit/2024dfd))
- Provider-check WebGUI readiness
  ([`9a0789b`](https://github.com/ogiboy/agentic-trader/commit/9a0789b))
- Keep slow dashboard polls alive
  ([`2fee91a`](https://github.com/ogiboy/agentic-trader/commit/2fee91a))
- Gate app-owned endpoints by host
  ([`259a136`](https://github.com/ogiboy/agentic-trader/commit/259a136))
- Type proposal row mapping
  ([`56d852f`](https://github.com/ogiboy/agentic-trader/commit/56d852f))
- Stabilize runtime QA flows
  ([`0b2db46`](https://github.com/ogiboy/agentic-trader/commit/0b2db46))
- Clear V1 quality gate warnings
  ([`c69dcea`](https://github.com/ogiboy/agentic-trader/commit/c69dcea))
- Fix markdown files
  ([`8f90bdd`](https://github.com/ogiboy/agentic-trader/commit/8f90bdd))
- Fix branch issues
  ([`29a016a`](https://github.com/ogiboy/agentic-trader/commit/29a016a))
- Harden V1 setup and review findings
  ([`06fc009`](https://github.com/ogiboy/agentic-trader/commit/06fc009))

### Documentation

- Configure agent skills
  ([`1baa65a`](https://github.com/ogiboy/agentic-trader/commit/1baa65a))
- Move agent notes to dev docs
  ([`fe663a0`](https://github.com/ogiboy/agentic-trader/commit/fe663a0))
- Align maintenance guidance
  ([`cd98116`](https://github.com/ogiboy/agentic-trader/commit/cd98116))
- Record V1 paper rehearsal proof
  ([`40689a0`](https://github.com/ogiboy/agentic-trader/commit/40689a0))
- Add V1 sectional review workflow
  ([`a1cd620`](https://github.com/ogiboy/agentic-trader/commit/a1cd620))
- Add docstrings to `review/v1-code-slice`
  ([`ba9fcf3`](https://github.com/ogiboy/agentic-trader/commit/ba9fcf3))

### Refactors

- Split control room helpers
  ([`4201481`](https://github.com/ogiboy/agentic-trader/commit/4201481))

### Tests

- Add V1 paper desk rehearsal
  ([`95d065e`](https://github.com/ogiboy/agentic-trader/commit/95d065e))

### Chores

- V1 readiness trading runtime
  ([#50](https://github.com/ogiboy/agentic-trader/pull/50),
  [`ac660d7`](https://github.com/ogiboy/agentic-trader/commit/ac660d7))
- Integrate reviewed V1 code slice fixes
  ([#56](https://github.com/ogiboy/agentic-trader/pull/56),
  [`da7c1bd`](https://github.com/ogiboy/agentic-trader/commit/da7c1bd))
- Docs: V1 sectional review workflow
  ([#52](https://github.com/ogiboy/agentic-trader/pull/52),
  [`61d35a7`](https://github.com/ogiboy/agentic-trader/commit/61d35a7))

## v0.11.2 (2026-05-20)

### Chores

- **deps**: Bump idna from 3.13 to 3.15 in `/sidecars/research_flow`
  ([#48](https://github.com/ogiboy/agentic-trader/pull/48),
  [`ad0ca96`](https://github.com/ogiboy/agentic-trader/commit/ad0ca96495b0475e74f0f8b9e8ec5345f28cf508),
  [`40c12b6`](https://github.com/ogiboy/agentic-trader/commit/40c12b6))

## v0.11.1 (2026-05-20)

### Chores

- **deps**: Bump idna from 3.13 to 3.15
  ([#49](https://github.com/ogiboy/agentic-trader/pull/49),
  [`abb71cc`](https://github.com/ogiboy/agentic-trader/commit/abb71cc7141f4b596e34367625182f51785f0d2a),
  [`3739565`](https://github.com/ogiboy/agentic-trader/commit/3739565))

## v0.11.0 (2026-05-17)

### Features

- Add read-only app doctor
  ([`fcb8f3b`](https://github.com/ogiboy/agentic-trader/commit/fcb8f3b))
- Add conservative app setup facade
  ([`aa5644c`](https://github.com/ogiboy/agentic-trader/commit/aa5644c))
- Add app service lifecycle facades
  ([`fe30429`](https://github.com/ogiboy/agentic-trader/commit/fe30429))
- Add scoped app update lane
  ([`2c4b50e`](https://github.com/ogiboy/agentic-trader/commit/2c4b50e))
- Add conservative app uninstall lane
  ([`b442f39`](https://github.com/ogiboy/agentic-trader/commit/b442f39))
- Add guided app up lifecycle
  ([`a447c49`](https://github.com/ogiboy/agentic-trader/commit/a447c49))
- Prefer app-owned local tools
  ([`4a26ba7`](https://github.com/ogiboy/agentic-trader/commit/4a26ba7))
- Add web proposal desk
  ([`48d5fc6`](https://github.com/ogiboy/agentic-trader/commit/48d5fc6))

### Bug Fixes

- Override Sonar axios dependency
  ([`1e7b719`](https://github.com/ogiboy/agentic-trader/commit/1e7b719))
- Apply CodeRabbit auto-fixes
  ([`ca68093`](https://github.com/ogiboy/agentic-trader/commit/ca68093),
  [`36e4f78`](https://github.com/ogiboy/agentic-trader/commit/36e4f78),
  [`e11ea84`](https://github.com/ogiboy/agentic-trader/commit/e11ea84))
- Gate runtime endpoint adoption by ownership
  ([`63edfc7`](https://github.com/ogiboy/agentic-trader/commit/63edfc7))
- Repair bootstrap script execution
  ([`49c3d1f`](https://github.com/ogiboy/agentic-trader/commit/49c3d1f))
- Harden V1 readiness QA blockers
  ([`84edb70`](https://github.com/ogiboy/agentic-trader/commit/84edb70))
- Resolve review quality nits
  ([`19dc16d`](https://github.com/ogiboy/agentic-trader/commit/19dc16d))
- Harden WebGUI operator error handling
  ([`8909bf4`](https://github.com/ogiboy/agentic-trader/commit/8909bf4))
- Satisfy WebGUI traceback Sonar rule
  ([`b90335e`](https://github.com/ogiboy/agentic-trader/commit/b90335e))

### CI

- Include WebGUI coverage in Sonar
  ([`4680a79`](https://github.com/ogiboy/agentic-trader/commit/4680a79))

### Documentation

- Add docstrings to `V1`
  ([`fd1939c`](https://github.com/ogiboy/agentic-trader/commit/fd1939c))

### Tests

- Port generated V1 readiness coverage
  ([`f15c811`](https://github.com/ogiboy/agentic-trader/commit/f15c811))

### Chores

- Advance V1 readiness setup lifecycle
  ([#40](https://github.com/ogiboy/agentic-trader/pull/40),
  [`fb6c561`](https://github.com/ogiboy/agentic-trader/commit/fb6c561))
- V1 readiness: app-owned tools, QA hardening, proposal desk
  ([#41](https://github.com/ogiboy/agentic-trader/pull/41),
  [`4638246`](https://github.com/ogiboy/agentic-trader/commit/4638246))
- Migrate Camofox helper to pnpm lock
  ([`0590ad2`](https://github.com/ogiboy/agentic-trader/commit/0590ad2))
- **deps**: Bump Ink from 5.2.1 to 7.0.3
  ([#35](https://github.com/ogiboy/agentic-trader/pull/35),
  [`294aa18`](https://github.com/ogiboy/agentic-trader/commit/294aa183d66c20a6af6a348b894a1f2372a7d17f),
  [`e2dba6c`](https://github.com/ogiboy/agentic-trader/commit/e2dba6c))
- **deps**: Bump fumadocs-mdx from 14.3.2 to 15.0.5
  ([#36](https://github.com/ogiboy/agentic-trader/pull/36),
  [`9fe1c8e`](https://github.com/ogiboy/agentic-trader/commit/9fe1c8ee371daec48ebbd85990b4897f8807d4b5),
  [`ed6c4e4`](https://github.com/ogiboy/agentic-trader/commit/ed6c4e4))
- **deps**: Bump urllib3 from 2.6.3 to 2.7.0 in `/sidecars/research_flow`
  ([#32](https://github.com/ogiboy/agentic-trader/pull/32),
  [`88c47f6`](https://github.com/ogiboy/agentic-trader/commit/88c47f6b54fb17f6934bffbc815c46cf3eaaad67),
  [`7823489`](https://github.com/ogiboy/agentic-trader/commit/7823489))
- **deps**: Bump urllib3 from 2.6.3 to 2.7.0
  ([#34](https://github.com/ogiboy/agentic-trader/pull/34),
  [`c9017a5`](https://github.com/ogiboy/agentic-trader/commit/c9017a5ec45b239e6a9c8622b59a2e81974c0994),
  [`e0af826`](https://github.com/ogiboy/agentic-trader/commit/e0af826))

## v0.10.1 (2026-05-15)

### Bug Fixes

- Sync release uv locks
  ([`5813704`](https://github.com/ogiboy/agentic-trader/commit/58137042ed3332fe19e25afab65b1403023e2a24))

## v0.10.0 (2026-05-15)

### Features

- Surface research cycle operator controls
  ([`300e4da`](https://github.com/ogiboy/agentic-trader/commit/300e4da40d6d84d8d2a8d1d5ee9a4a686bc2e73f))

### Documentation

- Plan setup lifecycle onboarding
  ([`085e86c`](https://github.com/ogiboy/agentic-trader/commit/085e86ca34b0400612e18ebc83b8728e6e7373f8))

## v0.9.12 - 2026-05-15

### Features

- feat: Implement review note generation and backtesting utilities (7139e97)
- feat: add unified agent context and model routing (b6d9401)
- feat: add historical memory retrieval and explorer (40dece7)
- feat: compare backtests against deterministic baselines (edf13ff)
- feat: persist per-stage agent traces (d7ab873)
- feat: add ink control room and observer APIs (f3584eb)
- feat: keep control room responsive during service launch (2e84996)
- feat: surface live agent progress in orchestrator UIs (7f43bfe)
- feat: route main launcher through ink control room (0cc2153)
- feat: expand ink control room workflows (d32d107)
- feat: add ink operator chat and review surfaces (164fb68)
- feat: add unified dashboard snapshot api (019a7b6)
- feat: add retrieval inspection surfaces (590540d)
- feat: add market session awareness (74544bd)
- feat: add market snapshot cache management (46762a3)
- feat: deepen market context and control room surfaces (42979d3)
- feat: enforce portfolio-level paper trading limits (39fad2b)
- feat: add memory-aware run replay surfaces (3871496)
- feat: add memory ablation backtest mode (baeea27)
- feat: add restartable background service state (a852f7e)
- feat: add restart controls to ink dashboard (befaf49)
- feat: surface manager override notes in review flows (e8c1a16)
- feat: persist manager conflicts and resolutions (3a6b288)
- feat: add hybrid vector-style memory retrieval (ae7bf33)
- feat: add downside-aware confidence calibration (df98d05)
- feat: propagate shared memory bus across agent stages (44ffddf)
- feat: persist specialist consensus before execution (aed0da4)
- feat: isolate operator chat history from trading memory (0f2fdff)
- feat: add tool-driven news context surfaces (2111bf8)
- feat: improve live agent visibility in control rooms (095684a)
- feat: add provider adapter foundation for llm runtime (bc872a1)
- feat: persist trade context for review surfaces (fb6e7b6)
- feat: enforce memory domain write policies (b68e600)
- feat: add daemon supervision metadata to operator surfaces (73f134e)
- feat: add curated operator tone and strictness presets (150169b)
- feat: enrich ink chat with live agent context (19fb185)
- feat: add broker adapter boundary and execution guardrails (2055ee7)
- feat: expose local observer api for future webui (eeeddf0)
- feat: Enhance Market Context Pack integration and dashboard visibility (4fcd333)
- feat: Enhance runtime mode management and diagnostics (520c604)
- feat: Introduce simulated execution backend and enhance broker adapters (2342941)
- feat: Enhance decision-making features with fundamental and macro assessments (b451ffd)
- feat: Implement canonical analysis snapshot and provider aggregation (02b9c7d)
- feat: update dependencies and improve test assertions (d949222)
- feat: enhance consensus assessment by excluding fallback-generated finance data from support (8b315e0)
- feat: enhance fundamental assessment structure and reporting, including evidence breakdown and bias tracking (e5654f2)
- feat: add public-source provider scaffolds for SEC EDGAR, Finnhub, FMP, and KAP with missing-field handling (6d4076f)
- feat: add initial layout and page structure for Agentic Trader Web GUI (c93eb94)
- feat: add initial configuration and components for web GUI (6f0451a)
- feat: add environment configuration for agentic-trader (bd5cad6)
- feat: add comprehensive documentation for architecture, onboarding, data execution, and project state with Fumadocs (a51e371)
- feat: add research sidecar foundation (2ff3794)
- feat: persist research snapshots (acb1636)
- feat: wire research crew sidecar contract (1f2b271)
- feat: add research crew task planning contract (6a73a7c)
- feat: migrate research sidecar to flow and uv (fd76db2)
- feat: add v1 readiness diagnostics and alpaca paper gate (499f310)
- feat: align v1 readiness operator surfaces (e91ceda)
- feat: add v1 evidence bundle command (e6cdd61)
- feat: add hardware profile readiness probe (58ff9a6)
- feat: define v1 operator workflow (5518858)
- feat: improve v1 operator finance readability (89aa5d0)
- feat: add sec company facts research evidence (b847086)
- feat: expand v1 readiness workflows and memory evidence (f9e6ef3)
- feat: expand v1 readiness tooling (3654885)
- feat: add bounded research cycle controls (fc81c57)
- feat: enrich research cycle readiness (93eca4a)
- feat: surface research tool health (0b7350b)
- feat: expose model generation probes (7a670e3)

### Fixes

- fix: harden Ollama response handling and update roadmap (3a0ce5f)
- fix: clarify live runtime status in control room (f6fd760)
- fix: stabilize control room observer mode (1da6d27)
- fix: stabilize runtime qa findings (021261e)
- fix: tighten runtime diagnostics review fixes (ede734c)
- fix: resolve sonarcloud workflow findings (d79db04)
- fix: remove invalid workflow guards (8daee58)
- fix: resolve sonarcloud quality gate findings (bf5305d)
- fix: address review hardening feedback (357d6f1)
- fix: align env docs and sonar findings (db043ac)
- fix: sync workspace release versions (1bbd987)
- fix: sync workspace release versions (#14) (6681b2e)
- fix: ensure terminal activates Python environment in current terminal (8840933)
- fix: repair release publish path and qa gate (63a43af)
- fix: harden v1 operations and operator docs (39e83f1)
- fix: harden v1 readiness and workspace setup (de7b227)
- fix: harden local security boundaries (b9b84e5)
- fix: tighten v1 observer and operator qa (bf58871)
- fix: use package manager pnpm version in workflows (7d65cf9)

### Documentation

- docs: align qa workflow with operator surfaces (62b116d)
- docs: record qa rerun findings (489a120)
- docs: refresh repo landing and guidance (b060a3b)
- docs: restore compact ascii logo (5c7723e)

### CI

- ci: add release and pages automation (3db1873)
- ci: update actions for node 24 (c8d1f98)
- ci: add SemVer branch build previews (cef2e1c)
- ci: deploy pages from V1 (7e9e0c0)
- ci: enable V1 docs deployment (#12) (4ed0924)
- ci: publish branch prerelease binaries (df740e4)
- ci: publish branch prerelease binaries (#13) (e04614a)

### Tests

- test: force operator instruction fallback path (2aaa7f0)
- test: harden runtime smoke qa (2b233c3)
- test: cover tui package manager resolver (1c8e04a)
- test: add smoke qa report artifact (37d2c0e)

### Maintenance

- chore: sync project memory docs and runtime polish (7dcb75e)
- chore: add repository hygiene templates (635eb9d)
- chore: consolidate workspace tooling (4088334)
- chore: harden repo quality automation (0e62434)
- chore: streamline sonar tooling (c31bdcd)
- chore: prepare V1 repo tooling and env contracts (157771d)
- chore: normalize env and add research crew sidecar (d7dc6e2)
- chore: complete sonar and QA readiness cleanup (6d1b85d)

### Other Changes

- Initial Agentic Trader scaffold (78b6add)
- Enhance README and ROADMAP with near-term goals; refine type hints and schemas in codebase (129f236)
- style: normalize recent test and tui formatting (191a7fc)
- Enhance TUI and Service Workflows with Improved Styling and Functionality (5d3d971)
- Prepare QA typing and operator docs (5b0fe13)
- Ignore QA report artifacts (8cceae1)
- 📝 Add docstrings to `qa-testing` (a53983a)
- Address PR review QA and docs feedback (b2121a3)
- Add SonarCloud quality gate status badge (d2b2aea)
- Enhance documentation and error handling; implement Market Context Pack and non-fatal error handling (7199c7d)
- 📝 Add docstrings to `feat/market-context-runtime-diagnostics` (d5a6b86)
- Refactor code structure for improved readability and maintainability (c2b912c)
- Improve V1 execution review visibility (8704810)
- Enhance operator UX and financial readability across CLI, Rich, and Ink interfaces (9c17f1d)
- Harden V1 QA and operator surfaces (680dda4)
- Close Ink parity gaps and add compact QA (a175c0e)
- 📝 Add docstrings to `webgui` (5096b17)
- 📝 CodeRabbit Chat: Add unit tests (2c9672c)
- Fix fallback guards and harden web GUI surfaces (2aa23e6)
- Add Turkish documentation and feedback system integration (dfc715f)
- Fix pyright typing in fundamental and schema tests (48f6e0b)
- Expand developer docs and harden QA surfaces (#9) (679c307)
- Harden web GUI QA and runtime surfaces (97b6cdf)
- Address PR review cleanup (5d903c1)
- Add local Web GUI and V1 QA hardening (#8) (ed79f15)
- Güncellemeleri ve bağımlılıkları yüklemek için ortam yapılandırmasını güncelle (56f7051)
- 📝 Add docstrings to `chore/repo-polish-ci-docs` (acb12f5)
- Polish repo tooling, docs, and quality automation (#10) (efdbfcd)
- Refresh main with V1 runtime, Web GUI, QA, and research sidecar (#15) (2bc4ba4)
- Prepare research sidecar and release QA foundation (#16) (2c12737)
- Harden local security boundaries (#18) (9bf2636)
- Harden local tooling and project metadata (1263124)
- Harden V1 local tooling and security readiness (#19) (ef87b2c)
