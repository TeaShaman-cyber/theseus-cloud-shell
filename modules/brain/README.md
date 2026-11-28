# Brain CLI — independent model advice

[Brain CLI](https://github.com/icheer/brain-cli) is a one-shot model consultation tool, not an autonomous coding agent or QA authority. Use it explicitly when another perspective helps. The accepted [comparison](../../research/advisor-cli/README.md) documents live independent answers and counterexamples. Coordination: [#44](https://github.com/TeaShaman-cyber/theseus-cloud-shell/issues/44) (installation), [#46](https://github.com/TeaShaman-cyber/theseus-cloud-shell/issues/46) (provider batches).

## Install / reproduce

On the governed Linux x86_64 exe.dev VM, from this repository:

    modules/brain/install.sh

Or use an already downloaded official release archive:

    modules/brain/install.sh /path/to/brain_0.13.2_linux_amd64.tar.gz

The installer pins version 0.13.2, source commit 377cc5e3ea87a5fcd3abeece18ac8a24a5c6ddea and exact archive/binary hashes; validates before installing, refuses different existing targets, and verifies installed bytes. No root, package manager, background service, global config or credentials.

- Executable: `$HOME/.local/bin/brain` (0755).
- Explicit non-secret profiles: `$HOME/.config/theseus/brain-{nous,openrouter,bothub,nim}.yaml` (0600). The placeholder key is not a credential: the corresponding existing exe.dev integration injects its provider-held bearer.
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
| nim | https://nvidi-nim.int.exe.xyz/v1/models | NVIDIA Developer Program hosted free endpoint, exact live model ID and model-specific availability; no :free suffix required |

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

### NVIDIA NIM developer profile

Use `BRAIN_CONFIG="$HOME/.config/theseus/brain-nim.yaml"` with the existing
`nvidi-nim` integration. The user confirms the account is on free developer
access and explicitly authorizes bounded research and QA consultations.
This is account-owner evidence, not a billing API readback.

- [NIM developer FAQ](https://docs.api.nvidia.com/nim/docs/product) and
  [rate-limit FAQ](https://forums.developer.nvidia.com/t/nvidia-nim-faq/300317)
  establish free prototyping, research, development and testing access;
  limits vary by model and load. Check the live catalog and individual
  model's hosted API availability; catalog membership alone is not proof
  of callable or free inference.
- [API Trial Terms](https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf),
  sections 1.2–1.4, 2.6 and 3.3: no production use, respect limits and trial
  terms, no confidential or sensitive inputs. Provider may log or use
  inputs/outputs as described in the terms. Do not send private history,
  credentials or personal data. Do not use this route as a production
  worker, bypass limits, or buy credits automatically.
- Unlike OpenRouter, NIM model IDs need not have a :free suffix and the
  catalog does not establish a token tariff. Select documented free
  hosted endpoints under the developer entitlement. No paid fallback.
- Live prior QA: MiniMax M3.1 Flash completed both CLI help selection
  trials (3/4 to 4/4); GLM-5.3 Flash timed out. See
  [repo-search #223](https://github.com/TeaShaman-cyber/theseus-repo-search-lab/issues/223#issuecomment-7236737402).
  No automatic retry; a timeout does not establish model unavailability.

Example (after verifying the model page and current catalog):

    export BRAIN_CONFIG="$HOME/.config/theseus/brain-nim.yaml"
    brain ask --json --timeout 60 --max-output-tokens 4096 \
      -m minimaxai/minimax-m3.1-flash 'Give a counterexample to this synthetic invariant.'

Apply the same nonempty content, exact model identity and finish-reason
checks as other profiles. No global default or worker routing change.

### Dated evidence (2026-11-28)

- Nous: 3/3 catalogued free routes produced complete answers; HY4 required
  4096 output tokens after exhausting the initial 2048 cap.
- OpenRouter: 8/10 catalogued zero-price text :free routes completed.
  Both Gemma 4 variants returned upstream Google AI Studio 429.
  Free-request counter readback: 8 used, 992 remaining out of 1000.
- BotHub: 4/5 catalogued :free routes completed. The official usage report
  independently matched all four Brain responses by model and token counts:

  | Model ID | Prompt | Completion | CAPS | RUB |
  | --- | ---: | ---: | ---: | ---: |
  | nemotron-3-nano-omni-30b-a3b-reasoning:free | 108 | 1870 | 0 | 0 |
  | nemotron-3-ultra-550b-a55b:free | 108 | 1310 | 0 | 0 |
  | nemotron-3.5-lightning:free | 108 | 3496 | 0 | 0 |
  | nemotron-3.5-super-vl:free | 108 | 1052 | 0 | 0 |

  Gemma 4 31B returned 429 with an error referring to OpenRouter upstream;
  no charge row was present at readback. Provider diversity does not guarantee
  independent upstream quotas. The 15 successful provider/model routes are
  not 15 independent model families.

### BotHub billing readback

The existing workstation collector in
[theseus-local-lab](https://github.com/TeaShaman-cyber/theseus-local-lab/blob/main/deploy/cost-metrics/bothub-usage-metrics.py)
uses Python's standard library to fetch and parse the official XLSX from
`https://bothub.chat/api/v2/transaction/usage-report`, with UTC from/to
parameters. On the authorized Windows workstation its deployed path is
`C:/Apps/theseus-metrics/bothub-usage-metrics.py`. Reuse its read_key,
fetch_report and parse_rows functions for read-only reconciliation; do not
invoke main merely to read billing, because main rewrites the metric file.
Keep credentials and raw XLSX local; export only the minimal model, token,
timestamp and charge fields. Match actual report rows to the experiment;
missing rows or blank charge fields are UNKNOWN, not zero.

The existing exe.dev `bothub-api` inference proxy returned HTTP404 JSON for
the finance report path, whereas the workstation collector against the
finance host returned the XLSX. This is an endpoint/route distinction, not a
Windows dependency. A separate governed finance integration would need
explicit authorization and a verified credential boundary; none was created.
Historical zero charges do not guarantee future tariffs.

See [#42](https://github.com/TeaShaman-cyber/theseus-cloud-shell/issues/42)
for exact per-leg receipts and the
[final BotHub reconciliation](https://github.com/TeaShaman-cyber/theseus-cloud-shell/issues/42#issuecomment-7236486982).
No default model or Dreaming Worker routing change.

## Operational boundaries

Each provided profile explicitly sets retry_max=0, timeout 60s, max_input_bytes=65536 and no aliases. Specify literal model IDs and output caps every time. The raw binary is not a policy enforcement sandbox: do not override retries, add aliases/failover, run council, or add tools/extra endpoints without separately establishing scope. The four explicit profiles are independent; do not combine them into a single gateway or fallback chain. Do not use model calls to bypass a prior host or provider refusal. On 429, denial, or uncertain dispatch, retain the receipt and stop that provider round rather than blindly repeating. Private history, secrets and source material require their own explicit permission and provider data-handling decision.

Known upstream issue [brain-cli#1](https://github.com/icheer/brain-cli/issues/1): empty, truncated or incomplete SSE can exit 0. The checks above reject missing/length finish and empty content; partial compare exit 0 is not all-leg success. The checks do not prove semantic truth, backend identity or independent billing. No worker routing, installed plugin or agent permissions are changed.
