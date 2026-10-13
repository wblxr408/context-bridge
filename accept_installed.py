"""Read real memory through each client's installed stdio route; no config probes."""
import json
import os
from pathlib import Path
import sys
import tempfile
import tomllib

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / 'tests'))
from test_mcp_e2e import StdioClient, value

QUERY = '为什么我们不另建一个持续学习后台，而是继续使用现有的监听器？'

def main():
    user = Path.home()
    codex = tomllib.loads((user / '.codex/config.toml').read_text(encoding='utf-8-sig'))
    claude = json.loads((user / '.claude.json').read_text(encoding='utf-8-sig'))
    routes = [('Codex', codex['mcp_servers']['basic-memory']),
              ('Claude', claude['mcpServers']['basic-memory'])]
    results = []
    with tempfile.TemporaryDirectory(prefix='installed-acceptance-', dir=ROOT) as temp:
        for label, route in routes:
            env = os.environ.copy()
            env.update(route.get('env', {}), PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
            client = StdioClient([route['command'], *route.get('args', [])], env,
                                 Path(temp) / (label + '-stderr.log'))
            try:
                client.call('initialize', {'protocolVersion': '2025-11-25', 'capabilities': {},
                      'clientInfo': {'name': 'installed-memory-acceptance', 'version': '1'}})
                client.send('notifications/initialized', notification=True)
                recalled = value(client.tool('memory_recall', {'query': QUERY, 'limit': 5}))
                assert recalled['results'], 'Real memory sources must answer the question'
                source = next(r for r in recalled['results'] if
                        r['title'] == 'Codex 重叠技能按领域融合并渐进式加载')
                native = value(client.tool('read_note', {'identifier': source['permalink'],
                               'project': 'main', 'output_format': 'json'}))
                assert native['title'] == source['title']
                model_evaluation=json.loads((ROOT/'evaluation-model-mcp.json').read_text(encoding='utf-8'))
                supports=[item['quote'] for item in model_evaluation['results']['supported_policy']['support']
                          if item['citation']==source['permalink']]
                assert supports and all(quote in native['content'] for quote in supports), \
                    'Model policy citations must match the actual native source'
                assert client.tool('memory_recall', {'query': ''})['isError']
                recovered = value(client.tool('memory_recall', {'query': QUERY, 'limit': 5}))
                assert source['permalink'] in {r['permalink'] for r in recovered['results']}
                result = {'client': label, 'status': 'passed', 'sources':
                          [r['permalink'] for r in recalled['results']],
                          'contracts': ['real recall', 'native source read', 'invalid input recovery']}
                if label == 'Codex':
                    reflected = client.tool('memory_reflect', {'query': QUERY})
                    if reflected.get('isError'):
                        error = '\n'.join(c.get('text', '') for c in reflected.get('content', []))
                        if 'budget exhausted' not in error:
                            raise AssertionError(error)
                        result['reflection'] = {'status': 'shared_budget_rejected'}
                    else:
                        result['reflection'] = value(reflected)
                        assert result['reflection']['status'] == 'synthesized'
                        assert result['reflection']['citations'] and result['reflection']['support']
                results.append(result)
                print(json.dumps(result, ensure_ascii=False), flush=True)
            finally:
                client.close()
    (ROOT / 'evaluation-installed.json').write_text(
          json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()
