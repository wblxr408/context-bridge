import test_memory_features as base
import unittest
from memory_runtime import ConflictError
from memory_integration import capture_claims

class Lifecycle(unittest.TestCase):
    setUp=base.MemoryFeatures.setUp
    tearDown=base.MemoryFeatures.tearDown
    fact=base.MemoryFeatures.fact
    note=base.MemoryFeatures.note
    def test_current_recall_does_not_return_replaced_event_claim(self):
        self.fact('old','允许冒烟测试','2026-09-01')
        self.fact('new','禁止冒烟测试','2026-10-01')
        result=self.memory.recall('冒烟测试')
        self.assertEqual(len(result['results']),1)
        self.assertNotIn('允许冒烟测试',result['results'][0]['excerpt'])
        self.assertEqual(len(self.memory.recall('冒烟测试',include_history=True)['results']),2)

    def test_one_event_cannot_leak_claim_from_another_scope(self):
        claims=[{'subject':'预算','predicate':'调用','value':'每小时2次','quote':'每小时2次','source':'user','scope':scope} for scope in ['D:/a','D:/b']]
        with self.assertRaises(ValueError): self.memory.retain('mixed',claims,{'user':'每小时2次','final':''})
        self.assertEqual(self.memory.observations(),[])

    def test_event_identity_survives_lost_rebuildable_cache(self):
        self.fact('same','禁止冒烟测试')
        with self.memory.db: self.memory.db.execute('DELETE FROM memory_events')
        with self.assertRaises(ConflictError): self.fact('same','允许冒烟测试')
        self.assertEqual(self.memory.observations()[0]['current'],'禁止冒烟测试')

    def test_technical_report_is_not_verified_by_user_problem_quote(self):
        payload={'user':'缓存的故障需要修复，并记录这次原因。','final':'缓存键已修复，据回复报告测试通过。','cwd':'D:/a'}
        note={'title':'缓存','kind':'pitfall','lesson':'缓存键冲突已修复','evidence':[{'source':'user','quote':payload['user']},{'source':'final','quote':payload['final']}]}
        capture_claims(self.memory,'tech',payload,[note])
        self.assertEqual(self.memory.observations('D:/a')[0]['status'],'experimental')

    def test_reflection_requires_exact_cited_support_quote(self):
        self.note('退款','重复请求仅退款一次。')
        def unsupported(evidence):
            return {'answer':'重复退款十次','citations':['main/退款'],'support':[{'citation':'main/退款','quote':'退款十次'}]}
        with self.assertRaises(ValueError): self.memory.reflect('退款',generator=unsupported)

    def test_literal_phrase_does_not_become_unrelated_word_matches(self):
        self.note('甲','代码正确但时间未知')
        self.note('乙','代码正确时间必须确定')
        result=self.memory.recall('"正确时间"',mode='text')
        self.assertEqual([r['title'] for r in result['results']],['乙'])
