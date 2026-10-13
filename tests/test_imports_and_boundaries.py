from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from listener import Store
from history_import import import_document,import_git,enqueue
from memory_runtime import MemoryRuntime,markdown,ConflictError

class ImportsAndBoundaries(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT);self.root=Path(self.tmp.name)
        self.workspace=self.root/'workspace';self.workspace.mkdir()
        self.vault=self.root/'vault';self.vault.mkdir()
        self.store=Store(self.root/'service');self.memory=MemoryRuntime(self.vault,self.root/'memory.sqlite',use_models=False)
    def tearDown(self):self.store.db.close();self.memory.close();self.tmp.cleanup()
    def test_document_import_keeps_tail_batches_and_one_effect_per_revision(self):
        path=self.workspace/'decision.md';tail='最终约定：业务退款只能生效一次。'
        path.write_text(('较长历史说明。'*1500)+'\n\n'+tail,encoding='utf-8')
        count=import_document(self.store,path,self.workspace)
        self.assertGreater(count,1)
        self.assertEqual(import_document(self.store,path,self.workspace),0)
        rows=self.store.db.execute('SELECT payload FROM jobs').fetchall()
        self.assertTrue(any(tail in json.loads(r[0])['final'] for r in rows))
        self.assertTrue(all(json.loads(r[0])['cwd']==str(self.workspace) for r in rows))
    def test_document_cannot_import_outside_chosen_scope(self):
        path=self.root/'outside.md';path.write_text('其他项目资料',encoding='utf-8')
        with self.assertRaises(ValueError):import_document(self.store,path,self.workspace)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM jobs').fetchone()[0],0)
    def test_explicit_import_retry_rejects_changed_source_and_redacts_credentials(self):
        body='访问 api_key=super-secret-example，重复业务副作用必须幂等。'
        self.assertEqual(enqueue(self.store,'source',self.workspace,'revision',body,'2026-10-01','document'),1)
        self.assertEqual(enqueue(self.store,'source',self.workspace,'revision',body,'2026-10-01','document'),0)
        with self.assertRaises(ValueError):enqueue(self.store,'source',self.workspace,'revision','不同的内容','2026-10-01','document')
        payload=json.loads(self.store.db.execute('SELECT payload FROM jobs').fetchone()[0])
        self.assertNotIn('super-secret-example',payload['final'])
    def test_git_history_imports_actual_commit_messages_without_patches(self):
        subprocess.run(['git','init',str(self.workspace)],check=True,capture_output=True)
        (self.workspace/'file.txt').write_text('用户的文件资料',encoding='utf-8')
        subprocess.run(['git','-C',str(self.workspace),'add','file.txt'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(self.workspace),'-c','user.name=Memory Test','-c','user.email=memory-test@example.invalid','commit','-m','修复退款请求重复处理，业务副作用必须幂等'],check=True,capture_output=True)
        self.assertEqual(import_git(self.store,self.workspace),1)
        self.assertEqual(import_git(self.store,self.workspace),0)
        payload=json.loads(self.store.db.execute('SELECT payload FROM jobs').fetchone()[0])
        self.assertIn('业务副作用必须幂等',payload['final']);self.assertNotIn('用户的文件资料',payload['final'])
    def test_quote_backed_model_can_report_insufficient_evidence_for_overlapping_topic(self):
        (self.vault/'note.md').write_text(markdown({'title':'工程记忆','permalink':'main/rule'},'每小时最多2次模型调用'),encoding='utf-8')
        result=self.memory.reflect('工程记忆的护照号码',generator=lambda e:{'status':'insufficient_evidence','answer':'来源未记录护照号码。','citations':[],'support':[]})
        self.assertEqual(result['status'],'insufficient_evidence');self.assertEqual(result['citations'],[])
    def test_different_business_concepts_are_not_consolidated(self):
        for subject,event in [('扣款','one'),('退款','two')]:
            self.memory.retain(event,[{'subject':subject,'predicate':'金额','value':'每次10元','quote':'每次10元','source':'user'}],{'user':'每次10元','final':''})
        self.assertEqual({o['subject'] for o in self.memory.observations()},{'扣款','退款'})
    def test_multihop_retrieval_reaches_linked_evidence(self):
        for name,body in [('入口','业务解释见 [[中间]]。'),('中间','另见 [[证据]]。'),('证据','原因是事务边界。')]:
            (self.vault/(name+'.md')).write_text(markdown({'title':name,'permalink':'main/'+name},body),encoding='utf-8')
        found=self.memory.recall('业务解释',graph_hops=2)['results']
        self.assertIn('main/证据',[r['permalink'] for r in found])
    def test_graph_recall_can_follow_backlinks_to_parent_decision(self):
        for name,body in [('总体决策','整体设计依据见 [[事务]]。'),('事务','退款业务副作用仅发生一次。')]:
            (self.vault/(name+'.md')).write_text(markdown({'title':name,'permalink':'main/'+name},body),encoding='utf-8')
        found=self.memory.recall('退款')['results']
        self.assertIn('main/总体决策',[r['permalink'] for r in found])
    def test_malformed_local_fact_does_not_break_other_memory_recall(self):
        folder=self.vault/'engineering/memory-facts';folder.mkdir(parents=True)
        (folder/'malformed.md').write_text(markdown({'title':'损坏资料','memory_event':'bad','memory_payload':{'claims':'invalid','sources':{}}},'不完整的手工记录'),encoding='utf-8')
        (self.vault/'normal.md').write_text(markdown({'title':'退款','permalink':'main/normal'},'退款只发生一次'),encoding='utf-8')
        result=self.memory.recall('退款')
        self.assertEqual(result['results'][0]['permalink'],'main/normal')
