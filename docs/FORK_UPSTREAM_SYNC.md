# Maintaining Strata-3060 across upstream releases

This is the repeatable maintenance runbook for `pecuna/Strata-3060`, whose upstream is
`Niko1221/Strata`. Read it before every upstream synchronization. Bring in reviewed upstream improvements
**without losing this fork's security behavior**. A successful Git merge is not sufficient verification.

The [security policy](FORK_SECURITY.md) defines required behavior. The
[original verification record](FORK_SECURITY_TESTING.md) records evidence and limits. This document records
what changed, where to find it, how to preserve/reapply it, and the release gates. It is a manual reviewed
procedure, not an automatic scheduler or a claim that all future upstream changes will merge safely.
The [documentation maintenance record](maintenance/2026-10-11-fork-sync-documentation.md) records fresh
checks performed while preparing this runbook; it is not a future release's verification receipt.

## 1. Historical baseline and scope

The initial synchronization and hardening were performed on 2026-10-11:

| Object | Exact revision / action |
| --- | --- |
| Fork before synchronization | `61b3fb5dd3f1e8ec09cf7e4e05208bc6d3c46406` |
| Reviewed upstream main imported | `7695859aa13afb248bdb4d36f9b2e95707db079d` |
| Import | Non-force fast-forward: 0 fork-only / 72 upstream-only commits; 66 files, 4,687 insertions, 187 deletions |
| Fork hardening commit | `960faa4e58e23d35143fa70fcd41f6f195549fb4` — `fix(security): harden offline runtime and artifact trust` |
| Original recovery reference | Local branch `fork-main-before-sync-20261011` at the pre-sync fork revision |
| Original execution | Isolated source review/test checkout on Smith, not the production working tree |

The existing SSH key was tested through Git repository reads, a dry-run push and real non-force pushes.
Fork refs were read back through SSH and independently through GitHub's HTTPS API. No new credential was
created. Strict GitHub host-key verification was retained; do not copy private keys into this repository.

The upstream review included request accounting/stop handling, non-finite-logit recovery, NUMA/cache-release
work, CUDA sm_86 and adaptive-copy work, AMD/Intel changes and benchmark tools. These were upstream source
changes and published claims, **not measured GPU gains on our hardware**. Importing a release does not
justify enabling all its tuning flags or replacing owner settings.

The network audit inspected runtime, browser assets, MCP, setup/update/build/download code and two
point-in-time production socket snapshots. No built-in cloud inference fallback, analytics upload or frontend
CDN requirement was found in the reviewed runtime paths. No Internet socket was attributed to Strata in those
snapshots. These are historical bounded findings, not a packet capture or proof that the whole host is offline.
The identified risks were remote image fetching/SSRF, permissive artifact verification, revision fallback,
MTP trust/cache bypasses, implicit launcher updates and misleading privacy wording.

The initial sync/hardening actions did not deploy or restart production. That statement applies to those
actions only; it does not describe subsequent deployments or current production state. Resolve the site's
current operational runbook before any deployment. This public source runbook contains no live credentials,
host-specific model tuning or production overlay patch.

## 2. Change ledger and reapplication map

Use function names and behavior, not historical line numbers; upstream refactors can move these boundaries.
The hardening commit is the complete historical patch. Preserve later fork commits too, not only this baseline.

### Runtime images — `serve/server.py`

- `Vision.download` always raises for remote image sources without URL opening, DNS, proxies or redirects.
- `Vision.load` and `Service.prepare` classify HTTP(S) with `urlsplit(...).scheme`, including uppercase,
  leading whitespace and control-character forms handled by the URL parser. User images are refused before
  encoder/file access where applicable; remote tool-result images are omitted without downloading.
- Base64 image data and supported local-file paths remain available. Error/help text does not advertise
  HTTP(S) as supported. Local-file access is **not** a filesystem sandbox.
- Do not restore unrestricted fetching, or replace it with a hostname-only allowlist that ignores DNS/redirects.

Regression owners: `serve/test_remote_image_policy.py`, `serve/test_remote_image_http.py`, and
`serve/test_server.py` classes `ImageSources` / `ImageMarkers`. The HTTP test sends actual loopback requests
to both OpenAI and Anthropic APIs with a mock engine/vision encoder; it is not GPU inference.

### Engine source and integrity — `setup.py`

- `PREBUILT_URL`, `REPO`, `PREBUILT_TAG_URL` default to `pecuna/Strata-3060`. Version-specific and latest
  default candidates remain in the fork; no implicit upstream binary fallback.
- `engine_digest` rejects missing/malformed release SHA256 metadata. `verify_engine_archive` requires a
  trusted expected hash, verifies size where release metadata supplies it, and hashes archive content before
  unpacking. Local archives and non-GitHub mirrors do not acquire trust simply by being local or mirrored.
- `STRATA_ENGINE_SHA256` accepts exactly 64 hexadecimal characters as an explicit owner pin, including for
  local/mirror archives, with accurate provenance in diagnostics. Obtain the expected hash independently;
  hashing an untrusted download and trusting that same hash is not verification.
- `STRATA_SKIP_SHA256=1` does not disable engine verification. An archive refusal removes download/finish
  marks and prevents installation. First installation stops; a refused update retains the existing engine.
- `get_prebuilt` must keep the installed `BUILD.json` in place until verified replacement.
  `install_unpacked` owns executable/metadata backup and rollback during replacement. Check both CUDA and
  HIP callers; do not rely only on a wrapper repairing metadata after an unsafe helper.
- Explicit `--prebuilt` GitHub sources remain an owner choice; their digest comes from the selected repository.
  Fork-first defaults are not a prohibition on every explicitly selected external artifact.

Regression owners: `tools/test_setup_engine_hash.py`, `tools/test_setup_amd.py`,
`tools/test_setup_choices.py`, `tools/test_setup_hotfix_tag.py`. In particular, preserve
`WhatARefusalDoesToTheCaller.test_refused_cuda_and_hip_updates_preserve_executable_and_metadata` and its
byte comparisons/no-install assertion. Do not weaken the tests to accommodate a refusal that loses metadata.

### Pinned model acquisition — `setup.py`

- `download` must not convert pinned Hugging Face revision 404s to `/resolve/main/`, including configured mirrors.
  An unavailable pin is an acquisition failure, not permission to download different content.
- A newly downloaded ModelScope file lacking provider SHA256 is removed and setup stops without completion
  marking. ModelScope current-file provenance is still weaker than a pinned Hugging Face revision.
- Keep model verification immune to the engine skip variable. The pre-existing model-shard `.done` cache
  still assumes a trusted local filesystem; this hardening did not make every model check a full rehash.

Regression owners: `tools/test_setup_pins.py`, `tools/test_setup_modelscope.py`,
`tools/test_setup_hardening.py` (`PinnedDownloads`, `ModelVerification`). Helper functions that can construct
unpinned URLs may still exist; the invariant is that acquisition does not invoke them as a silent fallback.

### MTP content identity — `tools/mtp_fetch.py` and `setup.py`

- `resolve_repo` never silently changes a missing revision to `main`.
- `trusted_sha256`, `inventory`, `fetch` require valid built-in expected hashes for every selected tensor.
  Unknown/malformed hash entries fail before tensor reads/publication. A manifest's self-computed digest alone
  is not a trust anchor. Range validation and valid partial resume remain supported.
- `STRATA_MTP_REVISION`, endpoint/source overrides and alternate repositories change the source, not trusted
  content identity. Byte-identical alternative sources can work; different tensors require reviewed pins/hashes.
- `verify` always rehashes expected raw tensors; it cannot certify by size/mtime sidecar, changed revision or
  absent directory. Same-size/preserved-mtime corruption must still be caught.
- `setup.mtp_corrupt`: missing raw tensors are unverified/corrupt; exit 0 is verified, exit 3 means corrupt,
  every other verifier status stops setup. Include bounded captured diagnostics (last 2,000 characters).
  Restoring raw tensors may be necessary to verify/reuse an already prepared MTP runtime.

Regression owners: `tools/test_mtp_fetch.py`, `tools/test_mtp_trust_policy.py`,
`tools/test_setup_pins.py`, `tools/test_setup_hardening.py` (`MTPVerifierErrors`). Never regenerate expected
hashes from a suspect mirror merely to make a download pass. New model/tensor support requires a reviewed
source-revision and content-hash update, with new fixtures/tests; this document is not authorization for it.

### Ordinary start versus explicit maintenance — `setup.py`

- Existing-config start and calibration do not call `update_installed_engine` implicitly.
- `ensure_engine_for` checks compatibility without downloading, fetching build dependencies, rebuilding,
  rewriting config or automatically migrating an older card to CUDA 12.
- Incompatibility refuses start with explicit preparation guidance (`--setup --build`, or
  `--setup --cuda 12 --build` where appropriate). Explicit install/setup/build/update can still use networking.
- Do not remove explicit update/build features; do not treat a production systemd start as installer setup.

Regression owners: `tools/test_setup_hardening.py` (`OrdinaryStartEnginePolicy`, `ExistingConfigLaunch`),
`tools/test_setup_older_gpus.py`. Preserve upstream compatibility checks while removing only implicit mutation.

### Acquisition instructions, UI and policy precedence

- `update.sh`, `UPDATE.bat`: ZIP fallback URL points to this fork. Git updates still follow configured remotes.
- `README.md`, `docs/AI_SETUP.md`: primary acquisition/AI setup instructions point to the fork. README replaces
  the external donation-button image with a normal link; upstream attribution/support/media links may remain.
- `serve/web/index.html`: fork link plus honest local-inference/MCP network disclosures, no blanket
  "Nothing leaves it" claim. Configured tool calls may transmit conversation-derived arguments.
- `docs/DETAILS.md`: base64/local images and HTTP(S) refusal. `docs/TROUBLESHOOTING.md`: integrity refusal,
  not advice to bypass checks. `AGENTS.md` and README establish fork-policy precedence over inherited
  upstream instructions/translations. Keep that precedence through future merges.
- `docs/FORK_SECURITY.md`, `docs/FORK_SECURITY_TESTING.md`: policy, remaining risks and historical evidence.
  Preserve this runbook and its entry-point links as part of future fork history.

Regression owner: `tools/test_fork_routes.py`. Inspect `docs/AI_SETUP.md`, translations and newly introduced
installers manually too; the route tests do not prove every text/link in the repository is correct.

### Benchmark startup — `tools/strata_bench.py`

The v0.1.43.1 import added a config copy to omit profile-saving flags. Such a copy
can contain credentials: preserve random atomic 0600 creation, private launch
log directories, refusal of existing log paths/symlinks, and cleanup on launch
failure or child exit. Never restore predictable ordinary-permission config copies.
Regression owner: `tools/test_bench_launch_security.py`; run alongside the full
`tools/test_strata_bench.py` suite. Attachment via `--url` must not stop an existing
server. Details: [v0.1.43.1 import record](maintenance/2026-10-13-upstream-v0.1.43.1.md).

### Test repairs, not product features

The original patch also adapted obsolete URL-download/pinned-fallback/local-archive expectations in
`serve/test_server.py`, `tools/test_mtp_fetch.py`, `tools/test_setup_pins.py`,
`tools/test_setup_engine_hash.py`, `tools/test_setup_older_gpus.py` and hotfix-tag tests. Installer CPU probes
were mocked in `tools/test_setup_amd.py` and `tools/test_setup_choices.py` so an ARM test host does not leak
into x86 GPU fixtures. Temp-root fixtures need version metadata or a mocked `source_version`.
These repairs isolate tests; they do not change CPU probing in production or certify hardware compatibility.

This ledger covers all 27 files in the original hardening commit. Recover the exact file/patch record with:

```sh
HARDENING=960faa4e58e23d35143fa70fcd41f6f195549fb4
git show --stat "$HARDENING"
git diff "$HARDENING^" "$HARDENING" -- serve/server.py setup.py tools/mtp_fetch.py
```

## 3. Choose an upstream release deliberately

Use an isolated clean review checkout, not a dirty managed production checkout. Origin must be
`git@github.com:pecuna/Strata-3060.git` (or its HTTPS equivalent); upstream must be
`https://github.com/Niko1221/Strata.git` (or its SSH equivalent). Inspect both fetch and push URLs.

For stable updates, inspect upstream release metadata/changelog and choose the exact non-draft,
non-prerelease tag. Do not assume upstream `main` is the stable release. The initial import above used reviewed
main; future development-main imports require an explicit decision and recorded SHA.
The fork may have no GitHub Releases even when source history is current: fork source, tags and binary releases
are distinct. Do not substitute a bare upstream tag for the hardened fork revision.

```sh
curl --fail --silent --show-error https://api.github.com/repos/Niko1221/Strata/releases/latest
```

Record chosen tag, release URL, upstream SHA, release date, old fork SHA and review decision. Fetch only the
chosen tag into a separate namespace: historical fork/upstream tags can differ, so do not fetch all tags with
force or overwrite them. GitHub API availability/digest failure is a blocker, not an excuse to weaken checks.

## 4. Prepare a review branch and recovery point

The following blocks are for a POSIX shell in the isolated checkout. Stop on any failed command. They share
shell variables (`OLD_FORK`, `UPSTREAM_COMMIT`, `HARDENING`, `RECOVERY_REF`, `SYNC_BRANCH`, `TEST_PY`); use one
shell session or restore their exact recorded values after opening another. Never reconstruct them from guesses.
Set `UPSTREAM_TAG` to the explicitly reviewed release tag **before** running this block. Start with a clean
worktree/index; if dirty, stop and preserve the existing work rather than reset/clean/stash it automatically.
Use the established SSH transport with strict host-key checking for origin.

```sh
set -eu
: "${UPSTREAM_TAG:?Set UPSTREAM_TAG to the reviewed upstream stable tag}"
test -z "$(git status --porcelain)"
git remote -v
# Human gate: confirm the exact fork/upstream identities above before continuing.
git fetch --no-tags origin refs/heads/main:refs/remotes/origin/main
git fetch --no-tags upstream "refs/tags/$UPSTREAM_TAG:refs/tags/upstream-review/$UPSTREAM_TAG"
OLD_FORK=$(git rev-parse --verify 'origin/main^{commit}')
UPSTREAM_COMMIT=$(git rev-parse --verify "refs/tags/upstream-review/$UPSTREAM_TAG^{commit}")
HARDENING=960faa4e58e23d35143fa70fcd41f6f195549fb4
git merge-base --is-ancestor "$HARDENING" "$OLD_FORK"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
RECOVERY_REF="fork-before-sync-$STAMP"
SYNC_BRANCH="sync/upstream-$STAMP"
git branch "$RECOVERY_REF" "$OLD_FORK"
git switch --create "$SYNC_BRANCH" "$OLD_FORK"
printf 'old=%s\nupstream=%s\nrecovery=%s\nbranch=%s\n' "$OLD_FORK" "$UPSTREAM_COMMIT" "$RECOVERY_REF" "$SYNC_BRANCH"
git rev-list --left-right --count "$OLD_FORK...$UPSTREAM_COMMIT"
git log --oneline "$OLD_FORK..$UPSTREAM_COMMIT"
git diff --stat "$OLD_FORK...$UPSTREAM_COMMIT"
```

If the hardening ancestry check fails, stop: inspect all fork-only history and use the fresh-history recovery
section below. An ancestry check passing is necessary for this normal workflow, not proof the behavior remains.
A recovery branch preserves old source, not engine/config/model state and not remote rollback by itself.

Before merging, review new network APIs, subprocess launchers, download verification, defaults, new UI assets,
MCP/tool behavior and compatibility changes. Search for new `urlopen`, `requests`, `httpx`, `fetch`, sockets,
package launchers, revision fallback and skip-hash logic; inspect full functions, not only string matches.

## 5. Merge without erasing fork history

Fork-only commits now exist. Use a normal merge on the review branch so previously published fork history and
its recovery points remain intact. Do not use GitHub's discard-fork-changes option, reset to upstream, force-push,
a blanket `ours` merge strategy or whole-file `--ours`/`--theirs` conflict resolution.

```sh
set -eu
if git merge-base --is-ancestor "$UPSTREAM_COMMIT" HEAD; then
    printf 'Chosen upstream revision is already present; inspect whether anything needs changing.\n'
else
    git merge --no-ff --no-commit "$UPSTREAM_COMMIT"
fi
```

On conflict, stop the block, inspect every conflict and reconcile behavior with Section 2. Preserve upstream
improvements and fork guarantees together. This is not solved by always taking an old whole file: that discards
new fixes. Preserve tests first, update implementation for upstream refactors, then add a regression for each
newly found bypass. Do not weaken assertions just to turn the suite green.

Inspect **all** changes relative to `OLD_FORK`, including a conflict-free merge. New entry points may bypass old
checks while existing tests still pass. Wait for all implementers to finish; never publish results from tests
started while files were being modified. If abandoning the candidate, preserve any new work first; abort only
the in-progress merge in this originally clean isolated checkout. Do not modify the production tree.

## 6. Recovery/reapplication when history cannot preserve the patch

Normally the merge retains the patch: do not cherry-pick `960faa4e` repeatedly into a history that already
contains it. Use the ledger to repair behavior that upstream accidentally overrides.

If an explicitly authorized migration/reconstruction starts from fresh upstream history, retain the original
fork and all later fork-only commits first. On a **separate clean scratch branch**, the historical patch can be
examined/exported and replayed as a starting point:

```sh
# Inspection/export only; output directory must already exist outside the source checkout.
: "${EVIDENCE_DIR:?Set EVIDENCE_DIR to the preserved review evidence directory}"
git format-patch --stdout "$HARDENING^..$HARDENING" > "$EVIDENCE_DIR/original-hardening.patch"
# Only on the authorized fresh-history scratch branch, not normal fork main:
git cherry-pick --no-commit "$HARDENING"
```

Stop on conflicts and port intent to the new architecture using Section 2; textual application is not proof.
Reconstruct later fork changes as well, retain provenance, run all gates and obtain owner approval for any
history replacement. This recipe does **not** authorize rewriting remote main. Prefer merging the maintained
fork history whenever possible. A copied patch cannot capture future commits unless the evidence is refreshed.

## 7. Required regression and review gates

Run from the candidate checkout with a separate Python environment, not production setup. Set `TEST_PY` to
its Python executable. A prepared Smith environment was `/root/workspace/strata-fork-sync/test-venv/bin/python`;
that local path is not a portable dependency or a reason to use a production venv.
For a new environment, use `python3 -m venv` and provision reviewed versions of `jinja2`, `regex`, `numpy`,
`pillow`, `psutil`, `requests`, `pyyaml` and any new test dependencies inside it. Record Python/package versions.
No system-wide pip install. Historical versions are not a promise that future tests need the same dependencies.

Fast security gate (includes adapted image-source/tool tests, not just new modules):

```sh
set -eu
: "${TEST_PY:?Set TEST_PY to the isolated environment Python}"
"$TEST_PY" -m unittest \
  serve.test_server.ImageSources serve.test_server.ImageMarkers \
  serve.test_remote_image_policy serve.test_remote_image_http \
  tools.test_setup_hardening tools.test_setup_engine_hash \
  tools.test_setup_pins tools.test_setup_modelscope tools.test_setup_older_gpus \
  tools.test_mtp_fetch tools.test_mtp_trust_policy tools.test_fork_routes
```

Full GPU-free merge gate, followed by upstream tests selected for new features:

```sh
set -eu
"$TEST_PY" -m unittest discover -s serve -p 'test_*.py'
"$TEST_PY" -m unittest discover -s tools -p 'test_setup_*.py'
"$TEST_PY" -m unittest tools.test_mtp_fetch tools.test_mtp_trust_policy tools.test_fork_routes
git diff --check
git diff --cached --check
sh -n setup.sh update.sh
node --check serve/web/app.js
```

A missing dependency, skipped relevant regression, unavailable command or failing test is unresolved evidence.
Preserve failed logs; repair the named problem and rerun affected tests, then the final merge gates. Report actual
suite totals/skips, avoid double-counting overlapping reruns, and do not treat delayed intermediate failures as
final results. The original totals belong to `FORK_SECURITY_TESTING.md`; they are not expected future counts.
Record exact tested source/patch state; if files change after testing, rerun the affected gates before commit.

Require independent review of full relevant functions and all conflict resolutions. Check for credentials,
unsafe execution and unsupported privacy/provenance claims. Native CUDA/HIP/SYCL builds, Windows execution,
real GPU/vision inference and air-gap enforcement remain separate checks; GPU-free mocks do not establish them.
No new binary releases, CI gate or automatic reapplication job is provided by this runbook.

## 8. Publish reviewed source without force

Only after all required checks pass, finish any pending merge and commit reviewed follow-up repairs/docs.
Use explicit file staging; do not sweep unrelated files into a commit. Record merge/conflict decisions and
commands/results in a per-sync record (for example `docs/maintenance/YYYY-MM-DD-<release>.md`). Include old/new
fork SHA, upstream tag/SHA, recovery ref, security checklist, failures/reruns/skips, independent review,
untested hardware/features and whether deployment was separately requested.

Before pushing, verify ancestry and re-read the remote. If someone advanced main since `OLD_FORK`, stop,
fetch/reconcile and retest instead of overwriting their work. A push race must fail safely via non-force push.

```sh
set -eu
test -z "$(git status --porcelain)"
NEW_FORK=$(git rev-parse HEAD)
git merge-base --is-ancestor "$OLD_FORK" "$NEW_FORK"
git merge-base --is-ancestor "$UPSTREAM_COMMIT" "$NEW_FORK"
git merge-base --is-ancestor "$HARDENING" "$NEW_FORK"
REMOTE_FORK=$(git ls-remote origin refs/heads/main | cut -f1)
test "$REMOTE_FORK" = "$OLD_FORK"
git push --dry-run origin HEAD:refs/heads/main
git push origin HEAD:refs/heads/main
READBACK=$(git ls-remote origin refs/heads/main | cut -f1)
test "$READBACK" = "$NEW_FORK"
curl --fail --silent --show-error https://api.github.com/repos/pecuna/Strata-3060/commits/main
```

Compare the API `sha` to `NEW_FORK` explicitly; HTTP 200 alone is not verification. Read back the exact target
ref, not another branch. Keep strict SSH host-key checks. If the API/readback fails after push, report pushed but
verification incomplete rather than repeatedly pushing. Source publication is not deployment or binary release.

## 9. Rollback and separate deployment

Before push, a bad candidate can be left on its isolated review branch while fork main remains unchanged.
After push, prefer a reviewed normal revert commit to restore previous behavior without history rewrite;
reverting a merge requires checking the actual parent ordering before selecting its mainline parent. Test and
read back the revert too. **A merge revert does not remove ancestry:** the same upstream revision can still
report "already present", and merging a later release does not automatically restore the reverted changes.
Before the next import, inspect rollback commits and the actual tree delta. Deliberately review whether to revert
the rollback commit (restoring the earlier import) or reapply corrected changes; either choice needs all security,
regression and publication gates again. Do not infer feature presence solely from `merge-base --is-ancestor`.
Never run a guessed `reset --hard`/force-push rollback against the owner fork.

If deployment is explicitly requested later, resolve the canonical host/service runbook, verify identity and
current state, preserve the local dashboard overlay and matching source/engine/venv/config recovery set, build
from the exact reviewed fork commit, and test real inference/readiness/restart through the established manager.
Do not replace the fork revision with a bare upstream stable tag. GPU source fingerprints and running binary
identity are separate from Git SHA. Production credentials, access controls, models and settings are not changed
by this source-sync procedure.

## 10. Permanent acceptance checklist

- [ ] Exact reviewed upstream tag/SHA; upstream improvements inspected, not blanket tuning enabled.
- [ ] Old fork history/recovery ref and all later fork-only work preserved.
- [ ] User and tool remote images cannot reach network APIs; base64/local paths still work.
- [ ] Fork-first binaries/acquisition routes; no silent upstream engine substitution.
- [ ] Engine hash mandatory; no local/mirror/skip bypass; refusal preserves executable **and** metadata.
- [ ] Pinned model failures do not switch revisions; missing ModelScope hash refuses completion.
- [ ] MTP content trust independent of source override/cache; missing tensors and verifier errors fail closed.
- [ ] Normal starts/calibration do not update/build/migrate; explicit maintenance remains available.
- [ ] UI/help/docs honestly describe MCP/hooks/package-manager networking; fork-policy precedence retained.
- [ ] New network paths and changed architecture reviewed; preserved tests plus new bypass regressions pass.
- [ ] Final tested candidate recorded, failures/skips explained, independent review and static checks complete.
- [ ] Non-force push and exact SSH/API readback agree; deployment status stated separately.

Remaining risks are intentional scope limits, not permission to regress: configured MCP/stdio tools, hooks and
optional wrappers can network; installation/build/package managers need sources unless pre-staged; release
checksums do not prove publisher safety; no signed release infrastructure/hash-locked wheelhouse was added;
model `.done` cache trusts the local filesystem; local image files are not sandboxed. Enforced egress, backend
access control and third-party trust require separately reviewed deployment policy.
