import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class HistoryReport(unittest.TestCase):
    def test_backfill_reports_only_eligible_events_as_queued_and_replay_adds_none(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            home=Path(temp);logs=home/'logs';logs.mkdir()
            (home/'config.json').write_text(json.dumps({'sources':[{'kind':'codex','path':str(logs)}]}),encoding='utf-8')
            events=[{'type':'session_meta','payload':{'id':'fixture-chat','cwd':str(home)}},
                    {'type':'response_item','payload':{'type':'message','role':'user','content':'以后必须先写行为测试再实现，并记住这个约定。'}},
                    {'type':'event_msg','payload':{'type':'turn_complete','turn_id':'important','last_agent_message':'已记住。'}},
                    {'type':'response_item','payload':{'type':'message','role':'user','content':'谢谢'}},
                    {'type':'event_msg','payload':{'type':'turn_complete','turn_id':'ordinary','last_agent_message':'不客气'}}]
            (logs/'chat.jsonl').write_text('\n'.join(json.dumps(e,ensure_ascii=False) for e in events)+'\n',encoding='utf-8')
            command=[sys.executable,str(ROOT/'app/memory_cli.py'),'backfill','--home',str(home),
                     '--source',str(logs),'--kind','codex']
            result=subprocess.run(command,capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0)
            report=json.loads(result.stdout)
            self.assertEqual(report['queued'],1,'Filtered courtesy messages must not be reported as pending classifications')
            self.assertEqual((report['events_added'],report['filtered']),(2,1))
            repeated=json.loads(subprocess.run(command,capture_output=True,timeout=10,check=True).stdout)
            self.assertEqual((repeated['events_added'],repeated['queued'],repeated['filtered']),(0,0,0))
