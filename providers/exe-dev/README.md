# exe.dev provider adapter

Status on 2026-11-07: **preferred governed Linux shell candidate**, under seven-day user-confirmed trial. Not yet a permanent production identity. Existing VM `theseus-exe-shell-probe`: Ubuntu 24.04, 2 vCPU, 4 GiB RAM, 20 GiB disk, Frankfurt. Reprobe before action.

## Current infrastructure

Observed current state on `theseus-exe-shell-probe`:

- **GitHub:** native `gh` OAuth is stored in GNOME Secret Service, not inline in `~/.config/gh/hosts.yml`. A real reboot verified automatic headless keyring unlock, `gh api`, private HTTPS Git and ordinary `git ls-remote`.
- **Neon:** exe.dev catalog integration `neon` is attached to the VM and the Neon management API returned HTTP 200 in the accepted probe. This is management-plane access only; it does **not** imply raw Postgres/SQL credentials or permission to expose Session Search corpus rows.
- **Google Drive corpus transport:** Google Cloud SDK 592.0.0 is installed. User OAuth was granted with `gcloud auth login --enable-gdrive-access`. The one-time login staging directory lived under `/run/user/1000` on tmpfs. The resulting Google credential was moved into the existing GNOME Secret Service login keyring.
- **Keyring-backed gcloud:** runtime helper `/home/exedev/.local/bin/gcloud-keyring` reconstructs `credentials.db` only in a temporary directory under `/run/user/1000`, invokes `gcloud` with the explicit stored account, then removes the temporary directory. Persistent `~/.config/gcloud/credentials.db`, `access_tokens.db`, and `application_default_credentials.json` are absent.
- **Drive acceptance:** direct Google Drive API `drive/v3/about` returned HTTP 200 before and after a real VM reboot. After reboot the login keyring was independently observed as unlocked, the Google credential was present, keyring-backed access-token mint succeeded, and persistent gcloud credential files remained absent.
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

## Actual ChatGPT MCP surface

Executable: `get_cli_help`, `list_vms`, `create_vm`, `run_vm_command`.
NOT EXPOSED: `pause`, `resume`, `billing` as first-class ChatGPT MCP actions. Account-level integration administration may be reachable only through a separately verified administrative route; do not infer availability from CLI help alone.

For commands: use bounded calls and verify guest exit and external target readback. Failed composition/host filtering is not guest failure; do not repeat an uncertain stateful operation blindly.

## GitHub and credentials: historical accepted probe

At trial VM, GitHub CLI 2.103.3 used native OAuth device flow (full granted GitHub scopes determined by `gh auth status`), then migrated existing token into GNOME Secret Service with `gh auth token | gh auth login --with-token` entirely inside VM. No token crossed chat/tools. The initial headless OAuth wrote plaintext `hosts.yml`; migration readback established `(keyring)`, **zero nonempty inline oauth_token fields**, API and private Git reads PASS.

No desktop login exists. Ubuntu GNOME Keyring was configured for automatic unlock through a user systemd service override using `systemd-creds` with host-encrypted unlock material; a genuine reboot confirmed `Locked=false`, `gh api user` and normal private HTTPS `git ls-remote` PASS. The host key is not a TPM guarantee; privileged root access on the guest can decrypt. Neither keyring migration nor credential recovery to a new host has been tested. Never copy token/keyring material into Git.

**Source of exact commands and verification:** [Theseus Research #112](https://github.com/TeaShaman-cyber/theseus-research/issues/112). This provider guide points to the receipt; it does not copy secret-bearing configuration, and does not certify cross-host portability.

## Cost / lifecycle boundary

User confirmed a 7-day trial; live account billing and exact final charges are **UNKNOWN** from the exposed MCP tools. Provider pause/resume cannot currently be invoked directly from this MCP: standby lifecycle still **NOT_TESTED**, not equivalent to reboot. Prefer one VM and short work until plan limits and acceptance are confirmed.

**Next capacity-specific gap:** an authorized account-admin route for lifecycle/billing or explicit NOT_EXPOSED disposition. No duplicate MCP bus or self-written OAuth system by default.
