# Reproduction

Use a trusted local Python 3.11+ runtime. Runtime dependencies are the standard library only. Ordinary regression checks are separate from the complete evaluation:

```sh
python3 -B -m unittest discover -s tests -v
python3 -B -m agent_replay_bench demo --format json
```

The demo intentionally returns exit status 1. To check agreement, compare examples/reference.json with itself. Unknown/malformed input returns status 2. Unit tests do not call evaluate(), sweep twenty seeds, or substitute their invented exporter receipt for evaluation evidence.

## Complete batch

The entire deterministic workload is `agent_replay_bench.core.evaluate()`. It takes no inputs, reads no files, seeds no ambient generator, starts no threads and makes no model calls. It constructs all ten scenarios at seeds 0..19 according to the frozen protocol and performs exactly 3,360 comparisons. It returns 77 numeric metrics and 24 acceptance checks. JSON and hashing belong outside this function.

A new reproduction is a new complete evaluation, not a report export. Run it once only after obtaining the appropriate resource admission for your environment, inside a trusted process supervisor with the protocol's 60 CPU-second, 256 MiB conservative combined memory and 120 wall-second targets. Do not run beside another admitted substantial workload. The following is the evaluator entry point to place inside that supervisor; it does not itself enforce resource bounds:

```python
from agent_replay_bench.core import evaluate
result = evaluate()
```

Compare all returned metrics and check identities with [PROTOCOL.md](../evaluation/PROTOCOL.md), not only the total detection rate. Source and protocol SHA-256 identities bind a reported run to its definition. The project's original production evaluation is admitted, metered and recorded separately from ordinary tests. No claim of kernel-enforced memory containment is made.

## Receipt-only export

`export-results` verifies an expected receipt byte digest, checks the source identity, all 77 metric values and 24 acceptance checks, and allowlists public fields. It does not import the comparator or launch a new evaluation. Input must be a genuine completed production receipt already verified by its owner; a digest establishes byte identity, not authenticity by itself.

```sh
python3 -B -m agent_replay_bench export-results RECEIPT.json \
  --receipt-sha256 RECEIPT_SHA256 \
  --source-sha256 CORE_SHA256 \
  --protocol-sha256 PROTOCOL_SHA256 \
  --output aggregate.json
```

The output file must not already exist. The command prints its SHA-256. Two serializations and hashes of the same aggregate payload must match. This does not claim per-trial SHA-256 digests. Preserve failed/uncertain launch evidence and reconcile it instead of silently retrying or recomputing a favorable result.

## Offline installation

A wheel can be built with an already available setuptools 68+ and wheel toolchain, then installed into a fresh local environment with `--no-index --no-deps`. No package index, dependency download, service, CI workflow or paid API is part of this project. The [admitted installation evidence](installation.json) states exact toolchain and artifact identities and verifies imports, CLI behavior and all 37 ordinary tests outside the source checkout. Runtime validation used Python 3.14.7; the declared Python 3.11 minimum was not separately qualified by a full runtime test suite.
