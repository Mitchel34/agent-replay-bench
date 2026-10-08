"""Pure, bounded synthetic replay and the predeclared in-memory evaluation.

No I/O, dynamic tools, model calls, or evaluation at import time.
"""
import math

SCHEMA = 'agent-replay-trace/1'
SENTINEL = 'SYNTHETIC_SECRET_DO_NOT_PUBLISH'
CATEGORIES = ('missing_event', 'reordered_event', 'duplicate_event',
              'unexpected_tool', 'input_mismatch', 'output_mismatch',
              'invalid_transition', 'invalid_terminal')
SCENARIOS = ('echo_pair', 'addition', 'division', 'lookup_hit', 'divide_failure',
             'lookup_failure', 'retry', 'inert_text', 'sentinel', 'empty')
STATES = ('running', 'succeeded', 'failed')


def identical(left, right):
    """JSON equality preserving numeric types (True is not 1)."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(identical(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(identical(a, b) for a, b in zip(left, right))
    return left == right


def clone(value):
    if isinstance(value, dict):
        return {k: clone(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clone(v) for v in value]
    return value


def identifier(value):
    return (type(value) is str and 1 <= len(value) <= 64
            and all(c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in value))


def json_value(value, depth=0):
    if depth > 12:
        raise ValueError('JSON nesting exceeds 12')
    if value is None or type(value) is bool:
        return
    if type(value) is str:
        if len(value) > 4096 or any(0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise ValueError('Invalid bounded Unicode string')
    elif type(value) is int:
        if abs(value) > 1000000000:
            raise ValueError('Integer outside trace bounds')
    elif type(value) is float:
        if not math.isfinite(value):
            raise ValueError('Nonfinite JSON number')
    elif type(value) is list:
        for v in value:
            json_value(v, depth + 1)
    elif type(value) is dict:
        for k, v in value.items():
            if type(k) is not str:
                raise ValueError('JSON keys must be strings')
            json_value(k, depth + 1)
            json_value(v, depth + 1)
    else:
        raise ValueError('Unsupported JSON value')


def fields(value, required, optional=()):
    if type(value) is not dict or not set(required) <= value.keys() or set(value) - set(required) - set(optional):
        raise ValueError('Invalid object fields')


def metadata(value):
    fields(value, (), ('timestamp', 'duration_ms', 'request_id'))
    for k, v in value.items():
        if k == 'duration_ms':
            if type(v) is not int or v < 0:
                raise ValueError('Invalid duration metadata')
        elif type(v) is not str:
            raise ValueError('Invalid string metadata')


def validate_shape(trace):
    """Observed shape only; semantic defects remain reportable divergences."""
    json_value(trace)
    fields(trace, ('schema', 'scenario', 'events', 'terminal'), ('metadata',))
    if trace['schema'] != SCHEMA or not identifier(trace['scenario']):
        raise ValueError('Unsupported schema or invalid scenario identifier')
    events = trace['events']
    if type(events) is not list or len(events) >= 50:
        raise ValueError('Trace requires fewer than 50 events')
    if 'metadata' in trace:
        metadata(trace['metadata'])
    fields(trace['terminal'], ('state', 'step'))
    term = trace['terminal']
    if term['state'] not in ('empty', 'succeeded', 'failed') or not (term['step'] is None or identifier(term['step'])):
        raise ValueError('Invalid terminal envelope')
    for event in events:
        fields(event, ('seq', 'step', 'tool', 'args', 'output', 'before', 'after'), ('metadata',))
        if (type(event['seq']) is not int or not 0 <= event['seq'] <= 48
                or not identifier(event['step']) or not identifier(event['tool'])
                or type(event['args']) is not dict
                or event['before'] not in STATES or event['after'] not in STATES):
            raise ValueError('Invalid event envelope')
        if 'metadata' in event:
            metadata(event['metadata'])


def run_tool(tool, args):
    """A closed dispatch of four pure stubs; trace strings are never operations."""
    if tool == 'echo':
        fields(args, ('text',))
        if type(args['text']) is not str:
            raise ValueError('echo requires string text')
        return {'ok': True, 'value': args['text']}
    if tool in ('add', 'divide'):
        fields(args, ('a', 'b'))
        if any(type(args[k]) is not int or abs(args[k]) > 1000000 for k in ('a', 'b')):
            raise ValueError('Arithmetic arguments must be bounded integers')
        a, b = args['a'], args['b']
        if tool == 'add':
            return {'ok': True, 'value': a + b}
        if b == 0:
            return {'ok': False, 'error': 'division_by_zero'}
        return {'ok': True, 'value': a // b}
    if tool == 'lookup':
        fields(args, ('key',))
        if type(args['key']) is not str:
            raise ValueError('lookup requires string key')
        table = {'red': 3, 'blue': 5, 'green': 8}
        if args['key'] not in table:
            return {'ok': False, 'error': 'missing_key'}
        return {'ok': True, 'value': table[args['key']]}
    raise ValueError('Unknown tool is not executable')


def validate_reference(trace):
    validate_shape(trace)
    seen = set()
    for i, event in enumerate(trace['events']):
        if event['seq'] != i or event['step'] in seen:
            raise ValueError('Reference order or identity is invalid')
        seen.add(event['step'])
        output = run_tool(event['tool'], event['args'])
        if not identical(output, event['output']):
            raise ValueError('Reference output disagrees with pure stub')
        after = 'running'
        if i == len(trace['events']) - 1:
            after = 'succeeded' if output['ok'] else 'failed'
        if event['before'] != 'running' or event['after'] != after:
            raise ValueError('Reference transition is invalid')
    terminal = {'state': 'empty', 'step': None}
    if trace['events']:
        last = trace['events'][-1]
        terminal = {'state': last['after'], 'step': last['step']}
    if not identical(trace['terminal'], terminal):
        raise ValueError('Reference terminal is invalid')


def compare(reference, observed):
    """Replay reference stubs and compare observed evidence, without executing it."""
    validate_reference(reference)
    validate_shape(observed)
    ref = {e['step']: e for e in reference['events']}
    first = {}
    seen_seq = set()
    records = []

    def record(category, index, step, field):
        item = {'category': category, 'index': index, 'step': step, 'field': field}
        if item not in records:
            records.append(item)

    for i, event in enumerate(observed['events']):
        step = event['step']
        known = step if step in ref else None
        repeated = step in first
        if repeated:
            record('duplicate_event', i, known, 'step')
        else:
            first[step] = (i, event)
        if event['seq'] in seen_seq:
            record('duplicate_event', i, known, 'seq')
        seen_seq.add(event['seq'])
        if step not in ref:
            record('unexpected_tool', i, None, 'step')
        elif not repeated:
            if event['tool'] != ref[step]['tool']:
                record('unexpected_tool', i, step, 'tool')
            if event['seq'] != ref[step]['seq']:
                record('reordered_event', i, step, 'seq')
    order = [ref[k]['seq'] for k in first if k in ref]
    if order != sorted(order):
        record('reordered_event', -1, None, 'order')
    for step, expected in ref.items():
        if step not in first:
            record('missing_event', -1, step, 'step')
            continue
        index, actual = first[step]
        if actual['tool'] != expected['tool']:
            continue
        if not identical(actual['args'], expected['args']):
            record('input_mismatch', index, step, 'args')
        if not identical(actual['output'], expected['output']):
            record('output_mismatch', index, step, 'output')
        if actual['before'] != expected['before'] or actual['after'] != expected['after']:
            record('invalid_transition', index, step, 'transition')
    for field in ('terminal', 'scenario'):
        if not identical(reference[field], observed[field]):
            record('invalid_terminal', -1, None, field)
    records.sort(key=lambda r: (CATEGORIES.index(r['category']), r['index'], r['step'] or '', r['field']))
    return {'schema': 'agent-replay-report/1', 'agreement': not records,
            'divergences': records, 'counts': {
                'reference_events': len(reference['events']),
                'observed_events': len(observed['events']), 'divergences': len(records),
                'categories': {c: sum(r['category'] == c for r in records) for c in CATEGORIES}}}


def redact(value):
    """Exact synthetic sentinel replacement, not a general secret sanitizer."""
    if type(value) is str:
        return value.replace(SENTINEL, '[REDACTED]')
    if type(value) is list:
        return [redact(v) for v in value]
    if type(value) is dict:
        result = {}
        for k, v in value.items():
            key = redact(k)
            if key in result:
                raise ValueError('Redacted keys collide')
            result[key] = redact(v)
        return result
    return value


def fixture(scenario, seed):
    """Independent closed-form fixture truth; never asks run_tool for outputs."""
    if scenario not in SCENARIOS or type(seed) is not int or not 0 <= seed < 20:
        raise ValueError('Unknown synthetic scenario or seed')
    n = seed + 1
    calls = []
    if scenario == 'echo_pair':
        calls = [('echo', {'text': 'hello-' + str(n)}, 'hello-' + str(n)),
                 ('echo', {'text': 'done-' + str(n)}, 'done-' + str(n))]
    elif scenario == 'addition':
        calls = [('add', {'a': n, 'b': 2}, n + 2), ('add', {'a': -n, 'b': 3}, 3 - n)]
    elif scenario == 'division':
        calls = [('divide', {'a': 6*n, 'b': 3}, 2*n), ('divide', {'a': -5*n, 'b': 2}, (-5*n)//2)]
    elif scenario == 'lookup_hit':
        calls = [('lookup', {'key': 'red'}, 3), ('lookup', {'key': 'blue'}, 5)]
    elif scenario == 'divide_failure':
        calls = [('echo', {'text': 'begin-' + str(n)}, 'begin-' + str(n)),
                 ('divide', {'a': n, 'b': 0}, {'error': 'division_by_zero'})]
    elif scenario == 'lookup_failure':
        calls = [('echo', {'text': 'lookup-' + str(n)}, 'lookup-' + str(n)),
                 ('lookup', {'key': 'absent'}, {'error': 'missing_key'})]
    elif scenario == 'retry':
        calls = [('divide', {'a': n, 'b': 0}, {'error': 'division_by_zero'}),
                 ('divide', {'a': 2*n, 'b': 2}, n), ('echo', {'text': 'recovered'}, 'recovered')]
    elif scenario == 'inert_text':
        text = '$(touch /tmp/agent-replay-inert)'
        url = 'https://invalid.example/no-call?n=' + str(n)
        calls = [('echo', {'text': text}, text), ('echo', {'text': url}, url)]
    elif scenario == 'sentinel':
        calls = [('echo', {'text': SENTINEL}, SENTINEL), ('add', {'a': n, 'b': 0}, n)]
    events = []
    for i, (tool, args, truth) in enumerate(calls):
        output = {'ok': False, 'error': truth['error']} if type(truth) is dict else {'ok': True, 'value': truth}
        after = 'running' if i < len(calls)-1 else ('succeeded' if output['ok'] else 'failed')
        events.append({'seq': i, 'step': 's' + str(i), 'tool': tool, 'args': args,
                       'output': output, 'before': 'running', 'after': after})
    terminal = {'state': events[-1]['after'], 'step': events[-1]['step']} if events else {'state': 'empty', 'step': None}
    return {'schema': SCHEMA, 'scenario': scenario, 'events': events, 'terminal': terminal}


def clean_copy(reference, seed):
    trace = clone(reference)
    trace['metadata'] = {'timestamp': 'seed-' + str(seed), 'duration_ms': seed, 'request_id': 'clean-' + str(seed)}
    for j, event in enumerate(trace['events']):
        suffix = str(seed) + '-' + str(j)
        event['metadata'] = {'timestamp': 'event-' + suffix, 'duration_ms': seed+j, 'request_id': 'call-' + suffix}
    return trace


def mutate(clean, category):
    if category not in CATEGORIES:
        raise ValueError('Unknown mutation category')
    trace = clone(clean)
    events = trace['events']
    if not events and category not in ('unexpected_tool', 'invalid_terminal'):
        raise ValueError('Mutation is inapplicable to empty trace')
    if category == 'missing_event':
        events.pop(0)
    elif category == 'reordered_event':
        if len(events) < 2:
            raise ValueError('Reorder needs two events')
        events[0], events[1] = events[1], events[0]
    elif category == 'duplicate_event':
        events.append(clone(events[0]))
    elif category == 'unexpected_tool':
        if events:
            events[0]['tool'] = 'shell'
        else:
            events.append({'seq': 0, 'step': 'extra', 'tool': 'shell', 'args': {'text': 'inert'},
                           'output': None, 'before': 'running', 'after': 'succeeded'})
    elif category == 'input_mismatch':
        args = events[0]['args']
        key = sorted(args)[0]
        args[key] = args[key] + 1 if type(args[key]) is int else args[key] + '!'
    elif category == 'output_mismatch':
        events[0]['output'] = None
    elif category == 'invalid_transition':
        events[0]['before'] = 'failed'
    else:
        trace['terminal']['state'] = 'empty' if events else 'succeeded'
    return trace


def evaluate():
    """The complete predeclared batch. Dispatch only under its reviewed grant."""
    metrics = {k: 0 for k in ('scenarios', 'seeds', 'clean_trials', 'mutated_trials', 'trials',
                'comparisons', 'false_alarms', 'deterministic_matches', 'redaction_checks',
                'max_events', 'expected_positives', 'detected_positives', 'exact_mutations',
                'baseline_validations', 'inapplicable_mutations')}
    metrics['scenarios'], metrics['seeds'] = 10, 20
    for i in range(10):
        for key in ('trials', 'clean_agree', 'exact_mutations'):
            metrics['s_' + str(i) + '_' + key] = 0
    for i in range(8):
        for key in ('tp', 'fn', 'fp', 'tn'):
            metrics['c_' + str(i) + '_' + key] = 0
    for i, scenario in enumerate(SCENARIOS):
        prefix = 's_' + str(i) + '_'
        for seed in range(20):
            reference = fixture(scenario, seed)
            validate_reference(reference)
            metrics['baseline_validations'] += 1
            clean = clean_copy(reference, seed)
            applicable = CATEGORIES if reference['events'] else ('unexpected_tool', 'invalid_terminal')
            metrics['inapplicable_mutations'] += 8 - len(applicable)
            trials = [(clean, set())] + [(mutate(clean, c), {c}) for c in applicable]
            for observed, truth in trials:
                first = compare(reference, observed)
                second = compare(reference, observed)
                predicted = {r['category'] for r in first['divergences']}
                metrics['comparisons'] += 2
                metrics['trials'] += 1
                metrics[prefix + 'trials'] += 1
                metrics['deterministic_matches'] += int(identical(first, second))
                metrics['max_events'] = max(metrics['max_events'], len(reference['events']), len(observed['events']))
                metrics['expected_positives'] += len(truth)
                metrics['detected_positives'] += len(predicted)
                if truth:
                    metrics['mutated_trials'] += 1
                    metrics['exact_mutations'] += int(predicted == truth)
                    metrics[prefix + 'exact_mutations'] += int(predicted == truth)
                else:
                    metrics['clean_trials'] += 1
                    metrics['false_alarms'] += int(bool(predicted))
                    metrics[prefix + 'clean_agree'] += int(first['agreement'])
                for j, category in enumerate(CATEGORIES):
                    count = ('tp' if category in predicted else 'fn') if category in truth else ('fp' if category in predicted else 'tn')
                    metrics['c_' + str(j) + '_' + count] += 1
            if scenario == 'sentinel':
                original = {SENTINEL: SENTINEL, 'nested': [SENTINEL, 'ordinary']}
                expected = {'[REDACTED]': '[REDACTED]', 'nested': ['[REDACTED]', 'ordinary']}
                metrics['redaction_checks'] += int(identical(redact(original), expected))
    checks = []
    for i in range(10):
        prefix = 's_' + str(i) + '_'
        checks.append({'name': 'scenario ' + str(i), 'passed':
                       metrics[prefix+'clean_agree'] == 20 and metrics[prefix+'trials'] == (180 if i < 9 else 60)
                       and metrics[prefix+'exact_mutations'] == (160 if i < 9 else 40)})
    for i in range(8):
        prefix = 'c_' + str(i) + '_'
        positives = 200 if i in (3, 7) else 180
        checks.append({'name': 'category ' + str(i), 'passed': metrics[prefix+'tp'] == positives
                       and metrics[prefix+'fn'] == 0 and metrics[prefix+'fp'] == 0
                       and metrics[prefix+'tn'] == 1680-positives})
    coverage = {'scenarios':10, 'seeds':20, 'clean_trials':200, 'mutated_trials':1480, 'trials':1680,
                'comparisons':3360, 'expected_positives':1480, 'detected_positives':1480,
                'exact_mutations':1480, 'inapplicable_mutations':120}
    checks += [
        {'name':'complete trial coverage', 'passed':all(metrics[k] == v for k,v in coverage.items())},
        {'name':'deterministic reports', 'passed':metrics['deterministic_matches'] == 1680},
        {'name':'clean false alarms', 'passed':metrics['false_alarms'] == 0 and sum(metrics['s_'+str(i)+'_clean_agree'] for i in range(10)) == 200},
        {'name':'fixture truth', 'passed':metrics['baseline_validations'] == 200},
        {'name':'sentinel redaction', 'passed':metrics['redaction_checks'] == 20},
        {'name':'event bound', 'passed':metrics['max_events'] == 4 and metrics['max_events'] < 50}]
    return {'checks': checks, 'metrics': metrics}
