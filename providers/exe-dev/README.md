# exe.dev provider adapter

Status on 2026-11-07: **preferred governed Linux shell candidate**, under seven-day user-confirmed trial. Not yet a permanent production identity. Existing VM `theseus-exe-shell-probe`: Ubuntu 24.04, 2 vCPU, 4 GiB RAM, 20 GiB disk, Frankfurt. Reprobe before action.

## Current infrastructure

Observed current state on `theseus-exe-shell-probe`:

- **GitHub:** native `gh` OAuth is stored in GNOME Secret Service, not inline in `~/.config/gh/hosts.yml`. A real reboot verified automatic headless keyring unlock, `gh api`, private HTTPS Git and ordinary `git ls-remote`.
- **Neon:** exe.dev catalog integration `neon` is attached to the VM and the Neon management API returned HTTP 200 in the accepted probe. This is management-plane access only; it does **not** imply raw Postgres/SQL credentials or permission to expose Session Search corpus rows.
- **Google Drive corpus transport:** Google Cloud SDK 592.0.0 is installed. User OAuth was granted with `gcloud auth login --enable-gdrive-access`. The one-time login staging directory lived under `/run/user/1000` on tmpfs. The resulting Google credential was moved into the existing GNOME Secret Service login keyring.
- **Keyring-backed gcloud:** runtime helper `/home/exedev/.local/bin/gcloud-keyring` reconstructs `credentials.db` only in a temporary directory under `/run/user/1000`, invokes `gcloud` with the explicit stored account, then removes the temporary directory. Persistent `~/.config/gcloud/credentials.db`, `access_tokens.db`, and `application_default_credentials.json` are absent.
- **Drive acceptance:** direct Google Drive API `drive/v3/about` returned HTTP 200 before and after a real VM reboot. After reboot the login keyring was independently observed as unlocked, the Google credential was present, keyring-backed access-token mint succeeded, and persistent gcloud credential files remained absent.
- **Routing invariant:** Drive corpus transport is direct `exe.dev VM -> keyring-backed gcloud -> Google Drive API`. Arcade/MCP is **not** in this Drive path. Session Search consumer/serving authority remains a separate surface.
- **Known boundary:** the headless keyring unlock uses host-encrypted `systemd-creds` material. Root on this VM can decrypt it; no TPM-backed guarantee is claimed. Reboot persistence is VERIFIED on this host, while pause/cold-resume, VM migration and recovery on a replacement host remain UNKNOWN.

The detailed acceptance trail, including the initial helper bug where the reconstructed account was visible but not ACTIVE and the correction to explicit `--account`, is recorded in [Theseus Research #112](https://github.com/TeaShaman-cyber/theseus-research/issues/112).

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
