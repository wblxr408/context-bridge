"""Persistent cooperative writer ownership on a single local filesystem."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
import tempfile
from canonical import canonical_path

STATE = ".context-bridge-writer.json"
GUARD = ".context-bridge-writer.guard"


def need(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


@contextmanager
def gate(root):
    with (root / GUARD).open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def state(root):
    path = root / STATE
    if not path.exists():
        return {"schema": 1, "workspace": str(root), "owner": None}
    data = read(path)
    need(isinstance(data, dict) and data.get("schema") == 1 and data.get("workspace") == str(root),
         "Invalid ownership state; inspect before recovery")
    need("owner" in data, "Missing ownership state")
    if data["owner"] is not None:
        need(isinstance(data["owner"], str) and bool(data["owner"]) and
             isinstance(data.get("token_hash"), str) and len(data["token_hash"]) == 64,
             "Incomplete ownership state")
    return data


def save(root, data):
    fd, name = tempfile.mkstemp(prefix=".context-bridge-", suffix=".tmp", dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, root / STATE)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def authenticate(root, current, claim_path, manifest=None):
    need(claim_path is not None, "Claim path required")
    claim = read(Path(claim_path))
    need(isinstance(claim, dict) and isinstance(claim.get("token"), str), "Invalid claim")
    token_hash = hashlib.sha256(claim["token"].encode()).hexdigest()
    need(current.get("owner") is not None and claim.get("workspace") == str(root) and
         claim.get("owner") == current["owner"] and token_hash == current.get("token_hash"),
         "Writer ownership does not match; remain read-only")
    if manifest is not None:
        need(current.get("snapshot_id", current.get("manifest")) == manifest, "Claim is for a different snapshot")


def grant(root, owner, claim_path, manifest=None):
    need(isinstance(owner, str) and bool(owner.strip()), "Nonempty owner required")
    need(claim_path is not None, "New claim path required")
    if manifest is not None:
        need(isinstance(manifest, str) and bool(manifest.strip()) and '/' in manifest,
             "Explicit task/snapshot identity required, e.g. task-001/revision-2")
    requested = Path(claim_path).absolute()
    target = canonical_path(requested.parent) / requested.name
    need(target not in {root / STATE, root / GUARD}, "Claim must not replace ownership files")
    token = secrets.token_hex(32)
    claim = {"workspace": str(root), "owner": owner, "token": token}
    with target.open("x", encoding="utf-8") as stream:
        json.dump(claim, stream, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
    save(root, {"schema": 1, "workspace": str(root), "owner": owner,
                "token_hash": hashlib.sha256(token.encode()).hexdigest(), "snapshot_id": manifest})
    return {"status": "owned", "owner": owner, "claim_path": str(target), "snapshot_id": manifest}


def operate(action, workspace, owner=None, claim=None, new_claim=None, manifest=None):
    root = canonical_path(workspace)
    need(root.is_dir(), "Workspace must be a directory")
    need(not (root / GUARD).is_symlink(), 'Ownership guard must not be a symlink')
    with gate(root):
        current = state(root)
        if action == "status":
            return {"owner": current.get("owner"), "snapshot_id": current.get("snapshot_id", current.get("manifest"))}
        if action == "acquire":
            need(current.get("owner") is None, "Workspace already has a writer")
            return grant(root, owner, claim, manifest)
        authenticate(root, current, claim, manifest if action == "assert" else None)
        if action == "assert":
            return {"status": "writer_verified", "owner": current["owner"], "snapshot_id": current.get("snapshot_id", current.get("manifest"))}
        if action == "release":
            save(root, {"schema": 1, "workspace": str(root), "owner": None})
            return {"status": "released"}
        need(action == "transfer", "Unknown operation")
        need(manifest is not None, "Transfer requires an explicit task/snapshot identity")
        return grant(root, owner, new_claim, manifest)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["acquire", "assert", "transfer", "release", "status"])
    p.add_argument("workspace", type=Path)
    p.add_argument("--owner")
    p.add_argument("--claim", type=Path)
    p.add_argument("--new-claim", type=Path)
    p.add_argument("--manifest")
    p.add_argument("--snapshot-id")
    a = p.parse_args()
    try:
        if a.manifest is not None:
            raise ValueError('Legacy --manifest is not the current handoff route; use --snapshot-id')
        print(json.dumps(operate(a.action, a.workspace, a.owner, a.claim, a.new_claim, a.snapshot_id), ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
