"""Final current-change contracts: correction, recovery and remote evidence."""
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from otari_gateway import GatewayReply
import test_otari_workflow as fixture


class DeliveryContract(unittest.TestCase):
    setUp = fixture.ResearchContract.setUp
    tearDown = fixture.ResearchContract.tearDown
    workflow = fixture.ResearchContract.workflow

    def test_remote_read_result_is_used_as_answer_evidence(self):
        base = self.factory
        class RemoteGateway:
            def complete(inner, messages, **args):
                if args.get('mcp_server_ids'):
                    return GatewayReply('Read the source.', None,
                        {'input_tokens': 10, 'output_tokens': 5, 'otari': {'cost_usd': None}},
                        ({'type': 'mcp', 'status': 'completed', 'server': 'published-demo', 'name': 'read_source',
                          'output': json.dumps({'citation': 'main/remote', 'title': 'Remote policy',
                            'text': 'Remote refunds require a stable operation identity.', 'revision': '4'})},))
                return base({}).complete(messages, **args)
        self.factory = lambda config: RemoteGateway()
        self.config['research']['mcp_server_ids'] = ['published-demo']
        flow = self.workflow()
        result = flow.run(flow.create('refund policy', mcp=True)['id'])
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['sources'][-1]['kind'], 'remote_mcp')
        self.assertIn('Remote refunds', result['answer']['support'][0]['quote'])

    def test_abandoned_worker_exposes_resume_after_lease_expiry(self):
        flow = self.workflow()
        task = flow.create('refund policy')
        task['status'] = 'running'
        with self.memory.db:
            self.memory.db.execute('UPDATE otari_tasks SET body=?,lease=?,lease_until=? WHERE id=?',
                (json.dumps(task), 'abandoned-worker', time.time()-1, task['id']))
        self.assertTrue(flow.get(task['id']).get('can_resume'))
        self.assertEqual(flow.run(task['id'])['status'], 'completed')

    def test_latest_explicit_correction_is_the_current_evidence(self):
        for event_id, date, text in [('old', '2026-11-01T00:00:00Z', 'Refund policy: use the initial operation token.'),
                                     ('new', '2026-11-02T00:00:00Z', 'Refund policy: use the corrected stable business key.')]:
            self.memory.retain(event_id, [{'subject': 'Refund policy', 'predicate': 'identity',
                'value': text, 'quote': text, 'source': 'user', 'authority': True, 'scope': 'global'}], {'user': text, 'final': ''}, date)
        flow = self.workflow()
        result = flow.run(flow.create('refund policy identity')['id'])
        self.assertEqual(result['status'], 'completed')
        evidence = result['observations'][0]
        self.assertIn('corrected stable business key', evidence['current'])
        self.assertEqual([x['event_id'] for x in evidence['current_evidence']], ['new'])

    def test_extraction_recovery_retains_one_event_after_partial_publication(self):
        text = 'Refund policy requires exactly one business effect per operation.'
        base = self.factory
        extraction_count = []
        class ExtractingGateway:
            def complete(inner, messages, **args):
                if args['role'] == 'extract':
                    extraction_count.append(args['operation_id'])
                    note = {'title': 'Refund policy', 'kind': 'preference', 'scope': 'global',
                        'lesson': text, 'limitations': 'Applies to refunds.', 'related_path': '',
                        'subject': 'Refund policy', 'predicate': 'business effect', 'value': text,
                        'evidence': [{'source': 'user', 'quote': text}]}
                    value = {'reason': 'Explicit user policy', 'notes': [note]}
                    return GatewayReply(json.dumps(value), value,
                        {'input_tokens': 10, 'output_tokens': 5, 'otari': {'cost_usd': None}}, ())
                return base({}).complete(messages, **args)
        self.factory = lambda config: ExtractingGateway()
        flow = self.workflow()
        task = flow.create('refund policy', event={'user': text, 'final': ''})
        original = self.memory.page
        with patch.object(self.memory, 'page', side_effect=RuntimeError('simulated interruption after retain')):
            self.assertEqual(flow.run(task['id'])['status'], 'paused')
        self.assertEqual(flow.run(task['id'])['status'], 'completed')
        self.assertEqual(len(extraction_count), 1)
        self.assertEqual(self.memory.db.execute('SELECT count(*) FROM memory_events').fetchone()[0], 1)


if __name__ == '__main__':
    unittest.main()
