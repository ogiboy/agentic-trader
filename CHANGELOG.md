# Changelog

All notable changes to Agentic Trader will be recorded here.

This file is maintained by `python-semantic-release` from conventional commits on
`main`.

<!-- version list -->

## v0.16.0 - 2026-06-07

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
- feat: surface research cycle operator controls (300e4da)
- feat: add read-only app doctor (fcb8f3b)
- feat: add conservative app setup facade (aa5644c)
- feat: add app service lifecycle facades (fe30429)
- feat: add scoped app update lane (2c4b50e)
- feat: add conservative app uninstall lane (b442f39)
- feat: add guided app up lifecycle (a447c49)
- feat: prefer app-owned local tools (4a26ba7)
- feat: add web proposal desk (48d5fc6)
- feat: align v1 trading readiness (199eb30)
- feat: replay research cycle memory (2f6cb23)
- feat: refresh broker proposal truth (07d6cdd)
- feat: add proposal candidate promotion (d15cdbb)
- feat: enrich proposal candidate evidence (94a3e1e)
- feat: add SEC companyfacts fundamentals (f9e4940)
- feat: add terminal ui locale setting (87ae669)
- feat: add webgui next-intl foundation (8478960)
- feat: add TUI locale copy foundation (491af96)
- feat: add terminal ui translation facade (09080dc)
- feat: complete modularity i18n gate (2b2edb2)
- feat: complete modularity i18n gate (#103) (0561d23)

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
- fix: sync release uv locks (5813704)
- fix: override sonar axios dependency (1e7b719)
- fix: apply CodeRabbit auto-fixes (ca68093)
- fix: apply CodeRabbit auto-fixes (36e4f78)
- fix: apply CodeRabbit auto-fixes (e11ea84)
- fix: gate runtime endpoint adoption by ownership (63edfc7)
- fix: repair bootstrap script execution (49c3d1f)
- fix: harden v1 readiness qa blockers (84edb70)
- fix: resolve review quality nits (19dc16d)
- fix: harden webgui operator error handling (8909bf4)
- fix: satisfy webgui traceback sonar rule (b90335e)
- fix: persist proposal position plans (eae6962)
- fix: flag unmanaged open positions (9f1909d)
- fix: surface exit plan coverage (651d021)
- fix: require proposal exit controls (e697394)
- fix: repair missing paper exit plans (ee3a1e9)
- fix: allow alpaca paper readiness (c90d1cf)
- fix: use alpaca paper account state (2024dfd)
- fix: provider-check webgui readiness (9a0789b)
- fix: keep slow dashboard polls alive (2fee91a)
- fix: gate app-owned endpoints by host (259a136)
- fix: type proposal row mapping (56d852f)
- fix: stabilize runtime qa flows (0b2db46)
- fix: clear v1 quality gate warnings (c69dcea)
- fix: harden v1 setup and review findings (06fc009)
- fix: stabilize CI and document Next apps (864c32c)
- fix: align CI with Python 3.13 (8e788d7)
- fix: restore changelog generation (3b621e0)
- fix: enforce release changelog coverage (5beddec)
- fix: harden release changelog coverage (5467f44)
- fix: type CLI JSON payloads (0a5c896)
- fix: type TUI status payloads (97f3bab)
- fix: type research provider payloads (58f5fb4)
- fix: type LLM provider responses (3cf7fcb)
- fix: type model service payloads (e017c15)
- fix: type smoke QA flows (44f367e)
- fix: type research source payloads (491e283)
- fix: type proposal candidate evidence (78b5e93)
- fix: type runtime data payloads (f89b987)
- fix: type optional tool payloads (ff746a0)
- fix: clear strict type backlog (2b06b8b)
- fix: satisfy sonar quality gate (57b2a8c)
- fix: preserve research sidecar contract errors (c42dd07)
- fix: inspect crewai sidecar version (887826b)
- fix: close review safety findings (f85ec9e)
- fix: pin qs security override (a7a3765)
- fix: harden cli and sidecar review paths (fcff907)
- fix: address review safety findings (854a22e)
- fix: backfill stable changelog sections (ed7c0c4)
- fix: restore next lint compatibility (bf33a64)
- fix: satisfy sonar quality gate (1cd99ab)
- fix: harden locale env persistence (9990531)
- fix: apply CodeRabbit auto-fixes (abd2791)
- fix: update settings.json (e51d0a4)
- fix: restore python ci gates (25d0875)
- fix: satisfy strict terminal pyright exports (f2b5e4c)
- fix: reduce qa script sonar findings (5780817)
- fix: satisfy tui sonar reexports (d131160)
- fix: remove tui reexport-only imports (bbc6748)
- fix: update gitignore and vscode settings json (ea35c15)
- fix: sorting (5d26392)
- fix: harden camofox trace security (2cc98a7)
- fix: stabilize camofox ci gates (3757850)
- fix: clarify camofox launch setup (2627cf9)
- fix: suppress CLI callback unused-function false positives (1db2d8c)
- fix: allow changelog backfill before release tag (11ed9d2)
- fix: allow changelog backfill before release tag (f762741)
- fix: allow changelog backfill before release tag (#84) (7b34fd4)
- fix: rate-limit camofox cookie imports (d5972fc)
- fix: update versioning (3c6eb20)
- fix: fix lockfile issue (eeef472)
- fix: fix lockfile issues and versioning (e14d5bc)
- fix: fix lockfile issues and versioning (468ebd6)
- fix: fix lockfile issues and versioning (5cf9136)
- fix: align aiohttp dependabot version metadata (3250e03)
- fix: harden agent skill catalog checks (6ca9d76)
- fix: keep CodeQL on default setup (bba8b3d)
- fix: codeql workflow update (fd71b5b)
- fix: added back custom codeql-config (f9e790f)
- fix: resolve editor diagnostics and codeql alert (240ede4)
- fix: clear pr merge blockers (72ca163)
- fix: update review profile to assertive (a7b50a4)
- fix: harden security gates and redaction (d78bd9b)
- fix: enforce coderabbit conventional titles (33fdf17)
- fix: enforce CodeRabbit conventional titles (#100) (7d9cb9f)
- fix: redact sensitive CodeQL logging finding (15ffe3a)
- fix: harden CI and secret boundaries (#101) (6e959e2)
- fix: restore sonar new-code gate (0881da7)
- fix: align sonar cpd exclusions (0d79896)
- fix: allow release guard for reviewed bot commit (f09158e)
- fix: allow release guard for reviewed bot commit (#104) (bff59e5)
- fix: apply CodeRabbit auto-fixes (d964722)
- fix: stabilize pr gates and control room ui (11d3ffc)
- fix: close review findings for artifacts and copy (18e50d6)
- fix: resolve runtime review findings (8e25b78)

### Documentation

- docs: align qa workflow with operator surfaces (62b116d)
- docs: record qa rerun findings (489a120)
- docs: refresh repo landing and guidance (b060a3b)
- docs: restore compact ascii logo (5c7723e)
- docs: plan setup lifecycle onboarding (085e86c)
- docs: configure agent skills (1baa65a)
- docs: move agent notes to dev docs (fe663a0)
- docs: align maintenance guidance (cd98116)
- docs: record v1 paper rehearsal proof (40689a0)
- docs: add v1 sectional review workflow (a1cd620)
- docs: map commercial readiness blockers (d0db6b6)
- docs: avoid future-dated readiness notes (adee92e)
- docs: add modularity branch docstrings (e545419)
- docs: record modularity workflow rules (9cf8042)
- docs: split extended qa scenarios (4a97c9c)
- docs: split runtime decision log (6a5e636)
- docs: split research flow agent reference (d1bb8ed)
- docs: mark modularity i18n milestones complete (813b964)
- docs: close modularity split status (b6d4a46)

### CI

- ci: add release and pages automation (3db1873)
- ci: update actions for node 24 (c8d1f98)
- ci: add SemVer branch build previews (cef2e1c)
- ci: deploy pages from V1 (7e9e0c0)
- ci: enable V1 docs deployment (#12) (4ed0924)
- ci: publish branch prerelease binaries (df740e4)
- ci: publish branch prerelease binaries (#13) (e04614a)
- ci: include webgui coverage in sonar (4680a79)
- ci: run sonarcloud scan through pysonar (160b18c)
- ci: scope sonar coverage gate to tested surfaces (6c92c26)
- ci: apply sonar coverage exclusions in scan script (d5f84a3)

### Build

- build: constrain uv workspace lock targets (00ba9d6)

### Tests

- test: force operator instruction fallback path (2aaa7f0)
- test: harden runtime smoke qa (2b233c3)
- test: cover tui package manager resolver (1c8e04a)
- test: add smoke qa report artifact (37d2c0e)
- test: port generated V1 readiness coverage (f15c811)
- test: add v1 paper desk rehearsal (95d065e)
- test: type service and research fixtures (6339727)
- test: expose model service diagnostics (5df7357)
- test: type service runtime fakes (d1c9659)
- test: type Camofox service fakes (a90f55c)
- test: simplify Camofox helper aliases (c384b5f)
- test: type runtime helper fixtures (4cd8edc)
- test: restore decision feature summary discovery (64cecf9)
- test: stabilize setup status typing (305287a)
- test: add modularity i18n audit (7955b04)
- test: cover locale persistence through cli (f1cd39c)
- test: cover json mapping fallback (16d306c)
- test: add coderabbit review coverage (184ac2d)
- test: cover tui page render paths (8cc1b83)
- test: cover tui chat fallback branches (3ee1755)
- test: pin ui translation locale (df55628)
- test: cover docs feedback components (7a712d2)
- test: cover docs ui primitives (706b2dc)
- test: update version bump expectation (f52196b)

### Refactors

- refactor: split control room helpers (4201481)
- refactor: share json payload helpers (9c28302)
- refactor: centralize docs home copy (9851840)
- refactor: extract ink tui copy helpers (6430513)
- refactor: reuse json shape helpers (02f3dcc)
- refactor: share utc timestamp helper (c03b04a)
- refactor: share dataclass payload helpers (c59f5ad)
- refactor: centralize cli help copy (1522d10)
- refactor: centralize proposal cli copy (7e98b37)
- refactor: centralize idea cli copy (0200daf)
- refactor: centralize execution cli copy (55dc169)
- refactor: centralize service cli copy (99b5997)
- refactor: centralize report cli copy (ef6c533)
- refactor: centralize review cli copy (fa5e96e)
- refactor: centralize backtest cli copy (a03d95d)
- refactor: centralize memory cli copy (3395ec7)
- refactor: centralize finance cli copy (db0d594)
- refactor: centralize runtime cli copy (c632dc3)
- refactor: centralize environment cli copy (f085a38)
- refactor: centralize setup cli copy (1ae83f4)
- refactor: centralize service status cli copy (75dfdb1)
- refactor: centralize operator launcher cli copy (2766645)
- refactor: centralize side service command copy (476ec36)
- refactor: centralize research status cli copy (5e39c07)
- refactor: centralize research control cli copy (e92abb3)
- refactor: centralize launch plan cli copy (e3357d5)
- refactor: centralize portfolio cli copy (d4d0887)
- refactor: centralize provider status cli copy (3f7eb26)
- refactor: centralize proposal cli help copy (cf4d3f4)
- refactor: centralize proposal candidate cli copy (c6720eb)
- refactor: centralize trade proposal cli copy (babf2f2)
- refactor: centralize idea strategy cli copy (a0d06f2)
- refactor: centralize research cycle cli copy (ab7d314)
- refactor: centralize operator evidence cli copy (c68c2c4)
- refactor: centralize observer calendar cli copy (2d8030f)
- refactor: centralize news cache cli copy (79acb15)
- refactor: centralize review context cli copy (b54d2cb)
- refactor: centralize replay backtest cli copy (ed56e70)
- refactor: centralize retrieval cli copy (c184162)
- refactor: centralize service cli copy (6cf8dab)
- refactor: centralize tui status copy (0887505)
- refactor: centralize tui workflow copy (9277e37)
- refactor: centralize tui system copy (f9a756f)
- refactor: centralize tui provider copy (92f408e)
- refactor: centralize tui review copy (c06ddf5)
- refactor: centralize tui menu copy (3bd833d)
- refactor: extract tui input routing (fd5f2cf)
- refactor: extract tui dashboard defaults (7c7be76)
- refactor: extract tui line formatters (2b0c80a)
- refactor: split tui page components (1425611)
- refactor: split tui line formatters (ff2f746)
- refactor: extract terminal monitor module (ec0d9df)
- refactor: split terminal monitor sections (6459f48)
- refactor: extract terminal status renderers (f348da9)
- refactor: split terminal control room flows (023a964)
- refactor: isolate llm structured parsing (927471a)
- refactor: split trade proposal drafts (d6d7667)
- refactor: isolate sec companyfacts parsing (f3dec2f)
- refactor: isolate proposal candidate context (4c3cfca)
- refactor: isolate model service status (37bd2e1)
- refactor: split model service status assembly (1847219)
- refactor: split model service probes and state (55abc6c)
- refactor: split terminal ui text catalogs (3610bf5)
- refactor: split storage schema management (fd53f09)
- refactor: split proposal storage operations (c81eb61)
- refactor: split service storage operations (c896fd2)
- refactor: split trade journal storage (ad3544e)
- refactor: split portfolio storage operations (62d7a1a)
- refactor: split research providers (4854552)
- refactor: split broker adapters (894d317)
- refactor: split service workflow modules (dd03c65)
- refactor: split schema models (02e6984)
- refactor: split cli proposal desk (ee8f0b4)
- refactor: split cli operator readiness (e56db00)
- refactor: split webgui service modules (fb8f53c)
- refactor: group tui modules (87a80bd)
- refactor: split cli tui and copy boundaries (ab5faac)
- refactor: tighten python runtime typing (8bc4f68)
- refactor: modularize webgui control room (a906306)
- refactor: split tui monitor modules (3779252)
- refactor: split tui status renderers (f653547)
- refactor: split model service process helpers (cd4bd99)
- refactor: split model service reports (cd7f1a6)
- refactor: split cli system registration (cfb91e7)
- refactor: split cli service rendering (32b83dd)
- refactor: split webgui service state (934db4d)
- refactor: split webgui service process helpers (aa2c8a7)
- refactor: split camofox service state (ebeeea9)
- refactor: split camofox service process helpers (56e878a)
- refactor: split sec edgar evidence modules (cb6f9f4)
- refactor: split storage database helpers (b41a9df)
- refactor: split workflow persistence helpers (eb34d85)
- refactor: split workflow run context (1e089a2)
- refactor: split research sidecar backends (64af421)
- refactor: split openai compatible llm helpers (ede2c1a)
- refactor: split proposal strategy commands (06ed6f3)
- refactor: split finance proposal actions (7f360ca)
- refactor: split alpaca adapter mapping (c8442d9)
- refactor: split paper broker helpers (7e0453d)
- refactor: split market feature helpers (ea60811)
- refactor: split walk forward backtest engine (948791c)
- refactor: split research cycle payloads (ddaa16c)
- refactor: split operator cli commands (de286f9)
- refactor: split legacy ui text exports (362d0a1)
- refactor: split ui text catalog types (28d7f9b)
- refactor: split cli record payloads (080baed)
- refactor: split ink tui runtime helpers (c3589e6)
- refactor: split webgui service status builders (fc517f1)
- refactor: split run output assembly (84eb76f)
- refactor: split llm provider payload helpers (32fd23a)
- refactor: split trade context assembly (b0e1bcd)
- refactor: split provider collection helpers (0a32c46)
- refactor: split finance rendering (31972e6)
- refactor: split record rendering (2074b7d)
- refactor: split proposal action payloads (7026a9b)
- refactor: split alpaca risk checks (9602919)
- refactor: split fundamental fallback logic (3f2937f)
- refactor: split llm provider health helpers (586ac31)
- refactor: split strategy catalog data (344b8dc)
- refactor: split service state records (ca0f672)
- refactor: split public source providers (971a1d2)
- refactor: split portfolio storage modules (ca145f5)
- refactor: split one-shot workflow stages (201cf63)
- refactor: split proposal desk commands (9ff2135)
- refactor: split structured llm helpers (6325b6b)
- refactor: split proposal storage records (426d20b)
- refactor: split paper broker execution helpers (35384df)
- refactor: split runtime mode CLI commands (d8db257)
- refactor: split service CLI commands (98d105d)
- refactor: split proposal candidate validation (dcd33fd)
- refactor: split noop research backend (f4c2a1e)
- refactor: split research contract helpers (80fe609)
- refactor: split research cycle helpers (80bfffb)
- refactor: rename webgui component files (1db76f3)
- refactor: rename docs component files (f04d642)
- refactor: split app services lifecycle (387296f)
- refactor: split app setup lifecycle (834723c)
- refactor: split app update lifecycle (dc9bd2a)
- refactor: split app uninstall lifecycle (422aee2)
- refactor: split app up lifecycle (81f6d71)
- refactor: add camofox route modules (866b6d9)
- refactor: move camofox trace routes (c2a81e9)
- refactor: move camofox session routes (74fcdb4)
- refactor: move camofox tab lifecycle routes (5c0a944)
- refactor: move camofox tab navigation route (78d829c)
- refactor: move camofox tab history routes (4cef81f)
- refactor: move camofox tab content routes (3aad590)
- refactor: move camofox tab media routes (756bc9b)
- refactor: move camofox tab evaluation routes (bae4c2e)
- refactor: move camofox basic interaction routes (34827b0)
- refactor: move camofox tab typing route (e923bb5)
- refactor: move camofox tab click route (7f3f813)
- refactor: move camofox tab snapshot route (dbee832)
- refactor: move camofox legacy core routes (4e5e31b)
- refactor: move camofox legacy snapshot route (ad0def4)
- refactor: move camofox legacy action route (a2fb174)
- refactor: move camofox google serp helpers (03b4588)
- refactor: move camofox ref helpers (6e842c2)
- refactor: move camofox route safety helpers (a9e894b)
- refactor: split smoke qa modules (977249d)
- refactor: trim smoke qa interactive helpers (dc87ff0)
- refactor: split paper rehearsal flow (fc296e4)
- refactor: split research flow task planning (7615819)
- refactor: split camofox server core (e1664f4)
- refactor: complete modularity and i18n foundation (#85) (1346d99)
- refactor: split Ink dashboard launcher (29e83f7)
- refactor: translate runtime mode copy by key (91c0ea7)
- refactor: migrate TUI status copy to translator keys (348fefe)
- refactor: migrate TUI menu copy to translator keys (cd37180)
- refactor: migrate TUI workflow menus to translator keys (5ebff64)
- refactor: migrate TUI monitor helpers to translator keys (6649d50)
- refactor: migrate TUI monitor tables to translator keys (a998e32)
- refactor: complete TUI i18n migration and diagnostics cleanup (#98) (9fe356d)
- refactor: split cli registration wiring (1fbc057)
- refactor: route cli copy through translator keys (aa1f133)
- refactor: localize cli service copy access (01b799d)
- refactor: route rich tui copy through translator keys (4b81ea3)
- refactor: split camofox runtime bootstrap (fa8f6c7)
- refactor: move ink tui modules under src (c22e30c)
- refactor: improve modularity by encapsulating model service label retrieval (c2ad506)
- refactor: complete modularity and i18n cleanup (#105) (6e4e782)

### Maintenance

- chore: sync project memory docs and runtime polish (7dcb75e)
- chore: add repository hygiene templates (635eb9d)
- chore: consolidate workspace tooling (4088334)
- chore: harden repo quality automation (0e62434)
- chore: streamline sonar tooling (c31bdcd)
- chore: prepare V1 repo tooling and env contracts (157771d)
- chore: normalize env and add research crew sidecar (d7dc6e2)
- chore: complete sonar and QA readiness cleanup (6d1b85d)
- chore(release): v0.9.12 (9826805)
- chore(deps): bump urllib3 from 2.6.3 to 2.7.0 in /sidecars/research_flow (7823489)
- chore(deps): bump urllib3 from 2.6.3 to 2.7.0 (e0af826)
- chore(deps): bump fumadocs-mdx from 14.3.2 to 15.0.5 (ed6c4e4)
- chore(release): v0.10.0 (63d384d)
- chore(deps): bump ink from 5.2.1 to 7.0.3 (e2dba6c)
- chore(release): v0.10.1 (5c0f5cd)
- chore(deps): bump urllib3 from 2.6.3 to 2.7.0 (#34) (c9017a5)
- chore(deps): bump urllib3 from 2.6.3 to 2.7.0 in /sidecars/research_flow (#32) (88c47f6)
- chore(deps): bump fumadocs-mdx from 14.3.2 to 15.0.5 (#36) (9fe1c8e)
- chore(deps): bump ink from 5.2.1 to 7.0.3 (#35) (294aa18)
- chore: migrate camofox helper to pnpm lock (0590ad2)
- chore(release): v0.11.0 (d34ffad)
- chore(deps): bump idna from 3.13 to 3.15 (3739565)
- chore(deps): bump idna from 3.13 to 3.15 (#49) (abb71cc)
- chore(release): v0.11.1 (a5630bb)
- chore(deps): bump idna from 3.13 to 3.15 in /sidecars/research_flow (40c12b6)
- chore(deps): bump idna from 3.13 to 3.15 in /sidecars/research_flow (#48) (ad0ca96)
- chore(release): v0.11.2 (2379b5e)
- chore(release): v0.12.0 (8a42fa9)
- chore(deps): bump SonarSource/sonarqube-scan-action from 7.1.0 to 8.1.0 (90e02da)
- chore(deps): bump crewai[tools] in /sidecars/research_flow (082a127)
- chore: improve V1 readiness and strict QA gates (b33a07f)
- chore(release): v0.12.1 (14715a7)
- chore(release): v0.12.2 (86ed3d6)
- chore(release): v0.12.3 (5b25019)
- chore(release): v0.12.4 (fd31929)
- chore(deps): bump duckdb from 1.5.2 to 1.5.3 (0dd52d1)
- chore(deps-dev): bump coverage from 7.13.5 to 7.14.0 (2c0dfcd)
- chore(deps): bump firecrawl-py from 4.25.1 to 4.28.0 (961fed1)
- chore(deps-dev): bump ruff from 0.15.12 to 0.15.14 (9ff79a5)
- chore(release): v0.12.5 (afa299c)
- chore(deps-dev): bump vitest from 4.1.6 to 4.1.7 (b89a4a6)
- chore(deps): bump fumadocs-ui from 16.8.11 to 16.9.1 (d63c7bf)
- chore(deps-dev): bump @vitest/coverage-v8 from 4.1.6 to 4.1.7 (c6ff239)
- chore(deps): bump fumadocs-core from 16.8.11 to 16.9.1 (378cfc4)
- chore(deps): bump the next-apps group across 1 directory with 5 updates (d0a99fc)
- chore: update project version (4c065cf)
- chore(deps): bump firecrawl-py from 4.25.1 to 4.28.0 (#61) (9124ca1)
- chore: update project version (e5c7676)
- chore(deps): bump fumadocs-core from 16.8.11 to 16.9.1 (#67) (773ac19)
- chore(deps-dev): bump vitest from 4.1.6 to 4.1.7 (#65) (3b420ac)
- chore(deps): bump SonarSource/sonarqube-scan-action from 7.1.0 to 8.1.0 (#57) (564a09e)
- chore(deps): bump duckdb from 1.5.2 to 1.5.3 (#58) (54b1b15)
- chore(deps): bump crewai[tools] from 1.14.4 to 1.14.5 in /sidecars/research_flow (#59) (e561042)
- chore(deps-dev): bump @vitest/coverage-v8 from 4.1.6 to 4.1.7 (#64) (5900f36)
- chore(deps-dev): bump ruff from 0.15.12 to 0.15.14 (#60) (c35f7f2)
- chore(deps): bump fumadocs-ui from 16.8.11 to 16.9.1 (#66) (d378126)
- chore(deps-dev): bump coverage from 7.13.5 to 7.14.0 (#62) (60e62ec)
- chore(deps): bump the next-apps group across 1 directory with 5 updates (#63) (84f6316)
- chore(deps-dev): bump pysonar from 1.5.0.4793 to 1.6.0.4905 (84383ba)
- chore: refresh workspace dependencies (535f230)
- chore: bump version to 0.12.6 (35bab29)
- chore: bump version to 0.12.7 (18e8b8b)
- chore: bump version to 0.12.8 (29d6d13)
- chore: bump version to 0.12.9 (adf50d4)
- chore: bump version to 0.12.10 (d875845)
- chore: bump version to 0.12.11 (939b216)
- chore: update node workspace dependencies (60b54a9)
- chore: bump version to 0.12.12 (935bfd4)
- chore: update Python dependency locks (d6ce301)
- chore: bump version to 0.12.13 (adf54fc)
- chore: bump version to 0.12.14 (e37eb9d)
- chore: expand modularity i18n audit scope (5b12646)
- chore: bump modularity i18n version (5fca753)
- chore(release): v0.13.0 (b2fd28b)
- chore(release): v0.14.0 (9bd9e94)
- chore(deps-dev): bump pysonar from 1.5.0.4793 to 1.6.0.4905 (#75) (432919e)
- chore: sync project agent skill catalog (a799887)
- chore(deps): bump aiohttp from 3.13.5 to 3.14.0 (d411126)
- chore(deps): bump aiohttp from 3.13.5 to 3.14.0 (#87) (b40cdd0)
- chore(release): v0.14.1 (7f530bc)
- chore(deps): bump crewai[tools] in /sidecars/research_flow (40649f5)
- chore(deps): bump crewai[tools] from 1.14.5 to 1.14.6 in /sidecars/research_flow (#73) (76c8588)
- chore(release): v0.14.2 (e217cca)
- chore(deps): bump astral-sh/setup-uv from 8.1.0 to 8.2.0 (34eb043)
- chore(release): v0.14.3 (802b5fe)
- chore: sync agent skill workflow catalog (#86) (951fcdd)
- chore(release): v0.14.4 (995818b)
- chore: exclude agent catalogs from frontend tooling (56c59d0)
- chore: adopt uv workspace for research sidecar (3a31b8b)
- chore: sync advisory tooling and release metadata (dfa2879)
- chore: sync advisory tooling and release metadata (#96) (6e23432)
- chore(release): v0.14.6 (e1174cf)
- chore(deps-dev): update hatchling requirement (0b7c7fa)
- chore(deps-dev): update hatchling requirement from <2.0.0,>=1.28.0 to >=1.30.1,<2.0.0 (#89) (439e5e3)
- chore(release): v0.14.7 (37fa2f9)
- chore(release): v0.14.11 (20946a1)
- chore: bump branch version metadata (c4d3434)
- chore(release): v0.14.12 (81b7217)
- chore(release): v0.15.0 (b21a228)
- chore: bump project version to 0.16.0 (e23aada)
- chore: enhance knowledge base configuration and update path filters (36b9f3b)

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
- Advance V1 readiness setup lifecycle (#40) (fb6c561)
- 📝 Add docstrings to `V1` (fd1939c)
- V1 readiness: app-owned tools, QA hardening, proposal desk (#41) (4638246)
- Harden proposal and broker audit flows (ffb64ab)
- Docs: V1 sectional review workflow (#52) (61d35a7)
- fix some md files (8f90bdd)
- fix branch issues (29a016a)
- 📝 Add docstrings to `review/v1-code-slice` (ba9fcf3)
- Integrate reviewed V1 code slice fixes (#56) (da7c1bd)
- V1 readiness trading runtime (#50) (ac660d7)
- refactor control room localization (d219801)
- Harden release changelog coverage (e0604a9)
- Improve type safety and V1 readiness (#68) (4e89211)
- style: sort python imports and formatting (c2a2aef)
- style: modernize camofox browser server lint (4bd354e)
- style: normalize modularity audit formatting (02087d3)
- style: normalize i18n and UI formatting (de57b85)
- Refactor modularity and i18n foundation (#69) (8e9acc7)
- 📝 Add docstrings to `refactor/modularity-i18n-completion-v2` (6a8bdbd)
- 📝 CodeRabbit Chat: Add generated unit tests (000ed4f)
- Update tests/test_modularity_i18n_audit.py (1c7a7ba)

## v0.15.0 (2026-06-06)

### Features

- Complete modularity i18n gate
  ([`2b2edb2`](https://github.com/ogiboy/agentic-trader/commit/2b2edb245a42adc96e37286f062143a5e11701f1))

### Bug Fixes

- Restore sonar new-code gate
  ([`0881da7`](https://github.com/ogiboy/agentic-trader/commit/0881da7269a629e6592e89ee529b1096d741d40e))
- Align sonar cpd exclusions
  ([`0d79896`](https://github.com/ogiboy/agentic-trader/commit/0d7989642f0eb068bad5ac822a02f4471db1037e))
- Allow release guard for reviewed bot commit
  ([`f09158e`](https://github.com/ogiboy/agentic-trader/commit/f09158e5d6c62ba8d6706dbc82afbb8afb6e0905))

### Other Changes

- Update tests/test_modularity_i18n_audit.py
  ([`1c7a7ba`](https://github.com/ogiboy/agentic-trader/commit/1c7a7ba7288145d20062279f30dcfc2fded78790))

## v0.14.12 (2026-06-06)

### Bug Fixes

- Harden security gates and redaction
  ([`d78bd9b`](https://github.com/ogiboy/agentic-trader/commit/d78bd9bc06a18e0b7cc19b9ac3dfbb7e83244f8a))
- Redact sensitive CodeQL logging finding
  ([`15ffe3a`](https://github.com/ogiboy/agentic-trader/commit/15ffe3affe164d30e1f8f0f806085237cd197850))

### Tests

- Update version bump expectation
  ([`f52196b`](https://github.com/ogiboy/agentic-trader/commit/f52196b8b5b8631c80836fb5f6e4aa0892f4575a))

### Chores

- Bump branch version metadata
  ([`c4d3434`](https://github.com/ogiboy/agentic-trader/commit/c4d343425ec8cb3f12eee4d1eb0ca8d17f4fa8fc))

## v0.14.11 - 2026-06-06

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
- feat: surface research cycle operator controls (300e4da)
- feat: add read-only app doctor (fcb8f3b)
- feat: add conservative app setup facade (aa5644c)
- feat: add app service lifecycle facades (fe30429)
- feat: add scoped app update lane (2c4b50e)
- feat: add conservative app uninstall lane (b442f39)
- feat: add guided app up lifecycle (a447c49)
- feat: prefer app-owned local tools (4a26ba7)
- feat: add web proposal desk (48d5fc6)
- feat: align v1 trading readiness (199eb30)
- feat: replay research cycle memory (2f6cb23)
- feat: refresh broker proposal truth (07d6cdd)
- feat: add proposal candidate promotion (d15cdbb)
- feat: enrich proposal candidate evidence (94a3e1e)
- feat: add SEC companyfacts fundamentals (f9e4940)
- feat: add terminal ui locale setting (87ae669)
- feat: add webgui next-intl foundation (8478960)
- feat: add TUI locale copy foundation (491af96)
- feat: add terminal ui translation facade (09080dc)

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
- fix: sync release uv locks (5813704)
- fix: override sonar axios dependency (1e7b719)
- fix: apply CodeRabbit auto-fixes (ca68093)
- fix: apply CodeRabbit auto-fixes (36e4f78)
- fix: apply CodeRabbit auto-fixes (e11ea84)
- fix: gate runtime endpoint adoption by ownership (63edfc7)
- fix: repair bootstrap script execution (49c3d1f)
- fix: harden v1 readiness qa blockers (84edb70)
- fix: resolve review quality nits (19dc16d)
- fix: harden webgui operator error handling (8909bf4)
- fix: satisfy webgui traceback sonar rule (b90335e)
- fix: persist proposal position plans (eae6962)
- fix: flag unmanaged open positions (9f1909d)
- fix: surface exit plan coverage (651d021)
- fix: require proposal exit controls (e697394)
- fix: repair missing paper exit plans (ee3a1e9)
- fix: allow alpaca paper readiness (c90d1cf)
- fix: use alpaca paper account state (2024dfd)
- fix: provider-check webgui readiness (9a0789b)
- fix: keep slow dashboard polls alive (2fee91a)
- fix: gate app-owned endpoints by host (259a136)
- fix: type proposal row mapping (56d852f)
- fix: stabilize runtime qa flows (0b2db46)
- fix: clear v1 quality gate warnings (c69dcea)
- fix: harden v1 setup and review findings (06fc009)
- fix: stabilize CI and document Next apps (864c32c)
- fix: align CI with Python 3.13 (8e788d7)
- fix: restore changelog generation (3b621e0)
- fix: enforce release changelog coverage (5beddec)
- fix: harden release changelog coverage (5467f44)
- fix: type CLI JSON payloads (0a5c896)
- fix: type TUI status payloads (97f3bab)
- fix: type research provider payloads (58f5fb4)
- fix: type LLM provider responses (3cf7fcb)
- fix: type model service payloads (e017c15)
- fix: type smoke QA flows (44f367e)
- fix: type research source payloads (491e283)
- fix: type proposal candidate evidence (78b5e93)
- fix: type runtime data payloads (f89b987)
- fix: type optional tool payloads (ff746a0)
- fix: clear strict type backlog (2b06b8b)
- fix: satisfy sonar quality gate (57b2a8c)
- fix: preserve research sidecar contract errors (c42dd07)
- fix: inspect crewai sidecar version (887826b)
- fix: close review safety findings (f85ec9e)
- fix: pin qs security override (a7a3765)
- fix: harden cli and sidecar review paths (fcff907)
- fix: address review safety findings (854a22e)
- fix: backfill stable changelog sections (ed7c0c4)
- fix: restore next lint compatibility (bf33a64)
- fix: satisfy sonar quality gate (1cd99ab)
- fix: harden locale env persistence (9990531)
- fix: apply CodeRabbit auto-fixes (abd2791)
- fix: update settings.json (e51d0a4)
- fix: restore python ci gates (25d0875)
- fix: satisfy strict terminal pyright exports (f2b5e4c)
- fix: reduce qa script sonar findings (5780817)
- fix: satisfy tui sonar reexports (d131160)
- fix: remove tui reexport-only imports (bbc6748)
- fix: update gitignore and vscode settings json (ea35c15)
- fix: sorting (5d26392)
- fix: harden camofox trace security (2cc98a7)
- fix: stabilize camofox ci gates (3757850)
- fix: clarify camofox launch setup (2627cf9)
- fix: suppress CLI callback unused-function false positives (1db2d8c)
- fix: allow changelog backfill before release tag (11ed9d2)
- fix: allow changelog backfill before release tag (f762741)
- fix: allow changelog backfill before release tag (#84) (7b34fd4)
- fix: rate-limit camofox cookie imports (d5972fc)
- fix: update versioning (3c6eb20)
- fix: fix lockfile issue (eeef472)
- fix: fix lockfile issues and versioning (e14d5bc)
- fix: fix lockfile issues and versioning (468ebd6)
- fix: fix lockfile issues and versioning (5cf9136)
- fix: align aiohttp dependabot version metadata (3250e03)
- fix: harden agent skill catalog checks (6ca9d76)
- fix: keep CodeQL on default setup (bba8b3d)
- fix: codeql workflow update (fd71b5b)
- fix: added back custom codeql-config (f9e790f)
- fix: resolve editor diagnostics and codeql alert (240ede4)
- fix: clear pr merge blockers (72ca163)
- fix: update review profile to assertive (a7b50a4)
- fix: enforce coderabbit conventional titles (33fdf17)
- fix: enforce CodeRabbit conventional titles (#100) (7d9cb9f)

### Documentation

- docs: align qa workflow with operator surfaces (62b116d)
- docs: record qa rerun findings (489a120)
- docs: refresh repo landing and guidance (b060a3b)
- docs: restore compact ascii logo (5c7723e)
- docs: plan setup lifecycle onboarding (085e86c)
- docs: configure agent skills (1baa65a)
- docs: move agent notes to dev docs (fe663a0)
- docs: align maintenance guidance (cd98116)
- docs: record v1 paper rehearsal proof (40689a0)
- docs: add v1 sectional review workflow (a1cd620)
- docs: map commercial readiness blockers (d0db6b6)
- docs: avoid future-dated readiness notes (adee92e)
- docs: add modularity branch docstrings (e545419)
- docs: record modularity workflow rules (9cf8042)
- docs: split extended qa scenarios (4a97c9c)
- docs: split runtime decision log (6a5e636)
- docs: split research flow agent reference (d1bb8ed)

### CI

- ci: add release and pages automation (3db1873)
- ci: update actions for node 24 (c8d1f98)
- ci: add SemVer branch build previews (cef2e1c)
- ci: deploy pages from V1 (7e9e0c0)
- ci: enable V1 docs deployment (#12) (4ed0924)
- ci: publish branch prerelease binaries (df740e4)
- ci: publish branch prerelease binaries (#13) (e04614a)
- ci: include webgui coverage in sonar (4680a79)
- ci: run sonarcloud scan through pysonar (160b18c)

### Tests

- test: force operator instruction fallback path (2aaa7f0)
- test: harden runtime smoke qa (2b233c3)
- test: cover tui package manager resolver (1c8e04a)
- test: add smoke qa report artifact (37d2c0e)
- test: port generated V1 readiness coverage (f15c811)
- test: add v1 paper desk rehearsal (95d065e)
- test: type service and research fixtures (6339727)
- test: expose model service diagnostics (5df7357)
- test: type service runtime fakes (d1c9659)
- test: type Camofox service fakes (a90f55c)
- test: simplify Camofox helper aliases (c384b5f)
- test: type runtime helper fixtures (4cd8edc)
- test: restore decision feature summary discovery (64cecf9)
- test: stabilize setup status typing (305287a)
- test: add modularity i18n audit (7955b04)
- test: cover locale persistence through cli (f1cd39c)
- test: cover json mapping fallback (16d306c)
- test: add coderabbit review coverage (184ac2d)
- test: cover tui page render paths (8cc1b83)
- test: cover tui chat fallback branches (3ee1755)
- test: pin ui translation locale (df55628)
- test: cover docs feedback components (7a712d2)
- test: cover docs ui primitives (706b2dc)

### Refactors

- refactor: split control room helpers (4201481)
- refactor: share json payload helpers (9c28302)
- refactor: centralize docs home copy (9851840)
- refactor: extract ink tui copy helpers (6430513)
- refactor: reuse json shape helpers (02f3dcc)
- refactor: share utc timestamp helper (c03b04a)
- refactor: share dataclass payload helpers (c59f5ad)
- refactor: centralize cli help copy (1522d10)
- refactor: centralize proposal cli copy (7e98b37)
- refactor: centralize idea cli copy (0200daf)
- refactor: centralize execution cli copy (55dc169)
- refactor: centralize service cli copy (99b5997)
- refactor: centralize report cli copy (ef6c533)
- refactor: centralize review cli copy (fa5e96e)
- refactor: centralize backtest cli copy (a03d95d)
- refactor: centralize memory cli copy (3395ec7)
- refactor: centralize finance cli copy (db0d594)
- refactor: centralize runtime cli copy (c632dc3)
- refactor: centralize environment cli copy (f085a38)
- refactor: centralize setup cli copy (1ae83f4)
- refactor: centralize service status cli copy (75dfdb1)
- refactor: centralize operator launcher cli copy (2766645)
- refactor: centralize side service command copy (476ec36)
- refactor: centralize research status cli copy (5e39c07)
- refactor: centralize research control cli copy (e92abb3)
- refactor: centralize launch plan cli copy (e3357d5)
- refactor: centralize portfolio cli copy (d4d0887)
- refactor: centralize provider status cli copy (3f7eb26)
- refactor: centralize proposal cli help copy (cf4d3f4)
- refactor: centralize proposal candidate cli copy (c6720eb)
- refactor: centralize trade proposal cli copy (babf2f2)
- refactor: centralize idea strategy cli copy (a0d06f2)
- refactor: centralize research cycle cli copy (ab7d314)
- refactor: centralize operator evidence cli copy (c68c2c4)
- refactor: centralize observer calendar cli copy (2d8030f)
- refactor: centralize news cache cli copy (79acb15)
- refactor: centralize review context cli copy (b54d2cb)
- refactor: centralize replay backtest cli copy (ed56e70)
- refactor: centralize retrieval cli copy (c184162)
- refactor: centralize service cli copy (6cf8dab)
- refactor: centralize tui status copy (0887505)
- refactor: centralize tui workflow copy (9277e37)
- refactor: centralize tui system copy (f9a756f)
- refactor: centralize tui provider copy (92f408e)
- refactor: centralize tui review copy (c06ddf5)
- refactor: centralize tui menu copy (3bd833d)
- refactor: extract tui input routing (fd5f2cf)
- refactor: extract tui dashboard defaults (7c7be76)
- refactor: extract tui line formatters (2b0c80a)
- refactor: split tui page components (1425611)
- refactor: split tui line formatters (ff2f746)
- refactor: extract terminal monitor module (ec0d9df)
- refactor: split terminal monitor sections (6459f48)
- refactor: extract terminal status renderers (f348da9)
- refactor: split terminal control room flows (023a964)
- refactor: isolate llm structured parsing (927471a)
- refactor: split trade proposal drafts (d6d7667)
- refactor: isolate sec companyfacts parsing (f3dec2f)
- refactor: isolate proposal candidate context (4c3cfca)
- refactor: isolate model service status (37bd2e1)
- refactor: split model service status assembly (1847219)
- refactor: split model service probes and state (55abc6c)
- refactor: split terminal ui text catalogs (3610bf5)
- refactor: split storage schema management (fd53f09)
- refactor: split proposal storage operations (c81eb61)
- refactor: split service storage operations (c896fd2)
- refactor: split trade journal storage (ad3544e)
- refactor: split portfolio storage operations (62d7a1a)
- refactor: split research providers (4854552)
- refactor: split broker adapters (894d317)
- refactor: split service workflow modules (dd03c65)
- refactor: split schema models (02e6984)
- refactor: split cli proposal desk (ee8f0b4)
- refactor: split cli operator readiness (e56db00)
- refactor: split webgui service modules (fb8f53c)
- refactor: group tui modules (87a80bd)
- refactor: split cli tui and copy boundaries (ab5faac)
- refactor: tighten python runtime typing (8bc4f68)
- refactor: modularize webgui control room (a906306)
- refactor: split tui monitor modules (3779252)
- refactor: split tui status renderers (f653547)
- refactor: split model service process helpers (cd4bd99)
- refactor: split model service reports (cd7f1a6)
- refactor: split cli system registration (cfb91e7)
- refactor: split cli service rendering (32b83dd)
- refactor: split webgui service state (934db4d)
- refactor: split webgui service process helpers (aa2c8a7)
- refactor: split camofox service state (ebeeea9)
- refactor: split camofox service process helpers (56e878a)
- refactor: split sec edgar evidence modules (cb6f9f4)
- refactor: split storage database helpers (b41a9df)
- refactor: split workflow persistence helpers (eb34d85)
- refactor: split workflow run context (1e089a2)
- refactor: split research sidecar backends (64af421)
- refactor: split openai compatible llm helpers (ede2c1a)
- refactor: split proposal strategy commands (06ed6f3)
- refactor: split finance proposal actions (7f360ca)
- refactor: split alpaca adapter mapping (c8442d9)
- refactor: split paper broker helpers (7e0453d)
- refactor: split market feature helpers (ea60811)
- refactor: split walk forward backtest engine (948791c)
- refactor: split research cycle payloads (ddaa16c)
- refactor: split operator cli commands (de286f9)
- refactor: split legacy ui text exports (362d0a1)
- refactor: split ui text catalog types (28d7f9b)
- refactor: split cli record payloads (080baed)
- refactor: split ink tui runtime helpers (c3589e6)
- refactor: split webgui service status builders (fc517f1)
- refactor: split run output assembly (84eb76f)
- refactor: split llm provider payload helpers (32fd23a)
- refactor: split trade context assembly (b0e1bcd)
- refactor: split provider collection helpers (0a32c46)
- refactor: split finance rendering (31972e6)
- refactor: split record rendering (2074b7d)
- refactor: split proposal action payloads (7026a9b)
- refactor: split alpaca risk checks (9602919)
- refactor: split fundamental fallback logic (3f2937f)
- refactor: split llm provider health helpers (586ac31)
- refactor: split strategy catalog data (344b8dc)
- refactor: split service state records (ca0f672)
- refactor: split public source providers (971a1d2)
- refactor: split portfolio storage modules (ca145f5)
- refactor: split one-shot workflow stages (201cf63)
- refactor: split proposal desk commands (9ff2135)
- refactor: split structured llm helpers (6325b6b)
- refactor: split proposal storage records (426d20b)
- refactor: split paper broker execution helpers (35384df)
- refactor: split runtime mode CLI commands (d8db257)
- refactor: split service CLI commands (98d105d)
- refactor: split proposal candidate validation (dcd33fd)
- refactor: split noop research backend (f4c2a1e)
- refactor: split research contract helpers (80fe609)
- refactor: split research cycle helpers (80bfffb)
- refactor: rename webgui component files (1db76f3)
- refactor: rename docs component files (f04d642)
- refactor: split app services lifecycle (387296f)
- refactor: split app setup lifecycle (834723c)
- refactor: split app update lifecycle (dc9bd2a)
- refactor: split app uninstall lifecycle (422aee2)
- refactor: split app up lifecycle (81f6d71)
- refactor: add camofox route modules (866b6d9)
- refactor: move camofox trace routes (c2a81e9)
- refactor: move camofox session routes (74fcdb4)
- refactor: move camofox tab lifecycle routes (5c0a944)
- refactor: move camofox tab navigation route (78d829c)
- refactor: move camofox tab history routes (4cef81f)
- refactor: move camofox tab content routes (3aad590)
- refactor: move camofox tab media routes (756bc9b)
- refactor: move camofox tab evaluation routes (bae4c2e)
- refactor: move camofox basic interaction routes (34827b0)
- refactor: move camofox tab typing route (e923bb5)
- refactor: move camofox tab click route (7f3f813)
- refactor: move camofox tab snapshot route (dbee832)
- refactor: move camofox legacy core routes (4e5e31b)
- refactor: move camofox legacy snapshot route (ad0def4)
- refactor: move camofox legacy action route (a2fb174)
- refactor: move camofox google serp helpers (03b4588)
- refactor: move camofox ref helpers (6e842c2)
- refactor: move camofox route safety helpers (a9e894b)
- refactor: split smoke qa modules (977249d)
- refactor: trim smoke qa interactive helpers (dc87ff0)
- refactor: split paper rehearsal flow (fc296e4)
- refactor: split research flow task planning (7615819)
- refactor: split camofox server core (e1664f4)
- refactor: complete modularity and i18n foundation (#85) (1346d99)
- refactor: split Ink dashboard launcher (29e83f7)
- refactor: translate runtime mode copy by key (91c0ea7)
- refactor: migrate TUI status copy to translator keys (348fefe)
- refactor: migrate TUI menu copy to translator keys (cd37180)
- refactor: migrate TUI workflow menus to translator keys (5ebff64)
- refactor: migrate TUI monitor helpers to translator keys (6649d50)
- refactor: migrate TUI monitor tables to translator keys (a998e32)
- refactor: complete TUI i18n migration and diagnostics cleanup (#98) (9fe356d)

### Maintenance

- chore: sync project memory docs and runtime polish (7dcb75e)
- chore: add repository hygiene templates (635eb9d)
- chore: consolidate workspace tooling (4088334)
- chore: harden repo quality automation (0e62434)
- chore: streamline sonar tooling (c31bdcd)
- chore: prepare V1 repo tooling and env contracts (157771d)
- chore: normalize env and add research crew sidecar (d7dc6e2)
- chore: complete sonar and QA readiness cleanup (6d1b85d)
- chore(release): v0.9.12 (9826805)
- chore(deps): bump urllib3 from 2.6.3 to 2.7.0 in /sidecars/research_flow (7823489)
- chore(deps): bump urllib3 from 2.6.3 to 2.7.0 (e0af826)
- chore(deps): bump fumadocs-mdx from 14.3.2 to 15.0.5 (ed6c4e4)
- chore(release): v0.10.0 (63d384d)
- chore(deps): bump ink from 5.2.1 to 7.0.3 (e2dba6c)
- chore(release): v0.10.1 (5c0f5cd)
- chore(deps): bump urllib3 from 2.6.3 to 2.7.0 (#34) (c9017a5)
- chore(deps): bump urllib3 from 2.6.3 to 2.7.0 in /sidecars/research_flow (#32) (88c47f6)
- chore(deps): bump fumadocs-mdx from 14.3.2 to 15.0.5 (#36) (9fe1c8e)
- chore(deps): bump ink from 5.2.1 to 7.0.3 (#35) (294aa18)
- chore: migrate camofox helper to pnpm lock (0590ad2)
- chore(release): v0.11.0 (d34ffad)
- chore(deps): bump idna from 3.13 to 3.15 (3739565)
- chore(deps): bump idna from 3.13 to 3.15 (#49) (abb71cc)
- chore(release): v0.11.1 (a5630bb)
- chore(deps): bump idna from 3.13 to 3.15 in /sidecars/research_flow (40c12b6)
- chore(deps): bump idna from 3.13 to 3.15 in /sidecars/research_flow (#48) (ad0ca96)
- chore(release): v0.11.2 (2379b5e)
- chore(release): v0.12.0 (8a42fa9)
- chore(deps): bump SonarSource/sonarqube-scan-action from 7.1.0 to 8.1.0 (90e02da)
- chore(deps): bump crewai[tools] in /sidecars/research_flow (082a127)
- chore: improve V1 readiness and strict QA gates (b33a07f)
- chore(release): v0.12.1 (14715a7)
- chore(release): v0.12.2 (86ed3d6)
- chore(release): v0.12.3 (5b25019)
- chore(release): v0.12.4 (fd31929)
- chore(deps): bump duckdb from 1.5.2 to 1.5.3 (0dd52d1)
- chore(deps-dev): bump coverage from 7.13.5 to 7.14.0 (2c0dfcd)
- chore(deps): bump firecrawl-py from 4.25.1 to 4.28.0 (961fed1)
- chore(deps-dev): bump ruff from 0.15.12 to 0.15.14 (9ff79a5)
- chore(release): v0.12.5 (afa299c)
- chore(deps-dev): bump vitest from 4.1.6 to 4.1.7 (b89a4a6)
- chore(deps): bump fumadocs-ui from 16.8.11 to 16.9.1 (d63c7bf)
- chore(deps-dev): bump @vitest/coverage-v8 from 4.1.6 to 4.1.7 (c6ff239)
- chore(deps): bump fumadocs-core from 16.8.11 to 16.9.1 (378cfc4)
- chore(deps): bump the next-apps group across 1 directory with 5 updates (d0a99fc)
- chore: update project version (4c065cf)
- chore(deps): bump firecrawl-py from 4.25.1 to 4.28.0 (#61) (9124ca1)
- chore: update project version (e5c7676)
- chore(deps): bump fumadocs-core from 16.8.11 to 16.9.1 (#67) (773ac19)
- chore(deps-dev): bump vitest from 4.1.6 to 4.1.7 (#65) (3b420ac)
- chore(deps): bump SonarSource/sonarqube-scan-action from 7.1.0 to 8.1.0 (#57) (564a09e)
- chore(deps): bump duckdb from 1.5.2 to 1.5.3 (#58) (54b1b15)
- chore(deps): bump crewai[tools] from 1.14.4 to 1.14.5 in /sidecars/research_flow (#59) (e561042)
- chore(deps-dev): bump @vitest/coverage-v8 from 4.1.6 to 4.1.7 (#64) (5900f36)
- chore(deps-dev): bump ruff from 0.15.12 to 0.15.14 (#60) (c35f7f2)
- chore(deps): bump fumadocs-ui from 16.8.11 to 16.9.1 (#66) (d378126)
- chore(deps-dev): bump coverage from 7.13.5 to 7.14.0 (#62) (60e62ec)
- chore(deps): bump the next-apps group across 1 directory with 5 updates (#63) (84f6316)
- chore(deps-dev): bump pysonar from 1.5.0.4793 to 1.6.0.4905 (84383ba)
- chore: refresh workspace dependencies (535f230)
- chore: bump version to 0.12.6 (35bab29)
- chore: bump version to 0.12.7 (18e8b8b)
- chore: bump version to 0.12.8 (29d6d13)
- chore: bump version to 0.12.9 (adf50d4)
- chore: bump version to 0.12.10 (d875845)
- chore: bump version to 0.12.11 (939b216)
- chore: update node workspace dependencies (60b54a9)
- chore: bump version to 0.12.12 (935bfd4)
- chore: update Python dependency locks (d6ce301)
- chore: bump version to 0.12.13 (adf54fc)
- chore: bump version to 0.12.14 (e37eb9d)
- chore: expand modularity i18n audit scope (5b12646)
- chore: bump modularity i18n version (5fca753)
- chore(release): v0.13.0 (b2fd28b)
- chore(release): v0.14.0 (9bd9e94)
- chore(deps-dev): bump pysonar from 1.5.0.4793 to 1.6.0.4905 (#75) (432919e)
- chore: sync project agent skill catalog (a799887)
- chore(deps): bump aiohttp from 3.13.5 to 3.14.0 (d411126)
- chore(deps): bump aiohttp from 3.13.5 to 3.14.0 (#87) (b40cdd0)
- chore(release): v0.14.1 (7f530bc)
- chore(deps): bump crewai[tools] in /sidecars/research_flow (40649f5)
- chore(deps): bump crewai[tools] from 1.14.5 to 1.14.6 in /sidecars/research_flow (#73) (76c8588)
- chore(release): v0.14.2 (e217cca)
- chore(deps): bump astral-sh/setup-uv from 8.1.0 to 8.2.0 (34eb043)
- chore(release): v0.14.3 (802b5fe)
- chore: sync agent skill workflow catalog (#86) (951fcdd)
- chore(release): v0.14.4 (995818b)
- chore: exclude agent catalogs from frontend tooling (56c59d0)
- chore: adopt uv workspace for research sidecar (3a31b8b)
- chore: sync advisory tooling and release metadata (dfa2879)
- chore: sync advisory tooling and release metadata (#96) (6e23432)
- chore(release): v0.14.6 (e1174cf)
- chore(deps-dev): update hatchling requirement (0b7c7fa)
- chore(deps-dev): update hatchling requirement from <2.0.0,>=1.28.0 to >=1.30.1,<2.0.0 (#89) (439e5e3)
- chore(release): v0.14.7 (37fa2f9)

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
- Advance V1 readiness setup lifecycle (#40) (fb6c561)
- 📝 Add docstrings to `V1` (fd1939c)
- V1 readiness: app-owned tools, QA hardening, proposal desk (#41) (4638246)
- Harden proposal and broker audit flows (ffb64ab)
- Docs: V1 sectional review workflow (#52) (61d35a7)
- fix some md files (8f90bdd)
- fix branch issues (29a016a)
- 📝 Add docstrings to `review/v1-code-slice` (ba9fcf3)
- Integrate reviewed V1 code slice fixes (#56) (da7c1bd)
- V1 readiness trading runtime (#50) (ac660d7)
- refactor control room localization (d219801)
- Harden release changelog coverage (e0604a9)
- Improve type safety and V1 readiness (#68) (4e89211)
- style: sort python imports and formatting (c2a2aef)
- style: modernize camofox browser server lint (4bd354e)
- style: normalize modularity audit formatting (02087d3)
- style: normalize i18n and UI formatting (de57b85)
- Refactor modularity and i18n foundation (#69) (8e9acc7)
- 📝 Add docstrings to `refactor/modularity-i18n-completion-v2` (6a8bdbd)
- 📝 CodeRabbit Chat: Add generated unit tests (000ed4f)

## v0.14.7 (2026-06-05)

### Chores

- Update hatchling requirement
  ([`0b7c7fa`](https://github.com/ogiboy/agentic-trader/commit/0b7c7fa69ab6bf411af9cb369d149609a7a5c5be))

## v0.14.6 - 2026-06-05

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
- feat: surface research cycle operator controls (300e4da)
- feat: add read-only app doctor (fcb8f3b)
- feat: add conservative app setup facade (aa5644c)
- feat: add app service lifecycle facades (fe30429)
- feat: add scoped app update lane (2c4b50e)
- feat: add conservative app uninstall lane (b442f39)
- feat: add guided app up lifecycle (a447c49)
- feat: prefer app-owned local tools (4a26ba7)
- feat: add web proposal desk (48d5fc6)
- feat: align v1 trading readiness (199eb30)
- feat: replay research cycle memory (2f6cb23)
- feat: refresh broker proposal truth (07d6cdd)
- feat: add proposal candidate promotion (d15cdbb)
- feat: enrich proposal candidate evidence (94a3e1e)
- feat: add SEC companyfacts fundamentals (f9e4940)
- feat: add terminal ui locale setting (87ae669)
- feat: add webgui next-intl foundation (8478960)
- feat: add TUI locale copy foundation (491af96)
- feat: add terminal ui translation facade (09080dc)

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
- fix: sync release uv locks (5813704)
- fix: override sonar axios dependency (1e7b719)
- fix: apply CodeRabbit auto-fixes (ca68093)
- fix: apply CodeRabbit auto-fixes (36e4f78)
- fix: apply CodeRabbit auto-fixes (e11ea84)
- fix: gate runtime endpoint adoption by ownership (63edfc7)
- fix: repair bootstrap script execution (49c3d1f)
- fix: harden v1 readiness qa blockers (84edb70)
- fix: resolve review quality nits (19dc16d)
- fix: harden webgui operator error handling (8909bf4)
- fix: satisfy webgui traceback sonar rule (b90335e)
- fix: persist proposal position plans (eae6962)
- fix: flag unmanaged open positions (9f1909d)
- fix: surface exit plan coverage (651d021)
- fix: require proposal exit controls (e697394)
- fix: repair missing paper exit plans (ee3a1e9)
- fix: allow alpaca paper readiness (c90d1cf)
- fix: use alpaca paper account state (2024dfd)
- fix: provider-check webgui readiness (9a0789b)
- fix: keep slow dashboard polls alive (2fee91a)
- fix: gate app-owned endpoints by host (259a136)
- fix: type proposal row mapping (56d852f)
- fix: stabilize runtime qa flows (0b2db46)
- fix: clear v1 quality gate warnings (c69dcea)
- fix: harden v1 setup and review findings (06fc009)
- fix: stabilize CI and document Next apps (864c32c)
- fix: align CI with Python 3.13 (8e788d7)
- fix: restore changelog generation (3b621e0)
- fix: enforce release changelog coverage (5beddec)
- fix: harden release changelog coverage (5467f44)
- fix: type CLI JSON payloads (0a5c896)
- fix: type TUI status payloads (97f3bab)
- fix: type research provider payloads (58f5fb4)
- fix: type LLM provider responses (3cf7fcb)
- fix: type model service payloads (e017c15)
- fix: type smoke QA flows (44f367e)
- fix: type research source payloads (491e283)
- fix: type proposal candidate evidence (78b5e93)
- fix: type runtime data payloads (f89b987)
- fix: type optional tool payloads (ff746a0)
- fix: clear strict type backlog (2b06b8b)
- fix: satisfy sonar quality gate (57b2a8c)
- fix: preserve research sidecar contract errors (c42dd07)
- fix: inspect crewai sidecar version (887826b)
- fix: close review safety findings (f85ec9e)
- fix: pin qs security override (a7a3765)
- fix: harden cli and sidecar review paths (fcff907)
- fix: address review safety findings (854a22e)
- fix: backfill stable changelog sections (ed7c0c4)
- fix: restore next lint compatibility (bf33a64)
- fix: satisfy sonar quality gate (1cd99ab)
- fix: harden locale env persistence (9990531)
- fix: apply CodeRabbit auto-fixes (abd2791)
- fix: update settings.json (e51d0a4)
- fix: restore python ci gates (25d0875)
- fix: satisfy strict terminal pyright exports (f2b5e4c)
- fix: reduce qa script sonar findings (5780817)
- fix: satisfy tui sonar reexports (d131160)
- fix: remove tui reexport-only imports (bbc6748)
- fix: update gitignore and vscode settings json (ea35c15)
- fix: sorting (5d26392)
- fix: harden camofox trace security (2cc98a7)
- fix: stabilize camofox ci gates (3757850)
- fix: clarify camofox launch setup (2627cf9)
- fix: suppress CLI callback unused-function false positives (1db2d8c)
- fix: allow changelog backfill before release tag (11ed9d2)
- fix: allow changelog backfill before release tag (f762741)
- fix: allow changelog backfill before release tag (#84) (7b34fd4)
- fix: rate-limit camofox cookie imports (d5972fc)
- fix: update versioning (3c6eb20)
- fix: fix lockfile issue (eeef472)
- fix: fix lockfile issues and versioning (e14d5bc)
- fix: fix lockfile issues and versioning (468ebd6)
- fix: fix lockfile issues and versioning (5cf9136)
- fix: align aiohttp dependabot version metadata (3250e03)
- fix: harden agent skill catalog checks (6ca9d76)
- fix: keep CodeQL on default setup (bba8b3d)

### Documentation

- docs: align qa workflow with operator surfaces (62b116d)
- docs: record qa rerun findings (489a120)
- docs: refresh repo landing and guidance (b060a3b)
- docs: restore compact ascii logo (5c7723e)
- docs: plan setup lifecycle onboarding (085e86c)
- docs: configure agent skills (1baa65a)
- docs: move agent notes to dev docs (fe663a0)
- docs: align maintenance guidance (cd98116)
- docs: record v1 paper rehearsal proof (40689a0)
- docs: add v1 sectional review workflow (a1cd620)
- docs: map commercial readiness blockers (d0db6b6)
- docs: avoid future-dated readiness notes (adee92e)
- docs: add modularity branch docstrings (e545419)
- docs: record modularity workflow rules (9cf8042)
- docs: split extended qa scenarios (4a97c9c)
- docs: split runtime decision log (6a5e636)
- docs: split research flow agent reference (d1bb8ed)

### CI

- ci: add release and pages automation (3db1873)
- ci: update actions for node 24 (c8d1f98)
- ci: add SemVer branch build previews (cef2e1c)
- ci: deploy pages from V1 (7e9e0c0)
- ci: enable V1 docs deployment (#12) (4ed0924)
- ci: publish branch prerelease binaries (df740e4)
- ci: publish branch prerelease binaries (#13) (e04614a)
- ci: include webgui coverage in sonar (4680a79)
- ci: run sonarcloud scan through pysonar (160b18c)

### Tests

- test: force operator instruction fallback path (2aaa7f0)
- test: harden runtime smoke qa (2b233c3)
- test: cover tui package manager resolver (1c8e04a)
- test: add smoke qa report artifact (37d2c0e)
- test: port generated V1 readiness coverage (f15c811)
- test: add v1 paper desk rehearsal (95d065e)
- test: type service and research fixtures (6339727)
- test: expose model service diagnostics (5df7357)
- test: type service runtime fakes (d1c9659)
- test: type Camofox service fakes (a90f55c)
- test: simplify Camofox helper aliases (c384b5f)
- test: type runtime helper fixtures (4cd8edc)
- test: restore decision feature summary discovery (64cecf9)
- test: stabilize setup status typing (305287a)
- test: add modularity i18n audit (7955b04)
- test: cover locale persistence through cli (f1cd39c)
- test: cover json mapping fallback (16d306c)
- test: add coderabbit review coverage (184ac2d)
- test: cover tui page render paths (8cc1b83)
- test: cover tui chat fallback branches (3ee1755)
- test: pin ui translation locale (df55628)
- test: cover docs feedback components (7a712d2)
- test: cover docs ui primitives (706b2dc)

### Refactors

- refactor: split control room helpers (4201481)
- refactor: share json payload helpers (9c28302)
- refactor: centralize docs home copy (9851840)
- refactor: extract ink tui copy helpers (6430513)
- refactor: reuse json shape helpers (02f3dcc)
- refactor: share utc timestamp helper (c03b04a)
- refactor: share dataclass payload helpers (c59f5ad)
- refactor: centralize cli help copy (1522d10)
- refactor: centralize proposal cli copy (7e98b37)
- refactor: centralize idea cli copy (0200daf)
- refactor: centralize execution cli copy (55dc169)
- refactor: centralize service cli copy (99b5997)
- refactor: centralize report cli copy (ef6c533)
- refactor: centralize review cli copy (fa5e96e)
- refactor: centralize backtest cli copy (a03d95d)
- refactor: centralize memory cli copy (3395ec7)
- refactor: centralize finance cli copy (db0d594)
- refactor: centralize runtime cli copy (c632dc3)
- refactor: centralize environment cli copy (f085a38)
- refactor: centralize setup cli copy (1ae83f4)
- refactor: centralize service status cli copy (75dfdb1)
- refactor: centralize operator launcher cli copy (2766645)
- refactor: centralize side service command copy (476ec36)
- refactor: centralize research status cli copy (5e39c07)
- refactor: centralize research control cli copy (e92abb3)
- refactor: centralize launch plan cli copy (e3357d5)
- refactor: centralize portfolio cli copy (d4d0887)
- refactor: centralize provider status cli copy (3f7eb26)
- refactor: centralize proposal cli help copy (cf4d3f4)
- refactor: centralize proposal candidate cli copy (c6720eb)
- refactor: centralize trade proposal cli copy (babf2f2)
- refactor: centralize idea strategy cli copy (a0d06f2)
- refactor: centralize research cycle cli copy (ab7d314)
- refactor: centralize operator evidence cli copy (c68c2c4)
- refactor: centralize observer calendar cli copy (2d8030f)
- refactor: centralize news cache cli copy (79acb15)
- refactor: centralize review context cli copy (b54d2cb)
- refactor: centralize replay backtest cli copy (ed56e70)
- refactor: centralize retrieval cli copy (c184162)
- refactor: centralize service cli copy (6cf8dab)
- refactor: centralize tui status copy (0887505)
- refactor: centralize tui workflow copy (9277e37)
- refactor: centralize tui system copy (f9a756f)
- refactor: centralize tui provider copy (92f408e)
- refactor: centralize tui review copy (c06ddf5)
- refactor: centralize tui menu copy (3bd833d)
- refactor: extract tui input routing (fd5f2cf)
- refactor: extract tui dashboard defaults (7c7be76)
- refactor: extract tui line formatters (2b0c80a)
- refactor: split tui page components (1425611)
- refactor: split tui line formatters (ff2f746)
- refactor: extract terminal monitor module (ec0d9df)
- refactor: split terminal monitor sections (6459f48)
- refactor: extract terminal status renderers (f348da9)
- refactor: split terminal control room flows (023a964)
- refactor: isolate llm structured parsing (927471a)
- refactor: split trade proposal drafts (d6d7667)
- refactor: isolate sec companyfacts parsing (f3dec2f)
- refactor: isolate proposal candidate context (4c3cfca)
- refactor: isolate model service status (37bd2e1)
- refactor: split model service status assembly (1847219)
- refactor: split model service probes and state (55abc6c)
- refactor: split terminal ui text catalogs (3610bf5)
- refactor: split storage schema management (fd53f09)
- refactor: split proposal storage operations (c81eb61)
- refactor: split service storage operations (c896fd2)
- refactor: split trade journal storage (ad3544e)
- refactor: split portfolio storage operations (62d7a1a)
- refactor: split research providers (4854552)
- refactor: split broker adapters (894d317)
- refactor: split service workflow modules (dd03c65)
- refactor: split schema models (02e6984)
- refactor: split cli proposal desk (ee8f0b4)
- refactor: split cli operator readiness (e56db00)
- refactor: split webgui service modules (fb8f53c)
- refactor: group tui modules (87a80bd)
- refactor: split cli tui and copy boundaries (ab5faac)
- refactor: tighten python runtime typing (8bc4f68)
- refactor: modularize webgui control room (a906306)
- refactor: split tui monitor modules (3779252)
- refactor: split tui status renderers (f653547)
- refactor: split model service process helpers (cd4bd99)
- refactor: split model service reports (cd7f1a6)
- refactor: split cli system registration (cfb91e7)
- refactor: split cli service rendering (32b83dd)
- refactor: split webgui service state (934db4d)
- refactor: split webgui service process helpers (aa2c8a7)
- refactor: split camofox service state (ebeeea9)
- refactor: split camofox service process helpers (56e878a)
- refactor: split sec edgar evidence modules (cb6f9f4)
- refactor: split storage database helpers (b41a9df)
- refactor: split workflow persistence helpers (eb34d85)
- refactor: split workflow run context (1e089a2)
- refactor: split research sidecar backends (64af421)
- refactor: split openai compatible llm helpers (ede2c1a)
- refactor: split proposal strategy commands (06ed6f3)
- refactor: split finance proposal actions (7f360ca)
- refactor: split alpaca adapter mapping (c8442d9)
- refactor: split paper broker helpers (7e0453d)
- refactor: split market feature helpers (ea60811)
- refactor: split walk forward backtest engine (948791c)
- refactor: split research cycle payloads (ddaa16c)
- refactor: split operator cli commands (de286f9)
- refactor: split legacy ui text exports (362d0a1)
- refactor: split ui text catalog types (28d7f9b)
- refactor: split cli record payloads (080baed)
- refactor: split ink tui runtime helpers (c3589e6)
- refactor: split webgui service status builders (fc517f1)
- refactor: split run output assembly (84eb76f)
- refactor: split llm provider payload helpers (32fd23a)
- refactor: split trade context assembly (b0e1bcd)
- refactor: split provider collection helpers (0a32c46)
- refactor: split finance rendering (31972e6)
- refactor: split record rendering (2074b7d)
- refactor: split proposal action payloads (7026a9b)
- refactor: split alpaca risk checks (9602919)
- refactor: split fundamental fallback logic (3f2937f)
- refactor: split llm provider health helpers (586ac31)
- refactor: split strategy catalog data (344b8dc)
- refactor: split service state records (ca0f672)
- refactor: split public source providers (971a1d2)
- refactor: split portfolio storage modules (ca145f5)
- refactor: split one-shot workflow stages (201cf63)
- refactor: split proposal desk commands (9ff2135)
- refactor: split structured llm helpers (6325b6b)
- refactor: split proposal storage records (426d20b)
- refactor: split paper broker execution helpers (35384df)
- refactor: split runtime mode CLI commands (d8db257)
- refactor: split service CLI commands (98d105d)
- refactor: split proposal candidate validation (dcd33fd)
- refactor: split noop research backend (f4c2a1e)
- refactor: split research contract helpers (80fe609)
- refactor: split research cycle helpers (80bfffb)
- refactor: rename webgui component files (1db76f3)
- refactor: rename docs component files (f04d642)
- refactor: split app services lifecycle (387296f)
- refactor: split app setup lifecycle (834723c)
- refactor: split app update lifecycle (dc9bd2a)
- refactor: split app uninstall lifecycle (422aee2)
- refactor: split app up lifecycle (81f6d71)
- refactor: add camofox route modules (866b6d9)
- refactor: move camofox trace routes (c2a81e9)
- refactor: move camofox session routes (74fcdb4)
- refactor: move camofox tab lifecycle routes (5c0a944)
- refactor: move camofox tab navigation route (78d829c)
- refactor: move camofox tab history routes (4cef81f)
- refactor: move camofox tab content routes (3aad590)
- refactor: move camofox tab media routes (756bc9b)
- refactor: move camofox tab evaluation routes (bae4c2e)
- refactor: move camofox basic interaction routes (34827b0)
- refactor: move camofox tab typing route (e923bb5)
- refactor: move camofox tab click route (7f3f813)
- refactor: move camofox tab snapshot route (dbee832)
- refactor: move camofox legacy core routes (4e5e31b)
- refactor: move camofox legacy snapshot route (ad0def4)
- refactor: move camofox legacy action route (a2fb174)
- refactor: move camofox google serp helpers (03b4588)
- refactor: move camofox ref helpers (6e842c2)
- refactor: move camofox route safety helpers (a9e894b)
- refactor: split smoke qa modules (977249d)
- refactor: trim smoke qa interactive helpers (dc87ff0)
- refactor: split paper rehearsal flow (fc296e4)
- refactor: split research flow task planning (7615819)
- refactor: split camofox server core (e1664f4)
- refactor: complete modularity and i18n foundation (#85) (1346d99)
- refactor: split Ink dashboard launcher (29e83f7)
- refactor: translate runtime mode copy by key (91c0ea7)

### Maintenance

- chore: sync project memory docs and runtime polish (7dcb75e)
- chore: add repository hygiene templates (635eb9d)
- chore: consolidate workspace tooling (4088334)
- chore: harden repo quality automation (0e62434)
- chore: streamline sonar tooling (c31bdcd)
- chore: prepare V1 repo tooling and env contracts (157771d)
- chore: normalize env and add research crew sidecar (d7dc6e2)
- chore: complete sonar and QA readiness cleanup (6d1b85d)
- chore(release): v0.9.12 (9826805)
- chore(deps): bump urllib3 from 2.6.3 to 2.7.0 in /sidecars/research_flow (7823489)
- chore(deps): bump urllib3 from 2.6.3 to 2.7.0 (e0af826)
- chore(deps): bump fumadocs-mdx from 14.3.2 to 15.0.5 (ed6c4e4)
- chore(release): v0.10.0 (63d384d)
- chore(deps): bump ink from 5.2.1 to 7.0.3 (e2dba6c)
- chore(release): v0.10.1 (5c0f5cd)
- chore(deps): bump urllib3 from 2.6.3 to 2.7.0 (#34) (c9017a5)
- chore(deps): bump urllib3 from 2.6.3 to 2.7.0 in /sidecars/research_flow (#32) (88c47f6)
- chore(deps): bump fumadocs-mdx from 14.3.2 to 15.0.5 (#36) (9fe1c8e)
- chore(deps): bump ink from 5.2.1 to 7.0.3 (#35) (294aa18)
- chore: migrate camofox helper to pnpm lock (0590ad2)
- chore(release): v0.11.0 (d34ffad)
- chore(deps): bump idna from 3.13 to 3.15 (3739565)
- chore(deps): bump idna from 3.13 to 3.15 (#49) (abb71cc)
- chore(release): v0.11.1 (a5630bb)
- chore(deps): bump idna from 3.13 to 3.15 in /sidecars/research_flow (40c12b6)
- chore(deps): bump idna from 3.13 to 3.15 in /sidecars/research_flow (#48) (ad0ca96)
- chore(release): v0.11.2 (2379b5e)
- chore(release): v0.12.0 (8a42fa9)
- chore(deps): bump SonarSource/sonarqube-scan-action from 7.1.0 to 8.1.0 (90e02da)
- chore(deps): bump crewai[tools] in /sidecars/research_flow (082a127)
- chore: improve V1 readiness and strict QA gates (b33a07f)
- chore(release): v0.12.1 (14715a7)
- chore(release): v0.12.2 (86ed3d6)
- chore(release): v0.12.3 (5b25019)
- chore(release): v0.12.4 (fd31929)
- chore(deps): bump duckdb from 1.5.2 to 1.5.3 (0dd52d1)
- chore(deps-dev): bump coverage from 7.13.5 to 7.14.0 (2c0dfcd)
- chore(deps): bump firecrawl-py from 4.25.1 to 4.28.0 (961fed1)
- chore(deps-dev): bump ruff from 0.15.12 to 0.15.14 (9ff79a5)
- chore(release): v0.12.5 (afa299c)
- chore(deps-dev): bump vitest from 4.1.6 to 4.1.7 (b89a4a6)
- chore(deps): bump fumadocs-ui from 16.8.11 to 16.9.1 (d63c7bf)
- chore(deps-dev): bump @vitest/coverage-v8 from 4.1.6 to 4.1.7 (c6ff239)
- chore(deps): bump fumadocs-core from 16.8.11 to 16.9.1 (378cfc4)
- chore(deps): bump the next-apps group across 1 directory with 5 updates (d0a99fc)
- chore: update project version (4c065cf)
- chore(deps): bump firecrawl-py from 4.25.1 to 4.28.0 (#61) (9124ca1)
- chore: update project version (e5c7676)
- chore(deps): bump fumadocs-core from 16.8.11 to 16.9.1 (#67) (773ac19)
- chore(deps-dev): bump vitest from 4.1.6 to 4.1.7 (#65) (3b420ac)
- chore(deps): bump SonarSource/sonarqube-scan-action from 7.1.0 to 8.1.0 (#57) (564a09e)
- chore(deps): bump duckdb from 1.5.2 to 1.5.3 (#58) (54b1b15)
- chore(deps): bump crewai[tools] from 1.14.4 to 1.14.5 in /sidecars/research_flow (#59) (e561042)
- chore(deps-dev): bump @vitest/coverage-v8 from 4.1.6 to 4.1.7 (#64) (5900f36)
- chore(deps-dev): bump ruff from 0.15.12 to 0.15.14 (#60) (c35f7f2)
- chore(deps): bump fumadocs-ui from 16.8.11 to 16.9.1 (#66) (d378126)
- chore(deps-dev): bump coverage from 7.13.5 to 7.14.0 (#62) (60e62ec)
- chore(deps): bump the next-apps group across 1 directory with 5 updates (#63) (84f6316)
- chore(deps-dev): bump pysonar from 1.5.0.4793 to 1.6.0.4905 (84383ba)
- chore: refresh workspace dependencies (535f230)
- chore: bump version to 0.12.6 (35bab29)
- chore: bump version to 0.12.7 (18e8b8b)
- chore: bump version to 0.12.8 (29d6d13)
- chore: bump version to 0.12.9 (adf50d4)
- chore: bump version to 0.12.10 (d875845)
- chore: bump version to 0.12.11 (939b216)
- chore: update node workspace dependencies (60b54a9)
- chore: bump version to 0.12.12 (935bfd4)
- chore: update Python dependency locks (d6ce301)
- chore: bump version to 0.12.13 (adf54fc)
- chore: bump version to 0.12.14 (e37eb9d)
- chore: expand modularity i18n audit scope (5b12646)
- chore: bump modularity i18n version (5fca753)
- chore(release): v0.13.0 (b2fd28b)
- chore(release): v0.14.0 (9bd9e94)
- chore(deps-dev): bump pysonar from 1.5.0.4793 to 1.6.0.4905 (#75) (432919e)
- chore: sync project agent skill catalog (a799887)
- chore(deps): bump aiohttp from 3.13.5 to 3.14.0 (d411126)
- chore(deps): bump aiohttp from 3.13.5 to 3.14.0 (#87) (b40cdd0)
- chore(release): v0.14.1 (7f530bc)
- chore(deps): bump crewai[tools] in /sidecars/research_flow (40649f5)
- chore(deps): bump crewai[tools] from 1.14.5 to 1.14.6 in /sidecars/research_flow (#73) (76c8588)
- chore(release): v0.14.2 (e217cca)
- chore(deps): bump astral-sh/setup-uv from 8.1.0 to 8.2.0 (34eb043)
- chore(release): v0.14.3 (802b5fe)
- chore: sync agent skill workflow catalog (#86) (951fcdd)
- chore(release): v0.14.4 (995818b)
- chore: exclude agent catalogs from frontend tooling (56c59d0)
- chore: adopt uv workspace for research sidecar (3a31b8b)
- chore: sync advisory tooling and release metadata (dfa2879)
- chore: sync advisory tooling and release metadata (#96) (6e23432)

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
- Advance V1 readiness setup lifecycle (#40) (fb6c561)
- 📝 Add docstrings to `V1` (fd1939c)
- V1 readiness: app-owned tools, QA hardening, proposal desk (#41) (4638246)
- Harden proposal and broker audit flows (ffb64ab)
- Docs: V1 sectional review workflow (#52) (61d35a7)
- fix some md files (8f90bdd)
- fix branch issues (29a016a)
- 📝 Add docstrings to `review/v1-code-slice` (ba9fcf3)
- Integrate reviewed V1 code slice fixes (#56) (da7c1bd)
- V1 readiness trading runtime (#50) (ac660d7)
- refactor control room localization (d219801)
- Harden release changelog coverage (e0604a9)
- Improve type safety and V1 readiness (#68) (4e89211)
- style: sort python imports and formatting (c2a2aef)
- style: modernize camofox browser server lint (4bd354e)
- style: normalize modularity audit formatting (02087d3)
- style: normalize i18n and UI formatting (de57b85)
- Refactor modularity and i18n foundation (#69) (8e9acc7)

## v0.14.4 (2026-06-05)

### Bug Fixes

- Harden agent skill catalog checks
  ([`6ca9d76`](https://github.com/ogiboy/agentic-trader/commit/6ca9d764f37be46673a503d93fd0b7dab6d95ed8))
- Keep CodeQL on default setup
  ([`bba8b3d`](https://github.com/ogiboy/agentic-trader/commit/bba8b3d4bfaf73db86c20f6e5ecb8b08d5968efa))

### Chores

- Sync project agent skill catalog
  ([`a799887`](https://github.com/ogiboy/agentic-trader/commit/a799887955c229add3310ab8a008c7131e4bfb1d))

## v0.14.3 (2026-06-05)

### Chores

- **deps**: Bump astral-sh/setup-uv from 8.1.0 to 8.2.0
  ([`34eb043`](https://github.com/ogiboy/agentic-trader/commit/34eb0439f2a540295fd527292cef98a1243a0297))

## v0.14.2 (2026-06-04)

### Chores

- Bump crewai[tools] in /sidecars/research_flow
  ([`40649f5`](https://github.com/ogiboy/agentic-trader/commit/40649f5320548c8bc24aed77b08e6a5399c6661d))

## v0.14.1 (2026-06-04)

### Bug Fixes

- Update versioning
  ([`3c6eb20`](https://github.com/ogiboy/agentic-trader/commit/3c6eb2009b61e4b909cb481ef11ccd8b72ee86d6))
- Fix lockfile issue
  ([`eeef472`](https://github.com/ogiboy/agentic-trader/commit/eeef4728de2844f57af7f0b75c6df34ae1632673))
- Fix lockfile issues and versioning
  ([`e14d5bc`](https://github.com/ogiboy/agentic-trader/commit/e14d5bcca59fe7d5ef9c5ff76f1d1a9d2f60f57d))
- Fix lockfile issues and versioning
  ([`468ebd6`](https://github.com/ogiboy/agentic-trader/commit/468ebd61b8d18ee646ea4100cf9cbbd4da5d4644))
- Fix lockfile issues and versioning
  ([`5cf9136`](https://github.com/ogiboy/agentic-trader/commit/5cf9136a95b452051801d4d960d177f4f06579f7))
- Align aiohttp dependabot version metadata
  ([`3250e03`](https://github.com/ogiboy/agentic-trader/commit/3250e03f586b465516e708629827bef9d87aa0b1))

### Chores

- Bump pysonar from 1.5.0.4793 to 1.6.0.4905
  ([`84383ba`](https://github.com/ogiboy/agentic-trader/commit/84383ba7a44a6b38ea42d0be2da62a7a3f7e0631))
- Bump aiohttp from 3.13.5 to 3.14.0
  ([`d411126`](https://github.com/ogiboy/agentic-trader/commit/d411126c6ffa5975959d4416c0a674e65c338bdb))

## v0.14.0 (2026-06-03)

### Features

- Add webgui next-intl foundation
  ([`8478960`](https://github.com/ogiboy/agentic-trader/commit/847896028306b9fcfd0ec1f060306cfd746f5ece))
- Add TUI locale copy foundation
  ([`491af96`](https://github.com/ogiboy/agentic-trader/commit/491af96290a43b19c632ee5e4b8cd5b321bfad96))
- Add terminal ui translation facade
  ([`09080dc`](https://github.com/ogiboy/agentic-trader/commit/09080dcab14d55a9361feeb821ef3513fe49da03))

### Bug Fixes

- Allow changelog backfill before release tag
  ([`11ed9d2`](https://github.com/ogiboy/agentic-trader/commit/11ed9d21cc63255f3460569dca990487413a4487))
- Rate-limit camofox cookie imports
  ([`d5972fc`](https://github.com/ogiboy/agentic-trader/commit/d5972fc5c1e18bac654796ecc2cb745f3b77c2d0))

### Documentation

- Split extended qa scenarios
  ([`4a97c9c`](https://github.com/ogiboy/agentic-trader/commit/4a97c9c96da90280bd7d115fe3ec412bafb3515d))
- Split runtime decision log
  ([`6a5e636`](https://github.com/ogiboy/agentic-trader/commit/6a5e636d279e6a3beac0edafe8139462bfab048c))
- Split research flow agent reference
  ([`d1bb8ed`](https://github.com/ogiboy/agentic-trader/commit/d1bb8edabcbda4abe682fe1b82e4acf22039631e))

### Tests

- Pin ui translation locale
  ([`df55628`](https://github.com/ogiboy/agentic-trader/commit/df5562835ca9421ebf1d60fed99979820d0b6bf8))
- Cover docs feedback components
  ([`7a712d2`](https://github.com/ogiboy/agentic-trader/commit/7a712d2665e25cb89786f00ddc2b6e804b719916))
- Cover docs ui primitives
  ([`706b2dc`](https://github.com/ogiboy/agentic-trader/commit/706b2dc9e3443435e11a5bce8685340db0106cee))

### Refactors

- Rename webgui component files
  ([`1db76f3`](https://github.com/ogiboy/agentic-trader/commit/1db76f39bd04e68fb72f0bb0202700f29d29c5b3))
- Rename docs component files
  ([`f04d642`](https://github.com/ogiboy/agentic-trader/commit/f04d64291bf0187ce101fdc7c5ec73197133f997))
- Split app services lifecycle
  ([`387296f`](https://github.com/ogiboy/agentic-trader/commit/387296f1ec2f0c0f62541882de92732969c5c2fd))
- Split app setup lifecycle
  ([`834723c`](https://github.com/ogiboy/agentic-trader/commit/834723cf40b0cc56173b7c47b0a5cebb52df7849))
- Split app update lifecycle
  ([`dc9bd2a`](https://github.com/ogiboy/agentic-trader/commit/dc9bd2a0e3261fdc27e99ef31ba9053465e5d607))
- Split app uninstall lifecycle
  ([`422aee2`](https://github.com/ogiboy/agentic-trader/commit/422aee2c7b8a84fba6ee1b298f29556b7a9b4b04))
- Split app up lifecycle
  ([`81f6d71`](https://github.com/ogiboy/agentic-trader/commit/81f6d7184f872cb57903a4a11d8d7ce36fb15af8))
- Add camofox route modules
  ([`866b6d9`](https://github.com/ogiboy/agentic-trader/commit/866b6d9ee337ca8790b8cb0fd4698f9a18248bc6))
- Move camofox trace routes
  ([`c2a81e9`](https://github.com/ogiboy/agentic-trader/commit/c2a81e92f2013d14a824d560c2c4e84479c37d38))
- Move camofox session routes
  ([`74fcdb4`](https://github.com/ogiboy/agentic-trader/commit/74fcdb471f888ad931f8508f77993eecc22a06d5))
- Move camofox tab lifecycle routes
  ([`5c0a944`](https://github.com/ogiboy/agentic-trader/commit/5c0a944a9e545a889f3bf4697e26852e324ad0d4))
- Move camofox tab navigation route
  ([`78d829c`](https://github.com/ogiboy/agentic-trader/commit/78d829c236d12ae926e0843120dcc56560922f22))
- Move camofox tab history routes
  ([`4cef81f`](https://github.com/ogiboy/agentic-trader/commit/4cef81fabbad47665a13f6f2315d0c8c2b8faa1c))
- Move camofox tab content routes
  ([`3aad590`](https://github.com/ogiboy/agentic-trader/commit/3aad590698ac0e5a904124d448c696a4289591ab))
- Move camofox tab media routes
  ([`756bc9b`](https://github.com/ogiboy/agentic-trader/commit/756bc9b30ebbcd887ab28ba377eab85139eb5871))
- Move camofox tab evaluation routes
  ([`bae4c2e`](https://github.com/ogiboy/agentic-trader/commit/bae4c2e1d1da6c411ed3f9833edd61dec53873ea))
- Move camofox basic interaction routes
  ([`34827b0`](https://github.com/ogiboy/agentic-trader/commit/34827b05108c829e4f59dcb6858f64cc2a957b32))
- Move camofox tab typing route
  ([`e923bb5`](https://github.com/ogiboy/agentic-trader/commit/e923bb5dcffe4608c38fbdbacf63a4f5c0aef8ef))
- Move camofox tab click route
  ([`7f3f813`](https://github.com/ogiboy/agentic-trader/commit/7f3f813ec087abc02a51b4e8b3562cb0a5dce5bb))
- Move camofox tab snapshot route
  ([`dbee832`](https://github.com/ogiboy/agentic-trader/commit/dbee832ba6e48119658b340e58efb3a50bd8c0e6))
- Move camofox legacy core routes
  ([`4e5e31b`](https://github.com/ogiboy/agentic-trader/commit/4e5e31b237a6ee28f740468c026f1337c33f4385))
- Move camofox legacy snapshot route
  ([`ad0def4`](https://github.com/ogiboy/agentic-trader/commit/ad0def4d60bda94068d8553558eae58ea3e2ffdb))
- Move camofox legacy action route
  ([`a2fb174`](https://github.com/ogiboy/agentic-trader/commit/a2fb1746bcdd9f283686a5637f90e72de7eb44ae))
- Move camofox google serp helpers
  ([`03b4588`](https://github.com/ogiboy/agentic-trader/commit/03b458873f8edad8bc72955cea88238a465e1b40))
- Move camofox ref helpers
  ([`6e842c2`](https://github.com/ogiboy/agentic-trader/commit/6e842c25c9b737a099742c7018eb28678d807480))
- Move camofox route safety helpers
  ([`a9e894b`](https://github.com/ogiboy/agentic-trader/commit/a9e894b7e9ac5a22b8bacea2e63b94c265fbcc15))
- Split smoke qa modules
  ([`977249d`](https://github.com/ogiboy/agentic-trader/commit/977249da96155150ce50719bb40f14fc0b51ed5f))
- Trim smoke qa interactive helpers
  ([`dc87ff0`](https://github.com/ogiboy/agentic-trader/commit/dc87ff0a1a61e1f347830458a9028f5d7d0e2624))
- Split paper rehearsal flow
  ([`fc296e4`](https://github.com/ogiboy/agentic-trader/commit/fc296e4f4486db07fba52b0cb28dd86828a881dd))
- Split research flow task planning
  ([`7615819`](https://github.com/ogiboy/agentic-trader/commit/76158199580d1888dbb71b6a4d190eb92cce666a))
- Split camofox server core
  ([`e1664f4`](https://github.com/ogiboy/agentic-trader/commit/e1664f46aa62c9ee2a1af6926029cfc7f240a482))

### Chores

- Expand modularity i18n audit scope
  ([`5b12646`](https://github.com/ogiboy/agentic-trader/commit/5b126464129d232f2692e1364865155b712e8921))
- Bump modularity i18n version
  ([`5fca753`](https://github.com/ogiboy/agentic-trader/commit/5fca7538399f43186bdc5f4f2237e9b3847f195d))

## v0.13.0 (2026-06-03)

### Features

- Add terminal ui locale setting
  ([`87ae669`](https://github.com/ogiboy/agentic-trader/commit/87ae669b93cf6243933caac004e585993b736901))

### Bug Fixes

- Backfill stable changelog sections
  ([`ed7c0c4`](https://github.com/ogiboy/agentic-trader/commit/ed7c0c414252f21ea977a128f173cfa9f9b6dc5e))
- Restore next lint compatibility
  ([`bf33a64`](https://github.com/ogiboy/agentic-trader/commit/bf33a64f7feb8c982f0e9fcbfba9fd5807ce28fc))
- Satisfy sonar quality gate
  ([`1cd99ab`](https://github.com/ogiboy/agentic-trader/commit/1cd99abbe704d9b240f856dbb82f2fc458c59068))
- Harden locale env persistence
  ([`9990531`](https://github.com/ogiboy/agentic-trader/commit/99905310bf8089541040fbb9ec99a43a1a671e6d))
- Apply CodeRabbit auto-fixes
  ([`abd2791`](https://github.com/ogiboy/agentic-trader/commit/abd2791015838dc44f9aeb4a414bebc5b1928f24))
- Update settings.json
  ([`e51d0a4`](https://github.com/ogiboy/agentic-trader/commit/e51d0a417a9eaa5026db83f74da2d79103fe35be))
- Restore python ci gates
  ([`25d0875`](https://github.com/ogiboy/agentic-trader/commit/25d0875d2489f5afdca5863cee9548755535d494))
- Satisfy strict terminal pyright exports
  ([`f2b5e4c`](https://github.com/ogiboy/agentic-trader/commit/f2b5e4c9866715336f0fa13adc53b997d0229f1c))
- Reduce qa script sonar findings
  ([`5780817`](https://github.com/ogiboy/agentic-trader/commit/5780817cdf02e31be13ba43337a8739f0b638ed9))
- Satisfy tui sonar reexports
  ([`d131160`](https://github.com/ogiboy/agentic-trader/commit/d13116072d821cd0faa4a9ceeee33ec085a160f7))
- Remove tui reexport-only imports
  ([`bbc6748`](https://github.com/ogiboy/agentic-trader/commit/bbc67489264466b9eb661af06303c8a92eb6bf7e))
- Update gitignore and vscode settings json
  ([`ea35c15`](https://github.com/ogiboy/agentic-trader/commit/ea35c15041f9ab096cf9aa8d7ed42ea3301ff399))
- Sorting
  ([`5d26392`](https://github.com/ogiboy/agentic-trader/commit/5d26392a8238aad780385b4fc65df241d54f271c))
- Harden camofox trace security
  ([`2cc98a7`](https://github.com/ogiboy/agentic-trader/commit/2cc98a76221816a2d7ac625befb3f3c93ace80a7))
- Stabilize camofox ci gates
  ([`3757850`](https://github.com/ogiboy/agentic-trader/commit/37578501a55ae73b5cb59b63b0ec3195f44204b3))
- Clarify camofox launch setup
  ([`2627cf9`](https://github.com/ogiboy/agentic-trader/commit/2627cf9d8bb7655e497759d42f9cbba6bf226045))
- Suppress CLI callback unused-function false positives
  ([`1db2d8c`](https://github.com/ogiboy/agentic-trader/commit/1db2d8c463bf91a8b544fed9a97d8ad4ca7d1711))
- Allow changelog backfill before release tag
  ([`f762741`](https://github.com/ogiboy/agentic-trader/commit/f7627414ae6bae1d92ef491f237897296f560fc3))

### Documentation

- Add modularity branch docstrings
  ([`e545419`](https://github.com/ogiboy/agentic-trader/commit/e545419a9f6bcf2e89583469fb0b2bc68d7ad705))
- Record modularity workflow rules
  ([`9cf8042`](https://github.com/ogiboy/agentic-trader/commit/9cf8042afb843ccdbdb7bed316388d708b8d2601))

### Continuous Integration

- Run sonarcloud scan through pysonar
  ([`160b18c`](https://github.com/ogiboy/agentic-trader/commit/160b18c09a82ba093b373e2e8e1a0da817ed7903))

### Tests

- Add modularity i18n audit
  ([`7955b04`](https://github.com/ogiboy/agentic-trader/commit/7955b04801fc73dc761a368925853e567df00c2c))
- Cover locale persistence through cli
  ([`f1cd39c`](https://github.com/ogiboy/agentic-trader/commit/f1cd39c527651a60232e5ce46acdc0b0e23edacc))
- Cover json mapping fallback
  ([`16d306c`](https://github.com/ogiboy/agentic-trader/commit/16d306c6d91dc1f9cd513d08b3e2233cf3a060b1))
- Add coderabbit review coverage
  ([`184ac2d`](https://github.com/ogiboy/agentic-trader/commit/184ac2d79600d61e26adcf4967a480d71b597c2a))
- Cover tui page render paths
  ([`8cc1b83`](https://github.com/ogiboy/agentic-trader/commit/8cc1b833e6ca927b302713b8a44e6aa491a021be))
- Cover tui chat fallback branches
  ([`3ee1755`](https://github.com/ogiboy/agentic-trader/commit/3ee17559326ec43654d9c0b28d429e805a634479))

### Refactors

- Share json payload helpers
  ([`9c28302`](https://github.com/ogiboy/agentic-trader/commit/9c28302c7264e55af8c55ed7812c98e3f55ef31e))
- Centralize docs home copy
  ([`9851840`](https://github.com/ogiboy/agentic-trader/commit/9851840f14159a8329ca316161f46d7ca0998201))
- Extract ink tui copy helpers
  ([`6430513`](https://github.com/ogiboy/agentic-trader/commit/6430513eb49b3cbc6d99a09081aaa03cd40d4d13))
- Reuse json shape helpers
  ([`02f3dcc`](https://github.com/ogiboy/agentic-trader/commit/02f3dcc22b0637896eccd7043636ab36b141cae1))
- Share utc timestamp helper
  ([`c03b04a`](https://github.com/ogiboy/agentic-trader/commit/c03b04ac93c0675967c6fa6ea9ee55fd09e1fee5))
- Share dataclass payload helpers
  ([`c59f5ad`](https://github.com/ogiboy/agentic-trader/commit/c59f5ad68bba58d2e094dc197f4b1f4adc3f4b97))
- Centralize cli help copy
  ([`1522d10`](https://github.com/ogiboy/agentic-trader/commit/1522d10dcfe7672fdb460adb35efec5dc3e9c16a))
- Centralize proposal cli copy
  ([`7e98b37`](https://github.com/ogiboy/agentic-trader/commit/7e98b373cd746045a1de90852d041aa4587f5e60))
- Centralize idea cli copy
  ([`0200daf`](https://github.com/ogiboy/agentic-trader/commit/0200daf9409a90f953f05ff8ec479721dd5afee8))
- Centralize execution cli copy
  ([`55dc169`](https://github.com/ogiboy/agentic-trader/commit/55dc16989d341af4342f5939269e13bcb8e2b52b))
- Centralize service cli copy
  ([`99b5997`](https://github.com/ogiboy/agentic-trader/commit/99b59970849b5854fd7b948c06d5c2c3516213c8))
- Centralize report cli copy
  ([`ef6c533`](https://github.com/ogiboy/agentic-trader/commit/ef6c533a89a0ae366975e0b6e3365f27fa7e9877))
- Centralize review cli copy
  ([`fa5e96e`](https://github.com/ogiboy/agentic-trader/commit/fa5e96ea7fb81a66b9890c8b190de6b5aa8feedb))
- Centralize backtest cli copy
  ([`a03d95d`](https://github.com/ogiboy/agentic-trader/commit/a03d95d76689dd8d09fefdb18d0478ec382a9eb0))
- Centralize memory cli copy
  ([`3395ec7`](https://github.com/ogiboy/agentic-trader/commit/3395ec7f0e28101fed1f84c35359c3f0fe9859bf))
- Centralize finance cli copy
  ([`db0d594`](https://github.com/ogiboy/agentic-trader/commit/db0d5945aa0a461783fb3496e2f477f666fab8f2))
- Centralize runtime cli copy
  ([`c632dc3`](https://github.com/ogiboy/agentic-trader/commit/c632dc314e584278fbe2b999930e6b857176c8ac))
- Centralize environment cli copy
  ([`f085a38`](https://github.com/ogiboy/agentic-trader/commit/f085a380623f7fcb685f03e434021aee59442ded))
- Centralize setup cli copy
  ([`1ae83f4`](https://github.com/ogiboy/agentic-trader/commit/1ae83f494b3b24dfdce34b927ae8c5b3344451db))
- Centralize service status cli copy
  ([`75dfdb1`](https://github.com/ogiboy/agentic-trader/commit/75dfdb1ddcdcbce13e0a946393d5356a70db9846))
- Centralize operator launcher cli copy
  ([`2766645`](https://github.com/ogiboy/agentic-trader/commit/276664513b9340dfe7f7dfbaf12134b8f7d49132))
- Centralize side service command copy
  ([`476ec36`](https://github.com/ogiboy/agentic-trader/commit/476ec36d7a0bcb56de5195ab55673794a22cd13b))
- Centralize research status cli copy
  ([`5e39c07`](https://github.com/ogiboy/agentic-trader/commit/5e39c07e50c3353b3f3921c0c91b247c60f95ab7))
- Centralize research control cli copy
  ([`e92abb3`](https://github.com/ogiboy/agentic-trader/commit/e92abb37e57e427b35af4944c3537f006175c658))
- Centralize launch plan cli copy
  ([`e3357d5`](https://github.com/ogiboy/agentic-trader/commit/e3357d5a537304218ef19a52d547aa934c843e96))
- Centralize portfolio cli copy
  ([`d4d0887`](https://github.com/ogiboy/agentic-trader/commit/d4d0887bc87e9e404cab6754dda39fc9fade6f24))
- Centralize provider status cli copy
  ([`3f7eb26`](https://github.com/ogiboy/agentic-trader/commit/3f7eb264ae92c893a3bff6dc739f51b955cd037e))
- Centralize proposal cli help copy
  ([`cf4d3f4`](https://github.com/ogiboy/agentic-trader/commit/cf4d3f4b6aa45729c449c2972a57fa22591e76a2))
- Centralize proposal candidate cli copy
  ([`c6720eb`](https://github.com/ogiboy/agentic-trader/commit/c6720ebe299d0d5379aafe2883bc53b547ec3465))
- Centralize trade proposal cli copy
  ([`babf2f2`](https://github.com/ogiboy/agentic-trader/commit/babf2f2187e9716697f09e361ea0bd3af87de2de))
- Centralize idea strategy cli copy
  ([`a0d06f2`](https://github.com/ogiboy/agentic-trader/commit/a0d06f25b300f3f1f44932cb980114f01f0f3f33))
- Centralize research cycle cli copy
  ([`ab7d314`](https://github.com/ogiboy/agentic-trader/commit/ab7d31403d86c798d562b176982d404258efcf13))
- Centralize operator evidence cli copy
  ([`c68c2c4`](https://github.com/ogiboy/agentic-trader/commit/c68c2c408bd7ab5388121fa8221770d7defa5849))
- Centralize observer calendar cli copy
  ([`2d8030f`](https://github.com/ogiboy/agentic-trader/commit/2d8030f420015be63fa0b41d5573d25b9cff7df5))
- Centralize news cache cli copy
  ([`79acb15`](https://github.com/ogiboy/agentic-trader/commit/79acb15bb34420e02bff77caa2a148700658a24e))
- Centralize review context cli copy
  ([`b54d2cb`](https://github.com/ogiboy/agentic-trader/commit/b54d2cb508d05f12dcade8a11f7f82b80af9df78))
- Centralize replay backtest cli copy
  ([`ed56e70`](https://github.com/ogiboy/agentic-trader/commit/ed56e701a8ceb464344c15f83f74c2fa0b11acbe))
- Centralize retrieval cli copy
  ([`c184162`](https://github.com/ogiboy/agentic-trader/commit/c184162dfe787068a6b34fda262f3e52575cb0a2))
- Centralize service cli copy
  ([`6cf8dab`](https://github.com/ogiboy/agentic-trader/commit/6cf8dabb89f6b43612c198dbdfb56c8a7456992a))
- Centralize tui status copy
  ([`0887505`](https://github.com/ogiboy/agentic-trader/commit/0887505424a5f282656875cccf2084cec8653cef))
- Centralize tui workflow copy
  ([`9277e37`](https://github.com/ogiboy/agentic-trader/commit/9277e377a11e5ff217fbff6da62c69ae4d8c7544))
- Centralize tui system copy
  ([`f9a756f`](https://github.com/ogiboy/agentic-trader/commit/f9a756fecf7c3bad1df1d2807ef8a1192a8e9874))
- Centralize tui provider copy
  ([`92f408e`](https://github.com/ogiboy/agentic-trader/commit/92f408e9cb679ab54eb1dd5ff01c878237ec2ab7))
- Centralize tui review copy
  ([`c06ddf5`](https://github.com/ogiboy/agentic-trader/commit/c06ddf5ac6b8d31077431305da77990020664645))
- Centralize tui menu copy
  ([`3bd833d`](https://github.com/ogiboy/agentic-trader/commit/3bd833d37eb1eb79d5a8430ec5ad84826786912f))
- Extract tui input routing
  ([`fd5f2cf`](https://github.com/ogiboy/agentic-trader/commit/fd5f2cf4720e9dc6a234d904e7ef3b65b5e60db2))
- Extract tui dashboard defaults
  ([`7c7be76`](https://github.com/ogiboy/agentic-trader/commit/7c7be7650e97dcbae200eda3caf3a4d37ca8d2f9))
- Extract tui line formatters
  ([`2b0c80a`](https://github.com/ogiboy/agentic-trader/commit/2b0c80acbb437a144f551bacac8c7cea2f7ec2fc))
- Split tui page components
  ([`1425611`](https://github.com/ogiboy/agentic-trader/commit/142561107b2356818c6fa49a9c1820dde101ed7a))
- Split tui line formatters
  ([`ff2f746`](https://github.com/ogiboy/agentic-trader/commit/ff2f746138a71c4ce54b1cb1fd0677fb7ef5e8a2))
- Extract terminal monitor module
  ([`ec0d9df`](https://github.com/ogiboy/agentic-trader/commit/ec0d9df5cb69402de17e2da5bd4c273da97beb8c))
- Split terminal monitor sections
  ([`6459f48`](https://github.com/ogiboy/agentic-trader/commit/6459f487d791de451b757055c6e8929c43da0ba9))
- Extract terminal status renderers
  ([`f348da9`](https://github.com/ogiboy/agentic-trader/commit/f348da9e193a0aca9a49a35d1a72b167b0d3146c))
- Split terminal control room flows
  ([`023a964`](https://github.com/ogiboy/agentic-trader/commit/023a96407ade2a928a2af0728ea7aa407b7f9176))
- Isolate llm structured parsing
  ([`927471a`](https://github.com/ogiboy/agentic-trader/commit/927471a5f3142c0002ef7a3b1f56c0dbd4f8aed8))
- Split trade proposal drafts
  ([`d6d7667`](https://github.com/ogiboy/agentic-trader/commit/d6d766709563ae9b65f74a455ddd2333641b4616))
- Isolate sec companyfacts parsing
  ([`f3dec2f`](https://github.com/ogiboy/agentic-trader/commit/f3dec2f12657b3f461853d479ed4eb8466bda923))
- Isolate proposal candidate context
  ([`4c3cfca`](https://github.com/ogiboy/agentic-trader/commit/4c3cfca84e3a8706057564d87d814728a1e326fc))
- Isolate model service status
  ([`37bd2e1`](https://github.com/ogiboy/agentic-trader/commit/37bd2e1a9cb1546eaac0c5763acd6ecfa4e98c5e))
- Split model service status assembly
  ([`1847219`](https://github.com/ogiboy/agentic-trader/commit/18472197e4004846b1bda4a0cf8d488dd6edd5ed))
- Split model service probes and state
  ([`55abc6c`](https://github.com/ogiboy/agentic-trader/commit/55abc6c03ec5a15ee03de2d06315dbdc0a4eeb7b))
- Split terminal ui text catalogs
  ([`3610bf5`](https://github.com/ogiboy/agentic-trader/commit/3610bf5c45e01d72ccefb4dd6a049d371749dcac))
- Split storage schema management
  ([`fd53f09`](https://github.com/ogiboy/agentic-trader/commit/fd53f09d1354218dc815357d9d816a226a57f237))
- Split proposal storage operations
  ([`c81eb61`](https://github.com/ogiboy/agentic-trader/commit/c81eb613993b6cffd749e6bd6ad1c83c1cdde86c))
- Split service storage operations
  ([`c896fd2`](https://github.com/ogiboy/agentic-trader/commit/c896fd278778fdf305c4c538464a806f5d4a7e86))
- Split trade journal storage
  ([`ad3544e`](https://github.com/ogiboy/agentic-trader/commit/ad3544e1e63dd1f47523e7fb8c57583206ecf714))
- Split portfolio storage operations
  ([`62d7a1a`](https://github.com/ogiboy/agentic-trader/commit/62d7a1ab2ae99b65a9e1727f7acd4c3be6d22328))
- Split research providers
  ([`4854552`](https://github.com/ogiboy/agentic-trader/commit/48545527185b8fcbcb2105208bfe879f4f836da2))
- Split broker adapters
  ([`894d317`](https://github.com/ogiboy/agentic-trader/commit/894d317d9f16b9542706e824d417e56a1d329d26))
- Split service workflow modules
  ([`dd03c65`](https://github.com/ogiboy/agentic-trader/commit/dd03c65643886c68b9e545481d3120819751890e))
- Split schema models
  ([`02e6984`](https://github.com/ogiboy/agentic-trader/commit/02e6984992572fce46af79e678ea640d681b96a9))
- Split cli proposal desk
  ([`ee8f0b4`](https://github.com/ogiboy/agentic-trader/commit/ee8f0b424205fdd1ddd0a1d08a19b09cdbe18b07))
- Split cli operator readiness
  ([`e56db00`](https://github.com/ogiboy/agentic-trader/commit/e56db007f660ea172cc4ff8e0a3a538666110dd0))
- Split webgui service modules
  ([`fb8f53c`](https://github.com/ogiboy/agentic-trader/commit/fb8f53cf3e458c7864d57df0e99f856f1aebeccb))
- Group tui modules
  ([`87a80bd`](https://github.com/ogiboy/agentic-trader/commit/87a80bd70739998d9244f8aec259cd139628969e))
- Split cli tui and copy boundaries
  ([`ab5faac`](https://github.com/ogiboy/agentic-trader/commit/ab5faacbde05be15bb19608c51a8709852160eab))
- Tighten python runtime typing
  ([`8bc4f68`](https://github.com/ogiboy/agentic-trader/commit/8bc4f6841a03d2f1af1b0fd24474501a40ad6427))
- Modularize webgui control room
  ([`a906306`](https://github.com/ogiboy/agentic-trader/commit/a9063064ec89d9f35c3c097f80025b814bf15379))
- Split tui monitor modules
  ([`3779252`](https://github.com/ogiboy/agentic-trader/commit/37792521c43b1f19b3ac65a68403a342f65d6464))
- Split tui status renderers
  ([`f653547`](https://github.com/ogiboy/agentic-trader/commit/f653547e3a7ea9877082723d14afa2a346d93622))
- Split model service process helpers
  ([`cd4bd99`](https://github.com/ogiboy/agentic-trader/commit/cd4bd99291c89ded88dd89e7956f1031c02b7660))
- Split model service reports
  ([`cd7f1a6`](https://github.com/ogiboy/agentic-trader/commit/cd7f1a68017e63563e86be1f9681879ba09d0d9f))
- Split cli system registration
  ([`cfb91e7`](https://github.com/ogiboy/agentic-trader/commit/cfb91e78cfcb1c366b44871d06ebf1fcbb238a42))
- Split cli service rendering
  ([`32b83dd`](https://github.com/ogiboy/agentic-trader/commit/32b83ddb49ea297616056e81c8f2291349451e13))
- Split webgui service state
  ([`934db4d`](https://github.com/ogiboy/agentic-trader/commit/934db4d9c90094555170c9769de785c3b11328ce))
- Split webgui service process helpers
  ([`aa2c8a7`](https://github.com/ogiboy/agentic-trader/commit/aa2c8a74adc23e61cdbb0e37a5b2d28838be9c73))
- Split camofox service state
  ([`ebeeea9`](https://github.com/ogiboy/agentic-trader/commit/ebeeea9f5ae3867b7f7e34e81bbf4893456b9ac9))
- Split camofox service process helpers
  ([`56e878a`](https://github.com/ogiboy/agentic-trader/commit/56e878ae02cfccd44b9683a3d98f73b0253ce0fa))
- Split sec edgar evidence modules
  ([`cb6f9f4`](https://github.com/ogiboy/agentic-trader/commit/cb6f9f44461a9676d24e1e061be69ffb7bda37d2))
- Split storage database helpers
  ([`b41a9df`](https://github.com/ogiboy/agentic-trader/commit/b41a9dfdb52e0ce101875bbf62e7d8c8eeec938d))
- Split workflow persistence helpers
  ([`eb34d85`](https://github.com/ogiboy/agentic-trader/commit/eb34d852b13c688b49c4bf4cdf280349ca2c2c92))
- Split workflow run context
  ([`1e089a2`](https://github.com/ogiboy/agentic-trader/commit/1e089a25de5456d16c024c0bfeea7a2e5a70f0a9))
- Split research sidecar backends
  ([`64af421`](https://github.com/ogiboy/agentic-trader/commit/64af421527afee53358ec69397a88f3c65b3b2f4))
- Split openai compatible llm helpers
  ([`ede2c1a`](https://github.com/ogiboy/agentic-trader/commit/ede2c1af3aed0f1b20f494c695845de6acf86d65))
- Split proposal strategy commands
  ([`06ed6f3`](https://github.com/ogiboy/agentic-trader/commit/06ed6f35a065b86221ebeafaed4e61f16ebd021b))
- Split finance proposal actions
  ([`7f360ca`](https://github.com/ogiboy/agentic-trader/commit/7f360cac0b9259eb182886a7d4b57557069dbb75))
- Split alpaca adapter mapping
  ([`c8442d9`](https://github.com/ogiboy/agentic-trader/commit/c8442d97c431c90f4c05add57eb1b141acd8ad07))
- Split paper broker helpers
  ([`7e0453d`](https://github.com/ogiboy/agentic-trader/commit/7e0453db9621f6991a1622261f867d4db92cae3e))
- Split market feature helpers
  ([`ea60811`](https://github.com/ogiboy/agentic-trader/commit/ea6081171e955e923eba5f318f5b9a67d23fd78b))
- Split walk forward backtest engine
  ([`948791c`](https://github.com/ogiboy/agentic-trader/commit/948791c6c0e416c45d7d1cd3bb395263ffa4fc93))
- Split research cycle payloads
  ([`ddaa16c`](https://github.com/ogiboy/agentic-trader/commit/ddaa16ca986cb490cc73b0d9fb16f0876649c181))
- Split operator cli commands
  ([`de286f9`](https://github.com/ogiboy/agentic-trader/commit/de286f94a754073206ce02e2f734c7bc1ff2bec1))
- Split legacy ui text exports
  ([`362d0a1`](https://github.com/ogiboy/agentic-trader/commit/362d0a11647e71101ee7b49179573b11fee0ac64))
- Split ui text catalog types
  ([`28d7f9b`](https://github.com/ogiboy/agentic-trader/commit/28d7f9b8189211874a79c2d6b18ed8d04312be83))
- Split cli record payloads
  ([`080baed`](https://github.com/ogiboy/agentic-trader/commit/080baed09021c05424005d3875bc87ad99856438))
- Split ink tui runtime helpers
  ([`c3589e6`](https://github.com/ogiboy/agentic-trader/commit/c3589e698505ece9895ad3d0e8f0e13f1eb1e170))
- Split webgui service status builders
  ([`fc517f1`](https://github.com/ogiboy/agentic-trader/commit/fc517f10ef30cec71aab44debeb545663756aaf4))
- Split run output assembly
  ([`84eb76f`](https://github.com/ogiboy/agentic-trader/commit/84eb76ffe53c774b775c0be7863f93dfc1679cbf))
- Split llm provider payload helpers
  ([`32fd23a`](https://github.com/ogiboy/agentic-trader/commit/32fd23a0ddbfc868fb7b7a80172199fc74f1eb41))
- Split trade context assembly
  ([`b0e1bcd`](https://github.com/ogiboy/agentic-trader/commit/b0e1bcde155fad3afdae830c1b5ef68773af1535))
- Split provider collection helpers
  ([`0a32c46`](https://github.com/ogiboy/agentic-trader/commit/0a32c464f45984b9380685bcc22961dbbc5b9ba2))
- Split finance rendering
  ([`31972e6`](https://github.com/ogiboy/agentic-trader/commit/31972e6ce030bae0c0950e9faa8b2979849aef93))
- Split record rendering
  ([`2074b7d`](https://github.com/ogiboy/agentic-trader/commit/2074b7d48f2633d818f10f3949539308c578d5bb))
- Split proposal action payloads
  ([`7026a9b`](https://github.com/ogiboy/agentic-trader/commit/7026a9b0d07d80e0536f1d07957bf485534ca3f5))
- Split alpaca risk checks
  ([`9602919`](https://github.com/ogiboy/agentic-trader/commit/9602919d00c1482e6bf8818ba82bb75093cb90d5))
- Split fundamental fallback logic
  ([`3f2937f`](https://github.com/ogiboy/agentic-trader/commit/3f2937f491163da5350f3e749c0b86f8ae11bc24))
- Split llm provider health helpers
  ([`586ac31`](https://github.com/ogiboy/agentic-trader/commit/586ac31849a7ba47c9d63c287d1405b0fcaf2c30))
- Split strategy catalog data
  ([`344b8dc`](https://github.com/ogiboy/agentic-trader/commit/344b8dc7b8f81ba82192afa7efadd8939a4d0a49))
- Split service state records
  ([`ca0f672`](https://github.com/ogiboy/agentic-trader/commit/ca0f672007ef6b009dbbca23bb6d340db1724e8b))
- Split public source providers
  ([`971a1d2`](https://github.com/ogiboy/agentic-trader/commit/971a1d2f8c0dcc60a9e2989cde2b943549089659))
- Split portfolio storage modules
  ([`ca145f5`](https://github.com/ogiboy/agentic-trader/commit/ca145f5299c107543ab16f6b5cd6acbdedcc5a0a))
- Split one-shot workflow stages
  ([`201cf63`](https://github.com/ogiboy/agentic-trader/commit/201cf6360af665d7d707daf899af80c09244ad63))
- Split proposal desk commands
  ([`9ff2135`](https://github.com/ogiboy/agentic-trader/commit/9ff2135324cc681f4e5bcff721c6dec4ec989981))
- Split structured llm helpers
  ([`6325b6b`](https://github.com/ogiboy/agentic-trader/commit/6325b6ba3f35b0b4dd5ca5e20ebbeb9b6809893a))
- Split proposal storage records
  ([`426d20b`](https://github.com/ogiboy/agentic-trader/commit/426d20b389a53f626d414ab50b207aeb25e5059f))
- Split paper broker execution helpers
  ([`35384df`](https://github.com/ogiboy/agentic-trader/commit/35384dfc629002c89b1b4c028d69dfca38f25d1d))
- Split runtime mode CLI commands
  ([`d8db257`](https://github.com/ogiboy/agentic-trader/commit/d8db2575dd21c44ca732f08f1d6f0a61a5eb7334))
- Split service CLI commands
  ([`98d105d`](https://github.com/ogiboy/agentic-trader/commit/98d105d1d96cc48dcd4688f5c48f2c4b17cdb1df))
- Split proposal candidate validation
  ([`dcd33fd`](https://github.com/ogiboy/agentic-trader/commit/dcd33fd522716807fa5a07bb7c37ec419cf48246))
- Split noop research backend
  ([`f4c2a1e`](https://github.com/ogiboy/agentic-trader/commit/f4c2a1eb7c0703b48c49bbe6daebe0a0e734c90d))
- Split research contract helpers
  ([`80fe609`](https://github.com/ogiboy/agentic-trader/commit/80fe609001d7cf3ba2a873ee07b12c6a53fabfe7))
- Split research cycle helpers
  ([`80bfffb`](https://github.com/ogiboy/agentic-trader/commit/80bfffb57c6eddceb29dc11efad20126401eb8a8))

### Styles

- Sort python imports and formatting
  ([`c2a2aef`](https://github.com/ogiboy/agentic-trader/commit/c2a2aef69919fe6416c7f4894eac60a4ced665ba))
- Modernize camofox browser server lint
  ([`4bd354e`](https://github.com/ogiboy/agentic-trader/commit/4bd354eb13912bec7523fc6c08ed51e86e7cad4a))
- Normalize modularity audit formatting
  ([`02087d3`](https://github.com/ogiboy/agentic-trader/commit/02087d305e684fe89ec7ab414dae941a880402d5))
- Normalize i18n and UI formatting
  ([`de57b85`](https://github.com/ogiboy/agentic-trader/commit/de57b859c621ca72d1d9466b745eea55550cccf3))

### Chores

- Bump SonarSource/sonarqube-scan-action from 7.1.0 to 8.1.0
  ([`90e02da`](https://github.com/ogiboy/agentic-trader/commit/90e02dada6c83ac7bac34558adbb32a0ea35b2e2))
- Bump crewai[tools] in /sidecars/research_flow
  ([`082a127`](https://github.com/ogiboy/agentic-trader/commit/082a12739ad465add551460fdaff3bb12bf39286))
- Bump duckdb from 1.5.2 to 1.5.3
  ([`0dd52d1`](https://github.com/ogiboy/agentic-trader/commit/0dd52d1e8fec18655bcef96c0769cf9ed111feaa))
- Bump coverage from 7.13.5 to 7.14.0
  ([`2c0dfcd`](https://github.com/ogiboy/agentic-trader/commit/2c0dfcd3bb18a5e1184e99ae21266bd5328d551e))
- Bump firecrawl-py from 4.25.1 to 4.28.0
  ([`961fed1`](https://github.com/ogiboy/agentic-trader/commit/961fed10e01b5de07f5af647ca77d7ec0d462167))
- Bump ruff from 0.15.12 to 0.15.14
  ([`9ff79a5`](https://github.com/ogiboy/agentic-trader/commit/9ff79a5d882f935497b6645b70077018cd827542))
- Bump vitest from 4.1.6 to 4.1.7
  ([`b89a4a6`](https://github.com/ogiboy/agentic-trader/commit/b89a4a6094fb4ff0992ee17ed168935875cfa73f))
- Bump fumadocs-ui from 16.8.11 to 16.9.1
  ([`d63c7bf`](https://github.com/ogiboy/agentic-trader/commit/d63c7bf7e16492cb83dca00f9d0b3d0a76b0ade7))
- Bump @vitest/coverage-v8 from 4.1.6 to 4.1.7
  ([`c6ff239`](https://github.com/ogiboy/agentic-trader/commit/c6ff239d5828467e6ae1d2c84dc378ff5ea85195))
- Bump fumadocs-core from 16.8.11 to 16.9.1
  ([`378cfc4`](https://github.com/ogiboy/agentic-trader/commit/378cfc47b2a7b34ced30aea0c9ab6c765005bd72))
- Bump the next-apps group across 1 directory with 5 updates
  ([`d0a99fc`](https://github.com/ogiboy/agentic-trader/commit/d0a99fcce218b69691b9682221551e13876edbdf))
- Update project version
  ([`4c065cf`](https://github.com/ogiboy/agentic-trader/commit/4c065cfecc63720c6c63f1e8149f33843c61d97f))
- Update project version
  ([`e5c7676`](https://github.com/ogiboy/agentic-trader/commit/e5c7676fa0da4ce3904118ac11ecb641b556e2c0))
- Refresh workspace dependencies
  ([`535f230`](https://github.com/ogiboy/agentic-trader/commit/535f230968e2152800029bd64df5ebebbff1a36f))
- Bump version to 0.12.6
  ([`35bab29`](https://github.com/ogiboy/agentic-trader/commit/35bab299964d574c062feff8bec2dbb2092732f1))
- Bump version to 0.12.7
  ([`18e8b8b`](https://github.com/ogiboy/agentic-trader/commit/18e8b8ba99bf4a7afeb8d02214afa5ec2e530e75))
- Bump version to 0.12.8
  ([`29d6d13`](https://github.com/ogiboy/agentic-trader/commit/29d6d13938bbf4d003ae3955472cce31a8b51b91))
- Bump version to 0.12.9
  ([`adf50d4`](https://github.com/ogiboy/agentic-trader/commit/adf50d4e38e34240e6d9afc29d692aca9c5d5606))
- Bump version to 0.12.10
  ([`d875845`](https://github.com/ogiboy/agentic-trader/commit/d8758458bf292a0e6e4de1e3c33461e2fd517488))
- Bump version to 0.12.11
  ([`939b216`](https://github.com/ogiboy/agentic-trader/commit/939b2162d0b95633cfc09aa06335893efa4350e6))
- Update node workspace dependencies
  ([`60b54a9`](https://github.com/ogiboy/agentic-trader/commit/60b54a969804ec95af3f6714d9ad6feb1d3a07b1))
- Bump version to 0.12.12
  ([`935bfd4`](https://github.com/ogiboy/agentic-trader/commit/935bfd4bef34f91cab58f8287c7eef8fac541874))
- Update Python dependency locks
  ([`d6ce301`](https://github.com/ogiboy/agentic-trader/commit/d6ce301f46324eb907ea9853ea45c4392cec2559))
- Bump version to 0.12.13
  ([`adf54fc`](https://github.com/ogiboy/agentic-trader/commit/adf54fc0bbfed83bc757501753142c46f11ba0f9))
- Bump version to 0.12.14
  ([`e37eb9d`](https://github.com/ogiboy/agentic-trader/commit/e37eb9d62ac04b9e051c430051f9b316b3bf0617))

## v0.12.5 (2026-05-26)

### Bug Fixes

- Type CLI JSON payloads
  ([`0a5c896`](https://github.com/ogiboy/agentic-trader/commit/0a5c8968be8ae237595c00e3a2dec4e852fa3033))
- Type TUI status payloads
  ([`97f3bab`](https://github.com/ogiboy/agentic-trader/commit/97f3bab4d9d5f0c73c8052322127bb2a644c9e5c))
- Type research provider payloads
  ([`58f5fb4`](https://github.com/ogiboy/agentic-trader/commit/58f5fb4bc32984b80d96df9287310608c8d38c21))
- Type LLM provider responses
  ([`3cf7fcb`](https://github.com/ogiboy/agentic-trader/commit/3cf7fcbfa2a4b87846f52cb33afd7c6341349d10))
- Type model service payloads
  ([`e017c15`](https://github.com/ogiboy/agentic-trader/commit/e017c15e288ac3ca526d2e712b817184c3912021))
- Type smoke QA flows
  ([`44f367e`](https://github.com/ogiboy/agentic-trader/commit/44f367e93617deb75461d8a88143f76752d9acf7))
- Type research source payloads
  ([`491e283`](https://github.com/ogiboy/agentic-trader/commit/491e28314fd002ca8f7fef9795c0929c629aa2c7))
- Type proposal candidate evidence
  ([`78b5e93`](https://github.com/ogiboy/agentic-trader/commit/78b5e9383dd4c9710d380465eefb739551349f6d))
- Type runtime data payloads
  ([`f89b987`](https://github.com/ogiboy/agentic-trader/commit/f89b9874829b87eaf8b110f3c14bb0e1b5ae096f))
- Type optional tool payloads
  ([`ff746a0`](https://github.com/ogiboy/agentic-trader/commit/ff746a07723b9c808b2b45425f01762fa4ec98df))
- Clear strict type backlog
  ([`2b06b8b`](https://github.com/ogiboy/agentic-trader/commit/2b06b8b44b003f226ffd076e2cfc9e9a91db2112))
- Satisfy sonar quality gate
  ([`57b2a8c`](https://github.com/ogiboy/agentic-trader/commit/57b2a8c0dbc96edc9efddeef01279d3ae1011b12))
- Preserve research sidecar contract errors
  ([`c42dd07`](https://github.com/ogiboy/agentic-trader/commit/c42dd078306403dff6f135cbc1a2f5bbd915ca87))
- Inspect crewai sidecar version
  ([`887826b`](https://github.com/ogiboy/agentic-trader/commit/887826bdbc09be77e9216b943ac16340f522838c))
- Close review safety findings
  ([`f85ec9e`](https://github.com/ogiboy/agentic-trader/commit/f85ec9ea4e0eeabe2f1e276ac308a2f565904650))
- Pin qs security override
  ([`a7a3765`](https://github.com/ogiboy/agentic-trader/commit/a7a376552fca45c7ce8a9fd132faa46bdee4ac12))
- Harden cli and sidecar review paths
  ([`fcff907`](https://github.com/ogiboy/agentic-trader/commit/fcff907e557df5dca0f93c588f3bbb8c47880aad))
- Address review safety findings
  ([`854a22e`](https://github.com/ogiboy/agentic-trader/commit/854a22ec74ed88246d674605c1f3308b2c773ce9))

### Documentation

- Map commercial readiness blockers
  ([`d0db6b6`](https://github.com/ogiboy/agentic-trader/commit/d0db6b67d6059afb7eb13d54ae3a7b04bbab66d9))
- Avoid future-dated readiness notes
  ([`adee92e`](https://github.com/ogiboy/agentic-trader/commit/adee92e53495163ab9a934d312b349b18901bfea))

### Tests

- Type service and research fixtures
  ([`6339727`](https://github.com/ogiboy/agentic-trader/commit/6339727a4390f7f6f63c96e7192328365cff920a))
- Expose model service diagnostics
  ([`5df7357`](https://github.com/ogiboy/agentic-trader/commit/5df73573f663f7abf101aa629c336c6ae7e1ba9f))
- Type service runtime fakes
  ([`d1c9659`](https://github.com/ogiboy/agentic-trader/commit/d1c9659c867f30cf297b09f5f49f5580f329a296))
- Type Camofox service fakes
  ([`a90f55c`](https://github.com/ogiboy/agentic-trader/commit/a90f55c91e395b078ba44bec5e20047182973146))
- Simplify Camofox helper aliases
  ([`c384b5f`](https://github.com/ogiboy/agentic-trader/commit/c384b5fb3a2061c828ee47ace4f78f9f9aef953c))
- Type runtime helper fixtures
  ([`4cd8edc`](https://github.com/ogiboy/agentic-trader/commit/4cd8edc37b435c9e44f2e1699143a202ce5bff41))
- Restore decision feature summary discovery
  ([`64cecf9`](https://github.com/ogiboy/agentic-trader/commit/64cecf98f677ab3045799899dd1192bcd73432ab))
- Stabilize setup status typing
  ([`305287a`](https://github.com/ogiboy/agentic-trader/commit/305287a051cbfeaefef4d9448ae494346865e36b))

## v0.12.4 (2026-05-25)

### Bug Fixes

- Harden release changelog coverage
  ([`5467f44`](https://github.com/ogiboy/agentic-trader/commit/5467f449aa934388dafa16e995491c2c645ad4b5))

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
