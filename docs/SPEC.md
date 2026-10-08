# Agent Replay Bench — frozen v1 contract

Purpose: locate regressions between a trusted, wholly synthetic reference trace and an observed toy trace. No agent/model, operating-system tool, plugin or network service is executed. Pure local stubs are the entire replay environment. Synthetic agreement is not evidence of real-agent safety or reliability.

## Format and boundaries

Trace JSON has exactly `schema` (`agent-replay-trace/1`), `scenario` (1–64 ASCII letters, digits, underscore or hyphen), `events` (0–49 entries), `terminal` and optional `metadata`. A file is at most 256 KiB UTF-8; reject malformed/truncated JSON, duplicate object keys, nonfinite values and nesting beyond 12. JSON scalars/containers are bounded by file size; integers are within ±1,000,000,000. Unknown fields and schema versions fail validation. Booleans do not equal integers. Strings are at most 4096 characters and contain no surrogate code points. CLI paths explicitly supplied by the caller select input files; strings inside traces never select paths or operations.

An event has exactly `seq` (integer 0–48), `step` (1–64 identifier characters), `tool` (1–64 identifier characters), `args` (object), `output` (JSON value), `before` and `after` (state strings), plus optional `metadata`. Event states are `running`, `succeeded`, `failed`. A canonical reference has contiguous zero-based sequence numbers, unique step IDs, starts running, remains running until its last event, and then succeeds or fails consistently with that last stub output. A failed intermediate call may remain running, allowing an explicit retry event with a new step ID. No event follows a terminal transition. An empty trace ends `{state: empty, step: null}`. Otherwise terminal is `{state: succeeded|failed, step: LAST_ID}` and matches the final transition.

Only event/trace `metadata` may be ignored. It contains a subset of `timestamp` (string), `duration_ms` (nonnegative integer), `request_id` (string); unknown metadata fields fail. No payload text, whitespace, list order, numeric type, argument, sequence, ID, state or output is normalized. Dictionary key ordering has no meaning. Ignored metadata cannot affect stub execution.

## Closed stub table

| Tool | Exact arguments | Pure output |
| --- | --- | --- |
| echo | `text`: string | `{ok: true, value: text}` |
| add | `a`, `b`: integers in ±1,000,000 | `{ok: true, value: a+b}` |
| divide | `a`, `b`: integers in ±1,000,000 | integer floor quotient; zero divisor gives `{ok: false, error: division_by_zero}` |
| lookup | `key`: string | fixed table `red→3`, `blue→5`, `green→8`; absent key gives `{ok: false, error: missing_key}` |

No dynamic imports, eval, subprocesses, filesystem access, URL fetches or callback registry exist in the core. Unknown reference tools or invalid reference stub arguments are rejected; an unknown observed tool produces `unexpected_tool` and is never invoked. Every reference output is checked against its stub and state rules before comparison. Observed inputs and outputs are compared to that verified reference; they are never trusted as a source of expected truth.

## Deterministic divergences

Report schema `agent-replay-report/1` has `agreement`, `divergences` and counts. Each divergence has only category, event index (or -1 for trace-level), fixed field label, and a stable reference step ID where applicable. Payload values and observed IDs are omitted. The exact record ordering and count schema below are normative. Exact duplicate records are suppressed. Every category and record remains visible; CLI human text is a concise summary of the same report. Expected reference IDs are synthetic; sentinel redaction still applies before JSON/text export.

| Category | Definition and single-fault truth |
| --- | --- |
| missing_event | A reference step ID has no observed occurrence. Remove first event without renumbering. |
| reordered_event | Surviving first occurrences of known IDs appear out of reference order, or a known event's seq differs. Swap first two events with seq retained; one category, potentially multiple records. Missing alone does not imply reorder. |
| duplicate_event | An observed ID or sequence is repeated. Append a copy of first event. |
| unexpected_tool | An extra unknown event ID or unknown/different tool appears. Change first tool to `shell`; on empty, insert a well-shaped `shell` event. |
| input_mismatch | Known matching tool's args differ in value/type from reference. Change first argument value. |
| output_mismatch | Known matching tool's output differs in value/type from reference. Replace first output with a different value. |
| invalid_transition | Known matching tool's before/after differs from reference. Change first before to failed. |
| invalid_terminal | Terminal differs from reference (including last step), or scenario differs (field scenario). Change terminal state to empty for nonempty, succeeded for empty. |

For duplicate IDs, compare only their first occurrence; for missing/extra/different-tool records, do not infer dependent content mismatches. This prevents cascades but does not suppress independent categories. Observed structural/state defects are reported, not silently normalized. Invalid envelope/types/field sets are validation errors instead of divergence records. CLI exits 0 for agreement, 1 for divergences, 2 for invalid input.

## Sentinel redaction

Recursively replace the exact test marker `SYNTHETIC_SECRET_DO_NOT_PUBLISH` in string values and keys with `[REDACTED]`, before export. Key collisions after redaction must fail rather than lose data. No real secrets or private traces are permitted. This sentinel utility is not a general secret detector or complete sanitizer. Compare original content first; redaction cannot create replay agreement.

## Exact report encoding and semantic validation boundary

Report keys are exactly `schema`, `agreement`, `divergences`, `counts`. Counts has exactly `reference_events`, `observed_events`, `divergences` (list length), and `categories` (all eight category names in table order, each mapped to the number of records). Agreement means the divergence list is empty. A divergence always has exactly `category`, `index`, `step`, `field`. `index` is the zero-based observed event position or -1 for a missing event, relative order or trace-level issue. `step` is a reference ID if that ID is known, otherwise null. Raw observed IDs never appear.

Structural detection emits one `missing_event` per absent reference ID (`index=-1, step=reference ID, field=step`). Scan observed events once: emit `duplicate_event` with field `step` for each repeated ID, and independently with field `seq` for each repeated seq; known IDs populate step, unknown ones use null. Emit `unexpected_tool` with field `step` for each unknown ID (even if repeated); otherwise emit field `tool` for a tool unequal to reference, considering only the ID's first occurrence. For first occurrences of known IDs, a seq unequal to its reference seq emits `reordered_event` with field `seq`. Extract known IDs' first occurrences in observed order; if their reference positions are not strictly increasing, emit exactly one `reordered_event` with `index=-1,step=null,field=order`. Missing alone causes no order record. Duplicate occurrences do not enter that order list.

For each known ID's first occurrence with matching tool, emit at most one `input_mismatch/args`, `output_mismatch/output`, and `invalid_transition/transition` based on strict equality to the reference (transition compares the before/after pair). Their index is that occurrence's observed position, and step is the reference ID. Compare terminal and scenario independently: unequal terminal gives `invalid_terminal/terminal`; unequal scenario gives `invalid_terminal/scenario`; both use index=-1,step=null. There are no other field labels. Exact duplicate records are suppressed. Finally sort records by category table ordinal, integer index, step (null sorts as empty string), then field lexicographically. Object serialization orders keys separately.

Observed envelope validation only requires terminal keys `state`, `step`, state in {empty,succeeded,failed}, and step null or a valid identifier. Thus `{state:succeeded,step:null}` for empty and `{state:empty,step:s1}` for nonempty reach comparison and yield invalid_terminal. Likewise valid state strings with semantically wrong transitions reach comparison. Canonical reference validation additionally enforces sequence, uniqueness, stub arguments/outputs and all transition/terminal invariants. Do not run reference invariants over the observed trace: appending a duplicate must produce duplicate_event only, with no dependent terminal/transition cascade. This distinction also applies when observed events are missing or their tools differ. An unrecognized enum value, missing key or incorrectly typed envelope is always an input validation error.
