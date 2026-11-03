"""Grounded synthesis through the existing no-tools classifier and shared budgets."""
import json
from pathlib import Path
import time
import threading

_lock=threading.Lock()

class BudgetExceeded(RuntimeError):
    pass

def gateway_call_history(db, limit=100):
    """Gateway records exposed to the competition workbench."""
    _gateway_table(db)
    rows = db.execute('SELECT call_id,state,metadata FROM memory_gateway_calls ORDER BY call_id DESC LIMIT ?',
                      (min(500, max(1, int(limit))),)).fetchall()
    return [dict(json.loads(row[2]), call_id=row[0], state=row[1]) for row in rows]

def _gateway_table(db):
    db.execute('CREATE TABLE IF NOT EXISTS memory_gateway_calls('
               'call_id INTEGER PRIMARY KEY,state TEXT NOT NULL,metadata TEXT NOT NULL)')

def settle_call(db, call, usage=None, error=None):
    """Settle reported tokens; retain the reservation for ambiguous usage."""
    usage = usage or {}
    incoming, outgoing = usage.get('input_tokens'), usage.get('output_tokens')
    known = all(isinstance(n, int) and not isinstance(n, bool) and n >= 0 for n in (incoming, outgoing))
    metadata = usage.get('otari') or getattr(error, 'metadata', None)
    with db:
        if known:
            db.execute('UPDATE calls SET tokens=? WHERE id=?', (incoming + outgoing, call))
        elif error is not None and (getattr(error, 'dispatched', None) is False or
                                    getattr(error, 'kind', None) in {'budget_exceeded', 'authentication', 'permission_denied', 'rate_limited'}):
            db.execute('UPDATE calls SET tokens=0 WHERE id=?', (call,))
        if metadata:
            _gateway_table(db)
            record = {key: metadata.get(key) for key in (
                'request_id', 'operation_id', 'role', 'requested_model', 'model', 'provider',
                'fallback', 'attempt_count', 'cost_usd', 'pricing_source', 'latency_ms', 'idempotent_replay')}
            record.update(input_tokens=incoming, output_tokens=outgoing,
                          error_kind=getattr(error, 'kind', None))
            db.execute('INSERT OR REPLACE INTO memory_gateway_calls VALUES(?,?,?)',
                       (call, 'failed' if error else 'succeeded', json.dumps(record)))

def reserve_call(db,config,estimate=None):
    now=time.time()
    reserve=max(config.get('reserve_tokens_per_call',12000),estimate or 0)
    with db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('CREATE TABLE IF NOT EXISTS calls(id INTEGER PRIMARY KEY,started REAL,tokens INTEGER DEFAULT 0)')
        used=db.execute('SELECT count(*),coalesce(sum(tokens),0) FROM calls WHERE started>?',(now-86400,)).fetchone()
        hourly=db.execute('SELECT count(*) FROM calls WHERE started>?',(now-3600,)).fetchone()[0]
        if used[0]>=config['max_calls_per_day'] or hourly>=config['max_calls_per_hour'] or used[1]+reserve>config['max_tokens_per_day']:
            raise BudgetExceeded('Existing shared memory model budget exhausted; use evidence-only recall or cached pages')
        return db.execute('INSERT INTO calls(started,tokens) VALUES(?,?)',(now,reserve)).lastrowid

def generator_from_config(config,home,memory):
    def generate(evidence):
        from listener import judge,HERE
        # A single process serializes its model worker. BEGIN IMMEDIATE serializes budget reservations across processes.
        with _lock:
            call=reserve_call(memory.db,config,len(json.dumps(evidence,ensure_ascii=False))+2000)
            import tempfile
            try:
                with tempfile.TemporaryDirectory(prefix='reflection-',dir=home) as run:
                    result,usage=judge(config,run,evidence,[],HERE/'reflect-schema.json',HERE/'reflect-instructions.txt')
            except Exception as exc:
                settle_call(memory.db,call,error=exc)
                raise
            settle_call(memory.db,call,usage)
            return result
    return generate
