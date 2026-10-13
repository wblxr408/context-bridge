"""Explicit failure recovery keeps the original business event and quota history."""
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
from listener import Store

class JobRecovery(unittest.TestCase):
    def test_selected_failed_event_can_be_retried_through_the_user_cli(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            home=Path(temp);(home/'config.json').write_text('{}',encoding='utf-8')
            store=Store(home)
            try:
                with store.db:
                    store.db.execute('INSERT INTO jobs(id,source,payload,state,created,available,attempts,error) VALUES(?,?,?,?,?,?,?,?)',
                        ('selected-event','original-log','{}','failed',1,1,3,'Judge timed out'))
                result=subprocess.run([sys.executable,str(ROOT/'app/memory_cli.py'),'retry-failed',
                     '--home',str(home),'--job','selected-event','--reason','model route fixed'],capture_output=True,timeout=10)
                self.assertEqual(result.returncode,0,'Selected recoverable event must return to the existing queue through the supported CLI')
                self.assertEqual(json.loads(result.stdout)['requeued'],1)
                self.assertEqual(store.db.execute('SELECT state FROM jobs WHERE id=?',('selected-event',)).fetchone()[0],'queued')
            finally:store.db.close()
    def test_explicit_retry_preserves_event_and_audits_failure_without_resetting_budget(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            store=Store(temp)
            try:
                payload=json.dumps({'user':'共享每小时最多2次额度','final':'已记住'})
                with store.db:
                    store.db.execute('INSERT INTO jobs(id,source,payload,state,created,available,attempts,error) VALUES(?,?,?,?,?,?,?,?)',
                         ('event-1','original-log',payload,'failed',1,1,3,'Judge timed out'))
                    store.db.execute('INSERT INTO calls(started,tokens) VALUES(?,?)',(10,12000))
                self.assertEqual(store.retry_jobs(['event-1'],'模型执行路径已经修复'),1)
                row=store.db.execute('SELECT * FROM jobs WHERE id=?',('event-1',)).fetchone()
                self.assertEqual((row['payload'],row['state'],row['attempts']),(payload,'queued',0))
                self.assertEqual(store.db.execute('SELECT started,tokens FROM calls').fetchall()[0][:],(10,12000))
                audit=store.db.execute('SELECT prior_state,prior_attempts,prior_error FROM job_recoveries').fetchone()
                self.assertEqual(tuple(audit),('failed',3,'Judge timed out'))
                self.assertEqual(store.retry_jobs(['event-1'],'重复恢复操作'),0)
                self.assertEqual(store.db.execute('SELECT count(*) FROM job_recoveries').fetchone()[0],1)
            finally:store.db.close()
    def test_saved_event_is_unchanged_and_missing_selection_is_rejected_atomically(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            store=Store(temp)
            try:
                with store.db:
                    for identity,state in [('saved-1','saved'),('failed-1','failed')]:
                        store.db.execute('INSERT INTO jobs(id,source,payload,state,created,available) VALUES(?,?,?,?,?,?)',
                               (identity,'source','{}',state,1,1))
                self.assertEqual(store.retry_jobs(['saved-1'],'保留已经保存的效果'),0)
                with self.assertRaises(ValueError):store.retry_jobs(['failed-1','unknown'],'不得恢复错误目标')
                self.assertEqual(store.db.execute('SELECT state FROM jobs WHERE id=?',('failed-1',)).fetchone()[0],'failed')
            finally:store.db.close()
