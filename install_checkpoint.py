"""Focused lifecycle deployment; no corpus backup, queue edits or model migration."""
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
from deployment import Backup,restore

ROOT=Path(__file__).resolve().parent
FILES=['checkpoint_lifecycle.py','memory_runtime.py','memory_integration.py','memory_cli.py','mcp_proxy.py','listener.py']


def deploy_files(service,user,backup_path):
    service,user=Path(service),Path(user)
    config=json.loads((service/'config.json').read_text(encoding='utf-8-sig'))
    model_root=Path(config['model_cache'])/'models--qdrant--paraphrase-multilingual-MiniLM-L12-v2-onnx-Q'
    tokenizer=next(iter(sorted(model_root.rglob('tokenizer.json'))),None)
    if tokenizer is None:raise ValueError('Configured multilingual tokenizer is unavailable; no files changed')
    targets=[user/'.codex/skills/context-bridge',user/'.agents/skills/context-bridge']
    memories=[user/'.codex/skills/engineering-memory',user/'.agents/skills/engineering-memory',user/'.claude/skills/engineering-memory']
    backup=Backup(backup_path,[service,*targets,*memories])
    try:
        for filename in FILES:backup.copy(ROOT/'app'/filename,service/'app'/filename)
        config.update(checkpoint_lifecycle_enabled=True,checkpoint_tokenizer=str(tokenizer))
        config.setdefault('checkpoint_fast_quarantine_minutes',60)
        backup.write(service/'config.json',json.dumps(config,ensure_ascii=False,indent=2))
        guide=ROOT/'context-bridge/references/checkpoint-lifecycle.md'
        for target in targets+memories:
            backup.copy(guide,target/'references/checkpoint-lifecycle.md')
            # Merge only the new route into the currently installed skill.
            skill=target/'SKILL.md'
            if skill.exists():
                text=skill.read_text(encoding='utf-8-sig')
                if '(references/checkpoint-lifecycle.md)' not in text:
                    backup.write(skill,text.rstrip()+'\n\nBasic Memory checkpoint 原件的摘要、隔离、恢复与到期删除，读取 [checkpoint 生命周期](references/checkpoint-lifecycle.md)。\n')
        return {'status':'files_deployed','backup':str(backup.folder),'tokenizer':str(tokenizer),
            'fast_quarantine_minutes':config['checkpoint_fast_quarantine_minutes'],'queue_changed':False}
    except Exception:
        restore(backup.folder)
        raise


def main():
    from install import SERVICE,USER,quiesce,powershell
    previous,ownership=quiesce()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    try:
        result=deploy_files(SERVICE,USER,ROOT/('checkpoint-deploy-backup-'+stamp))
        result['previous_task_state']=previous
    finally:
        ownership.close()
        if previous!='Disabled':
            (SERVICE/'stop').unlink(missing_ok=True)
            powershell("Enable-ScheduledTask -TaskName 'EngineeringMemoryListener' | Out-Null; Start-ScheduledTask -TaskName 'EngineeringMemoryListener'")
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
