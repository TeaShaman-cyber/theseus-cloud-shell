# Cloudflare account API token → repository Actions secret

Verified provisioning pattern, 2026-11-28. Evidence: [Public Observatory #25](https://github.com/TeaShaman-cyber/theseus-public-observatory/issues/25) and [Cloud Shell #51](https://github.com/TeaShaman-cyber/theseus-cloud-shell/issues/51).

This is an operator recipe, not a grant of authority to create credentials.
Apply the Project Contract and obtain authorization for the specific account,
workload, permission set and destination repository. Prefer a dedicated
account-owned workload token over copying the broad operator credential.

## When to use

A project needs a Cloudflare API in GitHub-hosted CI (Radar, R2, Workers or
another product). The existing credential-injecting exe.dev integration
can potentially provision a narrower token without sending a secret through
chat, the laptop, or a Git commit. Other products are candidates, not
verified by the Radar experiment; discover their actual API and permissions.

The native ChatGPT Cloudflare OAuth connector and the exe.dev Cloudflare
proxy are independent grants. On 2026-11-28 native
`GET /user/tokens/permission_groups` returned 403 / 9109 with no OAuth scope
covering that endpoint. Native account permission-group discovery succeeded.
The existing exe.dev proxy supported account token listing, permission-group
discovery and account token creation. Do not confuse user-owned and
account-owned token endpoints or infer write permission from a successful GET.

## 1. Preflight (read-only)

Select the current VM with `list_vms`, consult the provider README and verify
the `cloudflare` attachment using Reflection. Verify native `gh` identity
and the exact authorized destination repository. Use the documented
provider-injected credential; do not retrieve or copy its value.

From the selected guest, use the proxy base
`https://cloudflare.int.exe.xyz/client/v4`:

- `GET /accounts`: select the explicitly authorized account; never silently
  choose the first account in a multi-account result.
- `GET /accounts/{account_id}/tokens/permission_groups`: discover the exact
  named permission groups and their account scope from live data. Inspect
  all pages if paginated. Do not hard-code IDs or infer equivalent scopes.
- `GET /accounts/{account_id}/tokens`: check all pages for existing workload
  token name; check `gh secret list -R OWNER/REPO --json name` for the
  intended secret. If either exists, reconcile rather than overwriting.
- Check the API schema and accepted permission for account token creation
  (currently Account API Tokens Write). Verify the workload's actual API
  permission separately. A refusal is a boundary, not authorization to
  escalate, switch identity or request a global API key.

Use the [account token API](https://developers.cloudflare.com/api/resources/accounts/subresources/tokens/methods/create/)
and [token permission reference](https://developers.cloudflare.com/fundamentals/api/reference/permissions/).
For Radar the observed permission was exactly `Radar Read` (account scope).

## 2. Create a narrow account-owned token

POST to `/accounts/{account_id}/tokens` on the existing proxy.
Example request body (placeholders must be resolved from live discovery):

```json
{
  "name": "PROJECT WORKLOAD",
  "policies": [
    {
      "effect": "allow",
      "permission_groups": [{"id": "DISCOVERED_PERMISSION_GROUP_ID"}],
      "resources": {"com.cloudflare.api.account.ACCOUNT_ID": "*"}
    }
  ]
}
```

Choose expiry and rotation ownership deliberately. IP restrictions must
match the actual executor: do not assume hosted Actions has a fixed IP.
Do not widen resource scope to make provisioning pass. The Radar pilot used
one account and one read-only permission without an explicit IP or expiry
constraint; this is a historical choice, not a universal default.

Use a single local process (e.g. Python stdlib HTTP client and subprocess)
for creation, validation and transfer. Disable redirects for authenticated
requests, bound timeouts, validate HTTP status and API success, and retain
the newly returned token value only in process memory. Never output the
response body, bearer header or raw exception that may contain credentials.
The value is returned at creation; listing/details are not a recovery
mechanism for a lost value. Never use shell tracing or put the value into
command arguments, environment dumps, files or artifacts.

## 3. Verify before handing off

Read back `GET /accounts/{account_id}/tokens/{token_id}` via the operator
proxy. Require the exact intended policy: account, effect, permission
groups, and any expiry/IP restrictions. Verify using the newly minted
credential directly against the intended Cloudflare API (not through the
operator proxy, which would test the wrong credential). For Radar the
bounded read was:

```text
GET https://api.cloudflare.com/client/v4/radar/origins?format=JSON&limit=1
Authorization: Bearer [in-memory workload token]
```

Require HTTP 200 and JSON `success: true`; keep only sanitized status and
non-secret provenance. For a write-capable product prefer a safe readback
or specifically authorized bounded canary; a successful unrelated read
does not prove write capability.

## 4. Transfer directly to GitHub

In the same process, pass the token value by stdin to native gh. Example
fragment, after the above checks, not a standalone provisioning script:

```python
result = subprocess.run(
    ["gh", "secret", "set", secret_name, "-R", repo],
    input=value,
    text=True,
    capture_output=True,
    check=False,
)
# Check return code; never print stdout/stderr or the token.
del value
```

Check the exact secret name with a fresh `gh secret list -R OWNER/REPO --json name`.
GitHub does not return the secret value. Presence is not proof that the
runner can use it. Bind the secret only to the step that needs it, under
least-privilege workflow permissions. Never expose it to untrusted PR code.
Run the target trusted workflow and verify API outcome and sanitized receipt
at the exact head. Only then mark workload authorization end-to-end verified.

## 5. Reconcile failures and lifecycle

- Ambiguous POST: list/read back the exact token before considering any retry.
  No blind duplicate creation.
- Policy mismatch or failed API probe: do not store the credential. Reconcile
  and revoke only the newly created, demonstrably unused token when authorized;
  verify its absence. Do not revoke a pre-existing token.
- Ambiguous GitHub write: check secret presence first. If the value is lost,
  presence alone cannot verify it; reconcile via trusted runner probe.
- If a new token was created but not transferred, record the unresolved
  credential lifecycle; revoke or rotate under the appropriate authorization
  rather than leaving an unexplained unused grant.
- Keep token name, non-secret identifier if needed, permission names,
  destination, date, expiry/rotation owner, and verification status in the
  operational receipt. Do not commit live account IDs or token values in
  this reusable recipe. Rotation/revocation are separate authorized actions.

## Observed acceptance — Public Observatory

2026-11-28: the existing exe.dev proxy listed account tokens and permission
groups with HTTP 200; the dedicated `Theseus Public Observatory Radar`
account token was created. Readback matched exactly one account and
`Radar Read`. Direct Radar API probe with the new token returned HTTP 200
and API success. Native gh stored `CLOUDFLARE_RADAR_TOKEN` in
`TeaShaman-cyber/theseus-public-observatory`; secret-name readback succeeded.
No token value was printed or written to the repository. No laptop
intervention or new operator credential was required.

This proves provisioning and direct API access for that workload. The
GitHub-hosted Radar workflow itself had not yet been verified at the
provisioning checkpoint. This recipe does not certify other Cloudflare
products, future grants, runner access, billing or resource quotas.
