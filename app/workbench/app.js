'use strict';
const {taskMetrics, filterTasks} = window.BridgeDashboard;
const $ = id => document.getElementById(id);
const statuses = {pending:'等待执行',running:'正在研究',completed:'已完成',paused:'已暂停',failed:'需要重新研究'};
const names = {extract:'提取记忆',discover:'检索官方资料',mcp:'读取远程记忆',answer:'综合有据回答',analyze:'分析调用记录'};
let selected = null, current = null, generation = 0, timer = null, busy = false, taskFilter = 'all', savedTasks = [];
const node = (tag, text, cls) => { const el = document.createElement(tag); if(text !== undefined) el.textContent = text; if(cls) el.className = cls; return el; };
async function api(path, options={}) { const res = await fetch(path, {...options, headers:{'Content-Type':'application/json',...options.headers}}); const data = await res.json(); if(!res.ok) throw new Error(data.error || '请求未完成，请重试。'); return data; }
function message(text) { $('message').textContent=text; $('message').hidden=!text; }
function tab(which) { for(const name of ['sources','events']) { const on=name===which; $(name+'-tab').setAttribute('aria-selected',String(on)); $(name+'-tab').tabIndex=on?0:-1; $(name+'-panel').hidden=!on; } }
for(const name of ['sources','events']) { $(name+'-tab').onclick=()=>tab(name); $(name+'-tab').onkeydown=e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const other=name==='sources'?'events':'sources';tab(other);$(other+'-tab').focus();}}; }
function inspect(citation) { tab('sources'); const target=Array.from($('sources').children).find(el=>el.dataset.citation===citation); if(target){target.open=true;target.querySelector('summary').focus();target.scrollIntoView({block:'nearest',behavior:'auto'});} }
function metrics(task) {
  const data = taskMetrics(task);
  $('activity-state').textContent=task?(statuses[task.status]||task.status):'尚未开始';
  for(const [id,value,label] of [['progress',data.progress,'任务进度'],['source',data.sourceUse,'采用来源比例']]){
    $(id+'-arc').setAttribute('stroke-dasharray',`${value} 100`);
    $(id+'-dial').setAttribute('aria-valuenow',String(value));
    $(id+'-dial').setAttribute('aria-valuetext',task?`${label} ${value}%`:'尚未选择任务');
  }
  $('progress-value').textContent=task?data.progress+'%':'—';
  $('source-value').textContent=task?`${data.used}/${data.sources}`:'—';
  $('source-caption').textContent='采用来源 / 可用来源';
  $('token-value').textContent=data.tokens==null?'—':data.tokens.toLocaleString('zh-CN');
  $('token-note').textContent=data.unknownTokens?`${data.unknownTokens} 次用量未知`:(data.completedCalls?`${data.completedCalls} 次已返回调用`:'等待调用记录');
  $('spend-value').textContent=data.cost==null?'—':data.cost;
  $('spend-note').textContent=data.unknownCosts?`${data.unknownCosts} 次费用未知`:(data.completedCalls?'来自网关费用报告':'不将未知记为零');
}
function render(task) {
  current=task; $('main').classList.add('reading'); $('result').hidden=false; $('result-title').textContent=task.query;
  metrics(task);
  $('task-status').textContent=statuses[task.status]||task.status; $('task-status').dataset.status=task.status;
  $('task-time').textContent='创建于 '+new Date(task.created_at).toLocaleString('zh-CN');
  $('resume').hidden=!['paused','running','pending'].includes(task.status); $('resume').disabled=busy||!task.can_resume;
  $('task-error').hidden=!task.error; $('task-error').textContent=task.error?task.error.message+' ('+task.error.kind+')':'';
  $('answer').textContent=task.answer?.answer||(task.status==='running'?'正在检索与核对。已完成的步骤会持续保存。':'任务结果将在这里显示。');
  $('citations').replaceChildren(); for(const [i,cite] of (task.answer?.citations||[]).entries()){const b=node('button',`[${i+1}] `+(task.sources.find(s=>s.permalink===cite)?.title||cite),'citation');b.onclick=()=>inspect(cite);$('citations').append(b);}
  $('sources-empty').hidden=!!task.sources.length; $('evidence-count').textContent=String(task.sources.length);$('sources').replaceChildren();
  for(const source of task.sources){ const d=node('details',undefined,'source');d.dataset.citation=source.permalink;const summary=node('summary',source.title);summary.tabIndex=0;summary.append(node('small',(source.kind==='official_web'?'官方网页 · 版本 '+source.revision:source.kind==='remote_mcp'?'远程原文 · 版本 '+source.revision:'记忆原文')+' · '+source.permalink));d.append(summary);
    for(const support of task.answer?.support||[])if(support.citation===source.permalink)d.append(node('blockquote',support.quote));
    if(source.url){try{const url=new URL(source.url);if(url.protocol==='https:'){const a=node('a','打开原始网页');a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';d.append(a);}}catch{}}
    d.append(node('div',source.excerpt,'excerpt'));$('sources').append(d); }
  $('source-warnings').replaceChildren(...(task.source_warnings||[]).map(t=>node('p',t)));
  $('timeline').replaceChildren();$('ledger').replaceChildren();
  for(const step of task.steps){const result=step.result, meta=result?.usage?.otari||{};const item=node('li');item.append(node('strong',names[step.name]||step.name),node('p',step.state==='completed'?'已保存结果':'请求已准备，等待完成','muted'));
    if(meta.request_id)item.append(node('p',meta.request_id,'muted'));
    for(const tool of result?.tool_calls||[]){const details=node('details');details.append(node('summary',`${tool.type||'tool'} · ${tool.status||'未知'}`),node('pre',JSON.stringify(tool,null,2)));item.append(details);} $('timeline').append(item);
    if(!result)continue; const tr=node('tr'), label=node('td',names[step.name]||step.name);label.append(node('small',meta.request_id||'请求编号未报告'));tr.append(label,node('td',meta.model||'未报告'),node('td',`${result.usage.input_tokens??'?'} / ${result.usage.output_tokens??'?'}`),node('td',meta.cost_usd==null?'未知':'$'+meta.cost_usd),node('td',meta.fallback===true?'是':meta.fallback===false?'否':'未知'));$('ledger').append(tr);
  }
  const totals=taskMetrics(task);
  $('cost-total').textContent=(totals.cost==null?'暂无费用报告':`已报告 $${totals.cost}`)+(totals.unknownCosts?` · ${totals.unknownCosts} 次费用未知`:'');
  $('analysis-section').hidden=!task.analysis;if(task.analysis){$('analysis-status').textContent=task.analysis.verified?'已取得成功执行记录。':'未取得成功执行记录；下面的说明不证明工具已运行。';$('analysis-output').textContent=task.analysis.executions.map(t=>t.stdout).join('\n')||task.analysis.description;}
  if(task.mcp_evidence){const item=node('li',task.mcp_evidence.verified?'MCP：已取得完成记录。':'MCP：缺少完成记录。');$('timeline').append(item);}
}
function renderHistory(){const tasks=filterTasks(savedTasks,taskFilter);$('task-list').replaceChildren();$('workspace-count').textContent=savedTasks.length?`${savedTasks.length} 项已保存研究`:'从一个真实问题开始';if(!tasks.length){$('task-list').append(node('p',taskFilter==='all'?'还没有研究任务。你的问题、原文和研究结果会保存在这里。':taskFilter==='continue'?'没有待继续的任务，可在“全部任务”中查看所有记录。':'还没有已完成的任务。','empty-history'));return;}for(const task of tasks){const b=node('button',undefined,'history-item'+(selected===task.id?' active':''));b.dataset.status=task.status;if(selected===task.id)b.setAttribute('aria-current','true');b.append(node('strong',task.query),node('small',statuses[task.status]+' · '+new Date(task.created_at).toLocaleDateString('zh-CN')));b.onclick=()=>open(task.id);$('task-list').append(b);}}
async function history(){savedTasks=await api('/api/tasks');renderHistory();}
for(const button of document.querySelectorAll('[data-filter]'))button.onclick=()=>{taskFilter=button.dataset.filter;for(const b of document.querySelectorAll('[data-filter]'))b.setAttribute('aria-pressed',String(b===button));renderHistory();};
async function open(id){selected=id;const version=++generation;clearTimeout(timer);try{const task=await api('/api/tasks/'+id);if(version!==generation)return;render(task);await history();if(['running','pending'].includes(task.status))timer=setTimeout(()=>poll(id,version),1200);}catch(e){message(e.message);} }
async function poll(id,version){if(version!==generation||selected!==id)return;try{const task=await api('/api/tasks/'+id);if(version!==generation)return;render(task);if(['running','pending'].includes(task.status))timer=setTimeout(()=>poll(id,version),1200);else await history();}catch(e){message(e.message);} }
$('research-form').onsubmit=async event=>{event.preventDefault();if(busy)return;message('');busy=true;$('submit').disabled=true;$('submit-label').textContent='正在创建…';try{const payload={query:$('question').value,web:$('web').checked,analyze:$('analyze').checked,mcp:$('mcp').checked};if($('scope').value.trim())payload.scope=$('scope').value.trim();if($('conversation').value.trim())payload.event={user:$('conversation').value,final:''};const task=await api('/api/tasks',{method:'POST',body:JSON.stringify(payload)});await open(task.id);}catch(e){message(e.message);}finally{busy=false;$('submit').disabled=false;$('submit-label').textContent='开始研究';} };
$('resume').onclick=async()=>{if(busy||!selected)return;busy=true;$('resume').disabled=true;try{await api('/api/tasks/'+selected+'/resume',{method:'POST'});await open(selected);}catch(e){message(e.message);}finally{busy=false;$('resume').disabled=false;}};
$('refresh').onclick=()=>history().catch(e=>message(e.message));
$('new-task').onclick=()=>{selected=null;current=null;generation++;clearTimeout(timer);$('main').classList.remove('reading');$('result').hidden=true;$('sources').replaceChildren();$('timeline').replaceChildren();$('evidence-count').textContent='0';$('sources-empty').hidden=false;$('research-form').reset();metrics(null);message('');history().catch(e=>message(e.message));$('question').focus();};
$('example').onclick=()=>{$('question').value='退款任务重试时，怎样确保只产生一次业务效果？';$('conversation').value='退款请求可能重复传输，但必须保持幂等；同一退款业务只能产生一次实际退款效果。';$('conversation').closest('details').open=true;$('web').checked=false;$('analyze').checked=false;$('question').focus();};
$('scene-web').onclick=()=>{$('question').value='functools.lru_cache 能保证并发时底层函数只执行一次吗？请核对 Python 官方文档并说明边界。';$('conversation').value='';$('web').checked=true;$('analyze').checked=false;$('question').focus();};
$('scene-analysis').onclick=()=>{$('question').value='结合退款重试的幂等约定回答，并分析本次模型调用记录、费用报告和未知项。';$('conversation').value='';$('web').checked=false;$('analyze').checked=true;$('question').focus();};
async function init(){metrics(null);$('local-date').textContent=new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',month:'long',day:'numeric',weekday:'long'}).format(new Date())+' · 让每条记忆，都有来处。';try{const settings=await api('/api/settings');$('connection').textContent=settings.credential_ready?'Otari 凭据已配置':'待连接 Otari';$('connection').classList.toggle('ready',settings.credential_ready);$('setup-note').hidden=settings.credential_ready;$('setup-note').textContent='尚未配置 Otari 凭据，可先查看已保存的任务。配置后即可开始研究。';$('mcp').disabled=!settings.mcp_ready;$('mcp').parentElement.title=settings.mcp_ready?'使用配置的远程只读服务器':'先连接已发布的只读 MCP 服务器';$('credential-status').textContent=settings.credential_ready?'已配置':'待配置';$('credential-status').classList.toggle('ready',settings.credential_ready);const roles=Object.values(settings.models||{}).filter(v=>typeof v==='string'&&v.trim()&&!v.startsWith('SET_'));const distinct=new Set(roles).size;$('model-status').textContent=distinct>=2?`${distinct} 个模型已配置`:'待配置多个模型';$('model-status').classList.toggle('ready',distinct>=2);$('mcp-status').textContent=settings.mcp_ready?'已配置':'待连接';$('mcp-status').classList.toggle('ready',settings.mcp_ready);const list=$('settings-list');for(const [key,value] of Object.entries(settings.models||{})){list.append(node('dt',key),node('dd',value));}list.append(node('dt','允许的官方域名'),node('dd',settings.official_domains.join('、')||'尚未配置'));await history();}catch(e){message(e.message);}}
init();
