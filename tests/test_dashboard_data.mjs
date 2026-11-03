import test from 'node:test';
import assert from 'node:assert/strict';
import dashboard from '../app/workbench/dashboard-data.js';
const {taskMetrics, filterTasks} = dashboard;

test('dashboard preserves unreported costs and tokens as unknown', () => {
  const result = taskMetrics({sources: [], steps: [{result: {usage: {otari: {}}}}]});
  assert.equal(result.cost, null);
  assert.equal(result.unknownCosts, 1);
  assert.equal(result.tokens, null);
  assert.equal(result.unknownTokens, 1);
});

test('reported totals include zero and distinguish partial accounting', () => {
  const result = taskMetrics({sources: [], steps: [
    {result: {usage: {input_tokens: 20, output_tokens: 8, otari: {cost_usd: '0.000003'}}}},
    {result: {usage: {input_tokens: 0, output_tokens: 0, otari: {cost_usd: '0'}}}},
    {result: {usage: {otari: {}}}},
  ]});
  assert.equal(result.completedCalls, 3);
  assert.equal(result.cost, '0.000003');
  assert.equal(result.tokens, 28);
  assert.equal(result.unknownCosts, 1);
});

test('progress follows saved outcomes rather than declaring every prepared call done', () => {
  const task = {web: true, analyze: true, retrieved: true, web_materialized: true,
    sources: [{permalink: 'a'}, {permalink: 'b'}], steps: [], answer: {citations: ['b', 'b']}};
  const result = taskMetrics(task);
  assert.equal(result.progress, 75);
  assert.equal(result.sourceUse, 50);
  assert.equal(result.sources, 2);
});

test('segmented history filters keep resumable tasks and completed tasks distinct', () => {
  const tasks = ['pending','running','paused','completed','failed'].map(status => ({id:status,status}));
  assert.deepEqual(filterTasks(tasks,'continue').map(t=>t.id), ['pending','paused']);
  assert.deepEqual(filterTasks(tasks,'completed').map(t=>t.id), ['completed']);
  assert.equal(filterTasks(tasks,'all').length, 5);
});
