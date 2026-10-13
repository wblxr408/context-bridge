"""Install the already-reviewed staged upgrade into the user's existing memory stack."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime,timezone
from deployment import Backup,patch_toml,patch_service,patch_basic_memory,patch_claude,hook_command,append_hook_config,restore

ROOT=Path(__file__).parent
USER=Path.home()
SERVICE=USER/'.codex/services/engineering-memory'
PYTHON=USER/'AppData/Roaming/uv/tools/basic-memory/Scripts/python.exe'
ALLOWED=[SERVICE,USER/'.codex/bin/basic-memory-mcp-bridge.py',USER/'.codex/config.toml',USER/'.codex/hooks.json',
         USER/'.claude/settings.json',USER/'.claude.json',USER/'.basic-memory/config.json',
         USER/'.codex/skills/context-bridge',USER/'.agents/skills/context-bridge',
         USER/'.codex/skills/engineering-memory',USER/'.agents/skills/engineering-memory',USER/'.claude/skills/engineering-memory']

def powershell(script):
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],capture_output=True,timeout=30)
    if result.returncode:raise RuntimeError(result.stderr.decode('utf-8',errors='replace')[-1200:])
    return result.stdout.decode('utf-8',errors='replace')

def quiesce():
    import msvcrt
    # Disabling a task can hide a still-running writer behind State=Disabled.
    # Own the existing listener's byte lock before backing up or replacing data.
    state=powershell("(Get-ScheduledTask -TaskName 'EngineeringMemoryListener').State.ToString()").strip()
    (SERVICE/'stop').touch()
    powershell("Disable-ScheduledTask -TaskName 'EngineeringMemoryListener' | Out-Null")
    ownership=(SERVICE/'listener.lock').open('a+b')
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        ownership.seek(0)
        try:
            msvcrt.locking(ownership.fileno(),msvcrt.LK_NBLCK,1)
            return state,ownership
        except OSError:
            pass
        time.sleep(2)
    ownership.close()
    raise RuntimeError('Listener is still completing a model call; it remains stopped from restarting. No files were replaced.')

def install():
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup=Backup(ROOT/('backup-'+stamp),ALLOWED)
    previous,ownership=quiesce()
    task_xml=powershell("Export-ScheduledTask -TaskName 'EngineeringMemoryListener'")
    (backup.folder/'scheduled-task.xml').write_text(task_xml,encoding='utf-8')
    (backup.folder/'task-state.json').write_text(json.dumps({'previous':previous}),encoding='utf-8')
    for path in [SERVICE/'config.json',SERVICE/'state.sqlite',USER/'.codex/config.toml',USER/'.basic-memory/config.json',USER/'.claude/settings.json',USER/'.claude.json',USER/'.codex/hooks.json']:
        backup.remember(path)
    try:
        for source in (ROOT/'app').rglob('*'):
            if source.is_file() and '__pycache__' not in source.parts and source.suffix not in {'.pyc','.pyo'}:backup.copy(source,SERVICE/'app'/source.relative_to(ROOT/'app'))
        backup.copy(ROOT/'basic-memory-mcp-bridge.py',USER/'.codex/bin/basic-memory-mcp-bridge.py')
        config=json.loads((SERVICE/'config.json').read_text(encoding='utf-8-sig'))
        for source in (ROOT/'models').rglob('*'):
            if source.is_file() and '.locks' not in source.parts and not source.name.endswith('.incomplete'):
                backup.copy(source,SERVICE/'models'/source.relative_to(ROOT/'models'))
        config=patch_service(config,SERVICE/'models')
        backup.write(SERVICE/'config.json',json.dumps(config,ensure_ascii=False,indent=2))
        # Native BM embeddings and the enhanced passage cache are different rebuildable indexes.
        # Warm the latter before activating 30-second prompt hooks.
        from memory_runtime import runtime_from_config
        memory=runtime_from_config(config,SERVICE)
        try:
            import evaluate_memory
            cases=[]
            for case in evaluate_memory.CASES:
                result=memory.recall(case['query'],limit=5)
                pids=[r['permalink'] for r in result['results']]
                cases.append({'query':case['query'],'rank':pids.index(case['gold'])+1 if case['gold'] in pids else None,'sources':pids})
            (ROOT/'installation-retrieval.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf-8')
        finally:memory.close()
        raw=(USER/'.codex/config.toml').read_text(encoding='utf-8-sig')
        backup.write(USER/'.codex/config.toml',patch_toml(raw,PYTHON))
        claude=json.loads((USER/'.claude.json').read_text(encoding='utf-8-sig'))
        backup.write(USER/'.claude.json',json.dumps(patch_claude(claude,PYTHON,USER/'.codex/bin/basic-memory-mcp-bridge.py'),ensure_ascii=False,indent=2))
        bm=json.loads((USER/'.basic-memory/config.json').read_text(encoding='utf-8-sig'))
        backup.write(USER/'.basic-memory/config.json',json.dumps(patch_basic_memory(bm,SERVICE/'models'),ensure_ascii=False,indent=2))
        command=hook_command(PYTHON,SERVICE)
        for path in [USER/'.codex/hooks.json',USER/'.claude/settings.json']:
            try:current=json.loads(path.read_text(encoding='utf-8-sig'))
            except FileNotFoundError:current={}
            updated=append_hook_config(current,command)
            backup.write(path,json.dumps(updated,ensure_ascii=False,indent=2))
        for skill,targets in [('context-bridge',[USER/'.codex/skills/context-bridge',USER/'.agents/skills/context-bridge']),
                              ('engineering-memory',[USER/'.codex/skills/engineering-memory',USER/'.agents/skills/engineering-memory',USER/'.claude/skills/engineering-memory'])]:
            for target in targets:
                for source in (ROOT/skill).rglob('*'):
                    if source.is_file() and '__pycache__' not in source.parts and source.suffix!='.pyc':backup.copy(source,target/source.relative_to(ROOT/skill))
        exe=str(PYTHON).replace("'","''");script=str(SERVICE/'app/listener.py').replace('"','`"')
        powershell("$a=New-ScheduledTaskAction -Execute '"+exe+"' -Argument '\""+script+"\" watch'; Set-ScheduledTask -TaskName 'EngineeringMemoryListener' -Action $a | Out-Null")
        # Rebuild the existing native index for the model identity change. This is a data migration, not a startup check.
        environment=os.environ.copy();environment.update(PYTHONUTF8='1',BASIC_MEMORY_AUTO_UPDATE='false',
            BASIC_MEMORY_SEMANTIC_EMBEDDING_MODEL=config['memory_embedding_model'],BASIC_MEMORY_SEMANTIC_EMBEDDING_PROVIDER='fastembed',
            BASIC_MEMORY_SEMANTIC_EMBEDDING_DIMENSIONS='384',BASIC_MEMORY_RERANKER_ENABLED='true',BASIC_MEMORY_RERANKER_MODEL=config['memory_reranker_model'],
            BASIC_MEMORY_SEMANTIC_EMBEDDING_CACHE_DIR=str(SERVICE/'models'),HF_HOME=str(SERVICE/'models/hf'))
        result=subprocess.run([str(PYTHON),'-c','from basic_memory.cli.main import app; app()','reindex','--project','main','--embeddings','--full'],timeout=1800,env=environment)
        if result.returncode:raise RuntimeError('Native multilingual index migration failed; deployment stays stopped for review')
        ownership.close()
        (SERVICE/'stop').unlink(missing_ok=True)
        powershell("Enable-ScheduledTask -TaskName 'EngineeringMemoryListener' | Out-Null; Start-ScheduledTask -TaskName 'EngineeringMemoryListener'")
        result={'status':'installed','backup':str(backup.folder),'task_previous_state':previous,'remaining':'Reconnect the existing Codex/Claude MCP connection, then run the frozen functional evaluations.'}
        (ROOT/'installation-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        return result
    except Exception:
        # Keep writer stopped. Restore is explicit because native index migration may already have begun.
        (backup.folder/'installation-failed.txt').write_text('Writer is stopped; inspect restore.json and restore original task XML before restarting.',encoding='utf-8')
        raise
    finally:
        ownership.close()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--restore');args=parser.parse_args()
    if args.restore:
        previous,ownership=quiesce()
        try:
            result=restore(args.restore)
            xml=Path(args.restore)/'scheduled-task.xml'
            if xml.is_file():
                path=str(xml).replace("'","''")
                powershell("Register-ScheduledTask -TaskName 'EngineeringMemoryListener' -Xml (Get-Content -LiteralPath '"+path+"' -Raw) -Force | Out-Null")
        finally:ownership.close()
        result['next']='Restore the original model index before restarting the listener; user memory sources are retained.'
    else:result=install()
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
