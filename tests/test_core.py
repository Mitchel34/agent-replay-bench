import copy
from pathlib import Path
import tempfile
import unittest
from agent_replay_bench import core


def reference():
    return {'schema':'agent-replay-trace/1', 'scenario':'manual', 'events':[
        {'seq':0,'step':'a','tool':'echo','args':{'text':'hello'},'output':{'ok':True,'value':'hello'},'before':'running','after':'running'},
        {'seq':1,'step':'b','tool':'add','args':{'a':2,'b':3},'output':{'ok':True,'value':5},'before':'running','after':'succeeded'}],
        'terminal':{'state':'succeeded','step':'b'}}


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.ref = reference()
        self.observed = copy.deepcopy(self.ref)

    def categories(self):
        return {r['category'] for r in core.compare(self.ref, self.observed)['divergences']}

    def test_exact_and_metadata_only_agree(self):
        self.observed['metadata']={'timestamp':'different','request_id':'new','duration_ms':2}
        self.observed['events'][0]['metadata']={'request_id':'event'}
        self.assertTrue(core.compare(self.ref,self.observed)['agreement'])

    def test_missing_does_not_cascade(self):
        self.observed['events'].pop(0)
        report=core.compare(self.ref,self.observed)
        self.assertEqual(report['divergences'],[{'category':'missing_event','index':-1,'step':'a','field':'step'}])

    def test_reorder_detected(self):
        self.observed['events'].reverse()
        self.assertEqual(self.categories(),{'reordered_event'})

    def test_sequence_only_change(self):
        self.observed['events'][0]['seq']=9
        self.assertEqual(self.categories(),{'reordered_event'})

    def test_duplicate_does_not_cascade(self):
        self.observed['events'].append(copy.deepcopy(self.observed['events'][0]))
        report=core.compare(self.ref,self.observed)
        self.assertEqual(self.categories(),{'duplicate_event'})
        self.assertEqual([r['field'] for r in report['divergences']],['seq','step'])

    def test_unexpected_tool_inert_and_no_content_cascade(self):
        self.observed['events'][0].update(tool='shell',args={'command':'touch forbidden'},output=None)
        self.assertEqual(self.categories(),{'unexpected_tool'})
        with self.assertRaises(ValueError): core.run_tool('shell',{'command':'ignored'})

    def test_extra_unknown_id(self):
        self.observed['events'].append({'seq':2,'step':'extra','tool':'shell','args':{},'output':None,'before':'running','after':'succeeded'})
        self.assertEqual(self.categories(),{'unexpected_tool'})
        self.assertIsNone(core.compare(self.ref,self.observed)['divergences'][0]['step'])

    def test_input_mismatch_not_normalized(self):
        self.observed['events'][0]['args']['text']=' hello '
        self.assertEqual(self.categories(),{'input_mismatch'})

    def test_output_mismatch_and_type_distinction(self):
        self.observed['events'][1]['output']['value']=5.0
        self.assertEqual(self.categories(),{'output_mismatch'})
        self.assertFalse(core.identical(True,1))

    def test_invalid_transition(self):
        self.observed['events'][0]['before']='failed'
        self.assertEqual(self.categories(),{'invalid_transition'})

    def test_semantic_terminal_is_reportable(self):
        self.observed['terminal']['state']='empty'
        self.assertEqual(self.categories(),{'invalid_terminal'})

    def test_empty_and_empty_mutations(self):
        empty={'schema':core.SCHEMA,'scenario':'manual','events':[],'terminal':{'state':'empty','step':None}}
        self.assertTrue(core.compare(empty,empty)['agreement'])
        changed=copy.deepcopy(empty);changed['terminal']['state']='succeeded'
        self.assertEqual(core.compare(empty,changed)['divergences'][0]['category'],'invalid_terminal')
        inserted=core.mutate(empty,'unexpected_tool')
        self.assertEqual({r['category'] for r in core.compare(empty,inserted)['divergences']},{'unexpected_tool'})

    def test_combined_faults_and_stable_order(self):
        self.observed['events'][0]['args']['text']='changed'
        self.observed['events'][1]['output']=None
        self.observed['terminal']['step']='a'
        first=core.compare(self.ref,self.observed)
        self.assertEqual([r['category'] for r in first['divergences']],['input_mismatch','output_mismatch','invalid_terminal'])
        self.assertEqual(first,core.compare(self.ref,self.observed))
        self.assertEqual(sum(first['counts']['categories'].values()),3)

    def test_invalid_reference_truth(self):
        self.ref['events'][1]['output']['value']=6
        with self.assertRaises(ValueError):core.compare(self.ref,self.observed)

    def test_reference_duplicate_and_order_rejected(self):
        for key,value in [('step','a'),('seq',0)]:
            bad=reference();bad['events'][1][key]=value
            with self.assertRaises(ValueError):core.validate_reference(bad)

    def test_failure_and_retry_truth(self):
        failed=core.fixture('divide_failure',0)
        retry=core.fixture('retry',0)
        self.assertEqual(failed['events'][1]['output'],{'ok':False,'error':'division_by_zero'})
        self.assertEqual(retry['events'][1]['output'],{'ok':True,'value':1})
        core.validate_reference(failed);core.validate_reference(retry)
        self.assertEqual(retry['events'][0]['after'],'running')

    def test_stub_argument_and_lookup_contract(self):
        self.assertEqual(core.run_tool('lookup',{'key':'green'}),{'ok':True,'value':8})
        self.assertEqual(core.run_tool('lookup',{'key':'missing'}),{'ok':False,'error':'missing_key'})
        self.assertEqual(core.run_tool('divide',{'a':-5,'b':2}),{'ok':True,'value':-3})
        for args in ({'a':True,'b':1},{'a':1000001,'b':1},{'a':1,'b':2,'extra':0}):
            with self.assertRaises(ValueError):core.run_tool('add',args)

    def test_inert_command_and_url(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'must-not-exist'
            for text in (f'$(touch {target})','https://invalid.example/no-call'):
                self.assertEqual(core.run_tool('echo',{'text':text}),{'ok':True,'value':text})
            self.assertFalse(target.exists())

    def test_redaction_nested_and_collision(self):
        self.assertEqual(core.redact({core.SENTINEL:[core.SENTINEL,'keep']}),{'[REDACTED]':['[REDACTED]','keep']})
        with self.assertRaises(ValueError):core.redact({core.SENTINEL:1,'[REDACTED]':2})

    def test_redaction_never_changes_agreement(self):
        self.ref['events'][0]['args']['text']=core.SENTINEL
        self.ref['events'][0]['output']['value']=core.SENTINEL
        observed=copy.deepcopy(self.ref);observed['events'][0]['output']['value']='[REDACTED]'
        report=core.compare(self.ref,observed)
        self.assertFalse(core.redact(report)['agreement'])

    def test_invalid_shapes(self):
        bad_cases=[]
        for key,value in [('schema','agent-replay-trace/9'),('scenario','bad/id'),('events',{}),('extra',1)]:
            bad=reference();bad[key]=value;bad_cases.append(bad)
        for key,value in [('seq',True),('before','unknown'),('args',[]),('step','bad/id')]:
            bad=reference();bad['events'][0][key]=value;bad_cases.append(bad)
        bad=reference();bad['metadata']={'extra':0};bad_cases.append(bad)
        bad=reference();bad['events']*=25;bad_cases.append(bad)
        bad=reference();bad['terminal']={'state':'unknown','step':None};bad_cases.append(bad)
        for bad in bad_cases:
            with self.subTest(bad=bad),self.assertRaises(ValueError):core.validate_shape(bad)

    def test_value_bounds_and_surrogates(self):
        for value in (float('inf'),10**10,'\ud800','x'*4097):
            bad=reference();bad['events'][0]['output']=value
            with self.assertRaises(ValueError):core.validate_shape(bad)
        value=0
        for _ in range(14):value=[value]
        with self.assertRaises(ValueError):core.json_value(value)

    def test_mutation_recipes_and_no_input_mutation(self):
        clean=core.clean_copy(self.ref,2)
        self.assertEqual(clean['metadata'],{'timestamp':'seed-2','duration_ms':2,'request_id':'clean-2'})
        self.assertEqual(core.mutate(clean,'input_mismatch')['events'][0]['args']['text'],'hello!')
        self.assertEqual(self.ref,reference())
        with self.assertRaises(ValueError):core.mutate(core.fixture('empty',0),'missing_event')

    def test_report_omits_payload(self):
        self.observed['events'][0]['output']='PAYLOAD-MUST-NOT-APPEAR'
        self.assertNotIn('PAYLOAD-MUST-NOT-APPEAR',str(core.compare(self.ref,self.observed)))
