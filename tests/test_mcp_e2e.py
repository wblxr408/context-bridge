"""Real stdio flow through the staged proxy and installed Basic Memory server.

All configuration, database and source writes are confined to one temporary
workspace fixture. This checks tool effects and isolation, not server startup.
"""
import json
import os
from pathlib import Path
import queue
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from memory_runtime import MemoryRuntime
sys.path.insert(0, str(ROOT))
from deployment import patch_claude


class StdioClient:
    def __init__(self, command, environment, log):
        self.log = log.open('wb')
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        stderr=self.log, env=environment, cwd=ROOT, bufsize=0,
                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.messages = queue.Queue()
        self.pending = {}
        self.next_id = 0
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        try:
            for line in self.process.stdout:
                self.messages.put(json.loads(line))
        except Exception as error:
            self.messages.put(error)
        finally:
            self.messages.put(EOFError('MCP closed before the requested response'))

    def send(self, method, params=None, notification=False):
        message = {'jsonrpc': '2.0', 'method': method}
        if params is not None:
            message['params'] = params
        if not notification:
            self.next_id += 1
            message['id'] = 'acceptance-' + str(self.next_id)
        self.process.stdin.write((json.dumps(message, ensure_ascii=False) + '\n').encode('utf-8'))
        self.process.stdin.flush()
        return message.get('id')

    def receive(self, identity, timeout=240):
        if identity in self.pending:
            return self.pending.pop(identity)
        import time
        deadline = time.monotonic() + timeout
        while True:
            message = self.messages.get(timeout=max(0.01, deadline - time.monotonic()))
            if isinstance(message, Exception):
                raise message
            if message.get('id') == identity:
                return message
            if 'id' in message:
                self.pending[message['id']] = message

    def call(self, method, params=None):
        response = self.receive(self.send(method, params))
        if 'error' in response:
            raise AssertionError(response['error'])
        return response['result']

    def tool(self, name, arguments):
        return self.call('tools/call', {'name': name, 'arguments': arguments})

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=5)
        self.reader.join(timeout=5)
        self.process.stdout.close()
        self.log.close()


def value(reply):
    if reply.get('isError'):
        raise AssertionError(reply.get('content'))
    if 'structuredContent' in reply:
        return reply['structuredContent'].get('result', reply['structuredContent'])
    return json.loads(next(c['text'] for c in reply['content'] if c['type'] == 'text'))


class RealMcpFlow(unittest.TestCase):
    def test_native_write_read_enhanced_scopes_cached_page_rejection_and_delegation(self):
        with tempfile.TemporaryDirectory(prefix='mcp-acceptance-', dir=ROOT) as temp:
            home = Path(temp)
            vault = home / 'vault'; vault.mkdir()
            other = home / 'other'; other.mkdir()
            native = home / 'native'; native.mkdir()
            model_cache = ROOT / 'models'
            use_models = os.environ.get('MEMORY_E2E_MODELS') == 'true'
            config = {'vault': str(vault), 'model_cache': str(model_cache), 'memory_models': use_models,
                      'max_calls_per_hour': 0, 'max_calls_per_day': 8,
                      'max_tokens_per_day': 60000, 'reserve_tokens_per_call': 12000}
            (home / 'config.json').write_text(json.dumps(config), encoding='utf-8')
            (native / 'config.json').write_text(json.dumps({
                'projects': {'main': {'path': str(vault)}, 'other': {'path': str(other)}},
                'default_project': 'main', 'semantic_search_enabled': True,
                'semantic_embedding_threads': 2, 'semantic_embedding_batch_size': 16,
                'semantic_embedding_parallel': 1,
                'reranker_enabled': True, 'sync_changes': True,
                'logfire_enabled': False, 'logfire_send_to_logfire': False}), encoding='utf-8')
            # A previously materialized page must be readable when model quota is zero.
            memory = MemoryRuntime(vault, home / 'state.sqlite', use_models=False)
            try:
                memory.retain('current-budget', [{'subject': '验收工程记忆', 'predicate': '调用预算',
                    'value': '每小时最多2次', 'source': 'user', 'quote': '每小时最多2次', 'scope': 'D:/a'}],
                    {'user': '每小时最多2次', 'final': ''}, '2026-10-01')
                cached = memory.page('验收预算页', '验收工程记忆调用预算', scope='D:/a')
            finally:
                memory.close()
            env = os.environ.copy()
            env.update(ENGINEERING_MEMORY_HOME=str(home), BASIC_MEMORY_CONFIG_DIR=str(native),
                       BASIC_MEMORY_HOME=str(vault), BASIC_MEMORY_AUTO_UPDATE='false',
                       MEMORY_PROXY_TRACE='true',
                       PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
            shutil.copytree(ROOT / 'app', home / 'app', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            client_config=patch_claude({'mcpServers':{'basic-memory':{'type':'stdio','command':'basic-memory','args':['mcp']}}},
                                sys.executable,ROOT / 'basic-memory-mcp-bridge.py')
            selected=client_config['mcpServers']['basic-memory']
            client = StdioClient([selected['command'], *selected['args']], env, home / 'protocol-stderr.log')
            try:
                initialized = client.call('initialize', {'protocolVersion': '2025-11-25',
                        'capabilities': {}, 'clientInfo': {'name': 'memory-behavior-acceptance', 'version': '1'}})
                client.send('notifications/initialized', notification=True)
                tools = client.call('tools/list')['tools']
                # Tool declarations must expose operations used below, without hiding native tools.
                names = {t['name'] for t in tools}
                self.assertTrue({'write_note', 'read_note', 'memory_recall', 'memory_reflect',
                                 'memory_knowledge_page'} <= names)
                for title, scope, project, budget in [('项目甲验收规则', 'D:/a', 'main', 2),
                            ('项目乙私有规则', 'D:/b', 'main', 7), ('其他记忆库规则', 'D:/other', 'other', 9)]:
                    client.tool('write_note', {'title': title, 'directory': 'acceptance',
                        'project': project, 'output_format': 'json', 'overwrite': False,
                        'metadata': {'scope': scope, 'hourly_limit': budget, 'status': 'accepted'},
                        'content': '# ' + title + '\n\n模型调用预算每小时最多' + str(budget) + '次。'})
                read = value(client.tool('read_note', {'identifier': '项目甲验收规则', 'project': 'main', 'output_format': 'json'}))
                self.assertEqual(read['frontmatter']['hourly_limit'], 2)
                ids = [client.send('tools/call', {'name': 'memory_recall', 'arguments': {
                        'query': '模型调用预算', 'scope': scope, 'limit': 10}}) for scope in ('D:/a', 'D:/b')]
                rows = [value(client.receive(i)['result'])['results'] for i in ids]
                self.assertIn('项目甲验收规则', {r['title'] for r in rows[0]})
                self.assertNotIn('项目乙私有规则', {r['title'] for r in rows[0]})
                self.assertIn('项目乙私有规则', {r['title'] for r in rows[1]})
                self.assertNotIn('项目甲验收规则', {r['title'] for r in rows[1]})
                page = value(client.tool('memory_knowledge_page', {'name': '验收预算页',
                           'query': '验收工程记忆调用预算', 'scope': 'D:/a'}))
                self.assertEqual(page['content'], cached['content'])
                self.assertEqual(page['citations'], cached['citations'])
                self.assertTrue(client.tool('memory_reflect', {'query': '模型调用预算', 'scope': 'D:/a'})['isError'])
                self.assertTrue(client.tool('memory_recall', {'query': ''})['isError'])
                again = value(client.tool('memory_recall', {'query': '模型调用预算', 'scope': 'D:/a'}))
                self.assertIn('项目甲验收规则', {r['title'] for r in again['results']})
                direct = value(client.tool('read_note', {'identifier': '其他记忆库规则',
                               'project': 'other', 'output_format': 'json'}))
                self.assertEqual(direct['frontmatter']['hourly_limit'], 9)
                # Native writes publish into an asynchronous search index.
                # Verify the requested business result with a bounded deadline.
                deadline = time.monotonic() + 20
                attempts = 0
                while True:
                    delegated = value(client.tool('search_notes', {'query': '其他记忆库规则',
                                      'project': 'other', 'search_type': 'title', 'output_format': 'json'}))
                    attempts += 1
                    if delegated['results'] or time.monotonic() >= deadline:
                        break
                    time.sleep(0.25)
                self.assertIn('其他记忆库规则', {r['title'] for r in delegated['results']})
                self.assertNotIn('项目甲验收规则', {r['title'] for r in delegated['results']})
                report = 'evaluation-mcp-models.json' if use_models else 'evaluation-mcp.json'
                (ROOT / report).write_text(json.dumps({
                    'status': 'passed', 'backend': 'installed Basic Memory through real stdio proxy',
                    'enhanced_models': use_models,
                    'embedding': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2' if use_models else None,
                    'reranker': 'BAAI/bge-reranker-base' if use_models else None, 'native_search_attempts': attempts,
                    'contracts': ['native write/read preserves numeric fact', 'request IDs',
                        'recall project isolation', 'cached page with zero quota',
                        'reflection budget rejection', 'invalid input rejection and recovery',
                        'other-project native title search']}, ensure_ascii=False, indent=2), encoding='utf-8')
            finally:
                client.close()
                # Preserve failure context before removing the isolated fixture.
                stderr = (home / 'protocol-stderr.log').read_text(encoding='utf-8', errors='replace')
                (ROOT / 'evaluation-mcp-stderr.txt').write_text(stderr, encoding='utf-8')


if __name__ == '__main__':
    unittest.main()
