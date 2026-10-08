"""Local file/JSON boundary; trace-supplied strings never become operations."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

TRACE_BYTES = 256 * 1024


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON object key')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('Nonfinite JSON number')


def parse_json(raw, maximum=TRACE_BYTES):
    if len(raw) > maximum:
        raise ValueError('Input exceeds byte limit')
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object,
                          parse_constant=reject_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError('Invalid UTF-8 JSON input') from error


def read_bounded(path, maximum=TRACE_BYTES):
    with Path(path).open('rb') as handle:
        return handle.read(maximum + 1)


def display(report, mode):
    from .core import redact
    from .reports import stable_json
    safe = redact(report)
    if mode == 'json':
        return stable_json(safe)
    counts = safe['counts']
    lines = ['AGREEMENT' if safe['agreement'] else 'DIVERGENCE',
             f"{counts['reference_events']} reference / {counts['observed_events']} observed events; {counts['divergences']} divergence records"]
    for record in safe['divergences']:
        lines.append(f"{record['category']} index={record['index']} step={record['step']} field={record['field']}")
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description='Offline synthetic agent replay bench')
    commands = parser.add_subparsers(dest='command', required=True)
    compare = commands.add_parser('compare', help='Compare two caller-selected synthetic JSON files')
    compare.add_argument('reference')
    compare.add_argument('observed')
    compare.add_argument('--format', choices=['text','json'], default='text')
    demo = commands.add_parser('demo', help='Show one deliberately changed output (no full evaluation)')
    demo.add_argument('--format', choices=['text','json'], default='text')
    example = commands.add_parser('example', help='Emit one raw synthetic fixture')
    example.add_argument('scenario')
    example.add_argument('--seed', type=int, default=0)
    export = commands.add_parser('export-results', help='Export an admitted completed receipt; never replays')
    export.add_argument('receipt')
    export.add_argument('--receipt-sha256', required=True)
    export.add_argument('--source-sha256', required=True)
    export.add_argument('--protocol-sha256', required=True)
    export.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'export-results':
            from .reports import encoded_aggregate
            raw = read_bounded(args.receipt, 1024*1024)
            if hashlib.sha256(raw).hexdigest() != args.receipt_sha256:
                raise ValueError('Receipt digest mismatch')
            receipt = parse_json(raw, 1024*1024)
            data, digest = encoded_aggregate(receipt, args.source_sha256, args.protocol_sha256)
            with Path(args.output).open('xb') as handle:
                handle.write(data)
            print(digest)
            return 0
        from .core import compare as replay, fixture, mutate
        from .reports import stable_json
        if args.command == 'example':
            print(stable_json(fixture(args.scenario, args.seed)), end='')
            return 0
        if args.command == 'demo':
            reference = fixture('addition', 0)
            observed = mutate(reference, 'output_mismatch')
        else:
            reference = parse_json(read_bounded(args.reference))
            observed = parse_json(read_bounded(args.observed))
        report = replay(reference, observed)
        print(display(report, args.format), end='')
        return 0 if report['agreement'] else 1
    except (ValueError, OSError, RecursionError) as error:
        # Fixed local diagnostics avoid echoing file paths or trace payloads.
        print('Invalid input or unavailable local output. See the trace/receipt contract.', file=sys.stderr)
        return 2
