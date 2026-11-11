---
name: exe-dev-core-router
description: Route Theseus exe.dev operations involving live VM identity, direct MCP versus guest/provider control surfaces, governed wrappers and credentials, runtime selection, verification and finite fallback. Subordinate to the Project Contract.
---

# exe.dev Core Router

Thin project-specific guardrail. The **installed** Theseus Project Contract governs authority, permissions and change control. Current mechanics live in `TeaShaman-cyber/theseus-cloud-shell`; vendor docs refine mechanics only.

## Fast path

1. Identify the authority domain before selecting a tool.
2. Confirm the selected provider and exact live VM with `list_vms`; use provider-returned identity, not a remembered host.
3. Read only the smallest current section of `RULES.md` or `providers/exe-dev/README.md` needed for this branch.
4. Choose the thinnest valid route that preserves permission, credential boundary, verification and required durability.
5. Treat capability != permission and visible/cached state != current authority.
6. Claim success only after an observable authoritative postcondition.

## Control surfaces

Keep these routes distinct:

- **Direct ChatGPT exe.dev MCP:** `get_cli_help`, `list_vms`, `create_vm`, `run_vm_command`.
- **Guest shell:** bounded commands executed through `run_vm_command`.
- **Provider-native account bridge:** when the selected VM has the provider `exe` integration attached, account-control commands can be executed from the guest through `https://exe.int.exe.xyz/exec`. This is an available verified route, not a direct MCP action. Re-probe the attachment/current target before use.
- **Provider integration proxies:** attached services may expose credential-injecting `*.int.exe.xyz` endpoints. Catalog availability is not proof that an integration is configured or attached.
- **External service APIs / native connectors:** remain separate authority surfaces.

Missing a direct MCP action does **not** prove the provider capability is unavailable. `get_cli_help` is documentation, not execution. Guest access does not imply provider-admin SSH authority.

## Guest execution and shell composition

Use `run_vm_command` for bounded exact guest actions and preserve guest exit/status separately from provider or target readback.

Avoid `bash -lc` unless login-shell semantics are actually required. A login shell can replace PATH and hide `~/.local/bin`; this was observed with the governed Google Drive wrapper `gcloud-keyring`. If an expected helper appears missing:

1. inspect the effective **inner-shell** PATH;
2. check the documented absolute path in the current provider adapter;
3. only then diagnose missing capability.

Prefer the exact absolute path for a governed wrapper when practical. Do not repair PATH, credentials or runtime state merely to make a probe green.

After a blocked, timeout or ambiguous stateful result, inspect the guest/target postcondition before retry. Never blindly repeat a mutation.

## Credentials, integrations and governed wrappers

Native `gh` OAuth, provider-held integrations, GNOME Secret Service, service-specific OAuth, database roles and returned ephemeral credentials are separate surfaces.

When a provider-native integration already supplies the required credential boundary, prefer that route over duplicating secrets into the guest. Never infer one service's authorization from another.

When a current provider adapter defines a **governed wrapper** (for example a keyring-backed or tmpfs-backed CLI launcher), use the adapter as the mechanics authority rather than bypassing it with the raw CLI. Do not encode mutable account IDs, secrets, Drive IDs, integration counts or wrapper internals in this skill.

## Runtime and repository QA

Do not assume the VM default interpreter/toolchain satisfies a repository contract. Before QA, packaging or migration:

1. read the repository's pinned runtime/toolchain;
2. select the exact interpreter, venv or launcher required by that repo;
3. classify a host default-version mismatch as an environment result, not a source regression.

## Cross-runtime file bridge

Prefer, in order:

1. a directly available native file/reference bridge;
2. authorized Google Drive when both source and destination have a governed Drive route;
3. another explicit project-approved transport;
4. model-visible base64 chunking only as a last resort.

On exe.dev, use the governed Drive route from the provider adapter rather than plain persistent gcloud authentication. For consequential artifacts, record/verify size and cryptographic hash at both ends when practical. Transport evidence is not authority over artifact meaning or destination action.

## Failure taxonomy

Do not collapse these into one diagnosis:

- **MCP/control-plane** rejection or transport failure;
- guest command not started / execution unknown;
- guest command nonzero exit;
- **provider proxy HTTP** failure;
- external target refusal;
- credential/authentication failure;
- permission/capability mismatch;
- authoritative postcondition unknown.

A 403, timeout, internal error or missing tool name is a routing signal, not a complete diagnosis. If the required evidence cannot be established, report `DEGRADED`, `BLOCKED`, `UNKNOWN` or `REPROBE_REQUIRED` rather than guessing.

## Fallback and currentness

Use a finite fallback only after observed insufficiency of the selected route, preserving identity, permission and postcondition semantics. Do not route-switch to evade a real provider/service refusal.

Current authority layers:

`installed Project Contract > installed exe-dev router > current theseus-cloud-shell RULES/provider adapter > vendor docs > dated historical receipts`.

Historical `theseus-research#112` evidence is useful provenance, not current runtime authority. A Git commit does not prove this installed skill is current; installed plugin state requires independent readback.

Verify meaningful writes by exact target readback and keep durable receipts in the covering Issue when the workflow requires persistence.
