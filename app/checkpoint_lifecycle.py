"""Reviewed checkpoint retirement in the existing engineering-memory service.

Plans contain identities and versions, never an archive of the original corpus.
Only explicit apply moves data. The listener only finishes already approved work.
"""
from collections import defaultdict
from contextlib import contextmanager,closing
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
import subprocess
import sys
import time
from uuid import uuid4, uuid5, NAMESPACE_URL

from memory_runtime import atomic_text, markdown, parse_note, scope_key


def safe_path(root, relative):
    root=Path(root).absolute(); relative=Path(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Path must be relative to the registered root')
    target=root/relative
    for item in [target,*target.parents]:
        try:
            info=item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
            raise ValueError('Reparse/symbolic-link paths are not lifecycle targets')
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('Path escapes registered root')
    return target


def version(path):
    s=path.stat()
    return [s.st_mtime_ns,s.st_size,s.st_ino]


def timestamp(note):
    try:
        dt=datetime.fromisoformat(str(note['meta']['started']).replace('Z','+00:00'))
        if dt.tzinfo is not None:return dt.timestamp()
    except (ValueError,KeyError):pass
    match=re.search(r'\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z',note['title'])
    if match:return datetime.strptime(match[0],'%Y-%m-%dT%H-%M-%SZ').replace(tzinfo=timezone.utc).timestamp()
    return None


def is_history(meta):
    return meta.get('type')=='checkpoint_history' or meta.get('auto_inject') is False or meta.get('historical') is True


@contextmanager
def gate(home):
    home.mkdir(parents=True,exist_ok=True)
    with safe_path(home,'checkpoint-lifecycle.lock').open('a+b') as handle:
        handle.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:yield
        finally:
            handle.seek(0)
            if os.name=='nt':msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(handle,fcntl.LOCK_UN)


class Lifecycle:
    def __init__(self,vault,home,*,counter=None,clock=time.time,native_sync=None,tokenizer=None,fast_minutes=60):
        self.vault=Path(vault).absolute();self.home=Path(home).absolute()
        safe_path(self.vault,'.');safe_path(self.home,'.')
        self.quarantine=self.home/'checkpoint-quarantine'
        if self.quarantine.resolve().is_relative_to(self.vault.resolve()):
            raise ValueError('Quarantine must be outside the searchable vault')
        self.clock=clock;self.counter=counter;self.tokenizer=tokenizer
        self.native_sync=native_sync or self.sync_native
        if not isinstance(fast_minutes,(int,float)) or fast_minutes<1:raise ValueError('Fast quarantine must be positive')
        self.fast_minutes=fast_minutes

    def load(self):
        path=safe_path(self.home,'checkpoint-lifecycle.json')
        if not path.exists():return {'schema':1,'revision':0,'records':{},'operations':{},'pinned':[],'active_sessions':[]}
        data=json.loads(path.read_text(encoding='utf-8'))
        if data.get('schema')!=1:raise ValueError('Unsupported lifecycle state schema')
        return data

    def save(self,data):
        data['revision']+=1
        atomic_text(safe_path(self.home,'checkpoint-lifecycle.json'),json.dumps(data,ensure_ascii=False,indent=2))

    def inventory(self):
        notes=[]
        for path in self.vault.rglob('*.md'):
            if any(x.startswith('.') for x in path.relative_to(self.vault).parts):continue
            safe_path(self.vault,path.relative_to(self.vault))
            note=parse_note(path,self.vault)
            if note['meta'].get('type') not in {'codex_session','coding_session'}:continue
            meta=note['meta'];agent=meta.get('agent');session=meta.get('session_id')
            if not agent and meta.get('codex_session_id'):agent,session='codex',meta['codex_session_id']
            group=json.dumps([agent,session,scope_key(meta.get('cwd'))],ensure_ascii=False)
            notes.append({**note,'group':group,'agent':agent,'session':session,'stamp':timestamp(note),
                'version':version(path)})
        return notes

    def protections(self,notes,data,active=()):
        result={};groups=defaultdict(list);dependencies=set()
        active=set(active)|set(data.get('active_sessions',[]))
        for n in notes:
            groups[n['group']].append(n)
            dep=n['meta'].get('depends_on',[])
            dependencies.update(dep if isinstance(dep,list) else [dep])
        for members in groups.values():
            latest=max(members,key=lambda n:(n['stamp'] or float('inf'),n['path']))
            result[latest['permalink']]='latest recovery point'
        for n in notes:
            m=n['meta'];pid=n['permalink']
            if not n['agent'] or not n['session'] or n['stamp'] is None or not m.get('cwd'):
                result[pid]='unknown ownership or source timestamp'
            elif m.get('pinned') or m.get('in_use') or pid in data['pinned']:
                result[pid]='pinned or in use'
            elif n['session'] in active:result[pid]='active session protected'
            elif pid in dependencies or n['title'] in dependencies:result[pid]='explicit original dependency'
            elif pid in data['records'] and data['records'][pid]['state']!='restored':
                result[pid]='retired identity recreated; explicit reconciliation required'
        return result

    def plan(self,*,review=None,fraction=.8,lane='ordinary',active_sessions=()):
        if lane not in {'ordinary','fast','count'} or not 0<=fraction<=1:raise ValueError('Invalid cleanup policy')
        review=review or {};data=self.load();notes=self.inventory()
        protected=self.protections(notes,data,active_sessions);candidates=[]
        counts=defaultdict(int);folders=defaultdict(int);removed=defaultdict(int);folder_removed=defaultdict(int)
        for n in notes:
            counts[n['group']]+=1;folders[scope_key(n['scope'])]+=1
        for n in sorted(notes,key=lambda n:(n['stamp'] or float('inf'),n['path'])):
            pid=n['permalink']
            if pid in protected:continue
            folder=scope_key(n['scope'])
            if lane=='count' and not ((counts[n['group']]>8 and counts[n['group']]-removed[n['group']]>3) or
                    (folders[folder]>20 and folders[folder]-folder_removed[folder]>10)):
                protected[pid]='below count threshold or retention target';continue
            if lane=='ordinary' and self.clock()-(n['stamp'] or self.clock())<86400:
                protected[pid]='ordinary source younger than 24 hours';continue
            if not review.get(pid,{}).get('coverage'):
                protected[pid]='pending semantic coverage review';continue
            if review[pid].get('no_readers_confirmed') is not True or not review[pid].get('reader_evidence'):
                protected[pid]='reader ownership not reconciled';continue
            candidates.append({k:n[k] for k in ('permalink','title','path','group','agent','session','stamp','version')})
            candidates[-1]['coverage']=review[pid]['coverage']
            candidates[-1]['no_readers_confirmed']=True
            candidates[-1]['reader_evidence']=review[pid]['reader_evidence']
            removed[n['group']]+=1;folder_removed[folder]+=1
        target=math.floor(len(notes)*fraction)
        return {'operation_id':uuid4().hex,'revision':data['revision'],'created':self.clock(),'lane':lane,
            'vault':str(self.vault),'total':len(notes),'target':target,'candidates':candidates[:target],
            'protected':protected,'active_sessions':list(active_sessions),'shortfall':max(0,target-len(candidates)),
            'inventory':{n['path']:n['version'] for n in notes}}

    def count(self,text):
        if self.counter:return self.counter(text)
        if not self.tokenizer:raise ValueError('A fixed tokenizer path is required')
        from tokenizers import Tokenizer
        tokenizer=Tokenizer.from_file(str(self.tokenizer));tokenizer.no_truncation();tokenizer.no_padding()
        return len(tokenizer.encode(text,add_special_tokens=False).ids)

    def apply(self,plan,drafts):
        with gate(self.home):
            data=self.load();op=plan['operation_id']
            if op in data['operations']:
                self.recover(data)
                return self.report(data,op)
            notes=self.inventory();by_id={n['permalink']:n for n in notes}
            if str(self.vault)!=plan['vault'] or data['revision']!=plan['revision'] or \
                    {n['path']:n['version'] for n in notes}!=plan['inventory']:
                raise ValueError('Stale plan; inventory or protection changed')
            protection=self.protections(notes,data,plan['active_sessions']);prepared={}
            if len({c['permalink'] for c in plan['candidates']})!=len(plan['candidates']):
                raise ValueError('Duplicate source identities in plan')
            for c in plan['candidates']:
                safe_path(self.vault,c['path'])
                if c['permalink'] in protection:raise ValueError('Candidate is now protected')
                n=by_id[c['permalink']]
                if any(c[k]!=n[k] for k in ('path','group','version','session','agent')) or not c.get('coverage') or \
                        c.get('no_readers_confirmed') is not True or not c.get('reader_evidence'):
                    raise ValueError('Candidate identity mismatch or missing review')
            for group in {c['group'] for c in plan['candidates']}:
                draft=drafts.get(group,{})
                sources=sorted(c['permalink'] for c in plan['candidates'] if c['group']==group)
                if not draft.get('reviewed') or sorted(draft.get('sources',[]))!=sources or not draft.get('body','').strip():
                    raise ValueError('Summary requires reviewed exact source coverage')
                sid=uuid5(NAMESPACE_URL,group).hex
                path=f'engineering/checkpoint-history/{sid}.md';permalink='main/'+path[:-3]
                target=safe_path(self.vault,path)
                # Revisions require a new reviewed draft including the existing summary.
                old=None
                if target.exists():
                    old=parse_note(target,self.vault)
                    if old['meta'].get('checkpoint_group')!=group or draft.get('previous_version')!=version(target):
                        raise ValueError('Summary changed or previous history not reviewed')
                meta={'title':'Checkpoint history '+sid[:12],'type':'checkpoint_history','permalink':permalink,
                    'historical':True,'auto_inject':False,'checkpoint_group':group,
                    'scope':json.loads(group)[2],
                    'source_operation_id':op,'source_count':len(set(sources+[pid for pid,r in data['records'].items() if r['group']==group])),
                    'tokenizer':str(self.tokenizer or 'injected-test-counter'),'revision':1+(old['meta'].get('revision',0) if old else 0)}
                text=markdown(meta,draft['body']);count=self.count(text)
                if count>2000 or (count<1000 and not draft.get('short_history_reason')):
                    raise ValueError('Summary outside tokenizer budget; rewrite without padding')
                prepared[group]={'path':path,'permalink':permalink,'text':text,'tokens':count,
                    'previous_version':version(target) if old else None}
            # Publish and read back every summary before the first source is moved.
            for group,summary in prepared.items():
                target=safe_path(self.vault,summary['path'])
                previous=summary['previous_version']
                if previous is not None:
                    if version(target)!=previous:raise ValueError('Summary changed before publication')
                    backup_path=f'checkpoint-summary-revisions/{op}/{target.name}'
                    backup=safe_path(self.home,backup_path)
                    prior_text=target.read_text(encoding='utf-8')
                    atomic_text(backup,prior_text)
                    if backup.read_text(encoding='utf-8')!=prior_text:raise ValueError('Previous summary read-back failed')
                    deadline=self.clock()+(72*3600 if plan['lane']=='ordinary' else self.fast_minutes*60)
                    deadlines=[r['purge_after'] for r in data['records'].values() if r['group']==group]
                    data.setdefault('summary_backups',{})[backup_path]={'group':group,'version':version(backup),
                        'summary_path':summary['path'],'purge_after':max([deadline,*deadlines]),'state':'retained'}
                # Persist the reviewed publication before replacing the live summary.
                # This journal contains summary text only, never a source transcript.
                data.setdefault('summary_updates',{})[group]=summary
                self.save(data)
                self.publish_summaries(data)
                summary['version']=version(target)
            data['active_sessions']=sorted(set(data['active_sessions'])|set(plan['active_sessions']))
            data['operations'][op]={'state':'applying','created':self.clock(),'lane':plan['lane'],'expected':len(plan['candidates'])}
            self.save(data)
            for c in plan['candidates']:
                source=safe_path(self.vault,c['path'])
                if version(source)!=c['version']:raise ValueError('Source changed during apply')
                summary=prepared[c['group']];qid=uuid5(NAMESPACE_URL,c['permalink']).hex+'.md'
                dest=safe_path(self.quarantine,qid);dest.parent.mkdir(parents=True,exist_ok=True)
                if dest.exists():raise ValueError('Quarantine destination occupied')
                record={**c,'operation_id':op,'state':'moving','quarantine':qid,'summary':summary['permalink'],
                    'summary_path':summary['path'],'summary_version':summary['version'],'summary_tokens':summary['tokens'],
                    'quarantined_at':self.clock(),'purge_after':self.clock()+(72*3600 if plan['lane']=='ordinary' else self.fast_minutes*60),
                    'native_synced':False}
                data['records'][c['permalink']]=record;self.save(data)
                source.rename(dest)
                record['state']='quarantined';self.save(data)
            self.finish(data,op)
            return self.report(data,op)

    def publish_summaries(self,data):
        for group,summary in list(data.get('summary_updates',{}).items()):
            target=safe_path(self.vault,summary['path'])
            current=target.read_text(encoding='utf-8') if target.exists() else None
            if current!=summary['text']:
                previous=summary['previous_version']
                if (previous is None and current is not None) or \
                        (previous is not None and (current is None or version(target)!=previous)):
                    raise ValueError('Summary changed during interrupted publication; preserve history')
                atomic_text(target,summary['text'])
                if target.read_text(encoding='utf-8')!=summary['text']:raise ValueError('Summary read-back failed')
            current_version=version(target)
            for record in data['records'].values():
                if record['group']==group:
                    record['summary_version']=current_version
                    record['summary_tokens']=summary['tokens']
            del data['summary_updates'][group]
            self.save(data)

    def retire_caches(self,data):
        state=safe_path(self.home,'state.sqlite')
        if not state.exists():return
        retired=[r for r in data['records'].values() if r['state']!='restored']
        with closing(sqlite3.connect(state,timeout=30)) as db, db:
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'memory_vectors' in tables:
                db.executemany('DELETE FROM memory_vectors WHERE path=?',[(r['path'],) for r in retired])
            # Derived text may quote originals. Rebuild pages and per-session injection caches.
            for table in ('memory_pages','memory_injections'):
                if table in tables:db.execute('DELETE FROM '+table)
        pages=self.vault/'engineering/knowledge-pages'
        if pages.exists():
            for page in pages.rglob('*.md'):
                safe=safe_path(self.vault,page.relative_to(self.vault));text=safe.read_text(encoding='utf-8')
                note=parse_note(safe,self.vault)
                if note['meta'].get('managed_by')=='engineering-memory' and any(r['permalink'] in text for r in retired):safe.unlink()

    def sync_native(self):
        # The native coordinator always reconciles missing paths. force_full
        # additionally reprocesses every unchanged note and is unnecessary for
        # retirement; on a live corpus that work can exceed the sync deadline.
        code='from basic_memory.cli.commands.command_utils import run_with_cleanup,run_project_index; run_with_cleanup(run_project_index("main",force_full=False,run_in_background=False))'
        result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,encoding='utf-8',
            timeout=180,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode:raise RuntimeError('Native index retirement failed: '+result.stderr[-800:])

    def finish(self,data,op):
        self.retire_caches(data);self.native_sync()
        for r in data['records'].values():
            if r['operation_id']==op:r['native_synced']=True
        count=sum(r['operation_id']==op for r in data['records'].values())
        data['operations'][op]['state']='quarantined' if count==data['operations'][op]['expected'] else 'partial'
        self.save(data)

    def recover(self,data):
        self.publish_summaries(data)
        for path,backup in data.get('summary_backups',{}).items():
            if backup['state']=='purging' and not safe_path(self.home,path).exists():
                backup['state']='purged';backup['purged_at']=self.clock();self.save(data)
        for r in data['records'].values():
            source=safe_path(self.vault,r['path']);dest=safe_path(self.quarantine,r['quarantine'])
            if r['state']=='moving':
                if source.exists() and not dest.exists() and version(source)==r['version']:source.rename(dest)
                if dest.exists() and not source.exists() and version(dest)==r['version']:r['state']='quarantined';self.save(data)
                else:raise ValueError('Ambiguous interrupted move; preserve both paths')
            elif r['state']=='restoring':
                if dest.exists() and not source.exists():dest.rename(source)
                if source.exists() and not dest.exists():
                    r['state']='restored';data['pinned']=sorted(set(data['pinned'])|{r['permalink']});self.save(data)
                else:raise ValueError('Ambiguous interrupted restore')
            elif r['state']=='purging' and not dest.exists():
                r['state']='purged';self.save(data)
        for op,value in data['operations'].items():
            if value['state']=='applying':self.finish(data,op)

    def report(self,data,op):
        records=[r for r in data['records'].values() if r['operation_id']==op]
        return {'operation_id':op,'state':data['operations'][op]['state'],'expected':data['operations'][op]['expected'],
            'quarantined':sum(r['state']=='quarantined' for r in records),
            'purged':sum(r['state']=='purged' for r in records),'records':records}

    def read(self,identifier):
        key=str(identifier).removeprefix('memory://').strip('/')
        data=self.load()
        record=next((r for r in data['records'].values() if key in {r['permalink'],r['path'],r['title']}),None)
        if record is None:return None
        result={k:record[k] for k in ('permalink','title','state','summary','summary_path','purge_after')}
        if record['state'] in {'quarantined','moving','purging'}:
            result['content']=safe_path(self.quarantine,record['quarantine']).read_text(encoding='utf-8')
        if record['state']=='restored':result['pinned']=True
        return result

    def restore(self,identifier):
        with gate(self.home):
            data=self.load();self.recover(data);r=data['records'][identifier]
            if r['state']=='restored':return self.read(identifier)
            if r['state']!='quarantined':raise ValueError('Original is not recoverable from quarantine')
            source=safe_path(self.vault,r['path']);dest=safe_path(self.quarantine,r['quarantine'])
            if source.exists():raise ValueError('Restore would overwrite an existing source')
            r['state']='restoring';self.save(data);source.parent.mkdir(parents=True,exist_ok=True);dest.rename(source)
            r['state']='restored';data['pinned']=sorted(set(data['pinned'])|{identifier});self.save(data)
            self.native_sync();return self.read(identifier)

    def purge(self):
        with gate(self.home):
            data=self.load();self.recover(data);purged=0;blocked={}
            notes=self.inventory();dependencies={d for n in notes for d in
                (n['meta'].get('depends_on',[]) if isinstance(n['meta'].get('depends_on',[]),list) else [n['meta']['depends_on']])}
            for pid,r in data['records'].items():
                if r['state'] not in {'quarantined','purging'} or self.clock()<r['purge_after']:continue
                summary=safe_path(self.vault,r['summary_path']);dest=safe_path(self.quarantine,r['quarantine'])
                if pid in data['pinned'] or r['session'] in data['active_sessions'] or pid in dependencies or r['title'] in dependencies:
                    blocked[pid]='protected';continue
                if not r['native_synced'] or not summary.exists() or version(summary)!=r['summary_version']:
                    blocked[pid]='summary or native retirement requires review';continue
                if version(dest)!=r['version']:
                    blocked[pid]='quarantine original changed';continue
                # No recursive deletion: one prevalidated registered file only.
                r['state']='purging';self.save(data);dest.unlink()
                r['state']='purged';r['purged_at']=self.clock();self.save(data);purged+=1
            purged_summaries=0
            for path,backup in data.get('summary_backups',{}).items():
                if backup['state'] not in {'retained','purging'} or self.clock()<backup['purge_after']:continue
                target=safe_path(self.home,path);summary=safe_path(self.vault,backup['summary_path'])
                members=[r for r in data['records'].values() if r['group']==backup['group']]
                if not summary.exists() or any(r['summary_version']!=version(summary) for r in members):
                    blocked[path]='current summary requires review';continue
                if version(target)!=backup['version']:
                    blocked[path]='previous summary changed';continue
                backup['state']='purging';self.save(data);target.unlink()
                backup['state']='purged';backup['purged_at']=self.clock();self.save(data);purged_summaries+=1
            return {'purged':purged,'purged_summaries':purged_summaries,'blocked':blocked}


def from_config(config,home):
    return Lifecycle(config['vault'],home,tokenizer=config.get('checkpoint_tokenizer'),
        fast_minutes=config.get('checkpoint_fast_quarantine_minutes',60))
