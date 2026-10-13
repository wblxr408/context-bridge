"""Execute the installed 30-second native hook and verify duplicate suppression."""
import json
import os
from pathlib import Path
import subprocess
import uuid
from accept_installed import QUERY

ROOT=Path(__file__).parent
user=Path.home();service=user/'.codex/services/engineering-memory'
env=os.environ.copy();env.update(PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
report={}
for label,path in [('Codex',user/'.codex/hooks.json'),('Claude',user/'.claude/settings.json')]:
    settings=json.loads(path.read_text(encoding='utf-8'))
    command=next(h['command'] for entry in settings['hooks']['UserPromptSubmit'] for h in entry['hooks']
                 if str(service/'app/memory_cli.py') in h.get('command',''))
    payload={'session_id':'installed-acceptance-'+uuid.uuid4().hex,'cwd':str(ROOT),'prompt':QUERY,
             'hook_event_name':'UserPromptSubmit'}
    results=[]
    for repeat in (False,True):
        result=subprocess.run(command,input=json.dumps(payload,ensure_ascii=False).encode('utf-8'),
                              capture_output=True,timeout=30,env=env)
        assert result.returncode==0,result.stderr.decode('utf-8',errors='replace')
        output=json.loads(result.stdout)
        if repeat:assert output=={},'Same chat must not receive identical history twice'
        else:assert output['hookSpecificOutput']['additionalContext'] and len(output['hookSpecificOutput']['additionalContext'])<=6000
        results.append(output)
    report[label]={'status':'passed','results':results}
    print(json.dumps({'client':label,'status':'passed','contract':'30-second real prompt hook returns context and suppresses identical replay'}),flush=True)
(ROOT/'evaluation-installed-hook.json').write_text(json.dumps({'status':'passed','clients':report},ensure_ascii=False,indent=2),encoding='utf-8')
