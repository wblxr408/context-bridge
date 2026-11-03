"""JSON object transport still enforces the complete local consumer schema."""
import unittest
import test_otari_gateway as fixture


class JSONMode(unittest.TestCase):
    setUp = fixture.GatewayContract.setUp
    tearDown = fixture.GatewayContract.tearDown
    judge = fixture.GatewayContract.judge

    def test_json_mode_returns_valid_schema_data_without_provider_schema_decoding(self):
        self.config['otari']['response_modes'] = {'extract': 'json_object'}
        result, _ = self.judge()
        self.assertEqual(result, self.output)
        request = self.requests[0][2]
        self.assertEqual(request['response_format'], {'type': 'json_object'})
        self.assertTrue(any('Required response JSON schema:' in m['content'] for m in request['messages']))

    def test_json_mode_does_not_accept_json_that_violates_the_local_schema(self):
        self.config['otari']['response_modes'] = {'extract': 'json_object'}
        self.output = {'notes': 'not an array'}
        with self.assertRaises(RuntimeError) as caught:
            self.judge()
        self.assertEqual(caught.exception.kind, 'invalid_output')
        self.assertEqual(self.requests[0][2]['response_format'], {'type': 'json_object'})
