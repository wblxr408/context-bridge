'use strict';
(() => {
function taskMetrics(task) {
  const sources = task?.sources || [];
  const results = (task?.steps || []).filter(s=>s.result).map(s=>s.result);
  let micro = 0n, priced = 0, tokens = 0, measured = 0, unknownCosts = 0, unknownTokens = 0;
  for (const result of results) {
    const usage = result.usage || {}, cost = usage.otari?.cost_usd;
    if (cost != null && /^\d+(?:\.\d+)?$/.test(String(cost))) {
      const [whole, fraction=''] = String(cost).split('.');
      micro += BigInt(whole)*1000000n + BigInt((fraction+'000000').slice(0,6)) + (Number(fraction[6] || 0)>=5?1n:0n); priced++;
    } else unknownCosts++;
    if ([usage.input_tokens,usage.output_tokens].every(n=>Number.isSafeInteger(n)&&n>=0)) {
      tokens += usage.input_tokens+usage.output_tokens; measured++;
    } else unknownTokens++;
  }
  const planned = task ? 2 + Number(!!task.event) + Number(!!task.web) + Number(!!task.mcp) + Number(!!task.analyze) : 0;
  const finished = task ? Number(!!task.retrieved)+Number(!!task.answer)+
    Number(!!task.event&&!!task.retained)+Number(!!task.web&&!!task.web_materialized)+
    Number(!!task.mcp&&!!task.mcp_evidence)+Number(!!task.analyze&&!!task.analysis) : 0;
  const used = new Set((task?.answer?.citations || []).filter(c=>sources.some(s=>s.permalink===c))).size;
  return {progress: planned ? Math.min(100,Math.round(finished/planned*100)) : 0,
    sourceUse:sources.length?Math.round(used/sources.length*100):0, sources:sources.length, used,
    completedCalls:results.length, tokens:measured?tokens:null, unknownTokens,
    cost:priced?String(micro/1000000n)+'.'+String(micro%1000000n).padStart(6,'0'):null, unknownCosts};
}
function filterTasks(tasks, filter) {
  if (filter==='continue') return tasks.filter(t=>['pending','paused'].includes(t.status));
  if (filter==='completed') return tasks.filter(t=>t.status==='completed');
  return tasks;
}
if (typeof module !== 'undefined' && module.exports) module.exports = {taskMetrics, filterTasks};
else window.BridgeDashboard = {taskMetrics, filterTasks};
})();
