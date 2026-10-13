"""Grounded synthesis through the existing no-tools classifier and shared budgets."""
import json
from pathlib import Path
import time
import threading

_lock=threading.Lock()

class BudgetExceeded(RuntimeError):
    pass

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
            with tempfile.TemporaryDirectory(prefix='reflection-',dir=home) as run:
                result,usage=judge(config,run,evidence,[],HERE/'reflect-schema.json',HERE/'reflect-instructions.txt')
            total=usage.get('input_tokens',0)+usage.get('output_tokens',0)
            if total:
                with memory.db: memory.db.execute('UPDATE calls SET tokens=? WHERE id=?',(total,call))
            return result
    return generate
