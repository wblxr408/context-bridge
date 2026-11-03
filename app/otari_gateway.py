"""Bounded hosted Otari transport, shared by memory inference and research tools.

No SDK-owned retries: an ambiguous dispatch is resumed with the same operation key.
Gateway routing owns provider fallback; client failures never bypass that policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4


class GatewayError(RuntimeError):
    def __init__(self, kind, message, *, status=None, request_id=None,
                 dispatched=False, metadata=None):
        super().__init__(message)
        self.kind, self.status = kind, status
        self.request_id, self.dispatched = request_id, dispatched
        self.metadata = metadata or {}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def validate_json(value, schema):
    """Validate local schemas without allowing network reference retrieval."""
    from jsonschema import Draft202012Validator, ValidationError, SchemaError
    from referencing import Registry
    from referencing.exceptions import NoSuchResource

    def deny_reference(uri):
        raise NoSuchResource(ref=uri)

    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, registry=Registry(retrieve=deny_reference)).validate(value)
    except (ValidationError, SchemaError) as exc:
        path = '/'.join(map(str, exc.absolute_path)) or '<root>'
        raise GatewayError('invalid_output', 'Model JSON does not satisfy schema at ' + path,
                           dispatched=True) from None
    except Exception as exc:
        raise GatewayError('invalid_output', 'Model schema reference could not be resolved locally',
                           dispatched=True) from None
    return value


def _integer(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _cost(value):
    if value is None:
        return None
    try:
        cost = Decimal(str(value))
        return str(cost) if cost.is_finite() and cost >= 0 else None
    except InvalidOperation:
        return None


@dataclass(frozen=True)
class GatewayReply:
    content: str
    value: dict | None
    usage: dict
    tool_calls: tuple[dict, ...]


class GatewayClient:
    def __init__(self, config):
        self.settings = dict(config.get('otari') or {})
        self.base_url = str(self.settings.get('base_url', 'https://otari.ai/api/v1')).rstrip('/')
        parsed = urlsplit(self.base_url)
        loopback = parsed.hostname in ('localhost', '127.0.0.1', '::1')
        if (not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment
                or (parsed.scheme != 'https' and not (
                    parsed.scheme == 'http' and loopback and self.settings.get('allow_loopback_http') is True))):
            raise GatewayError('configuration', 'Gateway URL must use HTTPS; only explicit loopback tests may use HTTP')
        self.key_name = self.settings.get('api_key_env', 'OTARI_API_KEY')
        self.key = os.environ.get(self.key_name, '').strip()
        if not self.key:
            raise GatewayError('configuration', 'Set the configured Otari API key environment variable')
        if '\r' in self.key or '\n' in self.key:
            raise GatewayError('configuration', 'Invalid gateway credential')
        self.timeout = float(self.settings.get('timeout_seconds', config.get('judge_timeout_seconds', 45)))
        self.max_bytes = int(self.settings.get('max_response_bytes', 2 * 1024 * 1024))
        self.max_request_bytes = int(self.settings.get('max_request_bytes', 512 * 1024))
        self.max_tokens = int(self.settings.get('max_output_tokens', 2048))
        if not (0 < self.timeout <= 300 and 128 <= self.max_bytes <= 16 * 1024 * 1024
                and 128 <= self.max_request_bytes <= 4 * 1024 * 1024 and 1 <= self.max_tokens <= 32768):
            raise GatewayError('configuration', 'Gateway resource limits are outside supported bounds')
        self.opener = build_opener(_NoRedirect())

    def model(self, role):
        name = self.settings.get('models', {}).get(role)
        if not isinstance(name, str) or not name.strip():
            raise GatewayError('configuration', 'Configure an Otari model or routing policy for role ' + role)
        return name.strip()

    @staticmethod
    def _metadata(headers, body, role, model, operation_id, elapsed):
        usage = body.get('usage') or {}
        return {'request_id': headers.get('Otari-Request-ID') or body.get('id'),
                'role': role, 'requested_model': model, 'model': headers.get('Otari-Model'),
                'provider': headers.get('Otari-Provider'),
                'fallback': {'true': True, 'false': False}.get(str(headers.get('Otari-Fallback')).lower()),
                'attempt_count': _integer(int(headers['Otari-Attempt-Count']))
                    if str(headers.get('Otari-Attempt-Count', '')).isdigit() else None,
                'cost_usd': _cost(usage.get('cost_usd')),
                'pricing_source': usage.get('pricing_source'),
                'operation_id': operation_id, 'latency_ms': elapsed,
                'idempotent_replay': str(headers.get('Otari-Idempotent-Replayed', '')).lower() == 'true'}

    def complete(self, messages, *, role='reflect', schema=None, tools=None,
                 mcp_server_ids=None, operation_id=None):
        model = self.model(role)
        operation_id = operation_id or uuid4().hex
        if not isinstance(operation_id, str) or not 1 <= len(operation_id) <= 255 or not all(
                32 <= ord(char) <= 126 for char in operation_id):
            raise GatewayError('configuration', 'Operation ID must be printable ASCII, 1–255 characters')
        body = {'model': model, 'messages': messages, 'max_tokens': self.max_tokens,
                'temperature': 0, 'stream': False}
        if schema is not None:
            body['response_format'] = {'type': 'json_schema', 'json_schema': {
                'name': 'memory_result', 'strict': True, 'schema': schema}}
        if tools:
            body['tools'] = tools
            body['max_tool_iterations'] = min(10, max(1, int(self.settings.get('max_tool_iterations', 5))))
        if mcp_server_ids:
            body['mcp_server_ids'] = list(mcp_server_ids)
            body['max_tool_iterations'] = min(10, max(1, int(self.settings.get('max_tool_iterations', 5))))
        encoded = json.dumps(body, ensure_ascii=False, allow_nan=False).encode('utf-8')
        if len(encoded) > self.max_request_bytes:
            raise GatewayError('request_too_large', 'Evidence exceeds the configured gateway request limit')
        request = Request(self.base_url + '/chat/completions', data=encoded, method='POST', headers={
            'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json',
            'Idempotency-Key': operation_id})
        started = time.monotonic()
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read(self.max_bytes + 1)
                headers = response.headers
        except HTTPError as exc:
            # Do not expose gateway/provider free text: it can contain inputs or credentials.
            raw_error = exc.read(min(self.max_bytes, 16384)).decode('utf-8', errors='replace').lower()
            kind = ('budget_exceeded' if exc.code == 402 or 'budget' in raw_error
                    else 'authentication' if exc.code == 401
                    else 'permission_denied' if exc.code == 403
                    else 'rate_limited' if exc.code == 429 else 'gateway_error')
            request_id = exc.headers.get('Otari-Request-ID')
            raise GatewayError(kind, f'Otari refused this request ({exc.code}, {kind})',
                               status=exc.code, request_id=request_id, dispatched=True,
                               metadata={'request_id': request_id, 'operation_id': operation_id,
                                         'role': role, 'requested_model': model, 'cost_usd': None}) from None
        except (URLError, TimeoutError, OSError):
            raise GatewayError('transport_error', 'Otari request did not return; its billing state is unknown',
                               dispatched=True, metadata={'operation_id': operation_id, 'role': role,
                                                          'requested_model': model, 'cost_usd': None}) from None
        if len(raw) > self.max_bytes:
            raise GatewayError('invalid_output', 'Otari response exceeds the configured byte limit', dispatched=True)
        metadata = {'request_id': headers.get('Otari-Request-ID'), 'operation_id': operation_id,
                    'role': role, 'requested_model': model, 'cost_usd': None}
        try:
            result = json.loads(raw)
            message = result['choices'][0]['message']
            content = message.get('content') or ''
            if not isinstance(content, str) or message.get('refusal') or message.get('tool_calls'):
                raise ValueError('unfinished or refused model turn')
            usage = result.get('usage') or {}
            if not isinstance(usage, dict):
                raise ValueError('invalid usage')
            metadata = self._metadata(headers, result, role, model, operation_id,
                                      round((time.monotonic() - started) * 1000))
            normalized = {'input_tokens': _integer(usage.get('prompt_tokens')),
                          'output_tokens': _integer(usage.get('completion_tokens')), 'otari': metadata}
            value = json.loads(content) if schema is not None else None
            if schema is not None:
                validate_json(value, schema)
            tool_calls = result.get('otari_tool_calls') or []
            if not isinstance(tool_calls, list) or any(not isinstance(t, dict) for t in tool_calls):
                raise ValueError('invalid gateway tool records')
        except GatewayError as exc:
            exc.metadata = normalized['otari']
            exc.request_id = normalized['otari']['request_id']
            raise
        except (KeyError, IndexError, TypeError, ValueError, UnicodeError):
            raise GatewayError('invalid_output', 'Otari returned an incomplete or invalid model result',
                               request_id=headers.get('Otari-Request-ID'), dispatched=True,
                               metadata=metadata) from None
        return GatewayReply(content, value, normalized, tuple(tool_calls))


def judge(config, payload, existing, schema, instructions):
    role = 'reflect' if Path(schema).name == 'reflect-schema.json' else 'extract'
    reply = GatewayClient(config).complete([
        {'role': 'system', 'content': Path(instructions).read_text(encoding='utf-8')},
        {'role': 'user', 'content': json.dumps({'event': payload, 'existing_notes': existing}, ensure_ascii=False)}
    ], role=role, schema=json.loads(Path(schema).read_text(encoding='utf-8')),
        operation_id=payload.get('_gateway_operation_id') if isinstance(payload, dict) else None)
    return reply.value, reply.usage
