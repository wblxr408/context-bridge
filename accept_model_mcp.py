"""Real language-model synthesis via installed MCP code and a private evaluation ledger.

The existing vault is read as source data. Production quotas are not reset or
modified; these two frozen evaluation calls use temporary state, with the same limits.
"""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import tomllib

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / 'tests'))
from test_mcp_e2e import StdioClient, value
from accept_installed import QUERY

def main():
    user = Path.home()
    service = user / '.codex/services/engineering-memory'
    route = tomllib.loads((user / '.codex/config.toml').read_text(encoding='utf-8-sig'))['mcp_servers']['basic-memory']
    config = json.loads((service / 'config.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='installed-model-evaluation-', dir=ROOT) as temp:
        home = Path(temp)
        (home / 'config.json').write_text(json.dumps(config), encoding='utf-8')
        sys.path.insert(0, str(service / 'app'))
        from memory_runtime import MemoryRuntime
        # Reuse only the already-built production passage cache. This avoids
        # benchmarking a second cold corpus build while evaluating synthesis.
        memory = MemoryRuntime(config['vault'], home / 'state.sqlite', use_models=False)
        source = sqlite3.connect((service / 'state.sqlite').as_uri() + '?mode=ro', uri=True)
        try:
            with memory.db:
                memory.db.executemany('INSERT OR REPLACE INTO memory_vectors VALUES(?,?,?,?)',
                          source.execute('SELECT path,version,model,vector FROM memory_vectors'))
        finally:
            source.close()
            memory.close()
        # The exact deployed code is selected, while its evaluation state is private.
        shutil.copytree(service / 'app', home / 'app',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        env = os.environ.copy()
        env.update(route.get('env', {}), ENGINEERING_MEMORY_HOME=str(home),
                   PYTHONUTF8='1', PYTHONIOENCODING='utf-8', MEMORY_PROXY_TRACE='true')
        client = StdioClient([route['command'], *route['args']], env, home / 'stderr.log')
        results = {}
        try:
            client.call('initialize', {'protocolVersion': '2025-11-25', 'capabilities': {},
                      'clientInfo': {'name': 'installed-model-memory-evaluation', 'version': '1'}})
            client.send('notifications/initialized', notification=True)
            supported = value(client.tool('memory_reflect', {'query': QUERY}))
            assert supported['status'] == 'synthesized'
            assert supported['citations'] and supported['support']
            results['supported_policy'] = supported
            print(json.dumps(supported, ensure_ascii=False), flush=True)
            unknown = value(client.tool('memory_reflect', {
                'query': '工程记忆后台在2027年第二季度已经批准的GPU采购预算精确是多少人民币？'}))
            assert unknown['status'] == 'insufficient_evidence'
            assert unknown['citations'] == []
            results['unknown_detail'] = unknown
            print(json.dumps(unknown, ensure_ascii=False), flush=True)
        finally:
            client.close()
            (ROOT / 'evaluation-model-mcp-stderr.txt').write_text(
                (home / 'stderr.log').read_text(encoding='utf-8', errors='replace'), encoding='utf-8')
        (ROOT / 'evaluation-model-mcp.json').write_text(
              json.dumps({'status': 'passed', 'scope': 'deployed code, real main sources and models; warm passage cache and temporary evaluation quota ledger',
                          'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()
