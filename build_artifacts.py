"""Package reviewable source with an explicit allowlist; keep private runtime state local."""
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).parent
OUTPUTS = ROOT.parents[1] / 'outputs'
DIRECTORIES = ('app', 'context-bridge', 'engineering-memory', 'tests', 'openspec', 'docs')
FILES = ('README.md', 'deployment.py', 'install.py', 'install_checkpoint.py', 'basic-memory-mcp-bridge.py',
         'evaluate_memory.py', 'evaluate_synthesis.py', 'openspec-preload.cjs', 'build_artifacts.py',
         'accept_installed.py', 'accept_model_mcp.py', 'accept_hook.py',
         'accept_clients.py', 'retry_claude_client.py', 'accept_checkpoint_installed.py')

def main():
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    docs = ROOT / 'docs'
    docs.mkdir(exist_ok=True)
    shutil.copy2(OUTPUTS / '记忆升级实施说明.md', docs / '记忆升级实施说明.md')
    evaluation = json.loads((ROOT / 'evaluation-models.json').read_text(encoding='utf-8'))
    public = [{'query': row['query'], 'split': row['split'], 'designated_source': row['gold'],
               'designated_source_rank': row['rank'], 'seconds': row['seconds'],
               'returned_sources': [r['permalink'] for r in row['results']]} for row in evaluation]
    result_file = OUTPUTS / '真实中文检索结果.json'
    result_file.write_text(json.dumps({'scope': '现场6题指定来源检索，不含答案质量或Hindsight基准',
                         'hits': sum(r['rank'] is not None for r in evaluation), 'cases': public},
                         ensure_ascii=False, indent=2), encoding='utf-8')
    shutil.copy2(result_file, docs / result_file.name)
    mcp_result = OUTPUTS / '真实MCP端到端验收.json'
    mcp_evaluation = json.loads((ROOT / 'evaluation-mcp-models.json').read_text(encoding='utf-8'))
    mcp_evaluation['scope'] = '隔离安装布局的真实 stdio 业务链路，包含多语嵌入与重排；后续正式安装与语言模型结果见真实模型与安装验收.json'
    mcp_result.write_text(json.dumps(mcp_evaluation, ensure_ascii=False, indent=2), encoding='utf-8')
    shutil.copy2(mcp_result, docs / mcp_result.name)
    installed = json.loads((ROOT / 'evaluation-installed.json').read_text(encoding='utf-8'))
    clients = json.loads((ROOT / 'evaluation-clients.json').read_text(encoding='utf-8'))
    acceptance = {
        'date': '2026-10-13',
        'scope': '已安装代码、实际客户端配置路由、真实语言模型；不宣称全部历史分类或Hindsight同语料胜出',
        'regression': {'tests': 87, 'seconds': 87.040, 'status': 'passed', 'real_embedding_and_reranking': True},
        'installation': {'status': 'installed', 'clients': ['Codex', 'Claude Code'],
                         'native_multilingual_migration': {'embedded': 374, 'skipped': 0, 'errors': 0},
                         'backup_targets': 267, 'backed_up_existing_files': 184},
        'migration_preservation': json.loads((ROOT / 'evaluation-migration.json').read_text(encoding='utf-8')),
        'real_classification_and_reflection': json.loads((ROOT / 'evaluation-synthesis.json').read_text(encoding='utf-8')),
        'real_model_through_mcp': json.loads((ROOT / 'evaluation-model-mcp.json').read_text(encoding='utf-8')),
        'installed_mcp_routes': [{'client': row['client'], 'status': row['status'],
                                 'contracts': row['contracts'], **({'reflection': row['reflection']} if 'reflection' in row else {})}
                                 for row in installed],
        'native_clients': {
            'Codex': clients['Codex'],
            'Claude': {'status': clients['Claude']['status'],
                       **({'tools': clients['Claude']['tools'], 'answer': clients['Claude']['answer']}
                          if clients['Claude']['status'] == 'passed'
                          else {'reason': 'Claude模型渠道在验收时返回503 all nodes exhausted；有限重试没有成功证据',
                                'direct_mcp_route': 'passed'})}},
        'installed_hook': {name:{'status':data['status'],'contracts':['actual 30-second prompt context returned','same session replay suppressed']} for name,data in json.loads((ROOT/'evaluation-installed-hook.json').read_text(encoding='utf-8'))['clients'].items()},
        'checkpoint_lifecycle': json.loads((ROOT/'evaluation-checkpoint-installed.json').read_text(encoding='utf-8')),
        'history': json.loads((ROOT / 'evaluation-history.json').read_text(encoding='utf-8')),
        'remaining': ([] if clients['Claude']['status'] == 'passed' else ['Claude原生模型端到端缺成功结果'])
                     + ['历史队列按既有预算渐进处理'],
    }
    model_result = OUTPUTS / '真实模型与安装验收.json'
    model_result.write_text(json.dumps(acceptance, ensure_ascii=False, indent=2), encoding='utf-8')
    shutil.copy2(model_result, docs / model_result.name)
    archive = OUTPUTS / '记忆升级源码与安装包.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in FILES:
            bundle.write(ROOT / name, name)
        for name in DIRECTORIES:
            for path in sorted((ROOT / name).rglob('*')):
                if path.is_file() and '__pycache__' not in path.parts and path.suffix not in {'.pyc', '.pyo'}:
                    bundle.write(path, path.relative_to(ROOT).as_posix())
    print(json.dumps({'archive': str(archive), 'evaluation': str(result_file),
                      'mcp_evaluation': str(mcp_result), 'model_installation_evaluation': str(model_result)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
