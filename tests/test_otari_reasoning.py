"""Hosted discovery: bound reasoning while preserving useful structured output."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import test_otari_gateway as http_fixture
import test_otari_workflow as flow_fixture


class ReasoningTransport(unittest.TestCase):
    setUp=http_fixture.GatewayContract.setUp
    tearDown=http_fixture.GatewayContract.tearDown
    judge=http_fixture.GatewayContract.judge

    def test_extraction_can_disable_reasoning_without_changing_structured_contract(self):
        self.config['otari']['reasoning_effort']={'extract':'none','reflect':'low'}
        result,_=self.judge()
        self.assertEqual(result,self.output)
        self.assertEqual(self.requests[0][2].get('reasoning_effort'),'none')

    def test_invalid_effort_is_rejected_before_dispatch(self):
        self.config['otari']['reasoning_effort']={'extract':'unbounded-custom-value'}
        with self.assertRaises(RuntimeError) as error:
            self.judge()
        self.assertEqual(error.exception.kind,'configuration')
        self.assertEqual(self.requests,[])

    def test_length_limited_turn_is_rejected_even_if_partial_json_happens_to_parse(self):
        self.raw={'choices':[{'message':{'content':json.dumps(self.output)},'finish_reason':'length'}],
                  'usage':{'prompt_tokens':10,'completion_tokens':512,'cost_usd':'0.0006'}}
        with self.assertRaises(RuntimeError) as error:
            self.judge()
        self.assertEqual(error.exception.kind,'output_limit')
        self.assertEqual(error.exception.metadata['cost_usd'],'0.0006')


class FrozenReasoningSettings(unittest.TestCase):
    setUp=flow_fixture.ResearchContract.setUp
    tearDown=flow_fixture.ResearchContract.tearDown
    workflow=flow_fixture.ResearchContract.workflow

    def test_prepared_workflow_retains_the_selected_role_effort(self):
        self.config['otari']['reasoning_effort']={'reflect':'none'}
        settings=[]
        base=self.factory
        self.factory=lambda config:(settings.append(config) or base(config))
        flow=self.workflow()
        result=flow.run(flow.create('refund policy')['id'])
        self.assertEqual(result['status'],'completed')
        self.assertEqual(settings[0]['otari'].get('reasoning_effort'),{'reflect':'none'})
