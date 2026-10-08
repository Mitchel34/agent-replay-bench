# Predeclared synthetic evaluation v1

This document is the fixture truth specification, frozen before implementation and production evaluation. Baseline outputs below are independently defined arithmetic/table/string facts, not obtained from the replay stubs. One self-contained core module contains the pure implementation, fixture construction, mutation definitions and `evaluate()`; CLI parsing, JSON serialization, SHA-256 and file exports live separately. No evaluation runs at import.

## Ten scenarios × twenty seeds

Seeds are integers 0..19, exhaustive (no sampling). Write n = seed + 1. Every event initially has before=running; intermediate after=running; final after equals terminal. Step IDs are s0, s1 (and s2 for retry); seq equals index. No trace has 50 events. Reference truth construction must not call the tool implementation.

| Scenario | Calls in order | Literal/formula output truth | Terminal |
| --- | --- | --- | --- |
| echo_pair | echo `hello-n`; echo `done-n` | the two input strings | succeeded |
| addition | add n,2; add -n,3 | n+2; 3-n | succeeded |
| division | divide 6n,3; divide -5n,2 | 2n; floor(-5n/2) | succeeded |
| lookup_hit | lookup red; lookup blue | 3; 5 | succeeded |
| divide_failure | echo `begin-n`; divide n,0 | begin-n; division_by_zero error | failed |
| lookup_failure | echo `lookup-n`; lookup absent | lookup-n; missing_key error | failed |
| retry | divide n,0; divide 2n,2; echo recovered | division_by_zero; n; recovered | succeeded |
| inert_text | echo `$(touch /tmp/agent-replay-inert)`; echo `https://invalid.example/no-call?n=n` | exact input strings, always inert | succeeded |
| sentinel | echo SYNTHETIC_SECRET_DO_NOT_PUBLISH; add n,0 | exact marker; n | succeeded |
| empty | no calls | no events | empty |

All successful outputs are `{ok:true,value:...}` and failures `{ok:false,error:...}`. Each scenario gets metadata-only variations as its clean observed trace. Every nonempty scenario gets all eight SPEC single-fault mutations at each seed. Empty gets only unexpected_tool and invalid_terminal; six categories are inapplicable, not silently skipped. Thus: 200 clean trials; 9×20×8 + 1×20×2 = 1480 mutated trials; 1680 total. Missing/reordered/duplicate/input/output/transition each has 180 positives; unexpected_tool and terminal each has 200. Each mutation's expected category set is exactly its declared singleton, independent of comparator output.

Evaluate each trial twice inside the metered invocation (3360 comparisons) and require exact report equality. Record clean agreement/false alarms, mutation detection and exact category-set match. All non-target categories form negatives: for each category TP + FN = its declared positives; FP + TN = 1680 - positives. A divergence of the wrong category cannot count as exact mutation success. A positive detection without its expected singleton fails. All baselines must pass self-consistency against the pure stubs. The sentinel must be absent from sanitized representations; verify this on the synthetic sentinel example inside evaluation without serialization.

## Frozen aggregate output (runner envelope)

At most 100 finite numeric metrics and 100 checks, unchanged runner. Emit 77 metrics: nine global (`scenarios`, `seeds`, `clean_trials`, `mutated_trials`, `trials`, `comparisons`, `false_alarms`, `deterministic_matches`, `redaction_checks`); three per scenario (`s_INDEX_trials`, `s_INDEX_clean_agree`, `s_INDEX_exact_mutations`) = 30; four per category (`c_INDEX_tp/fn/fp/tn`) = 32; six coverage metrics (`max_events`, `expected_positives`, `detected_positives`, `exact_mutations`, `baseline_validations`, `inapplicable_mutations`). Index order is exactly the two tables in SPEC/this document. Emit one check for each scenario, one per category and six global checks = 24. No per-trial strings or logs are returned. This aggregation retains every declared trial; it does not claim to export individual reports.

Acceptance: all 200 clean agreements, zero false alarms, 1480 exact singleton mutation matches, zero category FP/FN, 1680 deterministic report matches, all fixture truth checks, expected coverage/counts and sentinel checks. Failures are retained; no fixture-specific threshold tuning after evaluation. Resource targets: one computation thread plus supervisor, 60 CPU-seconds, conservative combined 256 MiB and 120 wall-seconds. Resource use comes from the real production supervisor receipt, not self-estimation. Project ceilings remain two threads, 2 GiB and one aggregate CPU-hour.

Only the owner admits/claims and runs production once after plan/implementation/tests gates and fresh shared-host admission. Do not invoke evaluate for unit tests or export. A receipt-only exporter reads the genuine completed receipt, selects allowlisted checks/metrics and measured resource fields, validates the full contract, serializes stable JSON and computes SHA-256 twice from that same payload. Export never imports/reruns the comparator. This proves deterministic serialization of aggregate results; per-trial deterministic equality is measured in-run. Per-trial SHA-256 digests are not produced by this bounded reporting route and must not be claimed.

Ordinary tests cover a small handful of manual references and every fault class, malformed data, combined faults, inert text and redaction. They do not sweep the production seeds/scenarios or invoke evaluate. Offline clean installation and exact-commit public delivery are separate owner-reviewed once-only operations after genuine evaluation; no dependencies, downloads, workflows or license are added.

## Exact construction recipes and output identities

References have no metadata. A clean observed copy has trace metadata `{timestamp: "seed-N", duration_ms: N, request_id: "clean-N"}`; each event at position j has `{timestamp: "event-N-J", duration_ms: N+J, request_id: "call-N-J"}`, substituting decimal seed N and decimal position J. Every mutated trace starts from that same clean copy. All modifications retain other fields byte-for-value:

- missing_event removes position 0 without renumbering.
- reordered_event swaps positions 0 and 1 without changing seq.
- duplicate_event appends an exact deep copy of position 0.
- unexpected_tool replaces position 0 tool with `shell`; for empty it inserts exactly `{seq:0,step:"extra",tool:"shell",args:{text:"inert"},output:null,before:"running",after:"succeeded"}`, retaining the empty terminal.
- input_mismatch changes only the first argument key in lexicographic order. An integer is increased by one; a string gets `!` appended. These are the only argument types in these fixtures.
- output_mismatch replaces position 0 output with null (all baseline outputs are objects).
- invalid_transition changes position 0 before to failed.
- invalid_terminal changes only terminal state to empty on nonempty references, and to succeeded on empty; terminal step is retained.

For inert_text's second echo the exact string is `https://invalid.example/no-call?n=N`, substituting n=seed+1 (not the seed). Redaction is checked once for each sentinel scenario seed: sanitize an object with the marker in a key, its string value, and a nested list; require the exact replacement object with `[REDACTED]` in all three positions and preservation of an ordinary string. Each passing seed contributes one to redaction_checks, expected 20. This utility check adds no trace comparison. Unit tests separately assert redacted-key collision rejection.

Metric keys are precisely the nine global identifiers in the aggregate section, `s_I_trials`, `s_I_clean_agree`, `s_I_exact_mutations` for decimal I=0..9, `c_I_tp`, `c_I_fn`, `c_I_fp`, `c_I_tn` for decimal I=0..7, and the six coverage identifiers. These formulas define all 77 exact lowercase keys, with no zero padding. Per-trial metrics and confusion counts use only the FIRST comparison's category set. The SECOND comparison only increments comparisons and contributes one deterministic_matches if the complete two report objects are equal. Trials and confusion counts are never doubled. A clean trial has an empty expected category set. A category is predicted positive iff it occurs at least once, regardless of number of records.

baseline_validations counts successful independent reference-consistency validations once per scenario/seed before trial construction (expected 200), not the internal repeat validations performed by comparison. max_events is the maximum length over all reference and observed traces actually compared (expected 4, from duplicate retry). expected_positives sums expected category memberships over first-pass trials (1480). detected_positives sums predicted category memberships over first-pass trials (expected 1480; wrong/extra categories still count here and cause confusion failures). exact_mutations counts mutated first-pass trials whose category set equals their singleton truth (1480). inapplicable_mutations counts the six excluded categories × twenty empty seeds (120). No unexpected exception is converted into a passing result.

The ordered 24 check names and predicates are frozen as follows:

1. `scenario I` for I=0..9, in table order: s_I_clean_agree=20; s_I_trials=180 and s_I_exact_mutations=160 for I<9, or s_9_trials=60 and s_9_exact_mutations=40.
2. `category I` for I=0..7, in SPEC table order: TP equals declared positives (200 for I=3,7; 180 otherwise), FN=FP=0, TN=1680-positives.
3. `complete trial coverage`: scenarios=10, seeds=20, clean_trials=200, mutated_trials=1480, trials=1680, comparisons=3360, expected_positives=1480, detected_positives=1480, exact_mutations=1480, inapplicable_mutations=120.
4. `deterministic reports`: deterministic_matches=1680.
5. `clean false alarms`: false_alarms=0 and sum of all s_I_clean_agree=200.
6. `fixture truth`: baseline_validations=200.
7. `sentinel redaction`: redaction_checks=20.
8. `event bound`: max_events=4 and max_events<50.

The enumerated items with ranges expand to 10+8+6=24 checks. All predicates must pass. The serializer/exporter checks these exact keys and identities, not merely the runner's broad limits.
