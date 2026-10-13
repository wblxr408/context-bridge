import json
from datetime import datetime,timezone,timedelta
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'context-bridge/scripts'))
import retention

class Retention(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT);self.base=Path(self.tmp.name);self.root=self.base/'checkpoints';self.root.mkdir()
        self.now=datetime(2026,10,12,tzinfo=timezone.utc)
        rows=[]
        for n,date in [(1,'2026-09-01T00:00:00+00:00'),(2,'2026-10-01T00:00:00+00:00')]:
            name='cp-'+str(n);p=self.root/name;p.mkdir();(p/'source.md').write_text('按最新要求继续任务。',encoding='utf-8')
            ledger={'schema':1,'task_id':'task','snapshot_id':'task/revision-'+str(n),'requirements':[{'id':'R001','revision':1,'status':'active','kind':'goal','scope':'global','always_load':True,'statement':'按最新要求继续任务。','acceptance':'完成任务','progress':'pending','evidence':[],'source':{'path':'source.md','quote':'按最新要求继续任务。','locator':'原请求'}}]}
            (p/'requirements.json').write_text(json.dumps(ledger,ensure_ascii=False),encoding='utf-8')
            rows.append({'id':name,'snapshot_id':ledger['snapshot_id'],'created_utc':date,'lifecycle':'retired' if n==1 else 'received','pinned':False,'in_use':n==2,'self_contained':True,'depends_on':[],'no_readers_confirmed':True,**({'superseded_by':'cp-2'} if n==1 else {})})
        self.registration={'schema':2,'revision':1,'task_id':'task','current':'cp-2','last_received':'cp-2','policy':{'keep_last':1},'items':rows}
        self.save()
    def save(self): (self.root/retention.INDEX).write_text(json.dumps(self.registration),encoding='utf-8')
    def tearDown(self):self.tmp.cleanup()
    def test_two_phase_cleanup_preserves_current_and_unregistered_data(self):
        extra=self.root/'unregistered';extra.mkdir();(extra/'user.md').write_text('用户资料',encoding='utf-8')
        plan=retention.make_plan(self.root,self.now)
        self.assertEqual([a['id'] for a in plan['actions']],['cp-1'])
        path=self.base/'plan.json';path.write_text(json.dumps(plan),encoding='utf-8')
        result=retention.apply_plan(self.root,path,plan['plan_id'],self.now)
        self.assertEqual(result['completed'],[{'id':'cp-1','action':'quarantine'}])
        self.assertEqual(retention.make_plan(self.root,self.now)['actions'],[])
        later=retention.make_plan(self.root,self.now+timedelta(days=8));path.write_text(json.dumps(later),encoding='utf-8')
        retention.apply_plan(self.root,path,later['plan_id'],self.now+timedelta(days=8))
        self.assertEqual((extra/'user.md').read_text(encoding='utf-8'),'用户资料')
        self.assertEqual(json.loads((self.root/retention.INDEX).read_text())['items'][0]['lifecycle'],'deleted')
    def test_pinned_and_dependency_blocks_cleanup(self):
        self.registration['items'][1]['depends_on']=['cp-1'];self.save()
        self.assertEqual(retention.make_plan(self.root,self.now)['actions'],[])
    def test_registration_changed_after_plan_rejects_action(self):
        plan=retention.make_plan(self.root,self.now);path=self.base/'plan.json';path.write_text(json.dumps(plan),encoding='utf-8')
        self.registration['items'][0]['in_use']=True;self.save()
        with self.assertRaises(ValueError):retention.apply_plan(self.root,path,plan['plan_id'],self.now)
        self.assertEqual(json.loads((self.root/retention.INDEX).read_text())['items'][0]['lifecycle'],'retired')
    def test_unknown_snapshot_is_preserved_and_reported(self):
        self.registration['items'][0]['snapshot_id']='task/wrong';self.save()
        plan=retention.make_plan(self.root,self.now)
        self.assertEqual(plan['actions'],[]);self.assertTrue(plan['warnings'])
