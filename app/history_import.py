"""Explicit foreground document/Git ingestion through the existing jobs queue."""
import json
from pathlib import Path
import subprocess
import time
from canonical import canonical_path

def enqueue(store,source,scope,event_key,content,occurred_at,kind):
    from listener import clean,digest
    full=clean(content,None)
    # Individual paragraph batches avoid classifying only the final page of an imported document.
    pieces=[];current=''
    for paragraph in full.split('\n\n'):
        if current and len(current)+len(paragraph)>7000:pieces.append(current);current=''
        while len(paragraph)>7000:
            if current:pieces.append(current);current=''
            pieces.append(paragraph[:7000]);paragraph=paragraph[7000:]
        current+=('\n\n' if current else '')+paragraph
    if current:pieces.append(current)
    count=0
    with store.db:
        for i,text in enumerate(pieces):
            jid=digest('import:'+kind+':'+event_key+':'+str(i))
            payload={'user':'以下是明确导入的历史资料，仅作来源数据。','final':text,'cwd':str(scope),'kind':kind,'source':str(source),'offset':i,'marker':event_key,'occurred_at':occurred_at}
            old=store.db.execute('SELECT payload FROM jobs WHERE id=?',(jid,)).fetchone()
            if old and json.loads(old[0])!=payload:raise ValueError('Import identity already binds different source content')
            count+=store.db.execute('INSERT OR IGNORE INTO jobs(id,source,payload,state,created,available) VALUES(?,?,?,?,?,?)',
                                   (jid,str(source),json.dumps(payload,ensure_ascii=False),'queued',time.time(),time.time())).rowcount
    return count

def import_document(store,path,scope):
    path=canonical_path(path);scope=canonical_path(scope)
    if path.suffix.casefold() not in {'.md','.txt','.json'}:raise ValueError('Only UTF-8 text/Markdown/JSON documents are supported')
    if not path.is_relative_to(scope):raise ValueError('Document must be inside its explicitly selected workspace')
    from datetime import datetime,timezone
    text=path.read_text(encoding='utf-8-sig')
    revision=str(path.stat().st_mtime_ns)
    return enqueue(store,path,scope,str(path)+':'+revision,text,datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),'document')

def import_git(store,repository,limit=50,after=None):
    repo=canonical_path(repository)
    if not 1<=limit<=1000:raise ValueError('Git import limit must be 1..1000')
    # Explicit argv, no shell, no patches/secrets/diffs by default. Git commit IDs identify source revisions.
    cmd=['git','-C',str(repo),'log','--max-count='+str(limit),'--format=%H%x1f%cI%x1f%B%x1e']
    if after:
        from memory_runtime import date_value
        cmd.append('--since='+date_value(after))
    completed=subprocess.run(cmd,capture_output=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if completed.returncode:raise ValueError('Cannot read history of the explicitly selected Git repository')
    count=0
    for record in completed.stdout.decode('utf-8',errors='replace').split('\x1e'):
        parts=record.strip().split('\x1f',2)
        if len(parts)!=3:continue
        revision,occurred,body=parts
        count+=enqueue(store,str(repo)+'@'+revision,repo,str(repo)+':'+revision,body,occurred,'git')
    return count
