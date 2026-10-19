# Fork hardening verification

Latest source-import evidence: [2026-10-19 v0.1.45 review](maintenance/2026-10-19-upstream-v0.1.45.md)
(1,593 Python cases, 15 skipped; three additional GPU-free CPU-native tests).
This is source qualification only, not a production deployment receipt.

Source scope: security changes on top of `7695859aa13afb248bdb4d36f9b2e95707db079d` in `pecuna/Strata-3060`.
Execution: Smith's local isolated Python test environment, not the deployed `llm.lan` service.
This is the historical 2026-10-11 hardening record, not a continuously refreshed test/deployment status.
Hardening commit: `960faa4e58e23d35143fa70fcd41f6f195549fb4`.

For repeatable commands, invariant-to-test mapping and evidence required after every upstream import, see
[Maintaining Strata-3060 across upstream releases](FORK_UPSTREAM_SYNC.md). Future runs must record their own
exact source state, totals, skips and remaining limits; do not reuse the historical totals as a new result.

## Executed suites

| Command (using the isolated environment's Python) | Result |
| --- | --- |
| `python -m unittest discover -s serve -p 'test_*.py'` | 710 run; 11 skipped; no failures/errors |
| `python -m unittest discover -s tools -p 'test_setup_*.py'` | 477 run; 1 skipped; no failures/errors |
| `python -m unittest tools.test_mtp_fetch tools.test_mtp_trust_policy tools.test_fork_routes` | 20 run; no failures/errors |

These three non-overlapping suites account for 1,207 cases: 1,195 passed and 12 skipped.
After a final image-error-message correction, the image-source, image-marker and policy/HTTP suites were rerun
alongside the MTP/fork-route tests: 32 run, no failures/errors. This rerun overlaps the suites above and is not
added to the total. The full installer run includes the final verifier-diagnostic and ModelScope refusal changes.

Also passed: `git diff --check`, `sh -n setup.sh update.sh`, and `node --check serve/web/app.js`.
Added tracked lines were scanned for literal credentials, shell injection, dynamic evaluation and unsafe
serialization patterns; none were found. Independent review findings were addressed before publication.

## What the tests establish

- Actual loopback mock-server OpenAI and Anthropic requests with remote images return HTTP 400; base64 images
  still succeed with a mock vision encoder. No production GPU/model was used.
- Remote images are rejected before URL opening, DNS/proxy access or encoder/file access where applicable;
  remote tool images are omitted without fetching, including case/whitespace URL variations.
- Missing/incorrect engine digests refuse installation, including local archives, mirrors and skip-variable attempts.
- Refused CUDA and HIP acquisitions do not invoke installation, and installed executable/metadata bytes remain unchanged.
- ModelScope downloads without a provider checksum are refused.
- Pinned download failures do not select `main`; alternate MTP sources must match built-in expected tensor bytes.
- MTP verification rehashes even same-size/same-mtime corruption, rejects missing tensors, and unexpected verifier
  exits stop setup with a diagnostic.
- Existing-config starts do not update engines; incompatible GPU architectures require explicit setup, not migration/build.

Installer tests mock GPU/build/install operations. Their fixture output saying "Compiling" is not evidence of a
real GPU compilation. Existing telemetry file-handle ResourceWarnings appeared during server tests; they were
not introduced or fixed by this patch.

## Not established

No CUDA/HIP/SYCL build, real-engine inference, Windows batch execution, release-binary publication,
production deployment, firewall/authentication change or deployment-level air-gap test was performed.
Explicit MCP integrations and installer/package-manager downloads remain network-capable; see [the policy](FORK_SECURITY.md).
