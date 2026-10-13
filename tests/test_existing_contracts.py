import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
sys.path.insert(0, str(ROOT / 'context-bridge' / 'scripts'))
import listener
import writer
import requirements


class ExistingContracts(unittest.TestCase):
    def test_turn_context_updates_scope_when_same_session_changes_workspace(self):
        context={}
        listener.reduce_record('codex',{'type':'session_meta','payload':{'id':'s','cwd':'D:/a'}},context)
        listener.reduce_record('codex',{'type':'turn_context','payload':{'cwd':'D:/b'}},context)
        listener.reduce_record('codex',{'type':'response_item','payload':{'type':'message','role':'user','content':'以后采用这个项目的预算约定。'}},context)
        event=listener.reduce_record('codex',{'type':'event_msg','payload':{'type':'turn_complete','turn_id':'t','last_agent_message':'已记录当前项目要求。'}},context)
        self.assertEqual(event['cwd'],'D:/b')
    def test_chinese_paraphrase_recalls_relevant_prior_lesson(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            vault = Path(tmp)
            (vault / 'memory.md').write_text('---\ntitle: 重复退款\n---\n支付请求可以重复传输，但业务退款副作用必须仅执行一次。', encoding='utf-8')
            (vault / 'other.md').write_text('---\ntitle: 摄影\n---\n拍摄风景时使用柔和光线。', encoding='utf-8')
            found = listener.existing_notes(vault, {'user': '怎样避免重试导致多次扣款？', 'final': '需要找到之前关于交易去重的约定。'})
            self.assertTrue(any(r['path'] == 'memory.md' for r in found), 'Chinese paraphrase must recall the prior transaction lesson')

    def test_latest_user_constraint_is_not_lost_to_clipping(self):
        context = {}
        correction = '最终修正：所有实际写入必须核对当前任务版本。'
        listener.reduce_record('codex', {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': '背景介绍。' * 600 + correction}}, context)
        listener.reduce_record('codex', {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'channel': 'final', 'content': '已理解。'}}, context)
        event = listener.reduce_record('codex', {'type': 'event_msg', 'payload': {'type': 'turn_complete', 'turn_id': 't1'}}, context)
        self.assertIn(correction, event['user'], 'The correction at the end of a long user turn must remain retrievable')

    def test_transfer_binds_explicit_snapshot_and_invalidates_source(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            root = Path(tmp)
            source, target = root / 'source.json', root / 'target.json'
            writer.operate('acquire', root, owner='source', claim=source)
            failure = None
            try:
                writer.operate('transfer', root, owner='receiver', claim=source, new_claim=target, manifest='task-001/revision-2')
            except (ValueError, OSError) as exc:
                failure = str(exc)
            self.assertIsNone(failure, 'Explicit task/revision transfer must work without a snapshot checksum')
            with self.assertRaises(ValueError):
                writer.operate('assert', root, claim=source)
            self.assertEqual(writer.operate('assert', root, claim=target, manifest='task-001/revision-2')['owner'], 'receiver')

    def test_receipt_requires_task_version_and_semantic_coverage(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            root = Path(tmp)
            (root / 'request.md').write_text('按最新要求继续任务。', encoding='utf-8')
            ledger = {'schema': 1, 'task_id': 'task-001', 'snapshot_id': 'task-001/revision-2', 'requirements': [{'id': 'R001', 'revision': 2, 'status': 'active', 'kind': 'goal', 'always_load': True, 'scope': 'global', 'statement': '按最新要求继续任务。', 'acceptance': '旧要求不覆盖最新修正。', 'progress': 'pending', 'source': {'path': 'request.md', 'quote': '按最新要求继续任务。', 'locator': '用户消息'}, 'evidence': []}]}
            (root / 'requirements.json').write_text(json.dumps(ledger, ensure_ascii=False), encoding='utf-8')
            proof = {'task_id': 'task-001', 'snapshot_id': 'task-001/revision-2', 'scope': 'global', 'checks': [{'id': 'R001', 'revision': 2, 'result': 'aligned', 'interpretation': '已对照原请求和当前工作状态。', 'next_action': '依据当前版本继续任务。'}]}
            (root / 'receipt.json').write_text(json.dumps(proof, ensure_ascii=False), encoding='utf-8')
            failure = None
            try:
                result = requirements.receipt(root, 'global', root / 'receipt.json', 'task-001/revision-2')
            except (ValueError, OSError) as exc:
                failure = str(exc)
            self.assertIsNone(failure, 'Receipt must verify explicit version and requirement coverage without a checksum manifest')
            self.assertEqual(result['requirements'], 1)


if __name__ == '__main__':
    unittest.main()
