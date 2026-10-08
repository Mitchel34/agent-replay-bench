import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from agent_replay_bench.cli import main, parse_json


class CliTests(unittest.TestCase):
    def invoke(self,args):
        out,err=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            code=main(args)
        return code,out.getvalue(),err.getvalue()

    def test_demo_precise_diagnostic(self):
        code,out,err=self.invoke(['demo','--format','json'])
        self.assertEqual(code,1);self.assertFalse(err)
        report=json.loads(out)
        self.assertEqual(report['divergences'],[{'category':'output_mismatch','field':'output','index':0,'step':'s0'}])

    def test_local_files_agreement(self):
        root=Path(__file__).resolve().parents[1]
        path=str(root/'examples/reference.json')
        code,out,err=self.invoke(['compare',path,path])
        self.assertEqual(code,0);self.assertIn('AGREEMENT',out);self.assertFalse(err)

    def test_malformed_and_truncated_json(self):
        for raw in (b'{',b'{"x":1,"x":2}',b'{"x":NaN}',b'\xff',b'['*1100,b' '*262145):
            with self.subTest(raw=raw[:20]),self.assertRaises(ValueError):parse_json(raw)

    def test_invalid_file_exit_and_no_payload_echo(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'bad.json';path.write_text('{"private-payload"')
            code,out,err=self.invoke(['compare',str(path),str(path)])
            self.assertEqual(code,2);self.assertFalse(out);self.assertNotIn('private-payload',err)

    def test_example_is_one_fixture(self):
        code,out,err=self.invoke(['example','empty','--seed','0'])
        self.assertEqual(code,0);self.assertEqual(json.loads(out)['events'],[])

    def test_export_digest_mismatch_creates_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'receipt.json';path.write_text('{}')
            output=Path(directory)/'output.json'
            code,_,_=self.invoke(['export-results',str(path),'--receipt-sha256','0'*64,
                '--source-sha256','0'*64,'--protocol-sha256','0'*64,'--output',str(output)])
            self.assertEqual(code,2);self.assertFalse(output.exists())

    def test_export_large_integer_rejected_without_output(self):
        import hashlib
        from test_reports import receipt_fixture
        receipt=receipt_fixture();receipt['worker_cpu_seconds']=10**1000
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'receipt.json';raw=json.dumps(receipt).encode();path.write_bytes(raw)
            output=Path(directory)/'output.json'
            code,out,err=self.invoke(['export-results',str(path),'--receipt-sha256',hashlib.sha256(raw).hexdigest(),
                '--source-sha256','a'*64,'--protocol-sha256','b'*64,'--output',str(output)])
            self.assertEqual(code,2);self.assertFalse(output.exists());self.assertFalse(out);self.assertTrue(err)
