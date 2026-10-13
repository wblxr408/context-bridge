import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from memory_runtime import MemoryRuntime, markdown
from memory_integration import hook_context


class HistoryIsolation(unittest.TestCase):
    def test_native_context_filters_history_and_exact_retired_cursor_is_recoverable(self):
        from mcp_proxy import Adapter
        from checkpoint_lifecycle import Lifecycle
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            home=Path(tmp);vault=home/'vault';vault.mkdir()
            (vault/'history.md').write_text(markdown({'title':'历史故障','type':'checkpoint_history',
                'permalink':'main/history'},'已经完成的旧工作'),encoding='utf-8')
            memory=MemoryRuntime(vault,home/'state.sqlite',use_models=False)
            try:
                adapter=Adapter(memory,{'vault':str(vault)},home)
                request={'id':7,'method':'tools/call','params':{'name':'build_context',
                    'arguments':{'project':'main','url':'memory://main/*'}}}
                adapter.request(request)
                response=adapter.response({'id':7,'result':{'structuredContent':{'result':{'results':[
                    {'primary_result':{'permalink':'main/history','content':'已经完成的旧工作'},'observations':[{'content':'旧秘密'}]},
                    {'primary_result':{'permalink':'main/current','content':'今天的要求'}}]}}}})
                rows=response['result']['structuredContent']['result']['results']
                self.assertEqual(len(rows),1)
                self.assertEqual(rows[0]['primary_result']['content'],'今天的要求')
            finally:memory.close()

    def test_history_is_explicit_only_in_recall_and_prompt_hooks(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            root = Path(tmp); vault = root / 'vault'; vault.mkdir()
            (vault / 'old.md').write_text(markdown({'title': '旧故障历史',
                'permalink': 'main/old', 'type': 'checkpoint_history',
                'historical': True, 'auto_inject': False}, '紫色数据库连接曾经失败，后来已经解决。'), encoding='utf-8')
            memory = MemoryRuntime(vault, root / 'state.sqlite', use_models=False)
            try:
                self.assertEqual(memory.recall('紫色数据库', mode='text')['results'], [])
                self.assertEqual(hook_context(memory, {'session_id': 's', 'prompt': '紫色数据库',
                    'hook_event_name': 'UserPromptSubmit'}), {})
                self.assertEqual(memory.recall('紫色数据库', include_history=True,
                    mode='text')['results'][0]['permalink'], 'main/old')
            finally:
                memory.close()

    def test_lifecycle_plan_reports_empty_vault_without_removing_other_notes(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            root=Path(tmp); vault=root/'vault'; vault.mkdir()
            (vault/'policy.md').write_text('# Durable engineering policy', encoding='utf-8')
            (root/'config.json').write_text(json.dumps({'vault':str(vault)}), encoding='utf-8')
            result=subprocess.run([sys.executable,str(ROOT/'app/memory_cli.py'),
                'checkpoint-plan','--home',str(root)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['total'],0)
            self.assertEqual((vault/'policy.md').read_text(), '# Durable engineering policy')


class LifecycleBehavior(unittest.TestCase):
    def setUp(self):
        from checkpoint_lifecycle import Lifecycle
        self.temp=tempfile.TemporaryDirectory(dir=ROOT)
        self.root=Path(self.temp.name); self.vault=self.root/'vault'; self.vault.mkdir()
        self.clock=[2000000000.0]
        self.engine=Lifecycle(self.vault,self.root/'service',counter=lambda text:len(text.split()),
            clock=lambda:self.clock[0], native_sync=lambda:None)
        for i in range(5):
            self.note(f'n{i}',i)

    def note(self,name,order,**fields):
        meta={'title':name,'permalink':'main/'+name,'type':'codex_session','agent':'codex',
            'session_id':'s','cwd':'D:/a','status':'open','started':f'2020-01-{order+1:02d}T00:00:00Z'}
        meta.update(fields)
        (self.vault/(name+'.md')).write_text(markdown(meta,'退款失败后已修复，仍需验收供应商响应。'),encoding='utf-8')

    def review(self):
        return {'main/'+f'n{i}':{'coverage':'原件目标、结果及未完成验收均保留在摘要和最新恢复点',
            'no_readers_confirmed':True,'reader_evidence':'Isolated fixture; this test owns all consumers'} for i in range(4)}

    def draft(self,plan,body='退款失败已修复；供应商响应验收未完成。'):
        return {g:{'body':body,'reviewed':True,'short_history_reason':'短任务事实有限',
            'sources':[r['permalink'] for r in plan['candidates'] if r['group']==g]}
            for g in {r['group'] for r in plan['candidates']}}

    def tearDown(self):self.temp.cleanup()

    def test_quarantine_hides_originals_restore_pins_and_expiry_returns_tombstone(self):
        plan=self.engine.plan(review=self.review(),lane='fast')
        self.assertEqual(len(plan['candidates']),4)
        result=self.engine.apply(plan,self.draft(plan))
        self.assertEqual(result['quarantined'],4)
        memory=MemoryRuntime(self.vault,self.root/'service/state.sqlite',use_models=False)
        try:
            self.assertEqual([r['permalink'] for r in memory.recall('退款失败',mode='text')['results']],['main/n4'])
            self.assertEqual(len(memory.recall('退款失败',include_history=True,mode='text')['results']),2)
            self.assertEqual(memory.recall('退款失败',include_history=True,mode='text',scope='D:/other')['results'],[])
        finally:memory.close()
        self.assertIn('退款失败',self.engine.read('main/n0')['content'])
        self.engine.restore('main/n0')
        self.assertTrue(self.engine.read('main/n0')['pinned'])
        self.clock[0]+=59*60
        self.assertEqual(self.engine.purge()['purged'],0)
        self.clock[0]+=60
        self.assertEqual(self.engine.purge()['purged'],3)
        self.assertEqual(self.engine.read('main/n1')['state'],'purged')
        self.assertIn('history',self.engine.read('main/n1')['summary'])
        self.assertEqual(self.engine.purge()['purged'],0)

    def test_invalid_summary_and_stale_protection_leave_original_recoverable(self):
        plan=self.engine.plan(review=self.review(),lane='fast')
        with self.assertRaises(ValueError):self.engine.apply(plan,self.draft(plan,'word '*2100))
        self.assertIn('退款失败',(self.vault/'n0.md').read_text(encoding='utf-8'))
        self.note('n0',0,pinned=True)
        with self.assertRaises(ValueError):self.engine.apply(plan,self.draft(plan))
        self.assertIn('退款失败',(self.vault/'n1.md').read_text(encoding='utf-8'))

    def test_unknown_active_pinned_and_dependencies_are_protected(self):
        self.note('n0',0,pinned=True)
        self.note('n1',1,in_use=True)
        self.note('unknown',6,session_id='')
        self.note('dependent',7,session_id='other',depends_on=['main/n2'])
        plan=self.engine.plan(review=self.review(),lane='fast')
        self.assertEqual([r['permalink'] for r in plan['candidates']],['main/n3'])
        active=self.engine.plan(review=self.review(),active_sessions=['s'],lane='fast')
        self.assertEqual(active['candidates'],[])

    def test_restore_conflict_and_replayed_apply_do_not_erase_new_data(self):
        plan=self.engine.plan(review=self.review(),lane='fast');draft=self.draft(plan)
        self.engine.apply(plan,draft)
        self.assertEqual(self.engine.apply(plan,draft)['quarantined'],4)
        (self.vault/'n0.md').write_text('new independent note',encoding='utf-8')
        with self.assertRaises(ValueError):self.engine.restore('main/n0')
        self.assertEqual((self.vault/'n0.md').read_text(),'new independent note')
        self.assertEqual(self.engine.read('main/n0')['state'],'quarantined')

    def test_ordinary_waits_72_hours_and_fails_closed_if_summary_changed(self):
        plan=self.engine.plan(review=self.review(),lane='ordinary')
        self.engine.apply(plan,self.draft(plan))
        self.clock[0]+=71*3600
        self.assertEqual(self.engine.purge()['purged'],0)
        self.clock[0]+=3600
        self.assertEqual(self.engine.purge()['purged'],4)

    def test_changed_summary_prevents_expiry_and_unsafe_path_is_rejected(self):
        plan=self.engine.plan(review=self.review(),lane='fast')
        bad=json.loads(json.dumps(plan));bad['candidates'][0]['path']='../outside.md'
        with self.assertRaises(ValueError):self.engine.apply(bad,self.draft(bad))
        self.engine.apply(plan,self.draft(plan))
        summary=self.engine.read('main/n0')['summary_path']
        (self.vault/summary).write_text('unreviewed replacement',encoding='utf-8')
        self.clock[0]+=3600
        self.assertEqual(self.engine.purge()['purged'],0)
        self.assertEqual(self.engine.read('main/n0')['state'],'quarantined')

    def test_restart_after_rename_completes_once_and_native_failure_prevents_purge(self):
        from unittest.mock import patch
        from checkpoint_lifecycle import Lifecycle
        plan=self.engine.plan(review=self.review(),lane='fast')
        real=Path.rename
        calls=[]
        def interrupted(path,target):
            result=real(path,target);calls.append(str(path))
            if len(calls)==1:raise RuntimeError('simulated process death after rename')
            return result
        with patch.object(Path,'rename',interrupted):
            with self.assertRaises(RuntimeError):self.engine.apply(plan,self.draft(plan))
        self.engine.purge()
        self.assertIn('退款失败',self.engine.read('main/n0')['content'])
        # Recovery must report partial operation instead of claiming the whole plan applied.
        self.assertEqual(self.engine.apply(plan,self.draft(plan))['quarantined'],1)
        self.assertIn('退款失败',(self.vault/'n1.md').read_text(encoding='utf-8'))

    def test_count_lane_keeps_three_after_task_exceeds_eight(self):
        for i in range(5,9):self.note(f'n{i}',i)
        review={'main/n'+str(i):{'coverage':'Reviewed historical failure and latest pending validation',
            'no_readers_confirmed':True,'reader_evidence':'Isolated fixture'} for i in range(9)}
        plan=self.engine.plan(review=review,lane='count',fraction=1)
        self.assertEqual([r['permalink'] for r in plan['candidates']],['main/n'+str(i) for i in range(6)])

    def test_purge_waits_for_successful_native_retirement(self):
        plan=self.engine.plan(review=self.review(),lane='fast')
        def fail():raise RuntimeError('native index unavailable')
        self.engine.native_sync=fail
        with self.assertRaises(RuntimeError):self.engine.apply(plan,self.draft(plan))
        self.clock[0]+=3600
        with self.assertRaises(RuntimeError):self.engine.purge()
        self.assertIn('退款失败',self.engine.read('main/n0')['content'])
        self.engine.native_sync=lambda:None
        self.assertEqual(self.engine.purge()['purged'],4)

    def test_existing_listener_finishes_due_quarantine_without_selecting_new_sources(self):
        import time
        from unittest.mock import patch
        from listener import Service
        self.clock[0]=time.time()-4000
        plan=self.engine.plan(review=self.review(),lane='fast')
        self.engine.apply(plan,self.draft(plan))
        config={'vault':str(self.vault),'sources':[],'memory_models':False,
            'reconcile_seconds':300,'checkpoint_lifecycle_enabled':True}
        service=Service(self.root/'service',config)
        try:
            service.wake.set()
            with patch.object(service,'process_one',side_effect=lambda:(service.home/'stop').touch()):
                service.run()
            self.assertEqual(self.engine.read('main/n0')['state'],'purged')
            self.assertIn('退款失败',(self.vault/'n4.md').read_text(encoding='utf-8'))
        finally:
            service.memory.close();service.store.db.close()

    def test_coverage_alone_does_not_imply_readers_have_stopped(self):
        review={pid:{'coverage':entry['coverage']} for pid,entry in self.review().items()}
        self.assertEqual(self.engine.plan(review=review,lane='fast')['candidates'],[])

    def test_real_multilingual_tokenizer_rejects_long_chinese_summary_without_truncating(self):
        self.engine.counter=None
        self.engine.tokenizer=next((ROOT/'models/models--qdrant--paraphrase-multilingual-MiniLM-L12-v2-onnx-Q').rglob('tokenizer.json'))
        plan=self.engine.plan(review=self.review(),lane='fast')
        with self.assertRaisesRegex(ValueError,'tokenizer budget'):
            self.engine.apply(plan,self.draft(plan,'处理退款。'*1000))
        self.assertIn('退款失败',(self.vault/'n0.md').read_text(encoding='utf-8'))
        result=self.engine.apply(plan,self.draft(plan))
        self.assertEqual(result['quarantined'],4)

    def test_summary_revision_preserves_prior_history_without_blocking_existing_expiry(self):
        from checkpoint_lifecycle import version
        first=self.engine.plan(review=self.review(),lane='fast',fraction=.2)
        self.engine.apply(first,self.draft(first))
        self.clock[0]+=1800
        second=self.engine.plan(review=self.review(),lane='fast',fraction=.5)
        drafts=self.draft(second)
        old=self.engine.read('main/n0')
        for draft in drafts.values():draft['previous_version']=version(self.vault/old['summary_path'])
        self.engine.apply(second,drafts)
        self.clock[0]+=1800
        self.assertEqual(self.engine.purge()['purged'],1)
        self.clock[0]+=1800
        final=self.engine.purge()
        self.assertEqual(final['purged'],2)
        self.assertEqual(final['purged_summaries'],1)

    def test_restart_after_summary_publication_keeps_earlier_expiry_and_preserves_sources(self):
        from checkpoint_lifecycle import version
        from unittest.mock import patch
        import checkpoint_lifecycle
        first=self.engine.plan(review=self.review(),lane='fast',fraction=.2)
        self.engine.apply(first,self.draft(first))
        self.clock[0]+=1800
        second=self.engine.plan(review=self.review(),lane='fast',fraction=.5)
        drafts=self.draft(second)
        old=self.engine.read('main/n0')
        for draft in drafts.values():
            draft['previous_version']=version(self.vault/old['summary_path'])
            draft['body']+=' New reviewed failure: delivery cancellation remains pending.'
        real=checkpoint_lifecycle.atomic_text
        def interrupted(path,text):
            real(path,text)
            if path==self.vault/old['summary_path']:raise RuntimeError('process death after summary publication')
        with patch.object(checkpoint_lifecycle,'atomic_text',interrupted):
            with self.assertRaises(RuntimeError):self.engine.apply(second,drafts)
        self.clock[0]+=1800
        self.assertEqual(self.engine.purge()['purged'],1)
        self.assertIn('delivery cancellation',(self.vault/old['summary_path']).read_text(encoding='utf-8'))
        self.assertIn('退款失败',(self.vault/'n1.md').read_text(encoding='utf-8'))
        self.assertEqual(self.engine.read('main/n0')['state'],'purged')
