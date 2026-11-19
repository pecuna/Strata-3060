# Engine 0.1.62 isolated candidate — 2026-11-19

## Status and exact sources

**Hardware-tested candidate, not promoted to main. Temporarily exercised through the existing production service, then restored to0.1.58.** The [paired benchmark and live qualification report](2026-11-19-engine-0162-benchmark.md) records the measured, workload-specific results and limits.

- Fork baseline: `7ef64f389647a403a58296e376fe6054b1cf4e73`, engine0.1.58.
- Upstream app v0.2.16, engine0.1.62, peeled source `64524fb9fc82222ddce554c0643b64f056ec8366`.
- Candidate branch: `engine-v0.1.62-candidate-20261119`.
- Local recovery ref: `recovery-engine-0158-20261119` at the fork baseline.
- Native source fingerprint: `f35a7f05503bb9ac`; old vision fingerprint remains `13d9deaf827f14ef`.

The public fork and deployed checkout were read back at the baseline before work. Live health showed the existing UD-Q4_K_XL model loaded, context218336. The text PID was on three RTX3060s and the vision PID only on its existing card. The hardware window changed only the language executable and BUILD metadata temporarily; their exact originals and mode/ownership were restored. Production source (including overlays), unit, configuration, vision executable, gateway, model files and GPU placement were preserved.

## Integration boundary

Flattened the pinned upstream engine native sources into the existing root `src/`, `include/`, `cmake/`, `tests/`, `bench/` and native vendored dependencies. Do not apply upstream's repository-wide folder migration. Existing `serve/server.py`, application layout, launchers and installed `engine/` output location remain the management contract.

Root CPU/CUDA is the qualification target. Separate DeepSeek, standalone strata-split and SYCL builds are explicitly rejected by the root candidate CMake. Existing Metal/SYCL Python and native wrapper trees are preserved, NOT certified compatible with the new shared engine. HIP source is retained but not hardware-qualified. A layer split of the normal Qwen engine is not the separate standalone strata-split project.

The new upstream vision reader is **not imported**. `tools/vision/` and its pinned llama.cpp dependency remain independent of the language engine's new quantization stack. Old-encoder/new-engine image compatibility was subsequently exercised with real red-circle and blue-triangle requests, plus a fresh image after a clean candidate restart; source preservation alone was not treated as proof.

### Deliberate integration changes

- Import900 pinned native files; remove21 obsolete files only in the candidate's owned `src/`, `include/`, `cmake/` sets. Existing fork-only test and benchmark files outside those sets remain.
- Relocate CMake's `../tools/` and `../terminal/tools/` references to root `tools/`, and one AMD table-test path to `tools/hip/`.
- Preserve the fork's exact-object/weak-symbol ISA guard and CUDA spill guard. Add upstream's no-MMQ-symbol checker and its tests.
- Vendor the pinned engine's `strata-ggml` for CPU oracle tests/optional legacy CPU pool, and `strata-gguf-py` for deterministic native GPU fixtures. The fixture generator uses the vendored module without fetching a vision checkout.
- `setup.py`: extend `ENGINE_SOURCES` to include `third_party/strata-ggml`; remove only obsolete MMQ definitions and the vision-llama GGML override from explicit CUDA/HIP language builds. Keep image-reader LLAMA_DIR, build tooling, artifact verification, startup and acquisition behavior.
- Preserve zero effective route-prior default and explicit owner override; compiled resolver tests pass. Do not infer effective routing from the unused numeric constant alone.
- New optional runtime mechanisms are not added to the installed config. Native numerical/default changes in upstream are part of the candidate and must be benchmarked/validated; no bit-identical output promise versus0.1.58.
- Trim five upstream whitespace issues. The native provenance audit names ten deviations from pinned upstream: root CMake, five CMake modules, the AMD path-test fix, and three whitespace-only native files.

## Security and existing fixes

The fork policy in `docs/FORK_SECURITY.md` still takes precedence. The source audit compares422 protected payloads to a clean baseline checkout: no changes in application/server, launchers, model/MTP acquisition, vision, Metal or SYCL paths. Windows BAT checkout CRLF follows the existing `.gitattributes`; Git blobs use LF. `setup.py` is separately checked against the exact allowed integration delta.

Remote-image refusal, trusted checksums, no pinned-revision fallback, MTP full-content verification, private config writes and no ordinary-start mutation remain mandatory regression gates. This import does not add signed-release infrastructure or deploy egress/authentication controls. Production-only overlays must still be captured and reconciled before any future deployment; preserving public-fork bytes does not package every uncommitted production overlay.

## Executed tests and initial failures

Tests use the isolated pinned Python requirements; host Python3.14.8, GCC14.2, CMake4.4.3 and Ninja1.13.2. GPU-less tests are not real GPU inference.

- Baseline server:856 run,11 skipped, one existing keepawake worker-scheduling failure; original log retained.
- Candidate server:856 run,11 skipped, no failures/errors. Application source/tests unchanged.
- Baseline installer:636 run,one skipped, no failures/errors.
- Initial candidate installer:636 run,one skipped,two failures: source-version assertion expected0.1.58 and a historical test expected a removed MMQ option. Updated only those expectations; Q6_K remains explicitly enabled and the minimum-engine policy is unchanged.
- Final candidate installer:636 run,one skipped,no failures/errors.
- Baseline and candidate focused MTP/trust/routes/routing/ISA policy suite:34 run each, no failures/errors.
- Import/routing/guard suite: final27 cases (includes four new integration cases); raw final log is authoritative. Overlaps with policy tests; do not sum.
- New integration RED/GREEN observed for version/layout, vendored source-hash mutation/removal, obsolete build definitions, and offline fixture preparation.
- Full assertion-enabled CPU native build:340 build steps completed, two workers.
- Initial native CTest:145 tests, two AMD table-test path failures, eight skips. Corrected the path relocation; both affected cases pass. Final full rerun:145 tests,zero failures,eight skips, CTest exit0. Skips: io_priority, quant_golden_regen (compiler-specific reference regeneration), expert_multi, native_hadamard, tq_cpu, tq_cpu_avx2, expert_parity and pool_test. Skipped cases remain unqualified, not passed.
- Final staged whitespace gate uses `git -c core.whitespace=cr-at-eol diff --cached --check`, with exactly two checked exceptions: blank EOF lines in pinned, byte-identical vendor `ggml-cpu/arch/arm/quants.c` and `ggml-cpu/unary-ops.cpp`. Any other diagnostic fails the gate. The CRLF-aware setting preserves an upstream CRLF test file. Added tracked/untracked textual source scan found zero credential-literal, shell-execution or pickle-load matches in the selected patterns; this is a bounded scan, not a complete security audit.

Independent native dependency review identified relocation/source-hash/protocol gates; its verdict was partial, not compatibility approval. Protocol review `deleg_37642f34` found no mandatory wire-format break in inspected paths: INFO/READY, GEN/GENI, STOP, DONE/BDONE and RESUME retain the old server's required shape, and the old encoder's five-int32 plus float32 embedding records match the new reader. Parent independently read the READY parser and both embedding writer/reader implementations. This is static inspection, not real-model qualification.

Preserved server limitations: it does not request native `slot_read=1` or `hold=N:ID`, and ignores the optional batched prompt-read suffix and batched RESUME accounting. Do not claim slot-local prompt-read, native hold/batched hold or complete new telemetry as integrated. Keep those opt-in/capability additions out of the first candidate's claimed benefits. Subsequent hardware tests exercised GPU CLI operation, real image interpretation and cache reuse; cancellation latency remains unqualified.

Independent integration review `deleg_32b6eb76` passed with no identified security concerns or logic errors in the bounded source-candidate scope. It did not run tests or certify GPU/protocol/production operation. Its suggestions were addressed by strengthening fixture checks to require every expected name, binary header and data/reference size, excluding generated bytecode from staging, and explicitly scoping the preservation claim. Retained MMQ-only diagnostic sources and ggml-tq helpers are legacy/unwired: some reference removed headers and are not current MMQ coverage. This is not a full upstream engine-tree mirror or a cross-backend release.

## Reproducible isolated build

From the candidate checkout, with the fork's requirements installed in a dedicated environment and cmake/ninja on PATH:

```sh
cmake -S . -B ../strata-0162-build-cpu -G Ninja \
  -DSTRATA_ENABLE_CUDA=OFF -DSTRATA_ENABLE_HIP=OFF \
  -DSTRATA_NATIVE_EXPERTS=ON -DSTRATA_BUILD_TESTS=ON \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_CXX_FLAGS=-UNDEBUG
cmake --build ../strata-0162-build-cpu -j 2
ctest --test-dir ../strata-0162-build-cpu --output-on-failure -j 2 --timeout 180
python -m unittest tools.test_fork_engine_0162 tools.test_fork_engine_0157 tools.test_fork_engine_defaults tools.test_check_isa_guard tools.test_check_no_mmq
python -m unittest discover -s serve -p 'test_*.py'
python -m unittest discover -s tools -p 'test_setup_*.py'
python -m unittest tools.test_mtp_fetch tools.test_mtp_trust_policy tools.test_fork_routes
```

The separate SM86 CUDA build completed with `STRATA_ENABLE_CUDA=ON`, `CMAKE_CUDA_ARCHITECTURES=86`, `STRATA_BUILD_TESTS=ON`, and two workers. It ran under a bounded user.slice job (6-GiB maximum, no swap, two CPUs,2700-second limit). Do not invoke upstream setup/start/update launchers merely to test the candidate. Preserve the installed encoder and matching metadata. Do not run real GPU tests alongside busy inference without checking resource headroom and obtaining the required activation window.

## Remaining gates and rollback

The approved hardware window completed: isolated CUDA build,36 focused GPU test executions (12 per card,zero failures/skips), real text/tool/image requests,43K retrieval/cache reuse, candidate restart/image acceptance, and24 matched benchmark requests. A broad all-format IQ prefill diagnostic also passed on the first card before the broader run was stopped; complete broad coverage on the other cards is not claimed. The original0.1.58 executable/BUILD and all protected/source hashes plus installed modes/owners were restored and independently verified; original acceptance passed. Production was left active at0.1.58, NRestarts0. No main promotion or retained production upgrade occurred.

The hardware helpers initially exposed CTest log-ownership and process-name identity mistakes. Both failures are retained; native process verification now binds the managed child to the installed executable inode and SHA rather than its mutable `strata-host` thread name. Independent recovery review found partial-restore and reporting blockers; these were corrected before activation, nine failure-injection tests passed, follow-up review found no remaining blocker, and actual restoration was exercised.

Cancellation latency, full218336-token context, soak/reboot, gateway latency, diffusion/image generation and broad answer quality remain unqualified. Benchmark medians are three fixed-order repetitions, not randomized proof of universal gains. Permanent promotion remains a separate owner decision.

Before deployment: capture current source/overlays, config/unit, executable and BUILD metadata, preserve coherent rollback, reconcile every production-only fix, test the candidate against the exact workload and existing service sandbox. Keep public API/model aliases and systemd management unchanged. Present the concrete switch/rollback for owner approval before stopping the service. Restore0.1.58 after the test window unless explicitly retained.

Local source evidence: `/root/workspace/strata-0162-evidence/`. Hardware/raw benchmark evidence: `/root/workspace/strata-0162-live-evidence/`, exported from the retained private candidate/rollback directory on alex. Evidence archive SHA256 `157faceffe8e2cdf3b15f63626d9532bb3fffae29beabcecaa061789afcd8bc7`; all25 exported-file hashes verified after transfer. Helpers and isolated environments are outside the tracked candidate checkout. No operational credentials/configuration dumps are published with the report.
