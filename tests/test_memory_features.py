import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from memory_runtime import MemoryRuntime, ConflictError


class MemoryFeatures(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.root = Path(self.tmp.name)
        self.vault = self.root / 'vault'
        self.vault.mkdir()
        self.memory = MemoryRuntime(self.vault, self.root / 'state.sqlite', use_models=False)

    def tearDown(self):
        self.memory.close()
        self.tmp.cleanup()

    def note(self, name, text, **meta):
        meta = {'title': name, 'permalink': 'main/' + name, **meta}
        (self.vault / (name + '.md')).write_text('---\n' + '\n'.join(k + ': ' + json.dumps(v, ensure_ascii=False) for k, v in meta.items()) + '\n---\n' + text, encoding='utf-8')

    def fact(self, event, value, date='2026-10-12', scope='global', subject='开发验收', predicate='冒烟测试'):
        quote = '用户要求：' + value
        return self.memory.retain(event, [{'subject': subject, 'predicate': predicate, 'value': value, 'quote': quote, 'source': 'user', 'scope': scope}], {'user': quote, 'final': ''}, occurred_at=date)

    def test_chinese_keyword_and_boolean_queries_return_actual_lesson(self):
        self.note('交接', 'context-bridge 检查点回收要保护当前在用版本。')
        self.note('测试', 'TDD 禁止冒烟和只检查文件存在作为验收。')
        self.assertEqual(self.memory.recall('"context-bridge" AND "回收"', mode='text')['results'][0]['title'], '交接')
        self.assertEqual(self.memory.recall('"TDD" AND "冒烟"', mode='text')['results'][0]['title'], '测试')
        self.assertEqual(self.memory.recall('"TDD" AND "摄影"', mode='text')['results'], [])
    def test_boolean_query_does_not_expand_to_nonmatching_graph_neighbor(self):
        self.note('测试','TDD 禁止冒烟，额外资料见 [[摄影]]。')
        self.note('摄影','使用柔和光线拍照。')
        found=self.memory.recall('"TDD" AND "冒烟"',mode='text')['results']
        self.assertEqual([r['title'] for r in found],['测试'])

    def test_natural_question_retrieves_relevant_semantics(self):
        self.note('退款', '支付请求允许重复传输，但退款副作用必须仅执行一次。')
        self.note('摄影', '拍摄风景使用柔和光线。')
        self.assertEqual(self.memory.recall('怎样避免重试导致多次扣款？')['results'][0]['title'], '退款')

    def test_pagination_is_stable_and_deduplicates_permalinks(self):
        for i in range(5):
            self.note('缓存' + str(i), '缓存性能', permalink='main/shared' if i < 2 else 'main/' + str(i))
        first = self.memory.recall('缓存', limit=2, page=1)
        second = self.memory.recall('缓存', limit=2, page=2)
        self.assertEqual(first['total'], 4)
        self.assertFalse({r['permalink'] for r in first['results']} & {r['permalink'] for r in second['results']})

    def test_latest_scope_does_not_leak_another_repository(self):
        self.note('甲', '部署约定', cwd='D:/project-a', date='2026-10-01')
        self.note('乙', '部署约定', cwd='D:/project-b', date='2026-10-02')
        self.note('全局', '部署约定', scope='global', date='2026-10-03')
        result = self.memory.recall('部署', scope='D:/project-a')
        self.assertEqual({r['title'] for r in result['results']}, {'甲', '全局'})

    def test_time_filter_and_superseded_policy(self):
        self.note('旧约定', '冒烟测试可以使用', date='2026-09-01', status='superseded')
        self.note('新约定', '禁止冒烟测试', date='2026-10-01', status='accepted')
        self.assertEqual([r['title'] for r in self.memory.recall('冒烟', after='2026-09-15')['results']], ['新约定'])
        self.assertEqual([r['title'] for r in self.memory.recall('冒烟')['results']], ['新约定'])
        self.assertEqual(len(self.memory.recall('冒烟', include_history=True)['results']), 2)

    def test_graph_expands_linked_source_when_it_has_no_keyword_match(self):
        self.note('原因', '支付业务的重放必须幂等。')
        self.note('入口', '退款设计的原因见 [[原因]]。')
        found = self.memory.recall('退款设计')['results']
        self.assertIn('原因', [r['title'] for r in found])
        self.assertTrue(next(r for r in found if r['title'] == '原因')['retrieval']['graph'])

    def test_unknown_question_returns_no_fabricated_answer(self):
        self.note('开发', '行为测试先失败后通过。')
        result = self.memory.reflect('用户的护照号码是什么？')
        self.assertEqual(result['status'], 'insufficient_evidence')
        self.assertEqual(result['citations'], [])

    def test_retain_retry_has_one_business_effect_and_rejects_changed_payload(self):
        self.fact('evt-1', '禁止冒烟测试')
        self.fact('evt-1', '禁止冒烟测试')
        observation = self.memory.observations()[0]
        self.assertEqual(observation['proof_count'], 1)
        with self.assertRaises(ConflictError):
            self.fact('evt-1', '允许冒烟测试')

    def test_new_preference_preserves_prior_history_and_current_evidence(self):
        self.fact('old', '允许冒烟测试', '2026-09-01')
        self.fact('new', '禁止冒烟测试', '2026-10-01')
        self.fact('late-old', '允许冒烟测试', '2026-08-01')
        observation = self.memory.observations()[0]
        self.assertEqual(observation['current'], '禁止冒烟测试')
        self.assertEqual(len(observation['history']), 3)
        self.assertEqual(observation['proof_count'], 3)
        self.assertEqual(observation['current_evidence'][0]['event_id'], 'new')

    def test_negation_and_numeric_changes_do_not_collapse(self):
        self.fact('one', '每小时最多2次调用', predicate='预算')
        self.fact('two', '每小时最多8次调用', predicate='预算')
        observation = self.memory.observations()[0]
        self.assertEqual(observation['current'], '每小时最多8次调用')
        self.assertEqual(len({x['value'] for x in observation['history']}), 2)

    def test_quotes_must_be_grounded_and_failure_is_atomic(self):
        with self.assertRaises(ValueError):
            self.memory.retain('forged', [{'subject': '身份', 'predicate': '偏好', 'value': '伪造', 'quote': '不存在的原文', 'source': 'user', 'scope': 'global'}], {'user': '真实原文', 'final': ''})
        self.assertEqual(self.memory.observations(), [])

    def test_page_refresh_and_delete_source_do_not_leave_stale_claims(self):
        self.fact('first', '允许冒烟测试', '2026-09-01')
        first = self.memory.page('验收约定', '冒烟测试', refresh=True)
        self.fact('second', '禁止冒烟测试', '2026-10-01')
        second = self.memory.page('验收约定', '冒烟测试')
        self.assertTrue(second['stale'])
        refreshed = self.memory.page('验收约定', '冒烟测试', refresh=True)
        self.assertIn('禁止冒烟测试', refreshed['content'])
        self.memory.forget_event('second')
        restored = self.memory.page('验收约定', '冒烟测试', refresh=True)
        self.assertIn('允许冒烟测试', restored['content'])
        self.assertNotIn('禁止冒烟测试', restored['content'])

    def test_generated_reflection_rejects_unavailable_source_citation(self):
        self.note('退款', '重试不允许重复退款。')
        with self.assertRaises(ValueError):
            self.memory.reflect('退款重试', generator=lambda evidence: {'answer': '任意断言', 'citations': ['main/missing']})

    def test_snapshot_reads_are_reproducible_after_restart(self):
        self.fact('evt', '禁止冒烟测试')
        self.memory.close()
        self.memory = MemoryRuntime(self.vault, self.root / 'state.sqlite', use_models=False)
        self.assertEqual(self.memory.observations()[0]['current'], '禁止冒烟测试')

    def test_path_traversal_is_rejected_for_knowledge_pages(self):
        with self.assertRaises(ValueError):
            self.memory.page('../outside', '测试', refresh=True)


if __name__ == '__main__':
    unittest.main()
