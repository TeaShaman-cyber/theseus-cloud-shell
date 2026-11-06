# Theseus Cloud Shell

A single, provider-neutral home for **tested remote Linux / MCP engineering experience** across Theseus. When a new cloud-shell provider appears, add a provider adapter here rather than starting another repository.

**Governance:** [Theseus Project Contract](https://github.com/TeaShaman-cyber/theseus-research/blob/main/governance/chatgpt-project-contract.yaml) remains the source of authority. Cloud Shell owns operational guidance and reusable code, **not** project permission or provider secrets.

## Start here

- [AGENTS.md](AGENTS.md) — thin agent entrypoint.
- [RULES.md](RULES.md) — portable runtime invariants.
- [Exe.dev](providers/exe-dev/README.md) — current preferred cloud-shell route, observable limits, credential lifecycle.
- [Fly Sprites](providers/sprites/README.md) — provider adapter; original evidence stays in [theseus-sprites](https://github.com/TeaShaman-cyber/theseus-sprites).
- [MarcoPolo](providers/marcopolo/README.md) — legacy/fallback adapter; original evidence stays in [marcopolo-cookbook](https://github.com/TeaShaman-cyber/marcopolo-cookbook).
- [Native GitHub](modules/github/README.md) — reusable `git`/`gh` and API acceptance boundaries.
- [Repository map](docs/repository-map.md) — exact-SHA, derived navigation artifacts, based on [Session Search #152](https://github.com/TeaShaman-cyber/theseus-session-search-lab/issues/152).

Historical coordination: [Theseus Research #106](https://github.com/TeaShaman-cyber/theseus-research/issues/106), [exe.dev #112](https://github.com/TeaShaman-cyber/theseus-research/issues/112), [consolidation #113](https://github.com/TeaShaman-cyber/theseus-research/issues/113).

The Git repo contains source and verified runbooks, **not** VM filesystems, OAuth secrets, private backups, or live credentials. An installed plugin/runtime is a separate state and requires independent readback.

Run the offline source check with `python3 tools/dev/check.py`.
