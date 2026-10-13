import json
from pathlib import Path
import tempfile
import unittest
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from listener import Store,Service
from memory_runtime import MemoryRuntime,markdown
from memory_integration import hook_context
from model_synthesis import reserve_call,BudgetExceeded
from mcp_proxy import Adapter

class Adapters(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT);self.root=Path(self.tmp.name)
        self.vault=self.root/'vault';self.vault.mkdir()
        self.memory=MemoryRuntime(self.vault,self.root/'state.sqlite',use_models=False)
        self.config={'vault':str(self.vault),'max_calls_per_day':8,'max_calls_per_hour':2,'max_tokens_per_day':60000,'reserve_tokens_per_call':12000}
    def tearDown(self):self.memory.close();self.tmp.cleanup()
    def test_model_reservations_share_existing_budget(self):
        reserve_call(self.memory.db,self.config);reserve_call(self.memory.db,self.config)
        with self.assertRaises(BudgetExceeded):reserve_call(self.memory.db,self.config)
        self.assertEqual(self.memory.db.execute('SELECT sum(tokens) FROM calls').fetchone()[0],24000)
    def test_proxy_keeps_native_tools_and_augments_only_matching_list_response(self):
        adapter=Adapter(self.memory,self.config,self.root)
        request={'jsonrpc':'2.0','id':1,'method':'tools/list'}
        self.assertIsNone(adapter.request(request))
        response={'jsonrpc':'2.0','id':1,'result':{'tools':[{'name':'read_note','inputSchema':{'type':'object'}}]}}
        result=adapter.response(response)
        self.assertEqual(result['result']['tools'][0],{'name':'read_note','inputSchema':{'type':'object'}})
        self.assertEqual({t['name'] for t in result['result']['tools']},{'read_note','memory_recall','memory_reflect','memory_knowledge_page'})
        self.assertIsNone(adapter.request({'method':'tools/call','id':2,'params':{'name':'read_note','arguments':{'identifier':'foo'}}}))
    def test_proxy_result_preserves_request_identity_and_citations(self):
        (self.vault/'rule.md').write_text(markdown({'title':'退款','permalink':'main/rule'},'退款必须幂等。'),encoding='utf-8')
        adapter=Adapter(self.memory,self.config,self.root)
        reply=adapter.request({'method':'tools/call','id':'request-abc','params':{'name':'memory_recall','arguments':{'query':'退款'}}})
        self.assertEqual(reply['id'],'request-abc');self.assertEqual(reply['result']['structuredContent']['result']['results'][0]['permalink'],'main/rule')
    def test_hook_refreshes_when_same_chat_moves_to_a_different_project(self):
        for name in ['a','b']:
            (self.vault/(name+'.md')).write_text(markdown({'title':name,'scope':'D:/'+name,'permalink':'main/'+name},name+'项目部署约定'),encoding='utf-8')
        first=hook_context(self.memory,{'session_id':'one','prompt':'部署约定','cwd':'D:/a'})
        second=hook_context(self.memory,{'session_id':'one','prompt':'部署约定','cwd':'D:/b'})
        self.assertIn('main/b',second.get('hookSpecificOutput',{}).get('additionalContext',''))
        self.assertNotIn('main/a',second.get('hookSpecificOutput',{}).get('additionalContext',''))
    def test_explicit_backfill_replays_old_log_without_resetting_live_cursor(self):
        store=Store(self.root/'service');log=self.root/'old.jsonl'
        events=[{'type':'response_item','payload':{'type':'message','role':'user','content':'以后必须先观察行为失败再实现修复，并记住这一约定。'}},
                {'type':'event_msg','timestamp':'2026-01-01T00:00:00Z','payload':{'type':'turn_complete','turn_id':'t','last_agent_message':'已记住行为测试先失败再通过的约定。'}}]
        log.write_text(''.join(json.dumps(e,ensure_ascii=False)+'\n' for e in events),encoding='utf-8')
        try:
            with store.db:store.db.execute('INSERT INTO meta VALUES(?,?)',('since','1790000000'))
            store.ingest(log,'codex',baseline=True)
            self.assertEqual(store.backfill(log,'codex'),1)
            self.assertEqual(store.backfill(log,'codex'),0)
            self.assertEqual(store.ingest(log,'codex'),0)
            self.assertEqual(store.db.execute('SELECT count(*) FROM jobs').fetchone()[0],1)
        finally:store.db.close()
