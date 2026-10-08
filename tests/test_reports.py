"""Exporter fixtures are invented unit-test inputs, never evaluation evidence."""
import ast
from pathlib import Path
import unittest
from agent_replay_bench import reports


def receipt_fixture():
    return {'kind':'benchmark-receipt','outcome':'pass','source_sha256':'a'*64,
            'owned_child_reaped':True,'process_tree_stopped':True,'additional_external_services_used':False,
            'result':{'metrics':reports.expected_metrics(),'checks':[{'name':n,'passed':True} for n in reports.check_names()]},
            'measured_cpu_before_closeout_seconds':1.0,'cpu_seconds':60.0,'peak_memory_bytes':10000000,
            'wall_seconds':2.0,'worker_cpu_seconds':0.9,'supervisor_cpu_seconds':0.1,
            'private_path':'DO-NOT-EXPORT','task_id':'PRIVATE-IDENTIFIER'}


class ReportTests(unittest.TestCase):
    def test_exact_envelope_and_deterministic_bytes(self):
        receipt=receipt_fixture()
        raw,digest=reports.encoded_aggregate(receipt,'a'*64,'b'*64)
        self.assertEqual((raw,digest),reports.encoded_aggregate(receipt,'a'*64,'b'*64))
        self.assertNotIn(b'DO-NOT-EXPORT',raw);self.assertNotIn(b'PRIVATE-IDENTIFIER',raw)
        self.assertEqual(len(reports.expected_metrics()),77);self.assertEqual(len(reports.check_names()),24)

    def test_failed_or_wrong_source_receipt_rejected(self):
        for key,value in [('outcome','fail'),('source_sha256','b'*64),('owned_child_reaped',False)]:
            receipt=receipt_fixture();receipt[key]=value
            with self.assertRaises(ValueError):reports.encoded_aggregate(receipt,'a'*64,'b'*64)

    def test_missing_extra_and_boolean_metric_rejected(self):
        for kind in ('missing','extra','bool','wrong'):
            receipt=receipt_fixture();metrics=receipt['result']['metrics']
            if kind=='missing':del metrics['trials']
            elif kind=='extra':metrics['extra']=0
            elif kind=='bool':metrics['false_alarms']=False
            else:metrics['trials']=3360
            with self.assertRaises(ValueError):reports.encoded_aggregate(receipt,'a'*64,'b'*64)

    def test_resource_overrun_and_nonfinite_rejected(self):
        for key,value in [('wall_seconds',121),('peak_memory_bytes',300*1024**2),('worker_cpu_seconds',float('nan')),('worker_cpu_seconds',10**1000)]:
            receipt=receipt_fixture();receipt[key]=value
            with self.assertRaises(ValueError):reports.encoded_aggregate(receipt,'a'*64,'b'*64)

    def test_export_module_has_no_comparator_import(self):
        tree=ast.parse(Path(reports.__file__).read_text())
        imported=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        self.assertNotIn('core',imported)
        self.assertNotIn('evaluate',Path(reports.__file__).read_text())

    def test_malformed_receipt_envelopes_rejected(self):
        for receipt in ([], {}, {'result': []}):
            with self.assertRaises(ValueError):reports.encoded_aggregate(receipt,'a'*64,'b'*64)
