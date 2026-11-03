"""New workbench and read-only MCP HTTP consumer outcomes."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from starlette.testclient import TestClient
from memory_runtime import markdown
from otari_workbench import create_app
from otari_mcp import create_mcp_app
import test_otari_workflow as research_fixture


class WorkbenchHTTP(unittest.TestCase):
    setUp = research_fixture.ResearchContract.setUp
    tearDown = research_fixture.ResearchContract.tearDown
    workflow = research_fixture.ResearchContract.workflow

    def test_submit_and_reopen_cited_task_through_http(self):
        with TestClient(create_app(self.workflow()), base_url='http://localhost') as client:
            created = client.post('/api/tasks', json={'query': 'refund policy'})
            self.assertEqual(created.status_code, 202)
            task_id = created.json()['id']
            task = client.get('/api/tasks/' + task_id).json()
            self.assertEqual(task['status'], 'completed')
            self.assertEqual(task['answer']['citations'], ['main/refunds'])
            self.assertEqual(client.get('/api/tasks').json()[0]['id'], task_id)

    def test_budget_paused_task_can_be_resumed_from_workbench(self):
        self.config['max_calls_per_day'] = 0
        with TestClient(create_app(self.workflow()), base_url='http://localhost') as client:
            task_id = client.post('/api/tasks', json={'query': 'refund policy'}).json()['id']
            self.assertEqual(client.get('/api/tasks/' + task_id).json()['status'], 'paused')
            self.config['max_calls_per_day'] = 20
            self.assertEqual(client.post('/api/tasks/' + task_id + '/resume').status_code, 202)
            self.assertEqual(client.get('/api/tasks/' + task_id).json()['status'], 'completed')

    def test_cross_origin_and_untrusted_host_cannot_submit_work(self):
        with TestClient(create_app(self.workflow()), base_url='http://localhost') as client:
            self.assertEqual(client.post('/api/tasks', json={'query': 'refund'}, headers={'Origin': 'https://evil.example'}).status_code, 403)
            self.assertEqual(client.get('/api/tasks', headers={'Host': 'evil.example'}).status_code, 403)
            self.assertEqual(client.get('/api/tasks').json(), [])

    def test_invalid_request_does_not_create_task(self):
        with TestClient(create_app(self.workflow()), base_url='http://localhost') as client:
            self.assertEqual(client.post('/api/tasks', json={'query': ''}).status_code, 400)
            self.assertEqual(client.post('/api/tasks', json={'query': 'refund', 'otari': {'api_key': 'ignored'}}).status_code, 400)
            self.assertEqual(client.get('/api/tasks').json(), [])


class PublishedMCP(unittest.TestCase):
    setUp = research_fixture.ResearchContract.setUp
    tearDown = research_fixture.ResearchContract.tearDown

    def test_authenticated_protocol_exposes_only_published_read_tools_and_sources(self):
        (self.vault / 'private.md').write_text(markdown({'title': 'Private refund',
            'permalink': 'main/private', 'scope': 'global'}, 'Private refund account.'), encoding='utf-8')
        config = {'remote_mcp': {'scope': 'global', 'permalinks': ['main/refunds'],
                                'token_env': 'BRIDGE_MCP_TOKEN', 'allowed_hosts': ['localhost']}}
        with patch.dict(os.environ, {'BRIDGE_MCP_TOKEN': 'fixture-secret'}):
            with TestClient(create_mcp_app(self.memory, config), base_url='http://localhost') as client:
                headers = {'Authorization': 'Bearer fixture-secret', 'Accept': 'application/json, text/event-stream',
                           'MCP-Protocol-Version': '2025-11-25'}
                def rpc(method, params=None):
                    return client.post('/mcp', headers=headers, json={'jsonrpc': '2.0', 'id': 1,
                        'method': method, **({'params': params} if params else {})}).json()
                initialization = rpc('initialize', {'protocolVersion': '2025-11-25',
                    'capabilities': {}, 'clientInfo': {'name': 'contract', 'version': '1'}})
                self.assertIn('result', initialization)
                listed = rpc('tools/list')['result']['tools']
                self.assertEqual({t['name'] for t in listed}, {'search_memory', 'read_source', 'source_revision'})
                found = rpc('tools/call', {'name': 'search_memory', 'arguments': {'query': 'refund'}})['result']
                self.assertIn('main/refunds', str(found))
                self.assertNotIn('main/private', str(found))
                denied = rpc('tools/call', {'name': 'read_source', 'arguments': {'citation': 'main/private'}})['result']
                self.assertTrue(denied.get('isError'))
                self.assertNotIn('Private refund account', str(denied))
                source = rpc('tools/call', {'name': 'read_source', 'arguments': {'citation': 'main/refunds'}})['result']
                self.assertIn(self.quote, str(source))
                revision = rpc('tools/call', {'name': 'source_revision', 'arguments': {'citation': 'main/refunds'}})['result']
                self.assertIn('revision', str(revision))

    def test_remote_mcp_refuses_missing_or_wrong_authentication(self):
        config = {'remote_mcp': {'scope': 'global', 'permalinks': ['main/refunds'],
                                'token_env': 'BRIDGE_MCP_TOKEN', 'allowed_hosts': ['localhost']}}
        with patch.dict(os.environ, {'BRIDGE_MCP_TOKEN': 'fixture-secret'}):
            with TestClient(create_mcp_app(self.memory, config), base_url='http://localhost') as client:
                for headers in ({}, {'Authorization': 'Bearer wrong'}):
                    self.assertEqual(client.post('/mcp', json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}, headers=headers).status_code, 401)


if __name__ == '__main__':
    unittest.main()
