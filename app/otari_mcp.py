"""Authenticated HTTP MCP over an explicit, curated source publication list."""
import hmac
import json
import os

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from starlette.responses import JSONResponse
from memory_runtime import scope_key, tokens


class PublishedSources:
    def __init__(self, memory, settings):
        self.memory = memory
        self.scope = settings.get('scope')
        self.allowed = set(settings.get('permalinks', []))
        if not isinstance(self.scope, str) or not self.scope.strip():
            raise ValueError('Remote MCP requires an explicit publication scope')

    def sources(self):
        with self.memory.lock:
            found = []
            for note in self.memory.notes():
                if note['permalink'] in self.allowed and scope_key(note['scope']) == scope_key(self.scope):
                    found.append({'citation': note['permalink'], 'title': note['title'],
                        'text': note['content'][:60000], 'revision': str((self.memory.vault / note['path']).stat().st_mtime_ns)})
            # Only explicitly published immutable web revisions are eligible.
            table = self.memory.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='otari_sources'").fetchone()
            if table:
                for row in self.memory.db.execute('SELECT body FROM otari_sources'):
                    source = json.loads(row[0])
                    if source['permalink'] in self.allowed:
                        found.append({'citation': source['permalink'], 'title': source['title'],
                                      'text': source['excerpt'], 'revision': str(source['revision'])})
            return found

    def read(self, citation):
        source = next((s for s in self.sources() if s['citation'] == citation), None)
        if source is None:
            raise ValueError('Source is unavailable in this publication')
        return source


def create_mcp_app(memory, config):
    settings = config.get('remote_mcp') or {}
    catalog = PublishedSources(memory, settings)
    secret = os.environ.get(settings.get('token_env', 'BRIDGE_MCP_TOKEN'), '')
    if len(secret) < 12:
        raise ValueError('Set a separate MCP bearer token of at least 12 characters')
    server = MCPServer('Bridge published evidence')
    readonly = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)

    @server.tool(annotations=readonly)
    def search_memory(query: str, limit: int = 5) -> dict:
        """Search only published sources within the configured scope."""
        if not query.strip() or len(query) > 4000 or not 1 <= limit <= 10:
            raise ValueError('Use a bounded query and limit 1–10')
        terms = set(tokens(query))
        scored = [(len(terms & set(tokens(s['title'] + ' ' + s['text']))), s) for s in catalog.sources()]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return {'results': [dict(s, text=s['text'][:1200]) for score, s in scored if score][:limit]}

    @server.tool(annotations=readonly)
    def read_source(citation: str, revision: str | None = None) -> dict:
        """Read one published source, optionally requiring the known revision."""
        source = catalog.read(citation)
        if revision is not None and revision != source['revision']:
            raise ValueError('Source changed; request its current revision before reading')
        return source

    @server.tool(annotations=readonly)
    def source_revision(citation: str) -> dict:
        """Read the revision identity of a published source."""
        source = catalog.read(citation)
        return {'citation': source['citation'], 'revision': source['revision']}

    inner = server.streamable_http_app(json_response=True, stateless_http=True,
        max_request_body_size=65536, transport_security=TransportSecuritySettings(
            allowed_hosts=settings.get('allowed_hosts', ['127.0.0.1:*', 'localhost:*']),
            allowed_origins=settings.get('allowed_origins', [])))

    async def authenticated(scope, receive, send):
        if scope['type'] != 'http':
            return await inner(scope, receive, send)
        headers = dict(scope.get('headers', []))
        supplied = headers.get(b'authorization', b'').decode('latin-1')
        if not hmac.compare_digest(supplied.encode(), ('Bearer ' + secret).encode()):
            return await JSONResponse({'error': 'authentication_required'}, 401,
                headers={'WWW-Authenticate': 'Bearer'})(scope, receive, send)
        return await inner(scope, receive, send)
    return authenticated
