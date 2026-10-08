# Verification evidence

The plan, implementation, ordinary tests, evaluation and installation evidence each received independent review. Original code and data provenance are documented in [PROVENANCE.md](PROVENANCE.md). This summary contains measured completed checks, not invented fixture results.

## Tests and evaluation

37 ordinary tests passed in the checkout and again against the installed package outside the source tree. They cover all divergence categories, combined faults, retry/failure/empty cases, metadata normalization, malformed/truncated/duplicate-key JSON, type distinctions, bounded values, inert command-like strings and sentinel redaction. The exporter has a regression test for extreme integer receipt values. Ordinary tests never execute the complete evaluation function.

The separate, once-only production [evaluation](../evaluation/RESULTS.md) passed all 24 checks across 1,680 trials. Its core source and protocol digests are included with all 77 metrics in [results.json](../evaluation/results.json). 60 CPU-seconds were charged; measured CPU before final closeout was 0.39375 seconds. See the results for resource measurement limits.

## Clean offline installation

A single admitted installation built a local wheel, created a fresh environment and installed with no package index or dependency downloads. All five installed modules matched reviewed source bytes both before and after the tests. Isolated import checks confirmed resolution inside the fresh environment. All 37 installed tests and four CLI checks passed: module demo, console demo, two-file divergent comparison and same-reference agreement. Evaluation was explicitly blocked during installed tests. All nine direct children returned normally and were reaped.

| Fact | Observed value |
| --- | --- |
| Build Python | 3.11.13 |
| setuptools / wheel / pip | 80.9.0 / 0.45.1 / 25.1.1 |
| Tested runtime Python | 3.14.7 |
| Direct-child CPU accounting | 3.025283 s |
| Active execution wall time | 4.142702 s |
| Largest reported child RSS | 87,949,312 bytes |
| Reviewed installation source | 22 files / 83,247 bytes |

The declared Python 3.11 minimum was not separately tested as a runtime: Python 3.11 built the wheel; Python 3.14.7 ran the installed suite. Installation CPU excludes supervisor and receipt work. Installation memory is the largest child high-water mark, excludes the supervisor and is not simultaneous process-tree RSS. These operational bounds are not hard process-tree containment. This small packaging stage sampled shared-host availability; it did not claim atomic exclusion against another owner's later acquisition.

The full [sanitized installation facts](installation.json) retain these limitations. Exact wheel SHA-256: `76604c6c406200c62331fc5e0daa50780be5d8735d85eb5b19b2ac2eb795ee46`. The wheel, private environment, logs and raw receipts are not included in the repository.

## Documentation reconciliation

The final documentation adds this summary and installation.json and updates only INSTALLATION.md, REPRODUCIBILITY.md and PROVENANCE.md relative to the installation snapshot. The package's five modules, pyproject.toml and README.md are unchanged, as are all tests, synthetic examples, frozen SPEC/protocol and evaluation results. Full source/history and exact remote delivery undergo a separate publication review. No license or hosted CI workflow is included.
