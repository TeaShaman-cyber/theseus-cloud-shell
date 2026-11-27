# exe.dev provider adapter

Status on 2026-11-11: **preferred governed Linux shell candidate**. Live plan/trial/billing state is not inferred from historical trial timing and must be reprobed through an authorized current account surface when it matters. Existing VM `theseus-exe-shell-probe` has been the verified working target; always use `list_vms` before action rather than treating that name as permanent authority.

## Current infrastructure

Observed current state on `theseus-exe-shell-probe`:

- **GitHub:** native `gh` OAuth is stored in GNOME Secret Service, not inline in `~/.config/gh/hosts.yml`. A real reboot verified automatic headless keyring unlock, `gh api`, private HTTPS Git and ordinary `git ls-remote`.
- **Neon:** exe.dev catalog integration `neon` is attached to the VM and injects the Neon management credential at `https://neon.int.exe.xyz`; no Neon API key is stored in the guest. On 2026-11-07 the management API returned HTTP 200, the connection-URI endpoint returned a PostgreSQL URI without printing it, installed `/bin/psql` connected successfully, and `psql -f` executed a read-only SQL file. Database authority still comes from the selected Postgres role; this capability does **not** authorize exposing Session Search corpus rows. See [Neon SQL via provider proxy](#neon-sql-via-provider-proxy-2026-11-07) and [cloud-shell issue #10](https://github.com/TeaShaman-cyber/theseus-cloud-shell/issues/10).
- **Cloudflare (2026-11-20):** exe.dev's `cloudflare` integration is configured and attached to the currently verified VM. Guest Reflection listed its attachment and the credential-injecting proxy returned HTTP 200 from a read-only `GET https://cloudflare.int.exe.xyz/client/v4/accounts`. The independent native ChatGPT Cloudflare connector also successfully listed accounts. These are separate credential and authority surfaces; neither proves the other's mutation permissions. See [Cloudflare via exe.dev proxy](#cloudflare-via-exedev-proxy-2026-11-20).
- **LLM/provider integrations (2026-11-21):** the primary VM currently exposes attached OpenRouter, BotHub, Groq, and NVIDIA NIM routes through exe.dev integrations. The NVIDIA integration is currently named `nvidi-nim` (configured name), targets `https://integrate.api.nvidia.com/` with provider-side Bearer injection, and a guest read-only `GET https://nvidi-nim.int.exe.xyz/v1/models` returned HTTP 200 with 33 model IDs. Presence of the other provider integrations is attachment evidence only unless a target probe is recorded separately. See [LLM/provider integrations](#llmprovider-integrations-2026-11-21) and [cloud-shell issue #22](https://github.com/TeaShaman-cyber/theseus-cloud-shell/issues/22).
- **Turso Platform API + libSQL data plane:** exe.dev integration `turso` is attached and keeps the Platform API credential provider-side. The 2026-11-22 Repository Search work verified short-lived DB-token minting, SQLite upload, SQL-over-HTTP readback, and FTS5/`unicode61` queries without persisting a Turso platform credential in the guest. Native ChatGPT Turso MCP is a separate credential/authority surface. See [the Turso route](#turso-platform-api-and-libsql-data-plane-via-exedev) and [cloud-shell issue #30](https://github.com/TeaShaman-cyber/theseus-cloud-shell/issues/30).
- **Zenodo:** native provider-held HTTP proxy `zenodo` is attached to the governed VM; authenticated draft list, creation and manuscript file upload/readback verified. See [Zenodo via exe.dev](#zenodo-via-exedev-http-proxy-2026-11-27).
- **Azure control plane:** official Azure CLI 2.92.0 is installed from the Microsoft Ubuntu repository. Dedicated service principal `theseus-exe-operator` (`appId 9d03ca4c-53e1-4b57-9acf-728d4985457d`) has Azure RBAC `Owner` at subscription scope `/subscriptions/d760fa4b-978b-4b6d-a62e-93b55bc36746`. This is the explicitly authorized full Azure operator identity for the cloud shell; the narrower existing Translator workload identity remains unchanged.
- **Azure certificate/keyring:** the service-principal private key was generated on this exe.dev VM and never transferred to the laptop or chat. The combined private-key + public-certificate PEM is stored in GNOME Secret Service under `app=theseus, credential=azure-exe-operator`; only the public certificate was uploaded through the already authenticated Windows Azure CLI. Certificate SHA-256 fingerprint is `A8:61:CD:48:39:6A:AF:89:63:D1:E6:15:9A:81:87:F7:DA:F1:2D:D0:AC:96:E4:A6:56:B3:28:5E:DD:FC:AE:86`, expiring 2028-11-06 UTC.
- **Azure runtime wrapper:** versioned source `providers/exe-dev/az-owner` is projected as `/home/exedev/.local/bin/az-owner`. Every invocation retrieves the PEM from Secret Service, materializes it only below `/run/user/1000`, creates a temporary `AZURE_CONFIG_DIR` on the same tmpfs, performs certificate-based service-principal login for the fixed tenant/subscription, runs the requested `az` command, then removes the temporary PEM and Azure CLI cache. Persistent `~/.azure` is absent after accepted runs.
- **Azure acceptance:** independent Windows-side readback verified `ServicePrincipal / Owner` at subscription scope. On exe.dev, `az-owner account show` reports the intended enabled subscription/tenant with `user.type=servicePrincipal`, `az-owner resource list` returns the current inventory, and `az-owner role assignment list` reads back `Owner`. After a real VM reboot the GNOME keyring remained unlocked and all checks passed again with `~/.azure` absent and zero `theseus-azure-owner-*` tmpfs leftovers.
- **Google Drive corpus transport:** Google Cloud SDK 592.0.0 is installed. User OAuth was granted with `gcloud auth login --enable-gdrive-access`. The one-time login staging directory lived under `/run/user/1000` on tmpfs. The resulting Google credential was moved into the existing GNOME Secret Service login keyring.
- **Keyring-backed gcloud:** canonical runtime helper `/home/exedev/.local/bin/gcloud-keyring` reconstructs the credential-bearing gcloud state only in a temporary directory under `/run/user/1000`, invokes `gcloud` with the explicit stored account, then removes that temporary directory. The security invariant is **no persistent credential/token material in the default gcloud state**; plain diagnostic calls may create empty SQLite schema files under `~/.config/gcloud`. ADC remains absent. Do not use literal file nonexistence as the auth canary.
- **Drive acceptance:** direct Google Drive API `drive/v3/about` returned HTTP 200 before and after a real VM reboot. Fresh 2026-11-11 readback again confirmed the absolute-path `gcloud-keyring` helper can mint an access token and Drive `/about` returns HTTP 200 without exposing the token. Nested `bash -lc` was observed to reset PATH and hide `~/.local/bin`; use the governed helper path or verify the effective inner-shell PATH. Read-only inspection of default `credentials.db` / `access_tokens.db` found zero credential/token rows; empty schema files are not credential drift.
- **Grafana Cloud observability:** official Grafana `gcx` 1.7.1 is installed at `/home/exedev/.local/share/theseus/gcx/bin/gcx` and projected as `/home/exedev/.local/bin/gcx`. The archive and extracted binary were checked against the same pinned SHA-256 values already versioned in `TeaShaman-cyber/marcopolo-cookbook` issue #133 / `grafana/gcx.sh`.
- **Grafana OAuth/keyring:** context `tealaphid71` uses browser OAuth with `GCX_KEYCHAIN=on`. `~/.config/gcx/config.yaml` is mode 0600; read-only inspection found the OAuth field names but no obvious inline token/refresh-token values. Authentication depends on the same GNOME Secret Service login keyring rather than the MarcoPolo-era `GCX_KEYCHAIN=off` plaintext fallback.
- **Grafana acceptance:** `gcx config check` is online, `gcx dashboards get session-search-candidate` succeeds, and a real Tempo TraceQL metrics query against `grafanacloud-traces` returned nonzero Session Search series. After a real reboot, the keyring remained unlocked and all three checks passed again without re-login.
- **Observability authority boundary:** Grafana Cloud is the shared observability runtime and `gcx` on exe.dev is an operator/readback executor. The canonical Session Search telemetry contract and dashboard-as-code remain owned by `TeaShaman-cyber/theseus-session-search-lab` issue #109; installing `gcx` here does not transfer configuration ownership or authorize Grafana writes.
- **Arcade Cloud operator route:** native exe.dev HTTP Proxy integration `arcade-api` targets `https://api.arcade.dev` and stores/injects the Arcade project `Authorization: Bearer` credential provider-side. The real project key is not stored in GNOME Keyring, shell environment, helper source, or VM filesystem.
- **Arcade SDK runtime:** isolated venv `/home/exedev/.local/share/theseus/arcade-sdk` pins `arcadepy==1.8.0`, matching the previously verified Windows fallback. Versioned helper source is `providers/exe-dev/arcade_proxy.py`; runtime projection is `/home/exedev/.local/lib/theseus/arcade_proxy.py` with launcher `/home/exedev/.local/bin/arcade-proxy-python`. `arcadepy` requires a non-empty client `api_key`, so the helper uses the explicit one-character non-secret placeholder `"x"` while exe.dev injects the real Authorization header at the proxy edge.
- **Arcade acceptance:** direct guest GET through `https://arcade-api.int.exe.xyz/v1/workers/theseus-session-search` returned HTTP 200, and `arcadepy` `workers.get("theseus-session-search")` returned the expected project-bound MCP worker. The provider `integrations test arcade-api` command returned HTTP 422 and is **not** counted as success; real target readback is the acceptance signal. After a real VM reboot the proxy still returned HTTP 200 and the pinned SDK/helper readback passed without re-entering the project key.
- **Arcade authority boundary:** this route restores an operator/control-plane capability that previously needed the user laptop. It does not authorize arbitrary Arcade mutation, does not replace the App-backed Session Search consumer gateway, and does not transfer Session Search configuration authority into the cloud-shell repository.
- **Routing invariant:** Drive corpus transport is direct `exe.dev VM -> keyring-backed gcloud -> Google Drive API`. Arcade/MCP is **not** in this Drive path. Session Search consumer/serving authority remains a separate surface.
- **Known boundary:** the headless keyring unlock uses host-encrypted `systemd-creds` material. Root on this VM can decrypt it; no TPM-backed guarantee is claimed. Reboot persistence is VERIFIED on this host, while pause/cold-resume, VM migration and recovery on a replacement host remain UNKNOWN.

The detailed acceptance trail, including the initial Google helper bug and the later Grafana/gcx reboot acceptance, is recorded in [Theseus Research #112](https://github.com/TeaShaman-cyber/theseus-research/issues/112). Session Search observability design, telemetry privacy, dashboard ownership and TraceQL semantics remain tracked in [Session Search #109](https://github.com/TeaShaman-cyber/theseus-session-search-lab/issues/109).

## Zenodo via exe.dev HTTP proxy (2026-11-27)

The governed VM has an attached native HTTP proxy named `zenodo` targeting `https://zenodo.org/`, with provider-side Bearer injection. Routine unpublished draft operations use `https://zenodo.int.exe.xyz/api/` directly, independent of ChatGPT VZ tool discovery. The existing Vercel adapter remains unchanged.

Read-only acceptance probe:

```sh
curl -fsS https://reflection.int.exe.xyz/integrations |
  jq -e '[.integrations[].name] | index("zenodo") != null'
curl -fsS -H 'Accept: application/vnd.inveniordm.v1+json'   'https://zenodo.int.exe.xyz/api/user/records?size=20' |
  jq '{total:.hits.total,records:[.hits.hits[]|{id,status,is_published}]}'
```

Use current InvenioRDM draft endpoints: POST /api/records creates a draft; GET /api/records/{id}/draft independently verifies it; draft files use initialization, content PUT, commit POST and content readback. Search/list indexing may lag creation; never retry a creation before checking its postcondition. Preserve Git as manuscript authority and Zenodo as its archive projection. Publication, destructive changes and new credential authority remain separate explicit approval boundaries.

Verified in [cloud-shell #39](https://github.com/TeaShaman-cyber/theseus-cloud-shell/issues/39): credential provisioned through owner-approved Desktop Commander Review Panel and native exe.dev stdin, no raw token in guest or Git; attached integration, existing draft reads, new unpublished preprint draft and byte-identical manuscript file readback. See [research #141](https://github.com/TeaShaman-cyber/theseus-research/issues/141) for manuscript-specific evidence. The reused credential's full scopes were not re-inventoried; no publication capability was exercised. Reboot/migration persistence not independently tested for this integration.

## Cloudflare via exe.dev proxy (2026-11-20)

**Verified guest route:** `ChatGPT -> exe.dev MCP run_vm_command -> selected running VM -> https://cloudflare.int.exe.xyz/client/v4/... -> Cloudflare API`. Reflection showed `cloudflare` attached to the VM; the provider-native integration inventory confirmed it configured. A guest read-only `GET /client/v4/accounts` returned HTTP 200. No credentials, account identifiers, or full API response bodies were printed.

**Independent ChatGPT route:** the native Cloudflare connector successfully ran `GET /accounts` with `success=true` and one account in the result. This is a separate session, credential, and permission boundary. It does not establish that the native connector's grant is usable from exe.dev, or vice versa.

**Minimal read-only reprobe** (after fresh `list_vms`):

```bash
set -euo pipefail
curl -fsS --max-time 12 https://reflection.int.exe.xyz/integrations |
  jq -e '[.integrations[]?.name] | index("cloudflare") != null' >/dev/null
status="$(curl -sS --max-time 15 -o /dev/null -w '%{http_code}' \
  https://cloudflare.int.exe.xyz/client/v4/accounts)"
test "$status" = 200
printf 'cloudflare_attachment=present cloudflare_accounts_http=%s\n' "$status"
```

**Authority and limits:** HTTP 200 proves only access to this read-only endpoint at observation time, not Workers, DNS, R2, account-wide administration or write permissions. Before mutation, establish the exact resource, permitted operation and API schema; verify the resulting Cloudflare state independently. Keep provider-held credentials outside guest environment, Git and logs; do not duplicate credentials between native Cloudflare and exe.dev. Reprobe integration attachment after VM replacement, restart or provider changes.

**Observed disposition (2026-11-20):** `VM_RUNNING=VERIFIED`; `CLOUDFLARE_CONFIGURED=VERIFIED`; `CLOUDFLARE_ATTACHED=VERIFIED`; `GUEST_PROXY_ACCOUNTS_HTTP_200=VERIFIED`; `NATIVE_CHATGPT_ACCOUNT_LIST=VERIFIED_INDEPENDENT`; `MUTATION_SCOPES=UNKNOWN_NOT_TESTED`; `PERSISTENCE_AFTER_VM_REPLACEMENT=UNKNOWN_NOT_TESTED`.


## LLM/provider integrations (2026-11-21)

The primary governed VM `theseus-exe-shell-probe` currently reports these provider-facing integrations through Reflection: `openrouter`, `bothub-api`, `groq`, `nvidi-nim`, and `nous`. They are swappable inference routes; none is the architectural authority for Mastra or the dreaming worker.

**NVIDIA NIM verified route:** `ChatGPT -> exe.dev MCP -> theseus-exe-shell-probe -> https://nvidi-nim.int.exe.xyz/v1/... -> https://integrate.api.nvidia.com/v1/...`. The exe.dev HTTP proxy target is the host root `https://integrate.api.nvidia.com/`; request paths such as `/v1/models` are appended by the proxy. The integration stores/injects the Bearer credential provider-side. The current configured integration name is intentionally documented exactly as observed: `nvidi-nim`.

A read-only guest probe of `/v1/models` returned HTTP 200 and 33 model IDs. This proves the attached credential can reach NVIDIA model discovery at the observation time; it does not prove arbitrary inference models, quota, spend, retention terms, or future availability. No inference request was made for this acceptance check.

**Nous Research verified route (2026-11-22):** `ChatGPT -> exe.dev MCP -> theseus-exe-shell-probe -> https://nous.int.exe.xyz/v1/... -> https://inference-api.nousresearch.com/v1/...`. The `nous` HTTP proxy integration stores/injects the user's Nous bearer credential provider-side and is attached directly to `vm:theseus-exe-shell-probe`. A guest `GET /v1/models` returned HTTP 200 with 415 model IDs at acceptance. The local staging helper read `NOUS_API_KEY` only on the user's workstation and sent it to `ssh exe.dev integrations add ... --bearer=-` over stdin; the helper was removed after verification. No Nous credential is stored in the guest or repository. See cloud-shell issue #28.

**Other routes:** Reflection also shows `openrouter`, `bothub-api`, and `groq` attached to the VM. Existing OpenRouter integration metadata states that its credential is injected at the proxy and no API key is required in the guest. For BotHub and Groq, this dated checkpoint records attachment only; endpoint/model capability should be probed when a concrete Mastra/provider decision needs it.

**Credential boundary:** provider secrets must stay in exe.dev integration state rather than repository files, `.env`, shell history, process arguments, issue text, or model-visible logs. An integration being attached establishes availability of that proxy surface, not authorization to spend or send private Session Search evidence to that provider.

Evidence / coordination: [cloud-shell issue #22](https://github.com/TeaShaman-cyber/theseus-cloud-shell/issues/22).

## Neon SQL via provider proxy (2026-11-07)

Route: `ChatGPT -> exe.dev MCP run_vm_command -> verified VM -> https://neon.int.exe.xyz -> Neon management API -> ephemeral connection URI -> /bin/psql -> PostgreSQL`.

**FACT / observed:** Reflection reports the `neon` catalog integration with credentials injected by the provider proxy. `GET /api/v2/projects` returned HTTP 200. On an isolated Session Search benchmark branch, `GET /api/v2/projects/{project_id}/connection_uri?...` returned a standard PostgreSQL URI; the URI itself was never printed. `/bin/psql` then connected to the requested database and a second probe successfully executed a read-only `.sql` file with `psql -f`.

**Credential boundary:** the Neon API credential remains provider-side. The returned database URI contains a Postgres role password and must be treated as ephemeral secret material: keep it only in process/shell memory for the duration of the command, do not echo it, write it to Git, logs, receipts, command-line documentation or persistent config. No dedicated Neon API key, Neon CLI login, or GNOME-Keyring credential is currently required in the VM.

**Authority boundary:** the provider integration can obtain connection material, but the selected Postgres role still determines database authority. Existing capability roles and project-specific change control remain authoritative. Connection success does not authorize arbitrary DDL/DML or disclosure of private corpus rows.

**Repo-native SQL path:** use a version-controlled SQL file as the input and `psql -f`, rather than copying a long SQL body through an MCP/JSON payload. A bounded pattern is:

    set -euo pipefail
    uri_json="$(mktemp)"
    trap 'rm -f "$uri_json"' EXIT
    curl -fsS       "https://neon.int.exe.xyz/api/v2/projects/$PROJECT_ID/connection_uri?branch_id=$BRANCH_ID&database_name=$DATABASE_NAME&role_name=$ROLE_NAME&pooled=false"       -o "$uri_json"
    uri="$(jq -er '.uri' "$uri_json")"
    PGCONNECT_TIMEOUT=10 psql "$uri" -X -v ON_ERROR_STOP=1 -f path/to/versioned.sql
    unset uri

Callers must source `PROJECT_ID`, `BRANCH_ID`, `DATABASE_NAME`, and `ROLE_NAME` from the authorized project workflow rather than hard-code remembered runtime identities. For migrations requiring a capability role, use the already-authorized Postgres role transition (for example `SET LOCAL ROLE ...`) rather than creating or broadening credentials merely to run the migration.

**Current disposition:** `NEON_INTEGRATION_ATTACHED=VERIFIED`; `MANAGEMENT_API=VERIFIED`; `CONNECTION_URI=VERIFIED`; `PSQL_DIRECT_CONNECT=VERIFIED`; `PSQL_FILE_EXECUTION=VERIFIED`; `SEPARATE_NEON_CLI_KEYRING=NOT_NEEDED_CURRENTLY`. Revisit a dedicated CLI/keyring only if the provider proxy cannot support a required operation or if a later workflow needs an independent credential boundary.

Evidence / coordination: [theseus-cloud-shell#10](https://github.com/TeaShaman-cyber/theseus-cloud-shell/issues/10).

## Turso Platform API and libSQL data plane via exe.dev

Route boundaries:

```text
management: ChatGPT -> exe.dev MCP -> selected VM -> https://turso.int.exe.xyz -> Turso Platform API
database: selected VM -> short-lived DB token -> database host /v1/upload or /v2/pipeline
```

**FACT / credential boundary:** the attached exe.dev `turso` integration stores and injects the durable Turso Platform API credential at the provider proxy. The guest does not need that credential in environment variables, files, Git, or command arguments.

**FACT / DB-token and data-plane route (2026-11-22):** the Platform API successfully minted short-lived database tokens through the provider proxy. Repository Search used those tokens only transiently, then uploaded existing SQLite/FTS5 projections directly through the database host `/v1/upload` endpoint. SQL-over-HTTP readback through `/v2/pipeline` independently returned expected artifact identity, row counts, FTS results, `PRAGMA quick_check = ok`, `PRAGMA integrity_check = ok`, WAL mode, and page geometry. A roughly 460 MB projection was accepted by this route.

**FACT / libSQL compatibility:** the current Repository Search `fts5(... tokenize=unicode61)` query schema worked without translation to PostgreSQL. Ordinary FTS query parity was observed against the local SQLite reference.

**Observed limitation:** SQL-over-HTTP rejected connection-local `CREATE VIRTUAL TABLE temp... USING fts5vocab(...)` in the tested route. Repository Search ordinary FTS remains usable, but its existing local `projection_fingerprint()` cannot yet be recomputed remotely by that exact inspection method. Do not weaken the fingerprint contract to hide this limitation.

**Independent ChatGPT surface:** the native Turso MCP can create/configure databases and run SQL, but it is a separate OAuth/credential and permission boundary from the exe.dev provider integration. Success on one surface does not authorize the other.

The small management re-probe from the earlier 2026-11-07 section remains appropriate for checking current integration reachability: list organizations, derive the visible organization from the response, and list databases through `https://turso.int.exe.xyz`. That read-only probe does not by itself prove fresh DB-token or SQL capability.

**Current disposition:** `TURSO_INTEGRATION_ATTACHED=VERIFIED`; `PLATFORM_API=VERIFIED`; `DB_TOKEN_MINT=VERIFIED`; `SQL_OVER_HTTP=VERIFIED`; `SQLITE_UPLOAD=VERIFIED`; `FTS5_UNICODE61=VERIFIED`; `REMOTE_TEMP_FTS5VOCAB=UNAVAILABLE_OBSERVED`; `NATIVE_CHATGPT_TURSO_MCP=VERIFIED_SEPARATE_SURFACE`.

Evidence / coordination: [theseus-cloud-shell#6](https://github.com/TeaShaman-cyber/theseus-cloud-shell/issues/6), [theseus-cloud-shell#30](https://github.com/TeaShaman-cyber/theseus-cloud-shell/issues/30), [Repository Search #132](https://github.com/TeaShaman-cyber/theseus-repo-search-lab/issues/132), and merged [Repository Search PR #133](https://github.com/TeaShaman-cyber/theseus-repo-search-lab/pull/133).
## MotherDuck native DuckDB via exe.dev (2026-11-25)

The attached HTTP Proxy integration `motherduck` targets `https://api.motherduck.com`; exe.dev retains and injects the permanent Bearer credential. Native DuckDB uses a temporary 300-second Read/Write token from the REST API, not an MCP relay. No separate keyring or permanent VM credential is needed.

Run trusted, reviewed SQL files with the governed launcher from the checked-out repository:

```sh
python3 providers/exe-dev/motherduck_native.py my_db /absolute/path/to/query.sql
```

The launcher requires the verified single-user account shape (one active human user, no pagination; otherwise it fails closed). It mints a uniquely named token through the provider proxy, gives it to DuckDB only in the child environment, uses temporary HOME/XDG paths on tmpfs, disables core dumps and skips the CLI init file. It imposes a 240-second subprocess timeout, revokes the exact minted token and independently checks absence; ambiguous mint outcomes are reconciled by unique name without reissuing POST. Output is CSV buffered until successful execution and cleanup. Driver error details are suppressed because they may contain credentials. Do not use untrusted SQL or SQL that exports credentials. The temporary token still has the user's read/write authority while valid; tmpfs and revocation do not prove forensic erasure. A hard termination or unavailable cleanup API may leave the token valid until its requested expiry. Reconcile before retrying an ambiguous stateful SQL operation.

**Live acceptance:** local DuckDB 1.5.5 connected to MotherDuck 1.5.6 and read `my_db`. A local 399,960-byte ZSTD Parquet fixture of 100,000 synthetic graph edges was loaded using `CREATE TABLE ... AS SELECT * FROM read_parquet(...)`. A fresh native connection and the separate official ChatGPT MCP both returned 100,000 rows, 100,000 distinct source IDs, and zero formula/NULL/domain mismatches. The unique test table was dropped and catalog readback returned zero remaining tables of that name; the local fixture was removed. No existing table was changed. This is an ingestion-path acceptance, not a benchmark or proof that a complete RH corpus fits the account or the launcher's timeout.

**Status:** `REST_PROXY=VERIFIED`; `NATIVE_DUCKDB=VERIFIED`; `PARQUET_100K_INGEST=VERIFIED`; `SEPARATE_CHATGPT_MCP=VERIFIED`; `FULL_CORPUS_INGEST=UNKNOWN`.

Evidence: [Cloud Shell #32](https://github.com/TeaShaman-cyber/theseus-cloud-shell/issues/32), [Repository Search #131](https://github.com/TeaShaman-cyber/theseus-repo-search-lab/issues/131). Vendor API: [create token](https://motherduck.com/docs/sql-reference/rest-api/users-create-token/), [revoke token](https://motherduck.com/docs/sql-reference/rest-api/users-delete-token/).

### Routing summary: direct MCP vs provider-native control

The current control model is intentionally two-layered:

```text
ChatGPT exe.dev MCP
  -> list_vms / create_vm / run_vm_command / get_cli_help
  -> selected guest

selected guest + attached provider integration
  -> https://exe.int.exe.xyz/exec       # exe.dev account control
  -> https://<service>.int.exe.xyz/...  # provider-held service credential/proxy
```

Therefore, **not exposed as a direct MCP action != unavailable**. For account-control work, first confirm the live VM and that the provider-native `exe` integration is attached, then use a bounded read-only `/exec` canary before consequential account operations. For service integrations, distinguish catalog availability, configured integration, attachment to this VM, and real target readback.

Likewise, guest shell `PATH`, credential stores and repository runtime pins are part of routing. A helper hidden by a login shell, a raw CLI bypassing its governed wrapper, or a host-default Python mismatch is not evidence that the underlying provider capability is broken.

## Actual ChatGPT MCP surface

Executable: `get_cli_help`, `list_vms`, `create_vm`, `run_vm_command`.
NOT EXPOSED **as direct ChatGPT MCP actions**: `pause`, `resume`, `billing`, `integrations add/list/attach/test`. This does **not** mean exe.dev account controls are unavailable to us: when the provider-native `exe` integration is attached to the selected VM, it supplies an authenticated account-control bridge at `https://exe.int.exe.xyz/exec`. Do not try nested `ssh exe.dev` as a prerequisite, and do not infer account-level unavailability from the four MCP actions alone.

### Provider-native account control from inside the VM (2026-11-07)

Live target `theseus-exe-shell-probe` was confirmed running. Reflection lists `exe` and `turso` attached; direct POST from the VM to `https://exe.int.exe.xyz/exec` succeeded for `whoami --json`, `integrations list --json` (11 configured entries), and `integrations catalog upstash --json` (Upstash available). This is independently checked current evidence, not simply an advertised CLI command.

Safe read-only verification, using bounded output and no secret fields:

```bash
curl -fsS https://reflection.int.exe.xyz/integrations |
  jq -e '[.integrations[].name] | index("exe") != null'
curl -fsS -X POST https://exe.int.exe.xyz/exec   --data-raw 'integrations list --json' |
  jq -c 'if type == "array" then {"count":length} else {"keys":keys} end'
curl -fsS -X POST https://exe.int.exe.xyz/exec   --data-raw 'integrations catalog upstash --json' |
  jq -c 'if type == "array" then {"count":length} else {"keys":keys} end'
```

Boundaries: `exe` is a provider-held delegated integration, so it must be re-probed on each VM and used within its actual granted authority. Keep all integration credentials provider-side, never in ChatGPT output, the VM environment, command strings, Git or logs. Current Upstash catalog requires a concrete database `subdomain` and secret REST `token`. Seeing a catalog entry is **not** evidence of an Upstash database or attached integration; no Redis resource or key has been created. The original guest `ssh exe.dev` permission denial and laptop SSH registration prompt were irrelevant to this functioning bridge. See Theseus Research #112 and cloud-shell issue #8.

For commands: use bounded calls and verify guest exit and external target readback. Failed composition/host filtering is not guest failure; do not repeat an uncertain stateful operation blindly.

## GitHub and credentials: historical accepted probe

At trial VM, GitHub CLI 2.103.3 used native OAuth device flow (full granted GitHub scopes determined by `gh auth status`), then migrated existing token into GNOME Secret Service with `gh auth token | gh auth login --with-token` entirely inside VM. No token crossed chat/tools. The initial headless OAuth wrote plaintext `hosts.yml`; migration readback established `(keyring)`, **zero nonempty inline oauth_token fields**, API and private Git reads PASS.

No desktop login exists. Ubuntu GNOME Keyring was configured for automatic unlock through a user systemd service override using `systemd-creds` with host-encrypted unlock material; a genuine reboot confirmed `Locked=false`, `gh api user` and normal private HTTPS `git ls-remote` PASS. The host key is not a TPM guarantee; privileged root access on the guest can decrypt. Neither keyring migration nor credential recovery to a new host has been tested. Never copy token/keyring material into Git.

**Source of exact commands and verification:** [Theseus Research #112](https://github.com/TeaShaman-cyber/theseus-research/issues/112). This provider guide points to the receipt; it does not copy secret-bearing configuration, and does not certify cross-host portability.

## Cost / lifecycle boundary

User confirmed a 7-day trial; live account billing and exact final charges are **UNKNOWN** from the exposed MCP tools. Provider pause/resume cannot currently be invoked directly from this MCP: standby lifecycle still **NOT_TESTED**, not equivalent to reboot. Prefer one VM and short work until plan limits and acceptance are confirmed.

**Next capacity-specific gap:** an authorized account-admin route for lifecycle/billing or explicit NOT_EXPOSED disposition. No duplicate MCP bus or self-written OAuth system by default.

## Session Search accepted-corpus recovery handoff

Coordination: `TeaShaman-cyber/theseus-session-search-lab#211` and this repository issue #12.

The exe.dev adapter source is `providers/exe-dev/session_search_drive.py`. It reuses the existing keyring-backed Google OAuth route and the Session Search repo-native handoff validator; it does not define corpus authority itself.

Recovery route:

```text
current Drive pointer (discovered by protocol property)
  -> immutable recovery receipt
  -> exact projection + accepted-evidence Drive objects
  -> byte/hash readback
  -> decode projection according to receipt encoding
  -> session_search.recovery_handoff verify-local
  -> private local corpus lock
```

The pointer is discovered by Drive custom property (`theseus_recovery_kind=session-search-current-v1`), not by a corpus filename, date, row count, or remembered Drive ID. Zero or multiple pointers fail closed.

Publication is the final acceptance step for a newly verified corpus. The adapter first re-downloads the already staged projection/evidence objects and verifies their exact identities, uploads and reads back an immutable receipt, then updates the single current pointer. Existing pointer bytes are retained before update; a mismatched post-update readback triggers restoration and verification of the previous pointer. Publication finishes only after a fresh-runtime-style recovery probe recreates a valid local corpus lock.

Large recovery projection/evidence objects are staged through the adapter's bounded resumable uploader rather than loaded into model/chat memory or one giant request body:

    session_search_drive.py --session-search-repo <repo> stage-file \
      --source <private-file> \
      --kind <session-search-projection-v1|session-search-evidence-v1> \
      --receipt-out <private-0600-json> \
      --workdir <private-readback-dir>

stage-file uploads bounded chunks, independently downloads the resulting object, verifies exact size/SHA, deletes the temporary readback copy, and prints only bounded public-safe status metadata. The mode-0600 receipt contains the private Drive ID/size/SHA needed to assemble the subsequent publish spec. Staging never updates the current recovery pointer; publish remains the only pointer-promotion path.

Provider-specific Drive IDs, hashes, private filenames, OAuth tokens and corpus contents are never printed by the adapter or committed here. Accepted evidence remains authority; Drive remains private recovery transport.
