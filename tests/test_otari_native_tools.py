"""Observable native server-tool results, rather than the model's account."""
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from otari_gateway import GatewayClient, GatewayError
import test_otari_workflow as flow_fixture


def transcript(blocks, *, stop=True):
    events = [{'type': 'message_start', 'message': {'id': 'native-1', 'usage': {
        'input_tokens': 30, 'cache_read_input_tokens': 10, 'cache_creation_input_tokens': 2}}}]
    for index, block in enumerate(blocks):
        events.append({'type': 'content_block_start', 'index': index, 'content_block': block})
        events.append({'type': 'content_block_stop', 'index': index})
    events.append({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn'},
                   'usage': {'output_tokens': 18, 'cost_usd': '0.01003', 'pricing_source': 'deployment'}})
    if stop:
        events.append({'type': 'message_stop'})
    return ''.join('data: ' + json.dumps(event) + '\n\n' for event in events).encode()


class NativeTools(unittest.TestCase):
    def call(self, blocks, *, mcp=False, stop=True):
        raw = transcript(blocks, stop=stop)
        class Response(io.BytesIO):
            headers = {'Otari-Request-ID': 'native-1', 'Otari-Model': 'actual', 'Otari-Provider': 'host'}
        with patch.dict(os.environ, {'OTARI_API_KEY': 'test-only'}):
            client = GatewayClient({'otari': {'models': {'analysis': 'open-model'}, 'tool_transport': 'messages'}})
        def open_request(request, **kwargs):
            self.request = request
            return Response(raw)
        client.opener.open = open_request
        return client.complete([{'role': 'system', 'content': 'Use the tool.'}, {'role': 'user', 'content': 'refund'}],
            role='analysis', operation_id='native-operation',
            tools=None if mcp else [{'type': 'otari_code_execution', 'max_uses': 1}],
            mcp_server_ids=['demo-server'] if mcp else None)

    def test_code_output_and_actual_charge_reach_the_consumer(self):
        reply = self.call([
            {'type': 'server_tool_use', 'id': 'run-1', 'name': 'code_execution', 'input': {'code': 'print(3)'}},
            {'type': 'code_execution_tool_result', 'tool_use_id': 'run-1', 'content': {
                'type': 'code_execution_result', 'stdout': '3\n', 'stderr': '', 'return_code': 0}},
            {'type': 'text', 'text': 'Computed.'}])
        self.assertEqual(reply.tool_calls[0]['stdout'], '3\n')
        self.assertEqual(reply.tool_calls[0]['exit_code'], 0)
        self.assertEqual(reply.tool_calls[0]['status'], 'completed')
        self.assertEqual(reply.usage['otari']['cost_usd'], '0.01003')
        self.assertEqual(reply.usage['input_tokens'], 42)
        self.assertEqual(reply.content, 'Computed.')
        self.assertTrue(self.request.full_url.endswith('/messages'))
        self.assertTrue(json.loads(self.request.data)['stream'])
        self.assertEqual(json.loads(self.request.data)['tools'][0]['type'], 'code_execution_20250522')

    def test_mcp_read_output_is_preserved_with_server_and_identity(self):
        source = {'citation': 'demo/refund', 'title': 'Policy', 'revision': '1', 'text': 'Stable business key.'}
        reply = self.call([
            {'type': 'mcp_tool_use', 'id': 'read-1', 'server_name': 'demo', 'name': 'read_source', 'input': {'citation': 'demo/refund'}},
            {'type': 'mcp_tool_result', 'tool_use_id': 'read-1', 'is_error': False,
             'content': [{'type': 'text', 'text': json.dumps(source)}]},
            {'type': 'text', 'text': 'Read.'}], mcp=True)
        record = reply.tool_calls[0]
        self.assertEqual(json.loads(record['output']), source)
        self.assertEqual((record['server'], record['name'], record['status']), ('demo', 'read_source', 'completed'))
        self.assertIn('mcp-client-2025-11-20', self.request.get_header('Anthropic-beta'))

    def test_interrupted_stream_cannot_be_accepted_as_a_completed_tool_turn(self):
        with self.assertRaises(GatewayError) as caught:
            self.call([{'type': 'text', 'text': 'Possibly incomplete.'}], stop=False)
        self.assertEqual(caught.exception.kind, 'invalid_output')

    def test_nonzero_execution_is_preserved_as_failed(self):
        reply = self.call([
            {'type': 'server_tool_use', 'id': 'run-1', 'name': 'code_execution', 'input': {'code': 'raise ValueError()'}},
            {'type': 'code_execution_tool_result', 'tool_use_id': 'run-1', 'content': {
                'type': 'code_execution_result', 'stdout': '', 'stderr': 'ValueError', 'return_code': 1}},
            {'type': 'text', 'text': 'Execution failed.'}])
        self.assertEqual(reply.tool_calls[0]['status'], 'failed')
        self.assertEqual(reply.tool_calls[0]['exit_code'], 1)


class NativeRecovery(unittest.TestCase):
    setUp = flow_fixture.ResearchContract.setUp
    tearDown = flow_fixture.ResearchContract.tearDown
    workflow = flow_fixture.ResearchContract.workflow

    def test_synthesis_receives_actual_task_usage_as_distinct_from_memory_policy(self):
        flow = self.workflow()
        result = flow.run(flow.create('refund policy and current cost', web=True)['id'])
        self.assertEqual(result['status'], 'completed')
        synthesis = next(json.loads(messages[-1]['content']) for messages, args in self.calls if args['role'] == 'reflect')
        self.assertEqual(synthesis['run_usage'][0]['otari']['cost_usd'], '0.000003')
        self.assertEqual(synthesis['run_usage'][0]['otari']['role'], 'research')

    def test_uncertain_stream_requires_reconciliation_instead_of_redispatch(self):
        self.config['otari']['tool_transport'] = 'messages'
        self.fail_once = 'analysis'
        flow = self.workflow()
        task = flow.create('refund policy', analyze=True)
        self.assertEqual(flow.run(task['id'])['status'], 'paused')
        resumed = flow.run(task['id'])
        self.assertEqual(resumed['error']['kind'], 'reconciliation_required')
        self.assertEqual(sum(c[1]['role'] == 'analysis' for c in self.calls), 1)
        self.assertFalse(flow.get(task['id'])['can_resume'])
