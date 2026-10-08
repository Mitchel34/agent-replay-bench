# Provenance

All project source, documentation, fixture definitions and tests were written for Agent Replay Bench. There are no copied research projects, captured user sessions, downloaded datasets, model-generated benchmark traces, or private trace inputs. Python standard-library behavior is used through the installed runtime; no third-party code is vendored.

The ten scenarios are wholly synthetic strings, bounded arithmetic, fixed lookup tables and explicit state sequences. Their independent output formulas and mutation ground truth are specified in [PROTOCOL.md](../evaluation/PROTOCOL.md). Fixture construction never calls the stubs to obtain expected outputs. The two example JSON files contain synthetic addition calls at seed 0; observed.json deliberately replaces one output with null.

The synthetic marker named in SPEC is test data, not a credential. URLs use an invalid example host and are inert payload text. The command-like echo string is also inert text and is never executed. No dataset license is needed for these original synthetic inputs. No repository license has been selected or granted.

Public evaluation results, when present, contain only allowlisted numeric metrics, fixed check names, source/protocol digests and measured resource facts. Private coordination receipts, task IDs, host identities, filesystem paths and process IDs are not included. Exporter unit-test receipts are clearly labeled invented fixtures and are never project results.

The public [installation facts](installation.json) are an allowlisted report derived from the genuine completed clean-install receipt and independently checked. The installation snapshot contained 22 reviewed files. Final changes after that snapshot are documentation-only: this provenance note, installation/reproduction notes, and the added installation facts and verification summary. All seven wheel build inputs (five modules, pyproject.toml and README.md), tests, examples, frozen SPEC/protocol and measured evaluation files remain byte-identical. No evaluation or installation rerun was needed for these documentation changes.
