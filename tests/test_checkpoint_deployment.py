import json
from pathlib import Path
import sqlite3
import shutil
import subprocess
import sys
import tempfile
import unittest
from test_mcp_e2e import ROOT
sys.path.insert(0,str(ROOT))


class CheckpointDeployment(unittest.TestCase):
    def test_deployed_cli_protects_recovery_and_does_not_trim_job_queue(self):
        from install_checkpoint import deploy_files
        from memory_runtime import markdown
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root=Path(temp);service=root/'service';service.mkdir();vault=root/'vault';vault.mkdir()
            user=root/'user'
            config={'vault':str(vault),'max_calls_per_day':8,'model_cache':str(ROOT/'models')}
            shutil.copytree(ROOT/'app',service/'app',ignore=shutil.ignore_patterns('__pycache__'))
            (service/'config.json').write_text(json.dumps(config),encoding='utf-8')
            db=sqlite3.connect(service/'state.sqlite')
            try:
                db.execute('CREATE TABLE jobs(id TEXT PRIMARY KEY,state TEXT)')
                db.executemany('INSERT INTO jobs VALUES(?,?)',[('one','queued'),('two','retry')]);db.commit()
                for i in range(2):
                    (vault/f'n{i}.md').write_text(markdown({'type':'codex_session','title':str(i),
                        'permalink':'main/'+str(i),'agent':'codex','session_id':'s','cwd':'D:/a',
                        'started':f'2020-01-0{i+1}T00:00:00Z'},'待处理业务'),encoding='utf-8')
                review=root/'review.json';review.write_text(json.dumps({'main/0':{'coverage':'历史已纳入摘要',
                    'no_readers_confirmed':True,'reader_evidence':'Isolated deployment fixture'}}),encoding='utf-8')
                deploy_files(service,user,root/'backup')
                command=[sys.executable,str(service/'app/memory_cli.py'),'checkpoint-plan','--home',str(service),
                    '--review',str(review),'--lane','fast']
                result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8')
                self.assertEqual(result.returncode,0,result.stderr)
                plan=json.loads(result.stdout)
                self.assertEqual([r['permalink'] for r in plan['candidates']],['main/0'])
                self.assertIn('main/1',plan['protected'])
                self.assertEqual(db.execute('SELECT id,state FROM jobs ORDER BY id').fetchall(),[('one','queued'),('two','retry')])
                self.assertEqual(json.loads((service/'config.json').read_text())['max_calls_per_day'],8)
            finally:db.close()
