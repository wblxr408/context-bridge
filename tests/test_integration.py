import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
from memory_runtime import MemoryRuntime, markdown
from memory_integration import dispatch, hook_context, capture_claims, append_hook_config
import listener

class Integration(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT)
        self.root=Path(self.temp.name)
        self.vault=self.root/'vault'; self.vault.mkdir()
        self.memory=MemoryRuntime(self.vault,self.root/'state.sqlite',use_models=False)
        (self.vault/'lesson.md').write_text(markdown({'title':'业务重试','permalink':'main/lesson','scope':'global'},'支付请求可以重复传输，退款必须幂等，不允许重复扣款。'),encoding='utf-8')
    def tearDown(self):
        self.memory.close(); self.temp.cleanup()
    def test_native_search_returns_cited_results_and_other_projects_delegate(self):
        result=dispatch(self.memory,'search_notes',{'project':'main','query':'多次扣款怎么办','search_type':'hybrid'})
        self.assertEqual(result['structuredContent']['result']['results'][0]['permalink'],'main/lesson')
        self.assertIsNone(dispatch(self.memory,'search_notes',{'project':'other','query':'退款'}))
        self.assertIsNone(dispatch(self.memory,'search_notes',{'project_id':'unknown','query':'退款'}))
    def test_unsupported_native_filter_contract_is_not_silently_changed(self):
        self.assertIsNone(dispatch(self.memory,'search_notes',{'project':'main','query':'退款','entity_types':['relation']}))
    def test_hook_emits_scoped_data_once_and_does_not_obey_memory_instructions(self):
        payload={'session_id':'s1','prompt':'重复退款怎么办','cwd':'D:/project-a','hook_event_name':'UserPromptSubmit'}
        first=hook_context(self.memory,payload)
        self.assertIn('main/lesson',first['hookSpecificOutput']['additionalContext'])
        self.assertEqual(hook_context(self.memory,payload),{})
        self.assertIn('历史资料',first['hookSpecificOutput']['additionalContext'])
    def test_hook_settings_preserve_existing_commands_and_reinstall_deduplicates(self):
        original={'hooks':{'SessionStart':[{'hooks':[{'type':'command','command':'existing'}]}]},'other':42}
        one=append_hook_config(original,'memory-command')
        two=append_hook_config(one,'memory-command')
        self.assertEqual(two,one)
        self.assertEqual(two['hooks']['SessionStart'],original['hooks']['SessionStart'])
        self.assertEqual(two['other'],42)
    def test_capture_uses_original_evidence_and_cwd_as_scope(self):
        quote='以后退款业务副作用必须只发生一次。'
        payload={'user':quote,'final':'已记录。','cwd':'D:/project-a'}
        notes=[{'title':'重试','scope':'支付','lesson':'退款仅一次','kind':'preference','subject':'退款','predicate':'重试副作用','value':'仅一次','evidence':[{'source':'user','quote':quote}]}]
        capture_claims(self.memory,'ev',payload,notes)
        self.assertEqual(self.memory.observations('D:/project-a')[0]['current'],'仅一次')
        self.assertEqual(self.memory.observations('D:/project-b'),[])
    def test_history_ingestion_resumes_partial_lines_and_retries_once_effect(self):
        log=self.root/'history.jsonl'
        events=[{'type':'session_meta','payload':{'id':'s','cwd':'D:/project-a'}},
                {'type':'response_item','payload':{'type':'message','role':'user','content':'以后必须先写行为测试再实现，并记住这个约定。'}},
                {'type':'event_msg','payload':{'type':'turn_complete','turn_id':'t','last_agent_message':'已采用行为测试先失败再实现的约定，避免只验证程序启动。'}}]
        raw='\n'.join(json.dumps(e,ensure_ascii=False) for e in events)
        store=listener.Store(self.root/'service')
        try:
            log.write_text(raw,encoding='utf-8')
            self.assertEqual(store.ingest(log,'codex'),0)
            with log.open('a',encoding='utf-8') as stream: stream.write('\n')
            self.assertEqual(store.ingest(log,'codex'),1)
            self.assertEqual(store.ingest(log,'codex'),0)
            self.assertEqual(store.db.execute('SELECT count(*) FROM jobs').fetchone()[0],1)
        finally:
            store.db.close()

if __name__=='__main__': unittest.main()
