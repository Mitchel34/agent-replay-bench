# Measured synthetic evaluation

One admitted production run completed on October 8, 2026. All 24 acceptance checks passed. This is synthetic regression-detection evidence, not live-agent reliability evidence. The source and frozen protocol were independently reviewed before the run.

## Coverage

- 10 scenarios × 20 seeds: 200 clean trials and 1,480 declared mutated trials.
- All 200 clean traces agreed; zero false alarms.
- All 1,480 mutated traces produced exactly their expected singleton category.
- All 1,680 pairs of repeated reports matched exactly (3,360 total comparisons).
- 200 independent fixture validations; 20 sentinel redaction checks.
- Largest observed trace: four events. Six mutation types on empty traces account for 120 explicitly inapplicable combinations.

| Scenario | Trials | Clean agreement | Exact mutations |
| --- | ---: | ---: | ---: |
| echo_pair | 180 | 20/20 | 160 |
| addition | 180 | 20/20 | 160 |
| division | 180 | 20/20 | 160 |
| lookup_hit | 180 | 20/20 | 160 |
| divide_failure | 180 | 20/20 | 160 |
| lookup_failure | 180 | 20/20 | 160 |
| retry | 180 | 20/20 | 160 |
| inert_text | 180 | 20/20 | 160 |
| sentinel | 180 | 20/20 | 160 |
| empty | 60 | 20/20 | 40 |

## Category confusion counts

A category prediction is positive if at least one report record has that category. Repeated comparison does not double-count trials.

| Category | TP | FN | FP | TN |
| --- | ---: | ---: | ---: | ---: |
| missing_event | 180 | 0 | 0 | 1500 |
| reordered_event | 180 | 0 | 0 | 1500 |
| duplicate_event | 180 | 0 | 0 | 1500 |
| unexpected_tool | 200 | 0 | 0 | 1480 |
| input_mismatch | 180 | 0 | 0 | 1500 |
| output_mismatch | 180 | 0 | 0 | 1500 |
| invalid_transition | 180 | 0 | 0 | 1500 |
| invalid_terminal | 200 | 0 | 0 | 1480 |

## Measured resources

| Quantity | Value | Meaning |
| --- | ---: | --- |
| CPU before closeout | 0.39375 s | Lower bound before final receipt/database work |
| Wall time | 0.435622 s | Supervisor observation |
| Combined peak memory | 63,422,464 bytes (60.48 MiB) | Sum of worker/supervisor high-water marks |
| CPU ledger charge | 60 s | Full reserved amount, not measured runtime |

The run used one computation thread plus one supervisor, within the 60 CPU-second reservation, 256 MiB conservative combined memory target and 120 wall-second limit. The direct child was reaped and its shared lease released. These operational controls are not hard hostile-code containment. No provider APIs or incremental external services were used.

## Reproducible evidence

The [machine-readable aggregate](results.json) contains every predeclared metric and check plus allowlisted resource facts. Its [SHA-256 file](results.sha256) binds the exported bytes. Export selected fields from the completed receipt and serialized them twice; it did not rerun comparisons. The aggregate is a receipt-derived summary, not a per-trial report archive. No per-trial SHA-256 claim is made.

- Core source SHA-256: `4152654dccf1e5577457ba6d0a9d6d0b75c07a6716e018abd5b27c4270d5405b`
- Protocol SHA-256: `9d5018a158d7630bad837e02bba13e344692b134a255a23612ebb8ac3f80856c`
- Aggregate SHA-256: `f8a3036b3feb5300ace073f94157873ac8bca9614a2986c1bad2dbf547d83261`

See [the protocol](PROTOCOL.md), [reproduction instructions](../docs/REPRODUCIBILITY.md), and [threat boundary](../docs/THREAT_BOUNDARY.md). Benchmarks cover only the declared synthetic fault family.
