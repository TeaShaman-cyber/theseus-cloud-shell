# Experiment artifact housekeeping — creation, retention and verified cleanup

**Coordination:** [Cloud Shell #14](https://github.com/TeaShaman-cyber/theseus-cloud-shell/issues/14). Pattern borrowed from [Session Search Neon housekeeping #235](https://github.com/TeaShaman-cyber/theseus-session-search-lab/issues/235) and its [verified inventory](https://github.com/TeaShaman-cyber/theseus-session-search-lab/blob/main/docs/neon-housekeeping.md).

This is a **versioned operational rule**, not authority to remove local data. For the current exe.dev VM always verify runtime identity, filesystem state, live dependencies, accepted source identity and current covering Issue before cleanup. A prior `du` size or Git commit is not current proof of removability.

## Prevent archaeology: give significant artifacts a lifecycle at creation

For an experiment directory or a nontrivial artifact (large, expensive to rebuild, containing source/evidence, or lasting beyond one test), record in the owning Issue or a small manifest alongside that directory:

| Field | Minimum meaning |
| --- | --- |
| `host/path` | Current VM/runtime identity plus **exact** path; do not assume paths transfer across providers |
| `owner` | Owning repository, Issue, agent/run; optional PR |
| `purpose` | Why it exists and which postcondition it verifies |
| `class` | Lifecycle status below |
| `source` | Source SHA, accepted corpus identity/generation or input artifact URI when relevant |
| `evidence` | Bytes, checksum/manifest, output receipt and independently accepted source/backup pointer when material |
| `retention` | Specific trigger to review/retire (e.g., issue closed + accepted release verified + rollback window discharged), not merely an arbitrary calendar age |
| `cleanup` | The safe action and how to verify resulting absence and remaining authority/recoverability |

Capture this **per experiment**, not per cache file: ordinary package-manager caches may use a shared known `TEMP` lifecycle. Do not publish private corpus content, filesystem secrets, credentials, or bearer tokens in public Git/Issues. If an experiment is interrupted, write `PENDING_CLEANUP` with an exact candidate and missing prerequisite.

## Classification and deletion boundary

- `KEEP_ACTIVE`: current service, active project state, needed toolchain. Do not delete.
- `KEEP_RECOVERY_OR_SOURCE`: accepted source, independent backup or required rollback evidence. Do not delete until source and rollback obligations are discharged.
- `REVIEW_DELETE`: suspected obsolete experiment; requires exact owner/evidence, checksums where helpful, current process/dependency review, independent recovery route and explicit cleanup scope. A category is a candidate, not deletion approval.
- `UNKNOWN_NEED_EVIDENCE`: origin, dependencies or retention unknown. Never guess; leave a narrow question with the owner Issue.
- `TEMP`: reproducible installation/build artifact with a known cleanup trigger, no active consumer, and independently recoverable package or source. Remove only the verified target, not its parent experiment.
- `ALREADY_REMOVED`: exact path independently checked absent and outcome recorded.

At cleanup, verify exact paths and active consumers, record pre-state, delete only authorized objects, recheck absence and real free-space change, and log the result to the owning Issue. Matching size or filename alone **never proves duplicate content or redundant purpose**. Even matching checksums do not prove it is safe to remove all but one copy if distinct failure domains or recovery contracts are required.

## Initial exe.dev read-only snapshot — 2026-11-10

Observed target `theseus-exe-shell-probe`, 20 GiB volume. After bounded package-cache and temporary dependency cleanup under [theseus-research#112](https://github.com/TeaShaman-cyber/theseus-research/issues/112#issuecomment-6768057594), `df` showed **637 MiB available / 97% used**. No recovery-data or toolchain deletion was performed.

| Path / group | Observed logical size | Initial status / next evidence |
| --- | ---: | --- |
| `~/workdata/session-search` | ~4.6 GiB | `UNKNOWN_NEED_EVIDENCE` per candidate: recoveries, archives, SQLite projections and accepted sources may differ in purpose; reconcile with Session Search Issues and release/backup authority |
| `~/workdata/session-search-issue188` | ~2.1 GiB | `UNKNOWN_NEED_EVIDENCE`: confirm exact owner, retained corpus source, dependent jobs and acceptance before classifying any child |
| `~/.elan/toolchains/leanprover--lean4---v4.31.0` | ~2.8 GiB | `KEEP_ACTIVE`: only observed Lean toolchain; deleting would break reproducibility |
| `/tmp/ss188-reprobe/functions/node_modules` | ~220 MiB before deletion | `ALREADY_REMOVED`: reproducible untracked dependencies; lock/manifest retained; exact-path absence independently verified |
| `~/.npm/_npx/d42c3eb631d835c6` | ~51 MiB before deletion | `ALREADY_REMOVED`: isolated conformance runner bundle; independently verified absent |
| `/tmp/honcho-v2-wire-canary/server.ts` | small | `TEMP / PENDING_CLEANUP` after Honcho #10 candidate acceptance; process stopped, source **not** deleted |

Examples of observed large filenames include several `corpus.sqlite3` objects around 684 MiB and recovery evidence archives around 305 MiB. These are **not** classified as duplicates. This table is a partial dated snapshot, not an exhaustive or live inventory. Issues and actual runtime readback resolve any uncertainty.

## Next bounded work

First prepare a *read-only* exact-path inventory for the Session Search recovery set, including file identity/hash when needed, origin/generation, owning Issue, current consumers, accepted artifact/rollback responsibilities, and actual recoverable bytes. Then propose a small, separate deletion batch for approval with verifiable postconditions. No new cleanup daemon, automatic glob deletion or background task is authorized by this document.

## Managed disposable scratch (opt-in)

For a **new, reproducible, non-interactive foreground-only** experiment whose successful command
has already persisted and verified all required outputs outside scratch, use:

    python3 ~/work/theseus-cloud-shell/providers/exe-dev/managed_scratch.py \
      --owner owner/repo#123 --source exact-source-or-recovery-id \
      --purpose 'bounded disposable QA' -- /absolute/path/to/command

Invoke without a controlling terminal or TTY (for SSH, disable PTY allocation).
This is a synchronous batch helper, not a terminal job-control shell;
interactive commands, including commands needing /dev/tty, are out of scope.
TTY invocation fails before scratch allocation. The command starts in a private newly allocated directory under
`~/.cache/theseus-managed-scratch`. Success removes only that directory,
after confirming that the foreground process group is quiet and the directory
identity and mount boundary are unchanged. Failure retains files and prints
a `PENDING_CLEANUP` receipt with the owner and recovery source. A start receipt
is emitted before execution, so an interrupted run is recoverable. If the
start receipt cannot be emitted, the command is not launched and the new
directory is removed when its identity and boundaries are still verified.
For renamed scratch, the receipt records the retained device/inode and the
matching direct child of the private root when observable, and updates its
manifest after identity and mount checks. Otherwise its location or manifest
update remains explicitly unverified. SIGINT, SIGTERM, SIGHUP and SIGQUIT are relayed to
the managed foreground process group. A programmatic SIGTSTP pauses the
child group but leaves the wrapper responsive to termination; SIGCONT resumes it. A gated child cannot execute the command until
the wrapper commits launch; termination already recorded or pending at that
decision cancels execution. After launch authorization, termination is
ordinary process-group shutdown, not rollback of command side effects.
The persistent manifest includes host/runtime, exact identity, lifecycle
class, owner-review retention trigger and safe cleanup conditions. No secrets
in the owner/source/purpose fields. The caller must not detach workers,
launch services or leave authoritative outputs in this directory. This is
cooperative scratch lifecycle management, not a sandbox for hostile commands.

This does not grant deletion authority over existing workspaces, does not
sweep by age, and does not schedule a daemon. Existing candidates continue
through the explicit inventory and approval process above.
