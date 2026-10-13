"""Reviewable, targeted config transforms and deployment backups."""
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import tomllib
from datetime import datetime,timezone
from uuid import uuid4
import sys
import copy
sys.path.insert(0,str(Path(__file__).parent/'app'))
from canonical import canonical_path
from memory_integration import append_hook_config

EMBEDDING='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
RERANKER='BAAI/bge-reranker-base'

def patch_toml(raw,python):
    lines=raw.splitlines();out=[];table='';command=False;hooks=False;has_feature_table=False
    for line in lines:
        header=re.fullmatch(r'\s*\[([^\[\]]+)\]\s*(?:#.*)?',line)
        if header:
            if table=='features' and not hooks:out.append('hooks = true');hooks=True
            table=header.group(1)
            has_feature_table|=table=='features'
        if table=='mcp_servers.basic-memory' and re.match(r'\s*command\s*=',line):
            line='command = '+json.dumps(str(python));command=True
        if table=='features' and re.match(r'\s*(hooks|codex_hooks)\s*=',line):
            # Prefer the current native key and avoid two conflicting aliases.
            if hooks:continue
            line='hooks = true';hooks=True
        out.append(line)
    if table=='features' and not hooks:out.append('hooks = true');hooks=True
    if not has_feature_table:out+=['','[features]','hooks = true']
    if not command:raise ValueError('Existing basic-memory command is missing; cannot infer server configuration')
    result='\n'.join(out)+'\n'
    parsed=tomllib.loads(result)
    if parsed['mcp_servers']['basic-memory']['command']!=str(python) or parsed['features']['hooks'] is not True:raise ValueError('Configuration transform did not preserve target contract')
    return result

def patch_service(config,cache):
    return {**config,'memory_models':True,'model_cache':str(cache),'memory_embedding_model':EMBEDDING,'memory_reranker_model':RERANKER}

def patch_claude(config,python,bridge):
    result=copy.deepcopy(config)
    server=result.get('mcpServers',{}).get('basic-memory')
    if not isinstance(server,dict) or server.get('type','stdio')!='stdio':
        raise ValueError('The existing Claude Basic Memory server must be a known local stdio route')
    args=server.get('args',[])
    if args!=['mcp'] and args!=[str(bridge)]:
        raise ValueError('Existing Claude memory command has extra options; preserve them through an explicit supported adapter')
    server.update(type='stdio',command=str(python),args=[str(bridge)])
    return result

def patch_basic_memory(config,cache):
    return {**config,'semantic_search_enabled':True,'semantic_embedding_provider':'fastembed','semantic_embedding_model':EMBEDDING,
            'semantic_embedding_dimensions':384,'semantic_embedding_cache_dir':str(cache),'semantic_embedding_threads':2,
            'semantic_embedding_parallel':1,'semantic_embedding_batch_size':16,'reranker_enabled':True,
            'reranker_provider':'fastembed','reranker_model':RERANKER,'reranker_candidates':20}

def hook_command(python,service):
    return '"'+str(python)+'" "'+str(service/'app/memory_cli.py')+'" hook'

class Backup:
    def __init__(self,folder,allowed):
        self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=False)
        self.allowed=[Path(p).absolute() for p in allowed];self.entries=[]
    def check(self,path):
        path=Path(path).absolute()
        if not any(path==root or path.is_relative_to(root) for root in self.allowed):raise ValueError('Deployment target is not explicitly allowed')
        parent=path if path.exists() else path.parent
        while not parent.exists():parent=parent.parent
        actual=canonical_path(parent)
        # Deployment targets have been selected with their exact known junction targets.
        if not any(actual==root or actual.is_relative_to(root) or root.is_relative_to(actual) for root in self.allowed):raise ValueError('Deployment target is redirected outside the selected roots')
        return path
    def remember(self,path):
        path=self.check(path)
        if any(e['target']==str(path) for e in self.entries):return
        entry={'target':str(path),'existed':path.is_file()}
        if entry['existed']:
            saved=self.folder/(str(len(self.entries))+'-'+path.name)
            if path.suffix=='.sqlite':
                source=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True);dest=sqlite3.connect(saved)
                try:source.backup(dest)
                finally:source.close();dest.close()
            else:shutil.copy2(path,saved)
            entry['backup']=saved.name
        self.entries.append(entry);self.flush()
    def flush(self): (self.folder/'restore.json').write_text(json.dumps({'allowed':[str(p) for p in self.allowed],'files':self.entries},ensure_ascii=False,indent=2),encoding='utf-8')
    def write(self,path,content):
        self.remember(path);path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_name(path.name+'.'+uuid4().hex+'.tmp')
        temporary.write_text(content,encoding='utf-8');os.replace(temporary,path)
    def copy(self,source,target):
        self.remember(target);target=Path(target);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)

def restore(folder):
    folder=canonical_path(folder);data=json.loads((folder/'restore.json').read_text(encoding='utf-8'))
    guard=object.__new__(Backup);guard.allowed=[Path(p) for p in data['allowed']]
    for entry in reversed(data['files']):
        target=guard.check(entry['target'])
        if entry['existed']:
            if target.suffix=='.sqlite':
                source=sqlite3.connect((folder/entry['backup']).as_uri()+'?mode=ro',uri=True)
                destination=sqlite3.connect(target)
                try:source.backup(destination)
                finally:source.close();destination.close()
            else:shutil.copy2(folder/entry['backup'],target)
        elif target.is_file():target.unlink()
    return {'status':'restored','files':len(data['files'])}
