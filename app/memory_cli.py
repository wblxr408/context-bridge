"""Foreground memory tools and native hook adapter; no extra observer process."""
import argparse
import json
from pathlib import Path
import sys
from memory_runtime import runtime_from_config
from memory_integration import hook_context
from canonical import canonical_path

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['recall','reflect','page','hook','backfill','retry-failed','import-document','import-git','checkpoint-plan','checkpoint-apply','checkpoint-purge','checkpoint-restore'])
    parser.add_argument('query',nargs='?')
    parser.add_argument('--name')
    parser.add_argument('--scope')
    parser.add_argument('--home',default=str(Path.home()/'.codex/services/engineering-memory'))
    parser.add_argument('--source')
    parser.add_argument('--kind',choices=['codex','claude'])
    parser.add_argument('--limit',type=int,default=50)
    parser.add_argument('--after')
    parser.add_argument('--job',action='append')
    parser.add_argument('--reason')
    parser.add_argument('--review')
    parser.add_argument('--drafts')
    parser.add_argument('--fraction',type=float,default=.8)
    parser.add_argument('--lane',choices=['ordinary','fast','count'],default='ordinary')
    parser.add_argument('--active-session',action='append',default=[])
    args=parser.parse_args()
    home=Path(args.home);config=json.loads((home/'config.json').read_text(encoding='utf-8'))
    if args.action.startswith('checkpoint-'):
        from checkpoint_lifecycle import from_config
        engine=from_config(config,home)
        load=lambda path:json.loads(Path(path).read_text(encoding='utf-8'))
        if args.action=='checkpoint-plan':
            result=engine.plan(review=load(args.review) if args.review else {},fraction=args.fraction,
                lane=args.lane,active_sessions=args.active_session)
        elif args.action=='checkpoint-apply':
            if not args.source or not args.drafts:parser.error('Apply requires --source plan and --drafts reviewed summaries')
            result=engine.apply(load(args.source),load(args.drafts))
        elif args.action=='checkpoint-restore':result=engine.restore(args.query)
        else:result=engine.purge()
        print(json.dumps(result,ensure_ascii=False));return
    if args.action=='retry-failed':
        from listener import Store
        if not args.job or not args.reason:parser.error('Recovery requires --job IDs and --reason')
        store=Store(home)
        try:print(json.dumps({'requeued':store.retry_jobs(args.job,args.reason),'status':'queued_not_yet_classified'}))
        finally:store.db.close()
        return
    if args.action.startswith('import-'):
        from listener import Store
        from history_import import import_document,import_git
        store=Store(home)
        try:
            if args.action=='import-document':
                if not args.source or not args.scope:parser.error('Document import requires --source and --scope')
                count=import_document(store,args.source,args.scope)
            else:
                if not args.scope:parser.error('Git import requires --scope repository')
                count=import_git(store,args.scope,args.limit,args.after)
            print(json.dumps({'queued':count,'status':'queued_not_yet_classified'}))
        finally:store.db.close()
        return
    if args.action=='backfill':
        from listener import Store
        if not args.source or not args.kind:
            parser.error('backfill requires --source and --kind')
        source=canonical_path(args.source)
        allowed=[canonical_path(s['path']) for s in config['sources'] if s['kind']==args.kind and s.get('enabled',True)]
        if not any(source.is_relative_to(root) for root in allowed):
            raise ValueError('History source is outside configured local sources')
        store=Store(home)
        try:
            count=0;stats={'queued':0,'filtered':0}
            paths=[source] if source.is_file() else source.rglob('*.jsonl')
            for path in paths:
                if 'subagents' not in path.parts:
                    path=canonical_path(path)
                    if not path.is_relative_to(source if source.is_dir() else source.parent):
                        raise ValueError('History source link escapes the selected import directory')
                    # Explicit history import ignores first-install baseline and event-age cutoff.
                    while True:
                        before=store.db.execute('SELECT offset FROM cursors WHERE path=?',('backfill:'+str(path),)).fetchone()
                        count+=store.backfill(path,args.kind,stats=stats)
                        after=store.db.execute('SELECT offset FROM cursors WHERE path=?',('backfill:'+str(path),)).fetchone()
                        if before and after[0]==before[0] or after[0]>=path.stat().st_size: break
            print(json.dumps({'events_added':count,**stats,'source':str(source),
                              'status':'queued_not_yet_classified' if stats['queued'] else 'history_current'}))
        finally: store.db.close()
        return
    memory=runtime_from_config(config,home)
    try:
        if args.action=='hook':
            payload=json.load(sys.stdin)
            result=hook_context(memory,payload)
        elif args.action=='recall':result=memory.recall(args.query,scope=args.scope)
        elif args.action=='reflect':
            from model_synthesis import generator_from_config
            result=memory.reflect(args.query,args.scope,generator_from_config(config,home,memory))
        else: result=memory.page(args.name or args.query,args.query,args.scope,refresh=True)
        print(json.dumps(result,ensure_ascii=False))
    finally:memory.close()

if __name__=='__main__':main()
