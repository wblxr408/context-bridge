"""Consumer contract for the competition's hosted memory model boundary."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
import listener


class GatewayContract(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.status = 200
        self.output = {'reason': 'No durable lesson', 'notes': []}
        self.raw = None
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                owner.requests.append((self.path, dict(self.headers),
                                       json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                self.send_response(owner.status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Otari-Request-ID', 'request-17')
                self.send_header('Otari-Model', 'actual-open-model')
                self.send_header('Otari-Provider', 'test-provider')
                self.send_header('Otari-Fallback', 'true')
                self.send_header('Otari-Attempt-Count', '2')
                self.end_headers()
                body = owner.raw if owner.raw is not None else {
                    'choices': [{'message': {'content': json.dumps(owner.output)}}],
                    'usage': {'prompt_tokens': 20, 'completion_tokens': 8,
                              'cost_usd': '0.000012', 'pricing_source': 'deployment'}}
                self.wfile.write(json.dumps(body).encode())

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.temp = tempfile.TemporaryDirectory()
        self.config = {'model_backend': 'otari', 'judge_timeout_seconds': 5,
                       'otari': {'base_url': f'http://127.0.0.1:{self.server.server_port}/api/v1',
                                 'allow_loopback_http': True,
                                 'models': {'extract': 'extract-open', 'reflect': 'reflect-open'},
                                 'max_output_tokens': 512}}
        self.env = patch.dict(os.environ, {'OTARI_API_KEY': 'test-only-key'})
        self.env.start()
        self.cli = patch('listener.resolve_codex', side_effect=AssertionError(
            'A selected Otari backend must not dispatch the Codex CLI'))
        self.cli.start()

    def tearDown(self):
        self.cli.stop()
        self.env.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def judge(self, schema=None):
        return listener.judge(self.config, self.temp.name,
                              {'user': '以后保留每一项事实的原始来源。', 'final': ''}, [], schema)

    def test_extraction_reaches_gateway_and_preserves_billing_and_fallback(self):
        result, usage = self.judge()
        self.assertEqual(result, self.output)
        path, headers, request = self.requests[0]
        self.assertEqual(path, '/api/v1/chat/completions')
        self.assertEqual(headers['Authorization'], 'Bearer test-only-key')
        self.assertEqual(request['model'], 'extract-open')
        self.assertEqual(request['max_tokens'], 512)
        self.assertEqual(request['response_format']['type'], 'json_schema')
        self.assertEqual(usage['input_tokens'], 20)
        self.assertEqual(usage['output_tokens'], 8)
        self.assertEqual(usage['otari']['request_id'], 'request-17')
        self.assertEqual(usage['otari']['model'], 'actual-open-model')
        self.assertTrue(usage['otari']['fallback'])
        self.assertEqual(usage['otari']['cost_usd'], '0.000012')

    def test_reflection_uses_its_distinct_model_and_schema(self):
        self.output = {'status': 'insufficient_evidence', 'answer': '没有足够来源。',
                       'citations': [], 'support': []}
        result, _ = self.judge(ROOT / 'app/reflect-schema.json')
        self.assertEqual(result['status'], 'insufficient_evidence')
        self.assertEqual(self.requests[0][2]['model'], 'reflect-open')

    def test_invalid_structured_result_is_rejected(self):
        self.output = {'notes': 'not an array'}
        with self.assertRaises(RuntimeError) as caught:
            self.judge()
        self.assertEqual(caught.exception.kind, 'invalid_output')

    def test_budget_refusal_stays_explicit_and_never_bypasses_gateway(self):
        self.status = 429
        self.raw = {'detail': 'User has exceeded budget limit; test-only-key'}
        with self.assertRaises(RuntimeError) as caught:
            self.judge()
        self.assertEqual(caught.exception.kind, 'budget_exceeded')
        self.assertEqual(caught.exception.request_id, 'request-17')
        self.assertNotIn('test-only-key', str(caught.exception))
        self.assertEqual(len(self.requests), 1)

    def test_missing_key_is_a_configuration_failure_without_dispatch(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as caught:
                self.judge()
        self.assertEqual(caught.exception.kind, 'configuration')
        self.assertEqual(self.requests, [])

    def test_missing_cost_is_unknown_and_not_zero(self):
        self.raw = {'choices': [{'message': {'content': json.dumps(self.output)}}],
                    'usage': {'prompt_tokens': 10, 'completion_tokens': 5}}
        _, usage = self.judge()
        self.assertIsNone(usage['otari']['cost_usd'])


if __name__ == '__main__':
    unittest.main()
