"""The requested answer-publication, evidence-scope and saved-source contracts."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from otari_gateway import GatewayReply
from starlette.testclient import TestClient
from otari_workbench import create_app
import test_otari_workflow as fixture


class AnswerQuality(unittest.TestCase):
    setUp = fixture.ResearchContract.setUp
    tearDown = fixture.ResearchContract.tearDown
    workflow = fixture.ResearchContract.workflow

    def enable_review(self, decisions):
        self.config['otari']['models']['review'] = 'separate-review-model'
        self.decisions = iter(decisions)
        self.reviewed = []
        self.revision = None
        base = self.factory
        owner = self
        class ReviewedGateway:
            def __init__(self, config):
                self.base = base(config)
            def complete(self, messages, **args):
                if args['role'] == 'review':
                    owner.calls.append((messages, args))
                    owner.reviewed.append(json.loads(messages[-1]['content']))
                    value = next(owner.decisions)
                    return GatewayReply(json.dumps(value), value, {'input_tokens': 40, 'output_tokens': 15,
                        'otari': {'role': 'review', 'model': 'separate-review-model',
                                  'request_id': args['operation_id'], 'cost_usd': '0.00001'}}, ())
                result = self.base.complete(messages, **args)
                if args['role'] == 'reflect' and 'answer_revision' in args['operation_id']:
                    owner.revision = json.loads(messages[-1]['content'])
                return result
        self.factory = ReviewedGateway

    def source_task(self):
        flow = self.workflow()
        task = flow.create('refund policy')
        return flow.run(task['id'])

    def test_rejected_candidate_is_revised_and_only_approved_answer_is_published(self):
        self.enable_review([{'approved': False, 'issues': ['The answer contradicts the quoted negative.']},
                            {'approved': True, 'issues': []}])
        flow = self.workflow()
        task = flow.run(flow.create('refund policy')['id'])
        self.assertEqual(task['status'], 'completed')
        self.assertEqual(task['quality']['state'], 'approved')
        self.assertEqual(len(task['quality']['attempts']), 2)
        self.assertEqual(len(self.reviewed), 2)
        self.assertIn('contradicts', self.revision['review_issues'][0])
        self.assertEqual(task['answer']['citations'], ['main/refunds'])

    def test_two_rejections_never_publish_a_candidate_or_call_again_on_reopen(self):
        self.enable_review([{'approved': False, 'issues': ['Policy is not actual execution.']}] * 2)
        flow = self.workflow()
        task_id = flow.create('refund policy')['id']
        task = flow.run(task_id)
        self.assertIsNone(task['answer'])
        self.assertEqual(task['status'], 'failed')
        self.assertEqual(task['error']['kind'], 'quality_rejected')
        self.assertEqual(task['quality']['state'], 'rejected')
        flow.run(task_id)
        self.assertEqual(len(self.reviewed), 2)

    def test_unknown_review_transport_can_resume_without_repeating_the_candidate(self):
        self.enable_review([{'approved': True, 'issues': []}])
        original = self.factory
        owner = self
        class Interrupted:
            def __init__(self, config):
                self.inner = original(config)
            def complete(self, messages, **args):
                if args['role'] == 'review' and not hasattr(owner, 'interrupted'):
                    from otari_gateway import GatewayError
                    owner.interrupted = True
                    raise GatewayError('transport_error', 'unknown nonstream review', dispatched=True)
                return self.inner.complete(messages, **args)
        self.factory = Interrupted
        flow = self.workflow()
        task_id = flow.create('refund policy')['id']
        self.assertEqual(flow.run(task_id)['status'], 'paused')
        self.assertIsNone(flow.get(task_id)['answer'])
        self.assertEqual(flow.run(task_id)['status'], 'completed')
        self.assertEqual(sum(a['role'] == 'reflect' for _, a in self.calls), 1)

    def test_remote_only_scope_excludes_local_sources_and_observations_before_generation(self):
        previous = self.source_task()
        previous['sources'].append({'permalink': 'remote/demo/policy@1', 'title': 'Published policy',
            'excerpt': 'This fictional policy contains no real customer records.', 'kind': 'remote_mcp', 'revision': '1'})
        flow = self.workflow()
        flow._save(previous)
        task = flow.run(flow.create('Does it contain real records?', source_policy='remote_only',
                                   evidence_task_id=previous['id'])['id'])
        self.assertEqual(task['answer']['citations'], ['remote/demo/policy@1'])
        payload = json.loads(self.calls[-1][0][-1]['content'])
        self.assertEqual(payload['allowed_citations'], ['remote/demo/policy@1'])
        self.assertEqual(payload['observations'], [])

    def test_no_remote_evidence_does_not_substitute_local_memory(self):
        flow = self.workflow()
        task = flow.run(flow.create('refund policy', source_policy='remote_only')['id'])
        self.assertEqual(task['answer']['status'], 'insufficient_evidence')
        self.assertEqual(task['answer']['citations'], [])
        self.assertEqual(self.calls, [])

    def test_http_can_reuse_immutable_saved_sources_without_reacquiring_them(self):
        previous = self.source_task()
        (self.vault / 'refund.md').write_text('Unrelated replacement.', encoding='utf-8')
        with TestClient(create_app(self.workflow()), base_url='http://localhost') as client:
            response = client.post('/api/tasks', json={'query': 'refund policy',
                'source_policy': 'all', 'evidence_task_id': previous['id']})
            self.assertEqual(response.status_code, 202)
            task = client.get('/api/tasks/' + response.json()['id']).json()
            self.assertEqual(task['answer']['support'][0]['quote'], self.quote)
            self.assertEqual(task['evidence_task_id'], previous['id'])

    def test_source_reuse_cannot_change_the_original_memory_scope(self):
        previous = self.source_task()
        with self.assertRaises(ValueError):
            self.workflow().create('refund policy', evidence_task_id=previous['id'], scope='another-project')

    def test_accounting_summary_covers_only_completed_calls_before_synthesis(self):
        self.enable_review([{'approved': True, 'issues': []}])
        flow = self.workflow()
        task = flow.run(flow.create('refund policy', web=True)['id'])
        facts = task['answer_context']['run_facts']
        self.assertEqual(facts['completed_calls'], 1)
        self.assertEqual(facts['reported_subtotal_usd'], '0.000003')
        self.assertEqual(facts['unknown_cost_calls'], 0)
        self.assertFalse(facts['includes_whole_task_cost'])
        self.assertEqual(self.reviewed[0]['run_facts'], facts)
