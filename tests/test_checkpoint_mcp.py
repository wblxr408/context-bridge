"""Actual Basic Memory writes, index retirement and exact recovery over stdio."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from test_mcp_e2e import ROOT,StdioClient,value
from checkpoint_lifecycle import Lifecycle


class CheckpointMcp(unittest.TestCase):
    def test_native_quarantine_history_context_restore_and_expired_cursor(self):
        with tempfile.TemporaryDirectory(prefix='checkpoint-mcp-',dir=ROOT) as temp:
            home=Path(temp);vault=home/'vault';vault.mkdir();native=home/'native';native.mkdir()
            config={'vault':str(vault),'memory_models':os.environ.get('MEMORY_E2E_MODELS')=='true',
                'model_cache':str(ROOT/'models')}
            (home/'config.json').write_text(json.dumps(config),encoding='utf-8')
            (native/'config.json').write_text(json.dumps({'projects':{'main':{'path':str(vault)}},
                'default_project':'main','semantic_search_enabled':True,'sync_changes':True,
                'semantic_embedding_threads':2,'semantic_embedding_parallel':1,
                'semantic_embedding_model':'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                'semantic_embedding_provider':'fastembed','semantic_embedding_dimensions':384,
                'semantic_embedding_cache_dir':str(ROOT/'models'),
                'logfire_enabled':False,'logfire_send_to_logfire':False}),encoding='utf-8')
            env=os.environ.copy();env.update(ENGINEERING_MEMORY_HOME=str(home),BASIC_MEMORY_CONFIG_DIR=str(native),
                PYTHONUTF8='1',PYTHONIOENCODING='utf-8',BASIC_MEMORY_AUTO_UPDATE='false')
            client=StdioClient([sys.executable,str(ROOT/'app/mcp_proxy.py')],env,home/'protocol.log')
            try:
                client.call('initialize',{'protocolVersion':'2025-11-25','capabilities':{},
                    'clientInfo':{'name':'checkpoint-functional','version':'1'}})
                client.send('notifications/initialized',notification=True)
                for i in range(3):
                    client.tool('write_note',{'project':'main','directory':'codex','title':'生命周期试验'+str(i),
                        'note_type':'codex_session','overwrite':False,'metadata':{'agent':'codex','session_id':'trial',
                            'cwd':'D:/trial','started':f'2020-01-0{i+1}T00:00:00Z','status':'open'},
                        'content':'供应商重试失败，已解决协议冲突；账单验收仍待完成。'})
                    read=value(client.tool('read_note',{'project':'main','identifier':'生命周期试验'+str(i),'output_format':'json'}))
                    self.assertIn('账单验收',read['content'])
                clock=[2000000000.]
                engine=Lifecycle(vault,home,counter=lambda s:len(s.split()),clock=lambda:clock[0])
                notes=sorted(engine.inventory(),key=lambda n:n['stamp'])
                self.assertEqual(len(notes),3)
                review={n['permalink']:{'coverage':'失败已解决，账单仍待验收；最新点保留',
                    'no_readers_confirmed':True,'reader_evidence':'This fixture owns the MCP clients'} for n in notes}
                plan=engine.plan(review=review,lane='fast')
                group=plan['candidates'][0]['group'];pid=plan['candidates'][0]['permalink']
                draft={group:{'reviewed':True,'body':'供应商重试故障已解决，账单验收仍待完成。',
                    'short_history_reason':'三个相同业务快照','sources':[r['permalink'] for r in plan['candidates']]}}
                with patch.dict(os.environ,env,clear=True):engine.apply(plan,draft)
                direct=StdioClient([sys.executable,'-c','from basic_memory.cli.main import app; app()','mcp'],
                    env,home/'native-direct.log')
                try:
                    direct.call('initialize',{'protocolVersion':'2025-11-25','capabilities':{},
                        'clientInfo':{'name':'retired-index-consumer','version':'1'}})
                    direct.send('notifications/initialized',notification=True)
                    indexed=value(direct.tool('search_notes',{'project':'main','query':'生命周期试验',
                        'note_types':['codex_session'],'search_type':'text','output_format':'json'}))
                    self.assertEqual({r['title'] for r in indexed['results']},{'生命周期试验2'})
                finally:direct.close()
                exact=value(client.tool('read_note',{'identifier':pid,'project':'main','output_format':'json'}))
                self.assertEqual(exact['state'],'quarantined');self.assertIn('账单验收',exact['content'])
                current=value(client.tool('memory_recall',{'query':'供应商重试','limit':20}))['results']
                self.assertNotIn(pid,{r['permalink'] for r in current})
                historical=value(client.tool('memory_recall',{'query':'供应商重试','limit':20,'include_history':True}))['results']
                self.assertIn(exact['summary'],{r['permalink'] for r in historical})
                recent=value(client.tool('recent_activity',{'project':'main','timeframe':'365d','output_format':'json'}))
                self.assertNotIn(exact['summary'],json.dumps(recent,ensure_ascii=False))
                # Unsupported enhanced filter delegates to the actual native index.
                search=value(client.tool('search_notes',{'project':'main','query':'生命周期试验',
                    'note_types':['codex_session'],'search_type':'text','output_format':'json'}))
                self.assertNotIn(pid,{r.get('permalink') for r in search['results']})
                clock[0]+=3600
                with patch.dict(os.environ,env,clear=True):self.assertEqual(engine.purge()['purged'],2)
                expired=value(client.tool('read_note',{'identifier':pid,'project':'main','output_format':'json'}))
                self.assertEqual(expired['state'],'purged');self.assertNotIn('content',expired)
                self.assertEqual(expired['summary'],exact['summary'])
            finally:client.close()
