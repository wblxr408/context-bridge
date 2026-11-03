'use strict';
const $ = id => document.getElementById(id);
const statuses = {pending:'等待执行',running:'正在研究',completed:'已完成',paused:'已暂停',failed:'需要重新研究'};
const names = {extract:'提取记忆',discover:'检索官方资料',mcp:'读取远程记忆',answer:'综合有据回答',analyze:'分析调用记录'};
let selected = null, current = null, generation = 0, timer = null, busy = false;
const node = (tag, text, cls) => { const el = document.createElement(tag); if(text !== undefined) el.textContent = text; if(cls) el.className = cls; return el; };
async function api(path, options={}) { const res = await fetch(path, {...options, headers:{'Content-Type':'application/json',...options.headers}}); const data = await res.json(); if(!res.ok) throw new Error(data.error || '请求未完成，请重试。'); return data; }
function message(text) { $('message').textContent=text; $('message').hidden=!text; }
function tab(which) { for(const name of ['sources','events']) { const on=name===which; $(name+'-tab').setAttribute('aria-selected',String(on)); $(name+'-tab').tabIndex=on?0:-1; $(name+'-panel').hidden=!on; } }
for(const name of ['sources','events']) { $(name+'-tab').onclick=()=>tab(name); $(name+'-tab').onkeydown=e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const other=name==='sources'?'events':'sources';tab(other);$(other+'-tab').focus();}}; }
function inspect(citation) { tab('sources'); const target=Array.from($('sources').children).find(el=>el.dataset.citation===citation); if(target){target.open=true;target.querySelector('summary').focus();target.scrollIntoView({block:'nearest',behavior:'auto'});} }
function render(task) {
  current=task; $('main').classList.add('reading'); $('result').hidden=false; $('result-title').textContent=task.query;
  $('task-status').textContent=statuses[task.status]||task.status; $('task-status').dataset.status=task.status;
  $('task-time').textContent='创建于 '+new Date(task.created_at).toLocaleString('zh-CN');
  $('resume').hidden=!['paused','running','pending'].includes(task.status); $('resume').disabled=busy||!task.can_resume;
  $('task-error').hidden=!task.error; $('task-error').textContent=task.error?task.error.message+' ('+task.error.kind+')':'';
  $('answer').textContent=task.answer?.answer||(task.status==='running'?'正在检索与核对。已完成的步骤会持续保存。':'任务结果将在这里显示。');
  $('citations').replaceChildren(); for(const [i,cite] of (task.answer?.citations||[]).entries()){const b=node('button',`[${i+1}] `+(task.sources.find(s=>s.permalink===cite)?.title||cite),'citation');b.onclick=()=>inspect(cite);$('citations').append(b);}
  $('sources-empty').hidden=!!task.sources.length; $('evidence-count').textContent=String(task.sources.length);$('sources').replaceChildren();
  for(const source of task.sources){ const d=node('details',undefined,'source');d.dataset.citation=source.permalink;const summary=node('summary',source.title);summary.tabIndex=0;summary.append(node('small',(source.kind==='official_web'?'官方网页 · 版本 '+source.revision:'记忆原文')+' · '+source.permalink));d.append(summary);
    for(const support of task.answer?.support||[])if(support.citation===source.permalink)d.append(node('blockquote',support.quote));
    if(source.url){try{const url=new URL(source.url);if(url.protocol==='https:'){const a=node('a','打开原始网页');a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';d.append(a);}}catch{}}
    d.append(node('div',source.excerpt,'excerpt'));$('sources').append(d); }
  $('source-warnings').replaceChildren(...(task.source_warnings||[]).map(t=>node('p',t)));
  $('timeline').replaceChildren();$('ledger').replaceChildren();let known=0, unknown=0;
  for(const step of task.steps){const result=step.result, meta=result?.usage?.otari||{};const item=node('li');item.append(node('strong',names[step.name]||step.name),node('p',step.state==='completed'?'已保存结果':'请求已准备，等待完成','muted'));
    if(meta.request_id)item.append(node('p',meta.request_id,'muted'));
    for(const tool of result?.tool_calls||[]){const details=node('details');details.append(node('summary',`${tool.type||'tool'} · ${tool.status||'未知'}`),node('pre',JSON.stringify(tool,null,2)));item.append(details);} $('timeline').append(item);
    if(!result)continue; const tr=node('tr'), label=node('td',names[step.name]||step.name);label.append(node('small',meta.request_id||'请求编号未报告'));tr.append(label,node('td',meta.model||'未报告'),node('td',`${result.usage.input_tokens??'?'} / ${result.usage.output_tokens??'?'}`),node('td',meta.cost_usd==null?'未知':'$'+meta.cost_usd),node('td',meta.fallback===true?'是':meta.fallback===false?'否':'未知'));$('ledger').append(tr);
    if(meta.cost_usd==null)unknown++;else known+=Number(meta.cost_usd); }
  $('cost-total').textContent=`已报告 $${known.toFixed(6)}`+(unknown?` · ${unknown} 次费用未知`:'');
  $('analysis-section').hidden=!task.analysis;if(task.analysis){$('analysis-status').textContent=task.analysis.verified?'已取得成功执行记录。':'未取得成功执行记录；下面的说明不证明工具已运行。';$('analysis-output').textContent=task.analysis.executions.map(t=>t.stdout).join('\n')||task.analysis.description;}
  if(task.mcp_evidence){const item=node('li',task.mcp_evidence.verified?'MCP：已取得完成记录。':'MCP：缺少完成记录。');$('timeline').append(item);}
}
async function history(){const tasks=await api('/api/tasks');$('task-list').replaceChildren();if(!tasks.length){$('task-list').append(node('p','还没有研究任务。从一个真实问题开始。','muted'));return;}for(const task of tasks){const b=node('button',undefined,'history-item'+(selected===task.id?' active':''));b.append(node('strong',task.query),node('small',statuses[task.status]+' · '+new Date(task.created_at).toLocaleDateString('zh-CN')));b.onclick=()=>open(task.id);$('task-list').append(b);} }
async function open(id){selected=id;const version=++generation;clearTimeout(timer);try{const task=await api('/api/tasks/'+id);if(version!==generation)return;render(task);await history();if(['running','pending'].includes(task.status))timer=setTimeout(()=>poll(id,version),1200);}catch(e){message(e.message);} }
async function poll(id,version){if(version!==generation||selected!==id)return;try{const task=await api('/api/tasks/'+id);if(version!==generation)return;render(task);if(['running','pending'].includes(task.status))timer=setTimeout(()=>poll(id,version),1200);else await history();}catch(e){message(e.message);} }
$('research-form').onsubmit=async event=>{event.preventDefault();if(busy)return;message('');busy=true;$('submit').disabled=true;$('submit').firstChild.textContent='正在创建… ';try{const payload={query:$('question').value,web:$('web').checked,analyze:$('analyze').checked,mcp:$('mcp').checked};if($('scope').value.trim())payload.scope=$('scope').value.trim();if($('conversation').value.trim())payload.event={user:$('conversation').value,final:''};const task=await api('/api/tasks',{method:'POST',body:JSON.stringify(payload)});await open(task.id);}catch(e){message(e.message);}finally{busy=false;$('submit').disabled=false;$('submit').firstChild.textContent='开始研究 ';} };
$('resume').onclick=async()=>{if(busy||!selected)return;busy=true;$('resume').disabled=true;try{await api('/api/tasks/'+selected+'/resume',{method:'POST'});await open(selected);}catch(e){message(e.message);}finally{busy=false;$('resume').disabled=false;}};
$('refresh').onclick=()=>history().catch(e=>message(e.message));
$('new-task').onclick=()=>{selected=null;current=null;generation++;clearTimeout(timer);$('main').classList.remove('reading');$('result').hidden=true;$('sources').replaceChildren();$('timeline').replaceChildren();$('evidence-count').textContent='0';$('sources-empty').hidden=false;$('research-form').reset();message('');history().catch(e=>message(e.message));$('question').focus();};
$('example').onclick=()=>{$('question').value='退款任务重试时，怎样确保只产生一次业务效果？';$('conversation').value='退款请求可能重复传输，但必须保持幂等；同一退款业务只能产生一次实际退款效果。';$('conversation').closest('details').open=true;$('question').focus();};
async function init(){try{const settings=await api('/api/settings');$('connection').textContent=settings.credential_ready?'Otari 凭据已配置':'待连接 Otari';$('connection').classList.toggle('ready',settings.credential_ready);$('setup-note').hidden=settings.credential_ready;$('setup-note').textContent='当前尚未配置 Otari 凭据。请按启动指南在运行环境设置密钥，然后重启工作台；可先查看已保存的任务。';$('mcp').disabled=!settings.mcp_ready;$('mcp').parentElement.title=settings.mcp_ready?'使用配置的远程只读服务器':'先连接已发布的只读 MCP 服务器';const list=$('settings-list');for(const [key,value] of Object.entries(settings.models||{})){list.append(node('dt',key),node('dd',value));}list.append(node('dt','允许的官方域名'),node('dd',settings.official_domains.join('、')||'尚未配置'));await history();}catch(e){message(e.message);}}
init();
