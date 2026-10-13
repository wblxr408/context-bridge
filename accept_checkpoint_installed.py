"""Real installed client routes and the existing scheduled listener, with owned fixtures."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
import tomllib
import uuid

ROOT=Path(__file__).resolve().parent
SERVICE=Path.home()/'.codex/services/engineering-memory'
sys.path.insert(0,str(ROOT/'tests'))
from test_mcp_e2e import StdioClient,value
# Functional operations below use the deployed module, not the staged test module.
sys.path.insert(0,str(SERVICE/'app'))
from checkpoint_lifecycle import Lifecycle,gate

def main():
    config=json.loads((SERVICE/'config.json').read_text(encoding='utf-8'))
    user=Path.home()
    codex=tomllib.loads((user/'.codex/config.toml').read_text(encoding='utf-8-sig'))
    claude=json.loads((user/'.claude.json').read_text(encoding='utf-8-sig'))
    routes=[('Codex',codex['mcp_servers']['basic-memory']),('Claude',claude['mcpServers']['basic-memory'])]
    batch=uuid.uuid4().hex;session='checkpoint-acceptance-'+batch
    title='Checkpoint deployed acceptance '+batch
    directory='engineering/checkpoint-acceptance/'+batch
    phrase='紫罗兰账单验收'+batch
    clients=[];created=[];report={'batch':batch,'started':datetime.now(timezone.utc).isoformat(),
        'scope':'installed Codex/Claude MCP routes, real main fixture and original scheduled listener',
        'production_fast_minutes':config['checkpoint_fast_quarantine_minutes'],'clients':{},'operations':[]}
    engine=Lifecycle(config['vault'],SERVICE,tokenizer=config['checkpoint_tokenizer'],fast_minutes=1)
    op=None;summary=None;first=None
    try:
        for label,route in routes:
            env=os.environ.copy();env.update(route.get('env',{}),PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
            client=StdioClient([route['command'],*route.get('args',[])],env,ROOT/(label.lower()+'-checkpoint-installed.stderr.log'))
            clients.append((label,client))
            client.call('initialize',{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'installed-checkpoint-acceptance','version':'1'}})
            client.send('notifications/initialized',notification=True)
        writer=clients[0][1]
        for i in range(5):
            made=value(writer.tool('write_note',{'project':'main','directory':directory,'title':title+' '+str(i),
                'note_type':'codex_session','overwrite':False,'output_format':'json','metadata':{'agent':'codex','session_id':session,
                'cwd':str(ROOT/'acceptance'/batch),'started':f'2020-01-0{i+1}T00:00:00Z','status':'open'},
                'content':phrase+'：供应商重试失败已解决，协议冲突已修正；账单验收仍待完成。这些是本次验收专用的合成数据。'}))
            assert made['action']=='created',made
            created.append(made['permalink'])
        notes=[n for n in engine.inventory() if n['session']==session]
        assert len(notes)==5
        review={n['permalink']:{'coverage':'重试失败已解决、协议冲突修正；账单仍待验收已写入摘要，最新原件保留',
            'no_readers_confirmed':True,'reader_evidence':'Owned synthetic acceptance records; this runner owns both participating clients'} for n in notes}
        plan=engine.plan(review=review,lane='fast')
        assert len(plan['candidates'])==4 and all(c['session']==session for c in plan['candidates'])
        group=plan['candidates'][0]['group'];first=plan['candidates'][0]['permalink']
        op=plan['operation_id']
        drafts={group:{'reviewed':True,'sources':[c['permalink'] for c in plan['candidates']],
            'body':phrase+'：验收专用合成历史。供应商重试故障已解决，协议冲突已修正，账单验收仍待完成；最新原件保留供恢复。',
            'short_history_reason':'Five short identical synthetic acceptance records'}}
        applied=engine.apply(plan,drafts)
        assert applied['quarantined']==4 and applied['state']=='quarantined'
        report['operations'].append({'state':'quarantined','count':4,'actual_fast_minutes':1})
        for label,client in clients:
            exact=value(client.tool('read_note',{'project':'main','identifier':first,'output_format':'json'}))
            assert exact['state']=='quarantined' and '账单验收仍待完成' in exact['content']
            summary=exact['summary']
            current=value(client.tool('memory_recall',{'query':phrase,'limit':100}))['results']
            assert summary not in {r['permalink'] for r in current}
            assert not set(c['permalink'] for c in plan['candidates'])&{r['permalink'] for r in current}
            history=value(client.tool('memory_recall',{'query':phrase,'limit':100,'include_history':True}))['results']
            assert summary in {r['permalink'] for r in history}
            native=value(client.tool('search_notes',{'project':'main','query':title,'search_type':'text',
                'note_types':['codex_session'],'output_format':'json','page_size':100}))
            assert {r['permalink'] for r in native['results']}=={created[-1]}
            recent=value(client.tool('recent_activity',{'project':'main','timeframe':'1d','page_size':100,'output_format':'json'}))
            assert summary not in json.dumps(recent,ensure_ascii=False)
            report['clients'][label]={'status':'passed_before_expiry','contracts':['quarantine exact read','current/history isolation','native index retirement','automatic activity filtering']}
            print(json.dumps({'client':label,'phase':'quarantine and history','status':'passed'},ensure_ascii=False),flush=True)
        restored=engine.restore(first)
        assert restored['state']=='restored' and restored['pinned'] is True
        for label,client in clients:
            restored_read=value(client.tool('read_note',{'project':'main','identifier':first,'output_format':'json'}))
            assert '账单验收仍待完成' in restored_read['content']
            report['clients'][label]['contracts'].append('restore returns original source')
        new_plan=engine.plan(review=review,lane='fast')
        assert first in new_plan['protected'] and first not in {c['permalink'] for c in new_plan['candidates']}
        expiring=plan['candidates'][1]['permalink'];deadline=engine.read(expiring)['purge_after']
        # No purge command, mock time or extra maintenance process: the original
        # scheduled listener must perform the business transition at real expiry.
        limit=time.monotonic()+420
        while time.monotonic()<limit:
            state=value(writer.tool('read_note',{'project':'main','identifier':expiring,'output_format':'json'}))
            if time.time()<deadline:assert state['state']=='quarantined'
            if state['state']=='purged':break
            print(json.dumps({'phase':'waiting for existing scheduled maintenance','remaining_to_eligibility':max(0,round(deadline-time.time(),1))}),flush=True)
            time.sleep(20)
        else:raise AssertionError('Existing scheduled listener did not purge due owned fixtures within one cadence')
        assert time.time()>=deadline
        for label,client in clients:
            expired=value(client.tool('read_note',{'project':'main','identifier':expiring,'output_format':'json'}))
            assert expired['state']=='purged' and expired['summary']==summary and 'content' not in expired
            latest=value(client.tool('read_note',{'project':'main','identifier':created[-1],'output_format':'json'}))
            assert phrase in latest['content']
            history_note=value(client.tool('read_note',{'project':'main','identifier':summary,'output_format':'json'}))
            assert '账单验收仍待完成' in history_note['content']
            report['clients'][label]['status']='passed'
            report['clients'][label]['contracts']+=['real scheduled expiry','exact expired cursor tombstone','latest recovery source retained','summary readable after deletion']
        data=engine.load();records=[r for r in data['records'].values() if r['operation_id']==op]
        assert sum(r['state']=='purged' for r in records)==3
        assert sum(r['state']=='restored' for r in records)==1
        report['operations'].append({'state':'scheduled_purge','count':3,'real_clock':True,'deadline_utc':datetime.fromtimestamp(deadline,timezone.utc).isoformat()})
        report['operations'].append({'state':'restored_and_pinned','count':1})
        report['status']='passed'
    finally:
        # Remove only this runner's exact fixture identities. No directory delete.
        cleanup=[]
        if clients:
            writer=clients[0][1]
            data=engine.load()
            for pid in created:
                record=data['records'].get(pid)
                if record and record['state'] in {'quarantined','moving','purging'}:
                    engine.restore(pid)
                if not record or record['state']!='purged':
                    cleanup.append(value(writer.tool('delete_note',{'project':'main','identifier':pid,'is_directory':False,'output_format':'json'})))
            if summary:
                cleanup.append(value(writer.tool('delete_note',{'project':'main','identifier':summary,'is_directory':False,'output_format':'json'})))
            with gate(SERVICE):
                data=engine.load()
                for pid in created:data['records'].pop(pid,None)
                data['pinned']=[pid for pid in data['pinned'] if pid not in created]
                if op:data['operations'].pop(op,None)
                engine.save(data)
        for _,client in clients:client.close()
        report['fixture_cleanup']={'exact_native_deletions':len(cleanup),'results':cleanup}
        report['finished']=datetime.now(timezone.utc).isoformat()
        (ROOT/'evaluation-checkpoint-installed.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
