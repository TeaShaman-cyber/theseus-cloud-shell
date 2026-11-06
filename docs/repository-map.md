# Source map: cheap navigation, not architecture authority

Reuse [Session Search repository-map #152](https://github.com/TeaShaman-cyber/theseus-session-search-lab/issues/152) and its current `.github/workflows/repository-map.yml`, instead of building another hosted diagram server.

`exact Git checkout -> dekko==1.9.0 -> SUMMARY.txt / MAP.md / map.json -> git ls-files -> CI artifact`.

The generated files are **derived/non-authoritative** and retained as workflow artifacts, not committed. The tracked-file listing compensates for languages or extensionless scripts not parsed by dekko. Always bind map to source SHA. A static graph cannot attest live provider capabilities, credentials, billing, VM uptime or current permissions.

Start at `AGENTS.md` for agent routing, `RULES.md` for common invariants, then `providers/<name>/README.md` or `modules/<capability>/README.md`. For actual execution verify current runtime identity and authorized tool surface.
