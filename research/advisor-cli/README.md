# Independent model consultation and review — experiment #42

Dated 2026-11-28. Coordination: [cloud-shell #42](https://github.com/TeaShaman-cyber/theseus-cloud-shell/issues/42). This is research evidence, **not** an installed runtime or routing authority. No production change or new credential.

## Comparative disposition

| Candidate | Exact tested version | Result |
| --- | --- | --- |
| MPT | v0.14.3-f5777c6; clean source 6fd954535a56e15f6822fd6f0be6c64a1d4af099 | DROP from practical acceptance: retains independent texts and per-leg errors, but loses finish/usage, empty success; current source reproduces. Live Nous HTML denial; status and downstream execution unknown. |
| LLM | 0.38, OpenAI SDK 3.60.0 | DEGRADED: native CLI makes three physical POSTs on 429/500. Bounded library subclass passes seven offline cases (one request, usage, finish, timeout); real Solar request returned 400, precise cause not captured. |
| Brain | 0.13.2, 377cc5e3ea87a5fcd3abeece18ac8a24a5c6ddea | Leading advisory candidate; actual one-shot and two-model compare succeeded. Strict caller checks remain necessary. One base URL per config; multi-provider calls not tested. |
| AIChat | 0.30.0, release SHA256 6b0cc08c5ceb551dc52bfac2221752f82215be5908c70605d655e9b91ab1557c | DEGRADED: one physical call per offline case; rejects empty, loses finish/usage, outer deadline needed. Real Nous response decode failed, status unknown. |
| MCO | 0.13.0, 7ce642193a127f3fac9c68fb10c5d0198d4e837e; native Pi 1.5.0 | PARTIAL: actual repository-aware agent review, read-only filesystem isolation and independent call cap. One agent completed, other rate-limited. Keep as candidate, not acceptance authority. |

MPT release archive checksum verified; fresh source built offline from vendor with Go 1.27.3. Brain release checksum verified. MCO 86 upstream tests passed. Additional four black-box subprocess cases show complete, partial failure, timeout cleanup and false complete despite structured transport still running.

## Live results and semantic checks

Same neutral cache-key question for Brain/MPT/LLM/AIChat, Solar Mini4 Nous free catalog entry, 2048 output cap, no automatic retry. Brain completed in 4784ms, 243 tokens. MPT HTML denial; user excluded MPT. LLM 400; AIChat response decoding error. No conclusion about relative model quality or root cause of these provider/client failures.

Separate Brain compare: Solar Mini4 and Step 3.7 Flash on a crash-after-commit-before-queue-ack scenario; 418 and 1754 reported tokens, 3392/10682ms per leg, finish stop, no synthesis. Solar proposes an invalid COMPLETED=>ACKED invariant, precisely contradicted by the given crash window; its suggested test partially repairs the idea via idempotency. Step correctly identifies a unique durable job key and separates execution from persistent effects. Actual upstream request counts/billing not independently verified for Brain. Fresh zero-price catalog is not billing proof.

Actual MCO review: separate synthetic account.py. Initial provider-qualified model selection rejected by discovery with zero dispatch; explicit bare IDs plus provider resolved. Native Pi under bubblewrap, only synthetic repo read-only, disposable config, no host home/credentials/MCP/skills/extensions, no retry. Temporary loopback relay independently enforces allowed model IDs, 3 calls/model, 6 total, 1024 output tokens, read-only tool names, no redirects and stop on refusal. Solar made two actual calls (read tool then stop), Step made one call returning 429. Total wall 15846ms, 3450 tokens reported by provider, reported cost zero, independent billing unverified. MCO returned partial exit1, retained Solar answer, error "completed" for Step and usage null despite provider usage. Repository unchanged. No further live requests following 429.

Independent execution of the fixture:

- withdraw(0,0) and withdraw(100,100) raise; expected valid under a nonnegative withdrawal contract.
- withdraw(100,-10) returns 110 and withdraw(0,-1) returns 1; negative amounts create funds.
- withdraw(100,0) returns 100, contrary to Solar's claimed exception.
- withdraw(-100,0) raises, contrary to Solar's claimed return value 0.

Domain validation is assumed, not a specification of a real financial service. Review is useful but has false positives; do not treat agreement, CLI exit, or structured output as semantic authority.

## Next disposition

Brain is useful for independent consultations when an explicit caller rejects empty output, missing/non-stop finish, errors, incomplete legs and unapproved models. Missing usage remains UNKNOWN rather than zero. Disable retries and aliases/failover; do not require consensus. LLM and AIChat are secondary candidates with unresolved real compatibility. MCO actual multi-agent acceptance incomplete after 429; exact permission/model/budget requirements remain; use deterministic tests for findings.

This experiment is independent of the previously blocked Dreaming Worker run. No attempt to bypass that refusal, no paid fallback, no private history, no default provider change or persistent install.

## Evidence and reproduction

manifest.json binds retained artifacts and original raw hashes. Synthetic offline probes retained as executed; they expect binaries/venv in an isolated lab directory as documented in #42 (not installed or invoked by CI). The MCO probe expects synthetic git fixture and executable stand-in scripts restored from the text copies. Recorded live sources are text only, not launchers; they depend on the governed runtime and current authorization/catalog. Retained JSON is reserialized with lab-path redaction or selected final-response fields; raw provider HTML is deliberately not retained. Use `python3 research/advisor-cli/verify.py` for offline receipt consistency, not real-provider replay.

Upstream feedback: [MPT #43](https://github.com/umputun/mpt/issues/43), [LLM #504](https://github.com/simonw/llm/issues/504#issuecomment-7235824128), [Brain #1](https://github.com/icheer/brain-cli/issues/1), [MCO #136](https://github.com/mco-org/mco/issues/136).
