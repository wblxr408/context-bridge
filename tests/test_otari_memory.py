"""Gateway-backed memory outcomes and shared budget accounting."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from memory_runtime import MemoryRuntime, markdown
from model_synthesis import generator_from_config, gateway_call_history
import test_otari_gateway as gateway_fixture


class HostedMemoryContract(unittest.TestCase):
    setUp = gateway_fixture.GatewayContract.setUp
    tearDown = gateway_fixture.GatewayContract.tearDown

    def exercise(self, *, report_usage=True):
        vault = Path(self.temp.name) / 'vault'
        vault.mkdir()
        quote = '每次退款必须保持幂等，只产生一次业务效果。'
        (vault / 'refund.md').write_text(markdown({
            'title': '退款幂等', 'scope': 'global', 'permalink': 'main/refund'}, quote), encoding='utf-8')
        self.output = {'status': 'synthesized', 'answer': '退款必须幂等。',
                       'citations': ['main/refund'],
                       'support': [{'citation': 'main/refund', 'quote': quote}]}
        if not report_usage:
            self.raw = {'choices': [{'message': {'content': json.dumps(self.output)}}]}
        config = {**self.config, 'max_calls_per_day': 10, 'max_calls_per_hour': 10,
                  'max_tokens_per_day': 100000, 'reserve_tokens_per_call': 12000}
        memory = MemoryRuntime(vault, Path(self.temp.name) / 'state.sqlite', use_models=False)
        try:
            result = memory.reflect('退款幂等', generator=generator_from_config(config, self.temp.name, memory))
            history = gateway_call_history(memory.db)
            reservation = memory.db.execute('SELECT tokens FROM calls').fetchone()[0]
            return result, history, reservation
        finally:
            memory.close()

    def test_cited_reflection_and_actual_gateway_usage_are_available_together(self):
        result, history, reserved = self.exercise()
        self.assertEqual(result['citations'], ['main/refund'])
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['request_id'], 'request-17')
        self.assertEqual(history[0]['cost_usd'], '0.000012')
        self.assertEqual(history[0]['state'], 'succeeded')
        self.assertEqual(reserved, 28)

    def test_unreported_usage_keeps_reservation_and_unknown_cost(self):
        result, history, reserved = self.exercise(report_usage=False)
        self.assertEqual(result['status'], 'synthesized')
        self.assertIsNone(history[0]['cost_usd'])
        self.assertEqual(reserved, 12000)


if __name__ == '__main__':
    unittest.main()
