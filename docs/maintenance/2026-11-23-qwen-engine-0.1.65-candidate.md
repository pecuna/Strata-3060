# Qwen engine 0.1.65 candidate — 2026-11-23

## Scope and provenance

- Fork base `cf788a12a21736394275975b7bcbfec1529449f6` on the 0.1.63 quality branch. The installed comparator was built from `3f7e4de792eb99edeb7cd10b044548d38b4e1c87`; the extra base commit adjusts the SM86 guard only.
- Upstream [app v0.2.19 / engine 0.1.65](https://github.com/Niko1221/Strata/releases/tag/v0.2.19), peeled commit `c6f6427d9de9016fd92d13e29740f65625261df7`. This is deliberately pinned, not an automatic latest-version upgrade.
- Import the flattened native Qwen delta. Preserve the hardened server, installer and acquisition rules, vision helper, existing production overlays, and `strata.service`. Do not import separate Inkling/HY-4 model runtimes, change the layout, run upstream update, or advance fork `main` for this trial.
- Source fingerprints: engine `b601714a084be89f`; retained vision `13d9deaf827f14ef`. No newly enabled expert tail skipping; verify the runtime's actual overrides before retention.

## Evidence and gates

- Assert-enabled native CPU CTest: 157 passed, nine skipped, zero failures. Installer: 636 run, one skipped, no failures. Focused policy: 35 passed. The unchanged server suite ran 856 cases, with 11 skips and the documented keep-awake timing-test failure. Do not count that suite as green.
- Build the exact pinned source on SM86 with the existing CUDA toolchain. Check candidate resource usage against the exact live 0.1.63 artifact, preserve absolute findings, and reject new unexplained stack or local-memory findings. Exercise the selected native tests independently on each of the three production GPUs.
- Compare real direct API outputs on identical requests: exact text and arithmetic, abstention, authoritative record, typed JSON, tool selection and arguments, tool-result interpretation, two vision fixtures, remote-image refusal, and fresh/cached 43K retrieval. Validate the retrieval response as a complete JSON object with exact marker assignments and integer record number. Reject missing, mismatched, ineligible, or overlapping samples; speed cannot substitute for a correct answer.
- A passing set is evidence for the tested fixtures only, not general answer accuracy. Upstream's SM86 results were measured on RTX 3090 / paired RTX A4000, not this deployment. Neither upstream's throughput figures nor kernel parity establish an accuracy gain for our agent.
- Change only the native executable and matching build receipt through the existing manager. Retain only after real acceptance, restart and fresh inference; otherwise restore the verified 0.1.63 pair. Preserve unit/config/source/vision bytes and GPU placement. Use a new invocation-owned transaction; never rerun an earlier completed activation or its finalizer.
