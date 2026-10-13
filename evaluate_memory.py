"""Functional retrieval evaluation on the user's real, read-only memory corpus."""
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).parent/'app'))
from memory_runtime import MemoryRuntime

CASES = [
 {'query':'为什么我们不另建一个持续学习后台，而是继续使用现有的监听器？', 'gold':'main/codex/codex-checkpoint-2026-10-12-t06-14-16-z-ecc-双客户端融合完成','split':'diagnostic'},
 {'query':'我之前决定怎么清理检查点，哪些历史必须保留？','gold':'main/10-decisions/context-bridge-检查点采用保留保护与两阶段回收','split':'diagnostic'},
 {'query':'现在的开发流程允许启动一下程序或者检查文件存在就作为验收吗？','gold':'main/codex/codex-checkpoint-2026-10-12-t06-14-16-z-ecc-双客户端融合完成','split':'diagnostic'},
 {'query':'银发项目现在还可以向用户提供演示体验和虚构记录吗？','gold':'main/decisions/silver-economy-agent/银发前端只使用真实账号与业务数据','split':'held_out'},
 {'query':'课程学习资料应该做成什么文件，后续章节如何追加？','gold':'main/decisions/course-library/三门课学习站采用单文件离线书架并支持持续追加章节','split':'held_out'},
 {'query':'论文页数超标时，能否缩小字体和页边距满足篇幅？','gold':'main/notes/configscope/config-scope-九页预算与-secon-已发表-method-篇幅核验','split':'held_out'},
]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--models',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).parent
    memory=MemoryRuntime(r'C:\Users\wblxr\basic-memory',root/'evaluation-state.sqlite',use_models=args.models,cache=root/'models')
    records=[]
    try:
        for case in CASES:
            started=time.monotonic()
            result=memory.recall(case['query'],limit=5)
            pids=[r['permalink'] for r in result['results']]
            record={**case,'rank':pids.index(case['gold'])+1 if case['gold'] in pids else None,
                    'seconds':round(time.monotonic()-started,3),'results':result['results']}
            records.append(record)
            print(json.dumps({k:v for k,v in record.items() if k!='results'},ensure_ascii=False),flush=True)
        output=root/('evaluation-models.json' if args.models else 'evaluation-lexical.json')
        output.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        memory.close()

if __name__=='__main__':
    main()
