"""Current-change contracts: grounded research, durable continuation and tool proof."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from memory_runtime import MemoryRuntime, markdown
from otari_gateway import GatewayReply, GatewayError
from otari_workflow import ResearchWorkflow


class ResearchContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.vault = self.root / 'vault'
        self.vault.mkdir()
        self.memory = MemoryRuntime(self.vault, self.root / 'state.sqlite', use_models=False)
        self.quote = 'Refunds must produce one business effect.'
        (self.vault / 'refund.md').write_text(markdown(
            {'title': 'Refund policy', 'scope': 'global', 'permalink': 'main/refunds'}, self.quote), encoding='utf-8')
        self.calls = []
        self.fail_once = None
        self.bad_quote = False
        self.code_records = True
        self.web_text = 'The official refund limit is 30 days.'
        self.config = {'max_calls_per_day': 20, 'max_calls_per_hour': 20,
                       'max_tokens_per_day': 500000, 'reserve_tokens_per_call': 12000,
                       'otari': {'models': {'reflect': 'reflect-open', 'research': 'tools-open',
                                            'analysis': 'tools-open', 'extract': 'extract-open'}},
                       'research': {'official_domains': ['docs.example.org']}}
        owner = self

        class Gateway:
            def complete(self, messages, **kwargs):
                owner.calls.append((messages, kwargs))
                role = kwargs['role']
                if owner.fail_once == role:
                    owner.fail_once = None
                    raise GatewayError('transport_error', 'uncertain', dispatched=True)
                records, value = [], None
                if role == 'research':
                    records = [{'type': 'web_search', 'status': 'completed', 'query': 'refunds',
                                'sources': [{'url': 'https://docs.example.org/refunds', 'title': 'Refund policy'}]}]
                    text = 'Located official documentation.'
                elif role == 'analysis':
                    if owner.code_records:
                        records = [{'type': 'code_execution', 'status': 'completed',
                                    'code': 'print(1)', 'stdout': '1\n', 'stderr': '', 'exit_code': 0}]
                    text = 'Analysis description.'
                else:
                    evidence = json.loads(messages[-1]['content'])
                    source = evidence['sources'][-1]
                    citation = source['permalink']
                    value = {'status': 'synthesized', 'answer': 'Use the current refund policy.',
                             'citations': [citation], 'support': [{'citation': citation,
                             'quote': 'invented support' if owner.bad_quote else source['excerpt']}]}
                    text = json.dumps(value)
                return GatewayReply(text, value, {'input_tokens': 12, 'output_tokens': 7,
                    'otari': {'request_id': 'req-' + kwargs['operation_id'], 'role': role,
                              'cost_usd': '0.000003', 'model': role + '-open', 'fallback': False}}, tuple(records))

        self.factory = lambda config: Gateway()
        self.loader = lambda url: {'url': url, 'title': 'Official refund policy', 'text': self.web_text}

    def tearDown(self):
        self.memory.close()
        self.temp.cleanup()

    def workflow(self):
        return ResearchWorkflow(self.memory, self.config, self.factory, self.loader)

    def test_cited_answer_links_persisted_official_text_and_real_code_output(self):
        flow = self.workflow()
        task = flow.create('refund policy', web=True, analyze=True)
        result = flow.run(task['id'])
        self.assertEqual(result['status'], 'completed', result)
        self.assertEqual(result['answer']['status'], 'synthesized')
        self.assertEqual(result['analysis']['executions'][0]['stdout'], '1\n')
        self.assertEqual(result['sources'][-1]['excerpt'], self.web_text)
        self.assertEqual(result['sources'][-1]['revision'], 1)
        reopened = self.workflow().get(task['id'])
        self.assertEqual(reopened['answer'], result['answer'])
        self.assertEqual(reopened['sources'], result['sources'])

    def test_resume_freezes_dispatched_evidence_and_avoids_repeating_completed_steps(self):
        flow = self.workflow()
        self.fail_once = 'reflect'
        task = flow.create('refund policy', web=True)
        paused = flow.run(task['id'])
        self.assertEqual(paused['status'], 'paused')
        before = self.calls[-1]
        self.web_text = 'Changed after interruption.'
        (self.vault / 'refund.md').write_text('Unrelated new note.', encoding='utf-8')
        result = self.workflow().run(task['id'])
        self.assertEqual(result['status'], 'completed')
        after = self.calls[-1]
        self.assertEqual(before, after)
        self.assertEqual(result['sources'][-1]['excerpt'], 'The official refund limit is 30 days.')
        self.assertEqual(sum(c[1]['role'] == 'research' for c in self.calls), 1)
        self.assertEqual(self.memory.db.execute('SELECT count(*) FROM calls').fetchone()[0], 2)

    def test_unavailable_exact_quote_never_becomes_an_answer(self):
        self.bad_quote = True
        flow = self.workflow()
        result = flow.run(flow.create('refund policy')['id'])
        self.assertEqual(result['status'], 'failed')
        self.assertIsNone(result.get('answer'))
        self.assertEqual(result['error']['kind'], 'invalid_evidence')

    def test_local_budget_pause_preserves_evidence_and_resume_after_budget_change(self):
        self.config['max_calls_per_day'] = 0
        flow = self.workflow()
        task = flow.create('refund policy')
        result = flow.run(task['id'])
        self.assertEqual(result['status'], 'paused')
        self.assertEqual(result['error']['kind'], 'budget_exceeded')
        self.assertTrue(result['sources'])
        self.assertEqual(self.calls, [])
        self.config['max_calls_per_day'] = 20
        self.assertEqual(self.workflow().run(task['id'])['status'], 'completed')

    def test_changed_official_page_creates_revision_without_mutating_previous_run(self):
        flow = self.workflow()
        first = flow.run(flow.create('refund policy', web=True)['id'])
        self.web_text = 'The official refund limit is now 60 days.'
        second = flow.run(flow.create('refund policy', web=True)['id'])
        self.assertEqual(first['sources'][-1]['revision'], 1)
        self.assertEqual(second['sources'][-1]['revision'], 2)
        self.assertNotEqual(first['answer']['citations'], second['answer']['citations'])
        self.assertEqual(flow.get(first['id'])['sources'][-1]['excerpt'], 'The official refund limit is 30 days.')

    def test_missing_code_execution_record_is_explicitly_unverified(self):
        self.code_records = False
        flow = self.workflow()
        result = flow.run(flow.create('refund policy', analyze=True)['id'])
        self.assertEqual(result['status'], 'completed')
        self.assertFalse(result['analysis']['verified'])
        self.assertEqual(result['analysis']['executions'], [])

    def test_no_evidence_stops_without_a_model_call(self):
        (self.vault / 'refund.md').unlink()
        flow = self.workflow()
        result = flow.run(flow.create('Unanswerable question')['id'])
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['answer']['status'], 'insufficient_evidence')
        self.assertEqual(self.calls, [])

    def test_unapproved_domain_cannot_be_materialized(self):
        self.config['research']['official_domains'] = ['official.example.org']
        flow = self.workflow()
        result = flow.run(flow.create('refund policy', web=True)['id'])
        self.assertEqual(result['status'], 'completed')
        self.assertFalse(any(s.get('url') for s in result['sources']))
        self.assertTrue(result['source_warnings'])


if __name__ == '__main__':
    unittest.main()
