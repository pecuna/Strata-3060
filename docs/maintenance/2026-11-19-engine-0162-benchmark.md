# Strata 0.1.62 versus 0.1.58 — live qualification and benchmark

Checked UTC: 2026-11-19T02:58:47.262243+00:00

Tested candidate: `7a930bb276b94028b01574f25b34527549ddc485`; native source `f35a7f05503bb9ac`.

Both engines used the unchanged deployed application/configuration, three RTX 3060s, existing CUDA vision encoder, same Q4 model/pack, 218336 context and MTP settings. Global settings were not tuned. Benchmark requests used temperature0, max256 output tokens and thinking disabled. Acceptance and benchmark results are distinct. Startup excluded.

| Workload | 0.1.58 median | 0.1.62 median | Change (positive is better) | Matched samples |
|---|---:|---:|---:|---:|
| 256-token decode (native tok/s) | 73.800 | 72.900 | -1.22% | 3 |
| Synthetic ~8K fresh prompt (native tok/s) | 681.500 | 707.300 | +3.79% | 3 |
| 43K retrieval fresh prompt (native tok/s) | 1309.800 | 1342.900 | +2.53% | 3 |
| 43K cached request (HTTP seconds) | 1.096 | 0.764 | +30.33% | 3 |

Native GPU parity: 36 test executions, 0 failures, 0 skips across all three cards.

Candidate real text, forced tool, red-circle/blue-triangle vision, remote-image rejection, unchanged deployed assets/GPU placement, 43K retrieval and >43K cache reuse passed. Clean candidate restart and fresh image passed. Original executable/BUILD, modes/owners, source, config, unit and vision hashes restored; original0.1.58 acceptance passed. No candidate retained in production.

## Limits
- Only three repetitions, fixed engine order (candidate then original), not randomized or a soak.
- 8K is repeated-token synthetic input; 43K is the existing marker-retrieval fixture.
- Native timing counters and loopback HTTP wall time, not TTFT or end-user gateway latency.
- Image-generation/diffusion, full-context capacity, cancellation latency, gateway latency and broad answer quality are not qualified.
- Broad all-format IQ prefill passed on the first GPU before the run was deliberately stopped; complete coverage on the other two GPUs remains unqualified.
- Two harness/setup failures were retained: CTest log ownership and process-name identity.

Raw receipts are retained in the private evidence directory; compare only paired eligible inputs. These are workload-specific observations, not universal speed or answer-quality claims.
