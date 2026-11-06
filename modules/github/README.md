# Native GitHub module

Purpose: one portable GitHub conformance recipe, not another credential provider.

- Authenticate via supported GitHub CLI OAuth/credential store appropriate to the host. Granted scopes != permission to take unrelated actions.
- After `gh auth status`, verify the required **specific** capability: `gh repo view` (private repo), `git ls-remote` (native Git helper), `gh api graphql` for Projects V2, and Actions API when needed.
- A successful GitHub App integration or REST request is not proof of native `gh` or unrestricted account-level operations.
- `gh auth setup-git` binds HTTPS credential handling; check ordinary git independently. Never emit `gh auth token` to tool-visible output, Git or logs.
- A headless Linux host should have a verified Secret Service (GNOME Keyring or equivalent) before device login; GitHub CLI may otherwise fall back to plaintext `hosts.yml`. If migrating an existing session, use a guest-private pipe, no token exposure, and verify stored location without reading values.
- On reboot, independently check keyring unlock, GitHub API and private Git; host portability, encrypted-key backups and explicit recovery remain separate gates.

Original reproducible incident: [exe.dev #112](https://github.com/TeaShaman-cyber/theseus-research/issues/112); credential-helper collision: [MarcoPolo #3](https://github.com/TeaShaman-cyber/marcopolo-cookbook/issues/3). Do not turn a read-only smoke into a write authorization.
