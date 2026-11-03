"""New recovery/accounting boundaries found during delivery review."""
import json
from pathlib import Path
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from model_synthesis import reserve_call
import test_otari_workflow as fixture
import test_otari_gateway as http_fixture


class RecoveryBoundaries(unittest.TestCase):
    setUp = fixture.ResearchContract.setUp
    tearDown = fixture.ResearchContract.tearDown
    workflow = fixture.ResearchContract.workflow

    def test_operation_identity_keeps_one_reservation_across_journal_gap(self):
        first = reserve_call(self.memory.db, self.config, operation_id='one-logical-operation')
        second = reserve_call(self.memory.db, self.config, operation_id='one-logical-operation')
        self.assertEqual(first, second)
        self.assertEqual(self.memory.db.execute('SELECT count(*) FROM calls').fetchone()[0], 1)

    def test_ambiguous_request_outside_replay_window_is_not_sent_again(self):
        self.fail_once = 'reflect'
        flow = self.workflow()
        task = flow.run(flow.create('refund policy')['id'])
        task['steps'][0]['dispatched_at'] = time.time() - 2 * 86400
        with self.memory.db:
            self.memory.db.execute('UPDATE otari_tasks SET body=? WHERE id=?', (json.dumps(task), task['id']))
        attempts = len(self.calls)
        result = flow.run(task['id'])
        self.assertEqual(result['status'], 'paused')
        self.assertEqual(result['error']['kind'], 'replay_expired')
        self.assertEqual(len(self.calls), attempts)

    def test_string_flags_cannot_enable_paid_tools(self):
        flow = self.workflow()
        with self.assertRaises(ValueError):
            flow.create('refund policy', web='false')
        self.assertEqual(flow.list(), [])


class InvalidAccounting(unittest.TestCase):
    setUp = http_fixture.GatewayContract.setUp
    tearDown = http_fixture.GatewayContract.tearDown
    judge = http_fixture.GatewayContract.judge

    def test_malformed_model_json_keeps_reported_gateway_charge(self):
        self.raw = {'choices': [{'message': {'content': '{invalid'}}],
                    'usage': {'prompt_tokens': 25, 'completion_tokens': 5, 'cost_usd': '0.000004'}}
        with self.assertRaises(RuntimeError) as caught:
            self.judge()
        self.assertEqual(caught.exception.metadata.get('cost_usd'), '0.000004')
        self.assertEqual(caught.exception.metadata.get('request_id'), 'request-17')


if __name__ == '__main__':
    unittest.main()
