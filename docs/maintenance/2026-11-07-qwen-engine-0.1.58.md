# Qwen native engine 0.1.58 import — 2026-11-07

## Source identity and scope

- Owner fork baseline: `83ed4f4fab751703e0284ecc75f8cf4ecd4c891c` (native 0.1.52).
- Upstream app **v0.2.12**, engine **0.1.58**, published 2026-11-07T08:54:40Z.
- Tag object `123bad4acd5fd3fe70f02ad4c938e0c360efe5e5`; peeled source
  **`146df3c468739147f520ac3816de806f71232571`**, checked by Git and release API.
- Review branch: `engine-v0.1.58-qwen-20261107`. Earlier unpublished 0.1.57 candidate
  was retargeted; it was never deployed or pushed.

This is an **engine-only backport**, not a merge of the upstream Python app,
installers, updater, standalone `src/split` engine, DeepSeek, or drafting downloads.
The existing layer-split Qwen path is retained. New tuned DFlash2 acquisition is
not imported; current MTP configuration is not changed. `serve/`, `setup.py`,
`setup.sh`, `update.sh`, artifact verification and acquisition policy retain their
baseline bytes. Native version does not change installer minimum-version policy.

## Native closure and intentional differences

Imported upstream Qwen/shared `src/`, `include/`, root CMake, `cmake/`, ggml/TQP
overlays, native test and benchmark sources and test fixtures. Included the two
rocBLAS data tables needed by the new AMD community tests, without changing the
AMD Python installer. The pinned llama.cpp dependency remains unchanged.

A byte audit checked 559 native/include/overlay paths against the pinned release.
Only two native files differ by trimmed trailing blank lines. Root CMake also
retains the fork's early unsupported-DeepSeek diagnostic and trims whitespace.
The retained ISA checker still enforces exact object basenames and rejects weak
symbols; new guarded `q50_512_down_rows`, `iq512_fused_gu_rows`, `iq512x_rows`
entries have a compiled-call-site review and positive/negative policy tests.
Upstream now also defaults residency-biased routing to zero; explicit overrides
remain honored by a regression compiling the actual production resolver.

Relevant native changes include K-quant prompt MMQ defaults on SM80+, measured
CPU/PCIe miss balancing on CUDA layer splits, Linux expert-source admission
accounting, layer-split memory reductions and CUDA prompt safety fixes. These
can change arithmetic/results. Neither source tests nor upstream speed claims
establish local speed or answer quality.

## Source qualification (Smith; no GPU in these suites)

Commands use `/root/workspace/strata-fork-sync/test-venv/bin/python`:

- Installer: `-m unittest discover -s tools -p 'test_setup_*.py'`:
  **636 run, one skipped, no failures/errors**.
- Focused import/routing/ISA/spill/MTP/trust/fork-route suites:
  **47 run, no failures/errors** (overlap not added to other totals).
- Native CPU: Release, `-O2 -UNDEBUG`, native experts ON, CUDA/HIP OFF,
  existing pinned llama.cpp, two build workers. Complete build passed.
- Native CTest final: **99 total: 92 passed, five skipped, two failed**.
  `q8k_quant_parity` and `_avx` fail ggml's strict `nearest_int` assertion;
  both reproduced now against the preserved 0.1.52 build. Assertions were not disabled.
  Skips: io_priority, expert_multi, native_hadamard, tq_cpu and tq_cpu_avx2.
- Initial CTest additionally failed both AMD community tests due to absent table
  data. Importing the matching upstream tables fixed both; original log retained.
- Initial installer run on the 0.1.57 candidate failed a stale version assertion;
  updated only the native-version expectation, not installer policy.
- Initial server suite: **856 run, 11 skipped, one keepawake failure**. App bytes
  are unchanged. This original broad result is retained, not relabeled green.
  Independent diagnosis reproduced an inherited worker-scheduling race: the mock
  request can finish before the asynchronous Windows keepawake worker observes
  the busy state. Focused six tests passed; ten repeated service tests had one
  failure. An in-memory test-only synchronization ran 100 times without failure.
  No production keepawake behavior or tracked server test was changed.
  Final unmodified-server rerun: **856 run, 11 skipped, OK**. This confirms
  the final source gate; the intermittent failure above remains recorded.
- CRLF-aware whitespace gate `git -c core.whitespace=cr-at-eol diff --check`,
  shell syntax and JS syntax pass. Added-line scan found no credential literals,
  shell=True/os.system, pickle loading or eval calls.

## Independent review

Final staged-source review passed (`deleg_f72e04c8`), with no security concerns
or logic errors in the reviewed source scope. Earlier reviews identified missing
ROCm table fixtures; their upstream blob IDs were verified after staging and
both affected native tests passed. CUDA qualification remains separate.

Local detailed evidence: `/root/workspace/strata-0157-backport/` including build,
JUnit, original/final test logs, source audit and matched benchmark artifacts.
Production CUDA build, inference, deployment and measured speed are separate
qualification steps; this source receipt alone does not certify them.
