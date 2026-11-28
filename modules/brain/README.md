# Brain CLI — independent model advice

[Brain CLI](https://github.com/icheer/brain-cli) is a one-shot model consultation tool, not an autonomous coding agent or QA authority. Use it explicitly when another perspective helps. The accepted [comparison](../../research/advisor-cli/README.md) documents live independent answers and counterexamples. Coordination: [#44](https://github.com/TeaShaman-cyber/theseus-cloud-shell/issues/44) (installation), [#46](https://github.com/TeaShaman-cyber/theseus-cloud-shell/issues/46) (provider batches).

## Install / reproduce

On the governed Linux x86_64 exe.dev VM, from this repository:

    modules/brain/install.sh

Or use an already downloaded official release archive:

    modules/brain/install.sh /path/to/brain_0.13.2_linux_amd64.tar.gz

The installer pins version 0.13.2, source commit 377cc5e3ea87a5fcd3abeece18ac8a24a5c6ddea and exact archive/binary hashes; validates before installing, refuses different existing targets, and verifies installed bytes. No root, package manager, background service, global config or credentials.

- Executable: `$HOME/.local/bin/brain` (0755).
- Explicit non-secret profiles: `$HOME/.config/theseus/brain-{nous,openrouter,bothub}.yaml` (0600). The placeholder key is not a credential: the corresponding existing exe.dev integration injects its provider-held bearer.
- Verify version: `$HOME/.local/bin/brain --version`.
- Offline installer acceptance: `modules/brain/test-install.sh /path/to/pinned-archive`. Repeating installation of identical files is safe; local modifications are refused rather than overwritten.

No automatic updates. Review a new upstream version and repeat the transport contract tests before changing pins. To retire, verify the exact installed paths and their ownership/content, then remove just those files if authorized; no shared provider configuration or integration is removed.

## Use on exe.dev

Select the explicit profile in the current shell:

    export BRAIN_CONFIG="$HOME/.config/theseus/brain-nous.yaml"
    export PATH="$HOME/.local/bin:$PATH"

Use only an explicitly authorized model and input. Current tested Nous model IDs include `upstage/solar-mini4:free`, `stepfun/step-3.7-flash:free` and `tencent/hy4-flash:free`; these are examples, not a permanent entitlement or quality ranking. Before a live request verify current model pricing:

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

## Free-model batches across providers

Use the live catalog, not a hardcoded roster. Brain 0.13.2 uses one base URL per
invocation, so select a profile and a small group (normally two or three explicit
IDs) for each round. Reuse the same synthetic or otherwise authorized question
when comparing answers. No automatic global fanout, scheduled refresh, retry,
paid fallback, or model alias. Stop a round on refusal; retain other answers
already returned. Distinguish a model-specific upstream limit from an account
quota. Do not retry the refused route just because another model succeeded.

| Profile | Catalog URL | Selection rule |
| --- | --- | --- |
| nous | https://nous.int.exe.xyz/v1/models | Literal :free ID and all reported prices zero |
| openrouter | https://openrouter.int.exe.xyz/api/v1/models | Literal :free ID, all reported prices zero, text output |
| bothub | https://bothub-api.int.exe.xyz/v1/models | Explicit :free ID plus independent evidence of free API usage; do not infer zero price from missing pricing |

For Nous or OpenRouter, list eligible IDs before selecting a group:

    provider=openrouter
    catalog=https://openrouter.int.exe.xyz/api/v1/models
    curl -fsS --max-time 15 "$catalog" |
      jq -r '.data[] | select(.id|endswith(":free")) |
        select(.pricing|type=="object" and length>0 and all(.[]; .=="0" or .==0)) |
        select((.architecture.output_modalities // ["text"]) | index("text")) | .id' |
      sort -u

For Nous set the corresponding catalog and provider from the table. For
OpenRouter inspect the current free allowance:

    curl -fsS --max-time 15 https://openrouter.int.exe.xyz/api/v1/key |
      jq '.data.free_model_daily_requests'

Example OpenRouter round (revalidate both IDs and their pricing first):

    export BRAIN_CONFIG="$HOME/.config/theseus/brain-openrouter.yaml"
    umask 077
    brain compare --json --timeout 60 --max-output-tokens 4096 \
      -m baidu/ernie-5.5-flash-preview:free -m particle-ai/particle-1:free \
      'Give a counterexample and a falsifiable test.' > openrouter-round.json

Use the same pattern for other profiles. Only Nous uses the previously verified
`--extra-body '{"tags":["user=theseus-review"]}'` option. The output cap is per
model; 4096 was useful for HY4, which exhausted 2048 without a final answer.
The 60s deadline applies to the whole compare invocation. The cap is not a
requirement to consume all tokens. Never dispatch a model with an unverified
paid tariff.

Keep provider + requested model + outcome for each leg; same family behind two
providers is route redundancy, not an independent family. Preserve successful
answers even on PARTIAL, and do not conflate transport completeness with
scientific correctness. Validate nonempty final content, stop reason, no error
and exact expected model identity per leg; inspect missing usage separately.
A full useful response may still be wrong.

### Dated evidence (2026-11-28)

- Nous: 3/3 free IDs in catalog; first compare 2/3 full, HY4 length at 2048;
  separate 4096 probe HY4 completed (2360 reported tokens, 18.099s).
- OpenRouter: 10 zero-price text :free IDs, initial daily allowance 1000
  remaining. Two groups of 3 produced five complete answers; Gemma 4 26B
  explicit upstream Google AI Studio 429, not a demonstrated account-quota
  failure. Remaining four IDs not tested in this round.
- BotHub: five catalogued :free IDs, no price fields. Our historical
  provider-report-derived Grafana metric (last value within 35 days) showed
  zero CAPS for `nemotron-3-nano-omni-30b-a3b-reasoning:free` and
  `nemotron-3-ultra-550b-a55b:free`; both returned full responses through Brain.
  Current per-request billing remains UNKNOWN; the other three candidates are
  not yet accepted for automatic free selection. Historic zero is not a
  guarantee of a current tariff. Reconfirm before ongoing use.

See [#42](https://github.com/TeaShaman-cyber/theseus-cloud-shell/issues/42)
for exact per-leg experiment receipts. No default model or Dreaming Worker
routing change.

## Operational boundaries

Each provided profile explicitly sets retry_max=0, timeout 60s, max_input_bytes=65536 and no aliases. Specify literal model IDs and output caps every time. The raw binary is not a policy enforcement sandbox: do not override retries, add aliases/failover, run council, or add tools/extra endpoints without separately establishing scope. The three explicit profiles are independent; do not combine them into a single gateway or fallback chain. Do not use model calls to bypass a prior host or provider refusal. On 429, denial, or uncertain dispatch, retain the receipt and stop that provider round rather than blindly repeating. Private history, secrets and source material require their own explicit permission and provider data-handling decision.

Known upstream issue [brain-cli#1](https://github.com/icheer/brain-cli/issues/1): empty, truncated or incomplete SSE can exit 0. The checks above reject missing/length finish and empty content; partial compare exit 0 is not all-leg success. The checks do not prove semantic truth, backend identity or independent billing. No worker routing, installed plugin or agent permissions are changed.
