"""Validate requirement provenance, revisions, scoped briefs and receiver coverage."""
import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from canonical import canonical_path


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def need(condition, message):
    if not condition:
        raise ValueError(message)


def inside(root, name):
    need(isinstance(name, str) and name, "Missing evidence path")
    p = PurePosixPath(name)
    need(not p.is_absolute() and ".." not in p.parts and "\\" not in name and ":" not in name,
         "Evidence must be a bundle-relative path")
    path = root / name
    need(canonical_path(path).is_relative_to(canonical_path(root)) and path.is_file(), "Evidence missing: " + name)
    return path


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def check(root, previous=None):
    root = canonical_path(root)
    data = read(root / "requirements.json")
    need(isinstance(data, dict) and data.get("schema") == 1, "Unsupported requirements schema")
    need(nonempty(data.get("task_id")), "Missing task_id")
    if 'snapshot_id' in data:
        need(nonempty(data['snapshot_id']) and data['snapshot_id'].startswith(data['task_id']+'/') and len(data['snapshot_id'])>len(data['task_id'])+1,'Snapshot must belong to its explicit task namespace')
    rows = data.get("requirements")
    need(isinstance(rows, list) and bool(rows), "Empty requirement ledger")
    ids = set()
    for row in rows:
        need(isinstance(row, dict), "Invalid requirement")
        rid = row.get("id")
        need(isinstance(rid, str) and re.fullmatch(r"R[0-9]{3,}", rid), "Invalid requirement ID")
        need(rid not in ids, "Duplicate requirement ID: " + rid)
        ids.add(rid)
        need(type(row.get("revision")) is int and row["revision"] > 0, rid + ": invalid revision")
        need(row.get("status") in {"active", "superseded"}, rid + ": invalid status")
        need(row.get("kind") in {"goal", "constraint", "deliverable"}, rid + ": invalid kind")
        need(type(row.get("always_load")) is bool, rid + ": missing always_load")
        need(row["kind"] == "deliverable" or row["always_load"], rid + ": goal/constraint cannot be deferred")
        for key in ("statement", "scope", "acceptance"):
            need(nonempty(row.get(key)), rid + ": missing " + key)
        need(row["scope"] != "global" or row["always_load"], rid + ": global requirement must always load")
        need(row.get("progress") in {"pending", "in_progress", "done"}, rid + ": invalid progress")
        source = row.get("source")
        need(isinstance(source, dict), rid + ": missing source")
        need(nonempty(source.get("quote")) and nonempty(source.get("locator")), rid + ": missing source quote/locator")
        need(source["quote"] in inside(root, source.get("path")).read_text(encoding="utf-8"),
             rid + ": quote is not present in source evidence")
        evidence = row.get("evidence")
        need(isinstance(evidence, list), rid + ": missing evidence array")
        need(row["progress"] != "done" or bool(evidence), rid + ": done requires evidence")
        for name in evidence:
            inside(root, name)
    by_id = {row["id"]: row for row in rows}
    for row in rows:
        seen = set()
        node = row
        while node["status"] == "superseded":
            need(node["id"] not in seen, "Supersession cycle")
            seen.add(node["id"])
            replacement = node.get("superseded_by")
            need(isinstance(replacement, str) and replacement in ids, "Missing replacement ID")
            node = by_id[replacement]
    need(any(r["status"] == "active" for r in rows), "No active requirements")
    if previous is not None:
        old = check(Path(previous))
        need(old["task_id"] == data["task_id"], "Previous task_id differs")
        for before in old["requirements"]:
            need(before["id"] in by_id, "Requirement lost: " + before["id"])
            after = by_id[before["id"]]
            need(after["revision"] >= before["revision"], "Revision regressed: " + before["id"])
            keys = ("statement", "source", "acceptance", "kind", "scope", "always_load", "status", "superseded_by")
            changed = any(before.get(k) != after.get(k) for k in keys)
            need(not changed or after["revision"] > before["revision"], "Changed requirement needs new revision: " + before["id"])
    return data


def selected(data, scope):
    active = [row for row in data["requirements"] if row["status"] == "active"]
    need(scope in {row["scope"] for row in active}, "Unknown scope: " + str(scope))
    return [row for row in active if row["always_load"] or row["scope"] == scope]


def brief(root, scope):
    data = check(root)
    rows = selected(data, scope)
    compact = [{k: row[k] for k in ("id", "revision", "statement", "acceptance", "progress")} |
               {"source": {"path": row["source"]["path"], "locator": row["source"]["locator"]}}
               for row in rows]
    return {"task_id": data["task_id"], 'snapshot_id':data.get('snapshot_id'),"scope": scope, "requirements": compact,
            "deferred_count": sum(r["status"] == "active" for r in data["requirements"]) - len(rows)}


def receipt(root, scope, path, expected):
    need(nonempty(expected), "Expected task/snapshot identity is required")
    data = check(root)
    need(data.get('snapshot_id') == expected, 'Ledger snapshot differs or has no explicit snapshot_id')
    chosen = {row["id"]: row for row in selected(data, scope)}
    proof = read(path)
    need(isinstance(proof, dict), "Invalid receipt")
    need(proof.get("task_id") == data["task_id"], "Receipt task differs")
    need(proof.get("snapshot_id") == expected, "Receipt snapshot differs")
    need(proof.get("scope") == scope, "Receipt scope differs")
    checks = proof.get("checks")
    need(isinstance(checks, list), "Missing receipt checks")
    seen = set()
    for item in checks:
        need(isinstance(item, dict), "Invalid receipt check")
        rid = item.get("id")
        need(isinstance(rid, str) and rid in chosen and rid not in seen, "Unexpected/duplicate receipt ID")
        seen.add(rid)
        need(type(item.get("revision")) is int and item["revision"] == chosen[rid]["revision"], "Stale receipt revision: " + rid)
        need(item.get("result") == "aligned", "Unresolved requirement: " + rid)
        need(nonempty(item.get("interpretation")) and nonempty(item.get("next_action")), "Empty receiver interpretation: " + rid)
    need(seen == set(chosen), "Receipt misses requirements: " + ",".join(sorted(set(chosen) - seen)))
    return {"status": "coverage_verified", "requirements": len(seen), "scope": scope,
            "semantic_alignment": "receiver_attested_not_machine_proven"}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["check", "brief", "receipt"])
    p.add_argument("bundle", type=Path)
    p.add_argument("--scope")
    p.add_argument("--previous", type=Path)
    p.add_argument("--receipt", type=Path)
    p.add_argument("--expected-manifest")
    p.add_argument("--snapshot-id")
    a = p.parse_args()
    try:
        if a.action == "check":
            data = check(a.bundle, a.previous)
            result = {"status": "valid", "task_id": data["task_id"], "requirements": len(data["requirements"])}
        elif a.action == "brief":
            result = brief(a.bundle, a.scope)
        else:
            need(a.receipt is not None, "--receipt required")
            need(a.expected_manifest is None, 'Legacy checksum receipt is not the current route; use --snapshot-id')
            result = receipt(a.bundle, a.scope, a.receipt, a.snapshot_id)
        print(json.dumps(result, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
