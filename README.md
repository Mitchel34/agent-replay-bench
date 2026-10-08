# Agent Replay Bench

Find exactly where a synthetic agent trace diverged: missing/reordered/duplicate events, unexpected tools, changed inputs or outputs, and invalid transitions or terminal states. Replay is entirely offline, deterministic, and dependency-free at runtime.

The reference is checked against four pure toy tools (`echo`, `add`, `divide`, `lookup`). Observed traces are compared as data. Commands, paths, URLs and unknown tool names inside a trace cannot launch anything.

## Try it

Python 3.11 or newer is required. From the checkout:

```sh
python3 -m agent_replay_bench demo
python3 -m agent_replay_bench compare examples/reference.json examples/observed.json --format json
python3 -m unittest discover -s tests -v
```

The demo deliberately changes one output; exit status 1 means a divergence was found. Status 0 means agreement and status 2 means invalid input. The demo prints:

```text
DIVERGENCE
2 reference / 2 observed events; 1 divergence records
output_mismatch index=0 step=s0 field=output
```

Generate one fixture with `python3 -m agent_replay_bench example retry --seed 0`. Fixture output is raw synthetic data; the sentinel scenario intentionally contains a test marker. Compare reports omit payload values and redact that exact marker.

Use the library with `from agent_replay_bench.core import compare`. Pass two parsed synthetic trace dictionaries; the returned JSON-compatible report contains deterministic records and counts. Dictionary key order and the three documented metadata fields do not affect agreement. All meaningful content does.

## Measured results

One bounded production evaluation passed all 24 acceptance checks: **200/200 clean traces agreed**, **1,480/1,480 declared mutations were detected exactly**, and all **1,680 repeated report pairs matched**. Measured CPU before closeout was 0.394 seconds; conservative combined peak memory was 60.48 MiB. These are results on a declared synthetic fault family, not a measure of live-agent reliability.

The [results](evaluation/RESULTS.md) include all scenario outcomes, category confusion counts, resource limits and machine-readable aggregate evidence. The [frozen protocol](evaluation/PROTOCOL.md) defines coverage and denominators before evaluation.

## Guides

- [Trace contract and deterministic report format](docs/SPEC.md)
- [Offline installation](docs/INSTALLATION.md)
- [Reproduction and receipt-only export](docs/REPRODUCIBILITY.md)
- [Threat boundary and limitations](docs/THREAT_BOUNDARY.md)
- [Original synthetic provenance](docs/PROVENANCE.md)

No live models, paid APIs, downloaded data, CI jobs or license grant are included.
