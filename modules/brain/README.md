# Brain CLI — independent model advice

[Brain CLI](https://github.com/icheer/brain-cli) is a one-shot model consultation tool, not an autonomous coding agent or QA authority. Use it explicitly when another perspective helps. The accepted [comparison](../../research/advisor-cli/README.md) documents live independent answers and counterexamples. Coordination: [#44](https://github.com/TeaShaman-cyber/theseus-cloud-shell/issues/44).

## Install / reproduce

On the governed Linux x86_64 exe.dev VM, from this repository:

    modules/brain/install.sh

Or use an already downloaded official release archive:

    modules/brain/install.sh /path/to/brain_0.13.2_linux_amd64.tar.gz

The installer pins version 0.13.2, source commit 377cc5e3ea87a5fcd3abeece18ac8a24a5c6ddea and exact archive/binary hashes; validates before installing, refuses different existing targets, and verifies installed bytes. No root, package manager, background service, global config or credentials.

- Executable: `$HOME/.local/bin/brain` (0755).
- Explicit non-secret profile: `$HOME/.config/theseus/brain-nous.yaml` (0600). The placeholder key is not a credential: the existing exe.dev Nous integration injects its provider-held bearer.
- Verify version: `$HOME/.local/bin/brain --version`.
- Offline installer acceptance: `modules/brain/test-install.sh /path/to/pinned-archive`. Repeating installation of identical files is safe; local modifications are refused rather than overwritten.

No automatic updates. Review a new upstream version and repeat the transport contract tests before changing pins. To retire, verify the exact two paths and their ownership/content, then remove just those files if authorized; no shared provider configuration or integration is removed.

## Use on exe.dev

Select the explicit profile in the current shell:

    export BRAIN_CONFIG="$HOME/.config/theseus/brain-nous.yaml"
    export PATH="$HOME/.local/bin:$PATH"

Use only an explicitly authorized model and input. Current tested model IDs are `upstage/solar-mini4:free` and `stepfun/step-3.7-flash:free`; these are examples, not a permanent entitlement or quality ranking. Before a live request verify current model pricing:

    model=upstage/solar-mini4:free
    curl -fsS --max-time 10 https://nous.int.exe.xyz/v1/models |
      jq -e --arg m "$model" 'any(.data[]; .id==$m and (.pricing | type=="object" and length>0 and all(.[]; .=="0" or .==0)))'

For an independent one-shot consultation:

    umask 077
    brain ask --json --timeout 60 --max-output-tokens 2048 \
      -m "$model" --extra-body '{"tags":["user=theseus-review"]}' \
      'Give one counterexample to the proposed invariant and a test.' > answer.json

Check the exit status **and** the JSON before accepting it as a completed advisory answer:

    jq -e --arg m "$model" '
      .error == null and .model == $m and .requested_model == $m
      and .finish_reason == "stop"
      and (.content | type=="string" and test("\\S"))
    ' answer.json

Then inspect content and usage. Usage=null is UNKNOWN, never zero. Do not publish raw private response artifacts; compare can include extra model reasoning fields. Output caps are per model and do not cap hidden upstream cost; fresh zero-price catalog is not independently verified billing.

For independent comparison, after checking both models in the fresh catalog:

    brain compare --json --timeout 60 --max-output-tokens 2048 \
      -m upstage/solar-mini4:free -m stepfun/step-3.7-flash:free \
      --extra-body '{"tags":["user=theseus-review"]}' \
      'What alternative explanations fit this synthetic observation?' > compare.json

    jq -e '
      .error == null and
      ([.responses[].model] | sort) ==
        ["stepfun/step-3.7-flash:free","upstage/solar-mini4:free"]
      and all(.responses[];
        .ok == true and .error == null and .finish_reason == "stop"
        and (.content | type=="string" and test("\\S")))
    ' compare.json

Keep individual answers even if only one leg succeeds, but mark the overall result PARTIAL. Review disagreement against source evidence and deterministic tests; no automatic consensus.

## Operational boundaries

The provided profile explicitly sets retry_max=0, timeout 60s, max_input_bytes=65536 and no aliases. Specify literal model IDs and output caps every time. The raw binary is not a policy enforcement sandbox: do not override retries, add aliases/failover, run council, or add tools/extra endpoints without separately establishing scope. No additional providers are configured here. Do not use model calls to bypass a prior host or provider refusal. On 429, denial, or uncertain dispatch, retain the receipt and stop that provider round rather than blindly repeating. Private history, secrets and source material require their own explicit permission and provider data-handling decision.

Known upstream issue [brain-cli#1](https://github.com/icheer/brain-cli/issues/1): empty, truncated or incomplete SSE can exit 0. The checks above reject missing/length finish and empty content; partial compare exit 0 is not all-leg success. The checks do not prove semantic truth, backend identity or independent billing. No worker routing, installed plugin or agent permissions are changed.
