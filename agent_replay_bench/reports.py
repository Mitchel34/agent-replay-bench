"""Strict receipt-only aggregate export. Does not import or call the comparator."""
import hashlib
import json
import math
import re


def stable_json(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False) + '\n'


def expected_metrics():
    result = {'scenarios':10, 'seeds':20, 'clean_trials':200, 'mutated_trials':1480,
              'trials':1680, 'comparisons':3360, 'false_alarms':0, 'deterministic_matches':1680,
              'redaction_checks':20, 'max_events':4, 'expected_positives':1480,
              'detected_positives':1480, 'exact_mutations':1480, 'baseline_validations':200,
              'inapplicable_mutations':120}
    for i in range(10):
        result.update({f's_{i}_trials':180 if i < 9 else 60,
                       f's_{i}_clean_agree':20, f's_{i}_exact_mutations':160 if i < 9 else 40})
    for i in range(8):
        positive = 200 if i in (3,7) else 180
        result.update({f'c_{i}_tp':positive, f'c_{i}_fn':0, f'c_{i}_fp':0, f'c_{i}_tn':1680-positive})
    return result


def check_names():
    return ([f'scenario {i}' for i in range(10)] + [f'category {i}' for i in range(8)]
            + ['complete trial coverage', 'deterministic reports', 'clean false alarms',
               'fixture truth', 'sentinel redaction', 'event bound'])


def aggregate_from_receipt(receipt, source_sha256, protocol_sha256):
    """Allowlist public facts; caller verifies receipt bytes against owner digest."""
    if type(receipt) is not dict or type(receipt.get('result')) is not dict:
        raise ValueError('Receipt and result must be objects')
    for digest in (source_sha256, protocol_sha256):
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('Expected exact SHA-256 identity')
    if (receipt.get('kind') != 'benchmark-receipt' or receipt.get('outcome') != 'pass'
            or receipt.get('source_sha256') != source_sha256
            or receipt.get('owned_child_reaped') is not True
            or receipt.get('process_tree_stopped') is not True
            or receipt.get('additional_external_services_used') is not False):
        raise ValueError('Receipt is not a matching completed offline evaluation')
    result = receipt.get('result', {})
    metrics = result.get('metrics')
    expected = expected_metrics()
    if (type(metrics) is not dict or metrics.keys() != expected.keys()
            or any(type(metrics[k]) is not int or metrics[k] != expected[k] for k in expected)):
        raise ValueError('Aggregate metrics do not meet the frozen contract')
    checks = result.get('checks')
    if checks != [{'name':name,'passed':True} for name in check_names()] or any(type(c['passed']) is not bool for c in checks):
        raise ValueError('Aggregate checks do not meet the frozen contract')
    resource_keys = ('measured_cpu_before_closeout_seconds', 'cpu_seconds', 'peak_memory_bytes',
                     'wall_seconds', 'worker_cpu_seconds', 'supervisor_cpu_seconds')
    resources = {}
    for key in resource_keys:
        value = receipt.get(key)
        if (type(value) not in (int,float) or value < 0 or value > 2**53
                or not math.isfinite(value)):
            raise ValueError('Missing or invalid measured resource fact')
        resources[key] = value
    if (resources['peak_memory_bytes'] > 256*1024**2 or resources['wall_seconds'] > 120
            or resources['measured_cpu_before_closeout_seconds'] > 60):
        raise ValueError('Measured resources exceed declared targets')
    resources['cpu_seconds_meaning'] = 'charged reservation, not measured runtime'
    resources['measured_cpu_scope'] = 'lower bound before final receipt and database closeout'
    resources['peak_memory_scope'] = 'sum of process high-water marks, not simultaneous RSS or a hard cap'
    return {'schema':'agent-replay-evaluation/1', 'source_sha256':source_sha256,
            'protocol_sha256':protocol_sha256, 'result':{'metrics':dict(metrics), 'checks':checks},
            'resources':resources, 'scope':'wholly synthetic offline traces; no live-model reliability claim'}


def encoded_aggregate(receipt, source_sha256, protocol_sha256):
    payload = aggregate_from_receipt(receipt, source_sha256, protocol_sha256)
    first = stable_json(payload).encode('utf-8')
    second = stable_json(payload).encode('utf-8')
    digest = hashlib.sha256(first).hexdigest()
    if first != second or digest != hashlib.sha256(second).hexdigest():
        raise ValueError('Aggregate serialization is not deterministic')
    return first, digest
