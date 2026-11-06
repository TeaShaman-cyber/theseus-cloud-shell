---
name: exe-dev-core-router
description: Route Theseus exe.dev operations involving VM identity, MCP shell, GitHub credentials, provider capability gaps, verification or fallback. Subordinate to the Project Contract.
---

# exe.dev Core Router

The **installed** Theseus Project Contract governs authority, permissions and change control. This skill points to canonical operational guidance, not a competing policy.

1. For cloud-shell operations confirm the selected provider and live target VM with `list_vms`. Use provider-returned identity, not a remembered host.
2. Read current `TeaShaman-cyber/theseus-cloud-shell/RULES.md` and `providers/exe-dev/README.md` only as needed; a Git commit does not prove this plugin skill is installed.
3. Use `run_vm_command` for bounded exact guest actions. Observe status and independent postcondition; after a blocked/timeout response, do not assume guest execution failed or repeat stateful work blindly.
4. MCP currently exposes `get_cli_help`, `list_vms`, `create_vm`, `run_vm_command`. Account operations like `integrations`, `billing`, `pause`, `resume` can appear in help but are **NOT_EXPOSED** as executable MCP actions. Guest shell access does not authorize exe.dev admin SSH.
5. Native `gh`/GitHub OAuth, provider GitHub App, Secret Service/keyring and API permissions are separate. Probe required route; do not print OAuth tokens or move keyrings across machines.
6. Historical exe.dev trial machine `theseus-exe-shell-probe` passed GitHub OAuth, keyring migration and reboot unlock on 2026-11-06; this is **dated evidence**, not production identity or proof of pause/resume and restoration on another host.
7. Git source, guest filesystem, provider state, credentials, session-history projections and telemetry remain distinct. Select a finite fallback only after observed insufficiency; report `DEGRADED`, `BLOCKED`, `UNKNOWN` rather than guessing.
8. Verify meaningful writes by exact target readback and keep durable receipts in the covering Issue.

Provider docs refine mechanics but never override the Project Contract or grant authorization. Detailed evidence: `theseus-research#112`.
