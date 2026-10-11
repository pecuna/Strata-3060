# 2026-10-11 — fork maintenance documentation

## Scope and source

Owner request: document the completed upstream import and fork hardening so the fixes can be preserved or
reapplied whenever later upstream improvements are imported. Documentation-only work on Smith in the isolated
fork review checkout. No new upstream merge, production inspection/change, build or restart performed by this task.

Fork/upstream: `pecuna/Strata-3060` / `Niko1221/Strata`.
Runtime/test source baseline: `960faa4e58e23d35143fa70fcd41f6f195549fb4`.
Initial imported upstream base: `7695859aa13afb248bdb4d36f9b2e95707db079d`.
The containing documentation commit identifies the published documentation revision; source behavior is unchanged.

## Durable artifacts

- [Maintenance runbook](../FORK_UPSTREAM_SYNC.md): historical import/audit/hardening ledger; every original
  changed file; required behavioral invariants; stable-release selection; preserved-history merge; conflict and
  fresh-history reapplication guidance; regression gates; non-force push/readback; rollback and deployment boundary.
- README and security-policy links make the procedure discoverable. The historical testing page explicitly
  distinguishes its original results from future test/deployment state.
- No automated scheduler, merge bot, patch-replay script or CI workflow was introduced. Each sync requires
  review and execution of the runbook; security tests supplement, not replace, inspection of new entry points.

An attempted additional `AGENTS.md` link was blocked by the protected-instruction-file approval timeout;
that file was left unchanged. Its existing security-policy link leads to the new runbook indirectly.

## Fresh executed checks

Execution on Smith, using the isolated Python environment; no native GPU compilation or model inference.
Both test commands ran after the new documentation was written, against unchanged runtime/test source.
Python readback: `3.13.5`. Isolated environment package readback:

```text
certifi==2026.7.22
charset-normalizer==3.5.2
idna==3.20
Jinja2==3.1.6
MarkupSafe==3.0.4
numpy==2.5.4
pillow==12.3.0
psutil==7.2.2
PyYAML==6.0.3
regex==2026.9.29
requests==2.34.2
urllib3==2.8.0
```

This is the observed test environment, not a hash-locked dependency manifest or a recommendation to freeze
future upstream tests to these versions.

```sh
TEST_PY=/root/workspace/strata-fork-sync/test-venv/bin/python
"$TEST_PY" -m unittest \
  serve.test_server.ImageSources serve.test_server.ImageMarkers \
  serve.test_remote_image_policy serve.test_remote_image_http \
  tools.test_setup_hardening tools.test_setup_engine_hash \
  tools.test_setup_pins tools.test_setup_modelscope tools.test_setup_older_gpus \
  tools.test_mtp_fetch tools.test_mtp_trust_policy tools.test_fork_routes
"$TEST_PY" -m unittest discover -s tools -p 'test_setup_*.py'
```

| Check | Read-back result |
| --- | --- |
| Documented fast security gate | 121 tests; no failures/errors/skips; exit 0 |
| Full installer discovery | 477 tests; 1 skipped; no failures/errors; exit 0 |
| POSIX shell examples in maintenance runbook | All 8 blocks parsed with `sh -n`; no command execution implied |
| Relative Markdown links in changed docs | No missing file targets |
| Original hardening file coverage | 27 files from Git commit, all named in the ledger |
| Whitespace and launcher syntax | `git diff --check`, `sh -n setup.sh update.sh` passed |
| Web app JavaScript syntax | `node --check serve/web/app.js` passed |

The two test commands overlap; their totals are not a distinct-case sum. The original full server results
remain historical in [FORK_SECURITY_TESTING.md](../FORK_SECURITY_TESTING.md); full server discovery was not
rerun for this documentation-only change. Shell parsing is not an executed future merge or proof a future
upstream revision is compatible.

Local test logs: `/root/workspace/strata-fork-sync/documentation-security-gate.log` and
`/root/workspace/strata-fork-sync/documentation-installer-gate.log`; these local evidence paths are not portable
repository assets. Original local sync evidence is retained in `/root/workspace/strata-fork-sync/RESULT.md`;
historical hardening suite evidence is recorded in `docs/FORK_SECURITY_TESTING.md`, not freshly remeasured here.
No credentials are included. Independent read-only documentation review (`deleg_22492e67`) confirmed the
27-file ledger, function/test mapping and normal sync/publication safety. Its merge-revert ancestry caveat was
added to the rollback section, along with explicit shared-shell-variable guidance. The final documentation
still requires final static checks and exact remote revision readback before publication is reported complete.

## Evidence limits and future use

Historical no-deployment statements apply to the original source-only actions, not to later independently
managed deployments. This task did not verify current production state. Firmware/SPD/hardware measurements
are outside its scope. No Windows execution, CUDA/HIP/SYCL build, real inference, binary release publication or
air-gap enforcement was established. For each future import, replace historical counts with fresh source-bound
results, preserve failure/skip records, and separately authorize/verify any deployment.
