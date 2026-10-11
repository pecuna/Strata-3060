# Strata-3060: network and artifact security

This is the security policy for `pecuna/Strata-3060`. It takes precedence over inherited upstream installation
instructions and translations. These are source changes; updating the GitHub fork does not update any running
installation.

## Local inference and images

The engine runs local model files. The web app loads local assets and uses same-origin server endpoints.
No cloud inference fallback or analytics upload was found in the reviewed runtime paths.

**The server does not fetch HTTP(S) image URLs.** Send an image as a base64 `data:` URL, use the web app's file
attachment, or use a supported file path on the server. Remote images returned by tools are not downloaded either.
There is deliberately no switch to restore unrestricted server-side fetching: a destination allowlist without
safe DNS and redirect handling would reintroduce SSRF. If a client downloads an image before attaching its bytes,
that client owns the network access and privacy decision.

Local file access is not a filesystem sandbox. Only trusted clients should reach the API. Use an API key and
network access controls when binding beyond loopback; TLS belongs at a suitable trusted proxy. This patch does
not change a deployed listener, credentials, firewall or systemd service.

## Explicit integrations can use the network

Configured HTTP MCP servers receive initialization and tool-discovery messages at server startup. Tool calls send
the selected arguments, which can contain private conversation-derived information. Configured stdio MCP programs
can also use the network, and commands such as `npx` or `uvx` may download code. The web app can request MCP tools
when configured tools are available. An explicit `before_load` command can do anything permitted to the service
account, including networking. The optional Intel wrapper's configured model-switcher performs HTTP RPC.

None of these integrations is required for local inference. For an offline deployment, omit MCP servers,
`--mcp-config`, network-using hooks and remote switcher URLs; provision all dependencies in advance. For enforceable
isolation, use reviewed host/service egress controls. Static source review cannot certify third-party packages,
subprocesses, GPU drivers, browsers or the whole host as offline.

## Starts and updates are separate

An ordinary launcher start of an existing configuration does not automatically update its engine. If hardware
changes and the engine lacks code for a selected GPU, start refuses rather than downloading/rebuilding it.
Use `--setup --build` (or `--setup --cuda 12 --build` for a CUDA-12-only card) deliberately to prepare the engine.
Use `--update`, `update.sh` or `UPDATE.bat` deliberately for updates. First installation and explicit setup/build
operations may still download missing dependencies. A direct `serve/server.py` systemd launch is not an installer.

Source updates use the configured Git tracking remote. Primary download/update instructions point to this fork.
Prebuilt engine defaults point to this fork's releases, **not upstream releases**. If a matching fork binary is
not published, use an explicit source build rather than silently substituting an upstream binary. No fork binary
release is created by this security patch.

## Artifact verification fails closed

Engine archives require a valid SHA256 from the selected GitHub release or an independently obtained owner-pinned
`STRATA_ENGINE_SHA256` value (64 hexadecimal characters). A local archive or non-GitHub mirror does not bypass
verification. Do not generate an expected hash from an untrusted download and call that verification.
`STRATA_SKIP_SHA256=1` is not a supported bypass. A refused update keeps the installed engine rather than replacing
it with an unverified archive.

Pinned Hugging Face downloads no longer fall back to a repository's current files after a 404. MTP acquisition
requires byte identity with the built-in pinned-content SHA256 for every selected tensor. A self-computed hash in a
manifest is not a substitute for a trusted expected hash. An explicitly selected alternate source/revision is
accepted only if its tensor bytes match those same hashes; different content requires a reviewed code/hash update.
MTP verification always rehashes raw tensors and ignores old size/mtime sidecars. Missing tensors are not verified;
unexpected verifier errors stop setup rather than accepting or silently rebuilding an unverified runtime.
Explicit setup may need the raw tensors restored before it can reuse a previously prepared MTP runtime.

GitHub release digests prove consistency with the selected published asset, not that its publisher is trustworthy.
Python package versions are pinned, but this patch does not introduce a hash-locked wheelhouse or signed releases.
The existing model-shard `.done` verification cache still assumes a trusted local filesystem; unlike MTP verification,
this patch does not force a complete model-shard rehash on every setup run. It is not protection against local
file/sidecar tampering or a compromised service account.
Optional ModelScope uses that provider's current repository files and is not equivalent to pinned Hugging Face
provenance. Missing provider SHA256 metadata refuses the newly downloaded file rather than marking it complete.
Do not use it for a reproducible offline build without separately reviewed artifacts.

## Remaining install/build network dependencies

Installation/update may access GitHub and its API/CDNs, Hugging Face and its download/CDN hosts, explicitly selected
mirrors or ModelScope, pip indexes, distribution repositories, NVIDIA repositories, optional AMD wheel repositories,
managed Python sources and container registries. llama.cpp build sources are commit-pinned, but still need fetching
if absent locally. Redirect hosts and configured package mirrors are not a fixed firewall allowlist.

Pre-stage reviewed source, engine, Python environment, model shards, tokenizer, image projector and MTP runtime for
an offline machine. Avoid launching setup on a managed production service just to test whether it is offline.

## Regression verification

For every upstream import, follow [the maintenance/reapplication runbook](FORK_UPSTREAM_SYNC.md). It records the
complete change ledger, recovery baseline, conflict-handling procedure and mandatory release gates. Merge
upstream improvements without discarding these guarantees; neither ancestry nor a clean merge proves safety.
See [the historical verification record](FORK_SECURITY_TESTING.md) for executed checks and their limits.

The security changes have GPU-free tests for remote image rejection before network access, unchanged local/base64
image paths, engine archive verification refusal and mismatches, pinned acquisition policy, normal-start behavior,
and fork acquisition routes. Tests use mocks/local fixtures rather than fetching production model artifacts.
GPU builds, hardware inference, Windows installer execution and a deployment-level air-gap test are separate checks.
