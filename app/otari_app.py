"""Launch competition surfaces without modifying installed memory services."""
import argparse
import json
from pathlib import Path

from memory_runtime import MemoryRuntime
from otari_workflow import ResearchWorkflow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['workbench', 'mcp', 'run'])
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--state', type=Path, default=Path('local-state/otari.sqlite'))
    parser.add_argument('--port', type=int)
    parser.add_argument('--query')
    parser.add_argument('--resume')
    parser.add_argument('--web', action='store_true')
    parser.add_argument('--analyze', action='store_true')
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    vault = Path(config['vault']).absolute()
    vault.mkdir(parents=True, exist_ok=True)
    memory = MemoryRuntime(vault, args.state, use_models=config.get('memory_models', False))
    try:
        if args.mode == 'run':
            flow = ResearchWorkflow(memory, config)
            if not args.resume and not args.query:
                parser.error('run requires --query or --resume')
            task_id = args.resume or flow.create(args.query, web=args.web, analyze=args.analyze)['id']
            print(json.dumps(flow.run(task_id), ensure_ascii=False, indent=2))
        else:
            import uvicorn
            if args.mode == 'mcp':
                from otari_mcp import create_mcp_app
                application, port = create_mcp_app(memory, config), args.port or 8766
            else:
                from otari_workbench import create_app
                application, port = create_app(ResearchWorkflow(memory, config)), args.port or 8765
            uvicorn.run(application, host='127.0.0.1', port=port, access_log=False)
    finally:
        memory.close()


if __name__ == '__main__':
    main()
