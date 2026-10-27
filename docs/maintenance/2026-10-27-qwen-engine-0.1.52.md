# Qwen native engine 0.1.52 import — 2026-10-27

## Scope and provenance

Owner request: check newest upstream and apply Qwen engine changes to the owner fork. This is a source-only
import, not an update of the production checkout, binary, runtime configuration or systemd service.

- Upstream latest stable API: app **v0.2.7**, published **2026-10-27T14:54:42Z**.
- Tag object: `3f6d9c28e56bfce604601f39de53d457fa90dc74`; peeled source commit:
  **`5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d`**. Git and HTTPS API agree. Tag is unsigned;
  agreement proves revision identity, not publisher trust or a cryptographic release attestation.
- Native CMake project version: **0.1.52**; do not confuse it with app version 0.2.7.
- Previous public fork main: `e3c3106a4ce0e76f068ec5452e5df7b1bfc0c4d7` (hardened app v0.1.45).
- Candidate builds on the existing engine-only branch commit
  `0c193e54034481e2513613a12ee8135d7cdb5bf7` (native 0.1.48), retaining it in ancestry.
- Local recovery ref: `recovery-qwen-engine-20261027` at previous public main. Review branch:
  `engine-v0.1.52-qwen-20261027`. No reset, rebase or force push.

This is **not a full merge of upstream app 0.2.7**. Its Python server, UI, installers, new HTTP features and
DeepSeek engine are not imported. Upstream tag ancestry will not appear as a normal full merge: use this exact
source pin and tree comparison, not an ancestry-only claim, to verify the native backport.

## Included changes and relevance

Imported coherent Qwen/shared `src/` and `include/` (excluding `src/dsv41` and `include/strata/dsv41`), root CMake,
`cmake/`, ggml/TQP overlay changes, native core/program/platform/CUDA/HIP tests, referenced benchmark sources,
and the optional CUDA spill checker plus tests. The existing llama.cpp pin is unchanged. Included CMake test
sources and overlays are part of the build closure, not optional documentation.

Key upstream changes since native 0.1.48:

| Area | Included behavior and limits |
| --- | --- |
| CUDA layer-split prefill | Layer-major super-chunks, even chunk sizing, compatible PLE first stage, per-layer warm/staging and fallback rules. Default on for eligible CUDA layer splits (`37e4832a`, `6eff377a`, associated fixes). `STRATA_PREFILL_LAYER_MAJOR=0` opts out. Relevant to two-card prompt processing; no speed measurement on our Q4_K_XL setup. |
| Conversation correctness | Prevent parking a conversation with another conversation's retained K/V (`f8ff3420`); park idle batch slots before admission overwrites them (`01e404c1`); device-aware buffer reuse, copy-stream readiness and checkpoint joins. |
| Cache performance | Safe restore admission and copy-stream allocation; optional asynchronous parking, VRAM K/V tier, checkpoint pooling/gathering. The new optional switches are not enabled by this import. |
| Batch/MTP | Two-NVIDIA-card pipelined groups by default (`ec8e4059`); optional pipelined MTP and adaptive rounds. Existing solo/batch/DONE framing stays compatible with the retained server. Grouping can change floating-point execution shape; do not assert byte-identical generated answers. |
| PLE | RAM-resident table admission accounts for table + expert arena + headroom, with conservative handling of unknown telemetry (`472de9cd`); short mapped reads can use a safe fallback. Host-memory availability determines admission; this is not a fixed new RAM allocation guarantee. |
| CPU experts | AVX-512 IQ reference/gather paths, runtime parity checks, TQP overlay support and CPU-dispatch fixes. IQ speed claims do not establish Q4_K speedup. |
| Speculation | Coupled proposal/gating, sampler error handling and acceptance logic. New optional probabilistic modes are not enabled by this import. |

Upstream also adds a default prompt-attention integer-matrix path on suitable CUDA devices and different
summation-order kernels on some Blackwell cards; batch and backend defaults can change numerics. Existing
opt-outs and explicit overrides remain. `STRATA_DEFAULTS=026` restores its enumerated 0.2.7 default changes,
**not every behavior from engine 0.1.48**. Approximate KVA remains opt-in. None of these source imports proves
better answer quality or measured throughput on our model/hardware.

## Intentional fork adaptations

1. **Residency-biased routing remains opt-in.** Upstream 0.2.7 automatically uses a 1.5 expert-residency bonus
   on small discrete CUDA cards. It changes which experts execute, not only summation order; upstream speed
   measurements on IQ3_XXS do not establish acceptable accuracy for UD-Q4_K_XL. Fork constant
   `kRoutePriorSmallCard` is zero. Explicit `STRATA_ROUTE_PRIOR=1.5` remains honored before the default rule.
   A compiled regression first failed against upstream's 1.5 default, then passed against the fork policy.
   A second regression compiles the actual extracted `g_route_prior()` function in its no-device HIP branch,
   exercising unset/zero/1.5 override behavior; it is not a CUDA execution test.
2. **Qwen-only CMake graph.** `STRATA_BUILD_DSV41=ON` fails early with a clear unsupported diagnostic, rather
   than advertising a DeepSeek build whose sources were not imported. Dormant upstream DeepSeek CMake branches
   remain disabled. CUDA/HIP/SYCL/Metal paths are not hardware-qualified here.
3. **ISA verification follows the new guarded kernel.** Add `iq512_reference_gu_rows` only after inspecting
   the AVX-512/AVX2/FMA-guarded dispatcher. A regression also exposed the checker's old substring match that
   confused `expert.cpp.o` and `native_expert.cpp.o`; object matching now uses exact basenames. New tests accept
   the intended wide object but reject the baseline object and weak/COMDAT form. Runtime CPU feature checks are
   not weakened. The final compiled-library ISA check passes.
4. **Keep installer policy separate from engine version.** Retain minimum engine 0.1.45 and existing model
   minimums while updating the regression's native project-version expectation to 0.1.52. The sole setup.py
   difference from former public main remains the earlier 0.1.48 addition of `third_party/ggml-tq` to source
   fingerprint inputs. Hash refusal, fork acquisition URLs, pinned-download policy and ordinary-start behavior
   are unchanged.
5. Trim upstream trailing blank lines in three native files for whitespace checks. The checker retains existing
   CRLF lines; use the explicit CRLF-aware whitespace setting recorded below.

## Executed qualification

Execution host: Smith's isolated review checkout and Python environment. No production model/GPU was used.

```sh
TEST_PY=/root/workspace/strata-fork-sync/test-venv/bin/python
"$TEST_PY" -m unittest discover -s tools -p 'test_setup_*.py'
"$TEST_PY" -m unittest tools.test_mtp_fetch tools.test_mtp_trust_policy tools.test_fork_routes \
  tools.test_fork_engine_defaults tools.test_check_cuda_spills
"$TEST_PY" -m unittest tools.test_check_isa_guard tools.test_fork_engine_defaults
"$TEST_PY" -m unittest discover -s serve -p 'test_*.py'
```

- Installer final: **636 run, 1 skipped, no failures/errors**. Initial run had one stale version expectation
  (0.1.48 rather than 0.1.52), corrected without changing installer policy.
- MTP/fork/default/spill-check group: **33 run, no failures/errors**.
- ISA/routing policy final: **12 run, no failures/errors**, overlapping two routing tests in the previous group;
  do not sum these as distinct totals. Policy RED runs are retained.
- First full server run: **856 run, 11 skipped, one sampler thread-count failure** in unchanged runtime code.
  Second run instead hit a monitor-state timing assertion; an isolated third run and monitor-then-sampler
  reproducer exposed the sampler test's use of all `_loop` threads. The test now selects its own telemetry
  bound-method thread, requires it alive, closes its server and joins/asserts termination. Server/telemetry
  implementation is unchanged; only `serve/test_responses.py` was repaired. The combined reproducer passes.
  **Final full server run after this repair: 856 run, 11 skipped, no failures/errors.** Initial broad failures
  remain in the evidence logs rather than being counted as passes.

CPU-only native configuration uses native experts ON, tests ON, Release compiler settings with explicit
`-UNDEBUG` (assertions enabled), CPU ggml ON, GPU backends OFF, `GGML_NATIVE=ON`, and the existing pinned
llama.cpp source directory. Complete native target build succeeds with two workers. This is not a CUDA engine
binary build.

```sh
cmake -S . -B "$BUILD" -DSTRATA_ENABLE_CUDA=OFF -DSTRATA_ENABLE_HIP=OFF \
  -DSTRATA_BUILD_TESTS=ON -DSTRATA_NATIVE_EXPERTS=ON -DCMAKE_BUILD_TYPE=Release \
  '-DCMAKE_C_FLAGS_RELEASE=-O2 -UNDEBUG' '-DCMAKE_CXX_FLAGS_RELEASE=-O2 -UNDEBUG' \
  -DFETCHCONTENT_SOURCE_DIR_STRATA_LLAMACPP="$PINNED_LLAMA_SOURCE" -DGGML_NATIVE=ON
cmake --build "$BUILD" -j 2
ctest --test-dir "$BUILD" --output-on-failure -j 2 --output-junit "$EVIDENCE/ctest-final.xml"
```

**Final native result: 83 cases, 77 passed, 4 skipped, 2 failed. Do not call this a green native suite.**
Initial native run additionally failed the ISA allowlist check; that check now passes after the reviewed fix.
The two remaining failures are `q8k_quant_parity` and `q8k_quant_parity_avx`: pinned ggml's `nearest_int`
asserts on the existing edge-case vectors. A fresh run of those two **preserved 0.1.48 binaries** fails at the
same assertion, and the parity-test source is unchanged. These are inherited unresolved findings, not waived
passes or proof that model execution can never reach an edge case. Assertions were not disabled to conceal them.
The four skips are capability-specific: `expert_multi_test` requires AVX-512 features unavailable to this
execution host; `native_hadamard_test`, `tq_cpu_parity` and `tq_cpu_parity_avx2` require trellis types absent
from the pinned ggml build. The Hadamard test's preliminary FWHT calculation passes but its trellis path is
still skipped. No skipped-path execution is claimed.

Static gates passed: shell and JavaScript parse; exact native provenance comparison (no missing Qwen/shared
native files and only the six documented source/header deviations, plus adjusted CMake); protected
API/installer policy comparison; documentation relative-link checks; and CRLF-aware whitespace check.
Ordinary `git diff --check` reports CRLF endings in the changed ISA script and is not claimed green.
Added-content credential-pattern scanning also passed before commit.

Independent bounded static review (`deleg_787a8b4f`) returned `passed: true`, no import-specific logic or
security blockers; retained trusted-local DFlash2 and unqualified GPU/async ownership limits were recorded.
The reviewer did not execute tests or certify every upstream kernel. A bounded delta review (`deleg_62a523c4`)
also passed the sampler test repair, confirming that ownership matching preserves the live-thread and
termination assertions and cannot be masked by another sampler exiting. Parent-run tests provide the separate
execution evidence above.

```sh
git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --check
sh -n setup.sh update.sh
node --check serve/web/app.js
```

Local evidence root: `/root/workspace/strata-fork-sync/engine052-evidence/`. It includes configure/build logs,
initial and final native XML/logs, original and final installer/server logs, focused/policy logs and the
baseline quantizer recheck. These local paths are not portable repository assets or external credentials.

## Acceptance limits and recovery

This publishes reviewed native **source**, not a production-ready binary attestation. No CUDA/HIP/SYCL/Metal
build, dual-GPU cache/restore test, real Qwen inference, matched performance/quality benchmark, Windows execution,
air-gap certification, deployment, service restart or full restore was performed. The old native local DFlash2
pack-input bounds concern remains an unqualified optional path; it is not served MTP behavior. Retained Python
server does not expose the new upstream logprob/allowed-token API or split-serving app features.

Before deployment, separately qualify the exact fork candidate with the correct model/GPUs and preserve the
current source/engine/config/overlay recovery set. The repository does not change production just by advancing
GitHub main. Rollback of this public source import uses a reviewed revert rather than reset or force push;
restoring prior production state remains a separate managed operation. Future imports must preserve this
routing-policy exception, ISA-check regression and complete native dependency closure. See
[the upstream-sync runbook](../FORK_UPSTREAM_SYNC.md) and [security policy](../FORK_SECURITY.md).
