"""Explicitly launched, loopback-only workbench; credentials stay on the server."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import json
from pathlib import Path
from urllib.parse import urlsplit

from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route

ASSETS = Path(__file__).resolve().parent / 'workbench'


class LocalBoundary(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        host = request.headers.get('host', '')
        origin = request.headers.get('origin')
        try:
            local = urlsplit('http://' + host).hostname in {'127.0.0.1', 'localhost', '::1'}
        except ValueError:
            local = False
        if not local or (origin and origin != str(request.base_url).rstrip('/')):
            return JSONResponse({'error': '仅允许本机同源访问。'}, 403)
        response = await call_next(request)
        response.headers.update({'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store',
            'Content-Security-Policy': "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; font-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'"})
        return response


def create_app(workflow):
    # One worker avoids contention with this single-user SQLite connection.
    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='bridge-workbench')

    def execute(task_id):
        return pool.submit(workflow.run, task_id).result()

    @asynccontextmanager
    async def lifespan(app):
        yield
        pool.shutdown(wait=True)

    async def read_task(request):
        try:
            return JSONResponse(workflow.get(request.path_params['task_id']))
        except KeyError:
            return JSONResponse({'error': '任务不存在。'}, 404)

    async def tasks(request):
        if request.method == 'GET':
            return JSONResponse([{k: t[k] for k in ('id', 'query', 'created_at', 'status')} for t in workflow.list()])
        try:
            raw = bytearray()
            async for chunk in request.stream():
                raw.extend(chunk)
                if len(raw) > 65536:
                    return JSONResponse({'error': '输入过长，请缩短对话原文。'}, 413)
            value = json.loads(raw)
            if not isinstance(value, dict) or set(value) - {'query', 'scope', 'web', 'analyze', 'event', 'mcp'}:
                raise ValueError('Unknown task fields')
            task = workflow.create(**value)
        except (ValueError, TypeError):
            return JSONResponse({'error': '请填写问题，并检查输入格式。'}, 400)
        return JSONResponse({'id': task['id'], 'status': task['status']}, 202,
                            background=BackgroundTask(execute, task['id']))

    async def resume(request):
        try:
            task = workflow.get(request.path_params['task_id'])
        except KeyError:
            return JSONResponse({'error': '任务不存在。'}, 404)
        if task['status'] not in {'paused', 'pending', 'running'}:
            return JSONResponse({'error': '该任务已结束；刷新来源请创建新任务。'}, 409)
        if task['status'] == 'running':
            # Expired abandoned leases may be reclaimed inside run().
            with workflow.memory.lock:
                import time
                row = workflow.memory.db.execute('SELECT lease_until FROM otari_tasks WHERE id=?', (task['id'],)).fetchone()
                if row[0] > time.time():
                    return JSONResponse({'error': '任务正在运行。'}, 409)
        return JSONResponse({'id': task['id'], 'status': 'pending'}, 202,
                            background=BackgroundTask(execute, task['id']))

    async def settings(request):
        import os
        otari = workflow.config.get('otari', {})
        return JSONResponse({'credential_ready': bool(os.environ.get(otari.get('api_key_env', 'OTARI_API_KEY'))),
            'models': otari.get('models', {}),
            'official_domains': workflow.config.get('research', {}).get('official_domains', []),
            'mcp_ready': bool(workflow.config.get('research', {}).get('mcp_server_ids'))})

    async def asset(request):
        name = request.path_params.get('name', 'index.html')
        if name not in {'index.html', 'app.css', 'app.js', 'BridgeDisplay.ttf'}:
            return JSONResponse({'error': 'Not found'}, 404)
        return FileResponse(ASSETS / name)

    app = Starlette(routes=[Route('/', asset), Route('/assets/{name}', asset),
        Route('/api/settings', settings), Route('/api/tasks', tasks, methods=['GET', 'POST']),
        Route('/api/tasks/{task_id}', read_task), Route('/api/tasks/{task_id}/resume', resume, methods=['POST'])], lifespan=lifespan)
    app.add_middleware(LocalBoundary)
    return app
