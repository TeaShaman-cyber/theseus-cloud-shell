# exe.dev provider adapter

Status on 2026-11-06: **preferred governed Linux shell candidate**, under seven-day user-confirmed trial. Not yet a permanent production identity. Existing VM `theseus-exe-shell-probe`: Ubuntu 24.04, 2 vCPU, 4 GiB RAM, 20 GiB disk, Frankfurt. Reprobe before action.

## Actual ChatGPT MCP surface

Executable: `get_cli_help`, `list_vms`, `create_vm`, `run_vm_command`.
NOT EXPOSED: `pause`, `resume`, `billing`, `integrations add/list/attach/test`, despite vendor CLI help describing these commands. The guest does not automatically authenticate to administrative `ssh exe.dev`. Do not substitute `get_cli_help` for execution.

For commands: use bounded calls and verify guest exit and external target readback. Failed composition/host filtering is not guest failure; do not repeat an uncertain stateful operation blindly.

## GitHub and credentials: historical accepted probe

At trial VM, GitHub CLI 2.103.3 used native OAuth device flow (full granted GitHub scopes determined by `gh auth status`), then migrated existing token into GNOME Secret Service with `gh auth token | gh auth login --with-token` entirely inside VM. No token crossed chat/tools. The initial headless OAuth wrote plaintext `hosts.yml`; migration readback established `(keyring)`, **zero nonempty inline oauth_token fields**, API and private Git reads PASS.

No desktop login exists. Ubuntu GNOME Keyring was configured for automatic unlock through a user systemd service override using `systemd-creds` with host-encrypted unlock material; a genuine reboot confirmed `Locked=false`, `gh api user` and normal private HTTPS `git ls-remote` PASS. The host key is not a TPM guarantee; privileged root access on the guest can decrypt. Neither keyring migration nor credential recovery to a new host has been tested. Never copy token/keyring material into Git.

**Source of exact commands and verification:** [Theseus Research #112](https://github.com/TeaShaman-cyber/theseus-research/issues/112). This provider guide points to the receipt; it does not copy secret-bearing configuration, and does not certify cross-host portability.

## Cost / lifecycle boundary

User confirmed a 7-day trial; live account billing and exact final charges are **UNKNOWN** from the exposed MCP tools. Provider pause/resume cannot currently be invoked directly from this MCP: standby lifecycle still **NOT_TESTED**, not equivalent to reboot. Prefer one VM and short work until plan limits and acceptance are confirmed.

**Next capacity-specific gap:** an authorized account-admin CLI/API route for integrations, billing and pause/resume, or explicit NOT_EXPOSED disposition. No duplicate MCP bus or self-written OAuth system by default.
