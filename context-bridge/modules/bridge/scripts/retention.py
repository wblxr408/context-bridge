"""Plan or apply bounded checkpoint retention in one explicitly registered task root."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

from requirements import check, need
from writer import gate
from canonical import canonical_path
from uuid import uuid4

INDEX = ".retention.json"
PENDING = ".retention.pending.json"
DEFAULTS = {"keep_last": 3, "min_age_days": 7, "trash_days": 7, "budget_mib": 512}


def stamp(value):
    time = datetime.fromisoformat(value)
    need(time.tzinfo is not None, "Timestamps must include timezone")
    return time


def linked(path):
    try:return bool(path.lstat().st_file_attributes & 0x400) if os.name=='nt' else path.is_symlink()
    except FileNotFoundError:return False


def root_path(value):
    path = Path(value)
    need(not linked(path), "Task root must not be a link")
    root = canonical_path(path)
    need(root.is_dir() and root != Path(root.anchor), "Expected a dedicated task directory")
    need(not (root / ".git").exists(), "A repository root is not a checkpoint task root")
    for name in (INDEX, PENDING, ".trash", ".context-bridge-writer.guard"):
        need(not linked(root / name), "Management paths must not be links")
    return root


def load(root):
    need(not (root / PENDING).exists(), "Interrupted cleanup: inspect .retention.pending.json before proceeding")
    data = json.loads((root / INDEX).read_text(encoding="utf-8"))
    need(isinstance(data, dict) and data.get("schema") == 2 and type(data.get('revision')) is int and data['revision']>0 and isinstance(data.get("task_id"), str)
         and bool(data["task_id"].strip()), "Invalid retention registration")
    policy = DEFAULTS | data.get("policy", {})
    need(set(policy) == set(DEFAULTS), "Unknown policy fields")
    for key, number in policy.items():
        need(type(number) is int and number >= (1 if key in {"keep_last", "budget_mib"} else 0), "Invalid policy: " + key)
    rows = data.get("items")
    need(isinstance(rows, list), "Missing registered checkpoint list")
    entries = {}
    for row in rows:
        need(isinstance(row, dict), "Invalid registered checkpoint")
        name = row.get("id")
        need(isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", name), "Invalid checkpoint ID")
        need(name.casefold() not in {key.casefold() for key in entries}, "Duplicate checkpoint ID")
        need(row.get("lifecycle") in {"active", "received", "retired", "trash", "deleted"}, "Invalid lifecycle")
        need(isinstance(row.get('snapshot_id'),str) and row['snapshot_id'].startswith(data['task_id']+'/'), 'Missing registered task/snapshot identity')
        stamp(row["created_utc"])
        for flag in ("pinned", "in_use", "self_contained"):
            need(type(row.get(flag)) is bool, "Missing explicit flag: " + flag)
        need(isinstance(row.get("depends_on"), list) and all(isinstance(x, str) for x in row["depends_on"]), "Invalid dependency list")
        entries[name] = row
    for pointer in ("current", "last_received"):
        name = data.get(pointer)
        need(name is None or (name in entries and entries[name]["lifecycle"] not in {"trash", "deleted"}), "Invalid " + pointer)
    for name, row in entries.items():
        if row["lifecycle"] == "deleted":
            continue
        for dep in row["depends_on"]:
            need(dep in entries and entries[dep]["lifecycle"] not in {"deleted", "trash"}, "Missing/isolated dependency for " + name)
    return data, entries, policy


def location(root, row):
    parent = root / ".trash" if row["lifecycle"] == "trash" else root
    need(not linked(parent), "Checkpoint parent is a link")
    path = parent / row["id"]
    need(not linked(path), "Checkpoint is a link")
    resolved = canonical_path(path)
    need(resolved.parent == canonical_path(parent) and resolved.is_relative_to(root) and resolved != root,
         "Checkpoint escapes its registered task root")
    need(resolved.is_dir(), "Checkpoint is not a directory")
    for item in resolved.rglob("*"):
        need(not linked(item) and canonical_path(item).is_relative_to(resolved), "Checkpoint contains a link")
        need(item.name != ".git", "Refusing to manage a Git checkout")
    return resolved


def inspect(root, row, task_id):
    path = location(root, row)
    ledger = check(path)
    need(ledger["task_id"] == task_id, "Checkpoint belongs to another task")
    need(ledger.get('snapshot_id') == row['snapshot_id'], 'Registered snapshot differs from requirement ledger')
    size = sum(item.stat().st_size for item in path.rglob('*') if item.is_file())
    return path, size


def make_plan(root, now=None):
    root = root_path(root)
    now = now or datetime.now(timezone.utc)
    data, entries, policy = load(root)
    protected = {}
    paths = {}
    sizes = {}
    warnings = []
    def protect(name, why):
        if name is not None:
            protected.setdefault(name, []).append(why)
    for pointer in ("current", "last_received"):
        protect(data.get(pointer), pointer)
    live = [r for r in entries.values() if r["lifecycle"] not in {"trash", "deleted"}]
    latest = sorted(live, key=lambda r: (stamp(r["created_utc"]), r["id"]), reverse=True)[:policy["keep_last"]]
    for row in latest:
        protect(row["id"], "recent-version")
    for name, row in entries.items():
        if row["lifecycle"] == "deleted":
            continue
        if row["pinned"] or row["in_use"]:
            protect(name, "pinned-or-in-use")
        if row["lifecycle"] not in {"retired", "trash"}:
            protect(name, "not-retired")
        if row.get("no_readers_confirmed") is not True:
            protect(name, "readers-not-confirmed-stopped")
        if now - stamp(row["created_utc"]) < timedelta(days=policy["min_age_days"]):
            protect(name, "too-young")
        if row["lifecycle"] == "trash":
            try:
                if now - stamp(row["trashed_utc"]) < timedelta(days=policy["trash_days"]):
                    protect(name, "quarantine-grace")
            except (KeyError, TypeError, ValueError):
                protect(name, "unknown-quarantine-time")
        try:
            paths[name], sizes[name] = inspect(root, row, data["task_id"])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            protect(name, "verification-failed")
            warnings.append({"id": name, "reason": str(exc)})
    def closure():
        visited = set()
        pending = list(protected)
        while pending:
            name = pending.pop()
            if name in visited:
                continue
            visited.add(name)
            for dep in entries[name]["depends_on"]:
                if dep not in protected:
                    protect(dep, "required-by:" + name)
                pending.append(dep)
    closure()
    for name, row in entries.items():
        if row["lifecycle"] == "deleted" or name in protected:
            continue
        successor = row.get("superseded_by")
        if (successor not in protected or successor not in paths or not entries[successor]["self_contained"]
                or entries[successor]["lifecycle"] in {"trash", "deleted"}):
            protect(name, "no-verified-retained-replacement")
            continue
        try:
            need(stamp(entries[successor]["created_utc"]) > stamp(row["created_utc"]), "Replacement is not newer")
            check(paths[successor], paths[name])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            protect(name, "replacement-coverage-failed")
            warnings.append({"id": name, "reason": str(exc)})
    closure()
    actions = [{"action": "purge" if row["lifecycle"] == "trash" else "quarantine",
                "id": name, "snapshot_id": row['snapshot_id'], "bytes": sizes[name]}
               for name, row in sorted(entries.items()) if row["lifecycle"] != "deleted" and name not in protected]
    occupied = sum(sizes.values())
    unmanaged = sorted(p.name for p in root.iterdir() if p.is_dir() and p.name != ".trash" and p.name not in entries)
    if (root / ".trash").exists():
        unmanaged += [".trash/" + p.name for p in (root / ".trash").iterdir()
                      if p.name not in entries or entries[p.name]["lifecycle"] != "trash"]
    return {"schema": 2, "plan_id":uuid4().hex, "root": str(root), "task_id": data["task_id"], "generated_utc": now.isoformat(),
            "index_revision":data['revision'], "registration":data, "policy": policy, "actions": actions,
            "protected": protected, "warnings": warnings, "unmanaged_preserved": unmanaged,
            "verified_managed_bytes": occupied, "budget_exceeded": occupied > policy["budget_mib"] * 1024 * 1024,
            "quarantine_bytes": sum(a["bytes"] for a in actions if a["action"] == "quarantine"),
            "reclaim_bytes_now": sum(a["bytes"] for a in actions if a["action"] == "purge")}


def save_index(root, data):
    fd, temp = tempfile.mkstemp(prefix=".retention-", suffix=".tmp", dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(data, out, ensure_ascii=False, indent=2)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, root / INDEX)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def apply_plan(root, plan_file, expected, now=None):
    root = root_path(root)
    now = now or datetime.now(timezone.utc)
    plan = json.loads(Path(plan_file).read_text(encoding="utf-8"))
    need(expected and plan.get('plan_id')==expected, 'Explicit reviewed plan identity differs')
    with gate(root):
        fresh = make_plan(root, now)
        need(plan.get("root") == str(root) and plan.get("task_id") == fresh["task_id"], "Plan targets another task root")
        need(plan.get('index_revision')==fresh['index_revision'] and plan.get('registration')==fresh['registration'], 'Registration changed; create a fresh plan')
        need([{k:v for k,v in a.items() if k!='bytes'} for a in plan.get('actions',[])] == [{k:v for k,v in a.items() if k!='bytes'} for a in fresh['actions']], 'Candidates changed; create a fresh plan')
        need(not fresh["warnings"], "Resolve verification warnings before cleanup")
        data, entries, _ = load(root)
        if not fresh["actions"]:
            return {"status": "no-actions", "completed": []}
        with (root / PENDING).open("x", encoding="utf-8") as out:
            json.dump({'plan_id':expected,"plan":plan}, out, ensure_ascii=False, indent=2)
            out.flush()
            os.fsync(out.fileno())
        completed = []
        for action in fresh["actions"]:
            row = entries[action["id"]]
            path, _ = inspect(root, row, data["task_id"])
            # Resolved source and destination are rechecked immediately before mutation.
            if action["action"] == "quarantine":
                trash = root / ".trash"
                need(not linked(trash), "Quarantine directory became a link")
                trash.mkdir(exist_ok=True)
                target = trash / row["id"]
                need(not target.exists() and not linked(target) and canonical_path(target.parent)==canonical_path(trash)
                     and canonical_path(target.parent).is_relative_to(root), "Unsafe quarantine destination")
                os.rename(path, target)
                row["lifecycle"] = "trash"
                row["trashed_utc"] = now.isoformat()
            else:
                need(path.parent == canonical_path(root / '.trash') and path.is_relative_to(root), "Unsafe purge target")
                shutil.rmtree(path)
                row["lifecycle"] = "deleted"
                row["deleted_utc"] = now.isoformat()
            data['revision']+=1
            save_index(root, data)
            completed.append({"id": row["id"], "action": action["action"]})
        (root / PENDING).unlink()
        return {"status": "applied", "completed": completed, "reclaimed_bytes": fresh["reclaim_bytes_now"]}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["plan", "apply"])
    p.add_argument("root", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--plan", type=Path)
    p.add_argument('--plan-id')
    a = p.parse_args()
    try:
        root = root_path(a.root)
        if a.action == "plan":
            need(a.out is not None and not canonical_path(a.out.parent).is_relative_to(root), "Plan output must be outside the task root")
            with gate(root):
                result = make_plan(root)
                with a.out.open("x", encoding="utf-8") as stream:
                    json.dump(result, stream, ensure_ascii=False, indent=2)
            print(json.dumps({"plan_path": str(canonical_path(a.out)), 'plan_id':result['plan_id'],
                              "actions": result["actions"], "protected_count": len(result["protected"]),
                              "warnings": result["warnings"], "unmanaged_preserved": result["unmanaged_preserved"],
                              "verified_managed_bytes": result["verified_managed_bytes"],
                              "budget_exceeded": result["budget_exceeded"],
                              "reclaim_bytes_now": result["reclaim_bytes_now"]}, ensure_ascii=False))
        else:
            need(a.plan is not None, "--plan is required")
            print(json.dumps(apply_plan(root, a.plan, a.plan_id), ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
