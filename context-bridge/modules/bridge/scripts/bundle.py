"""Seal/verify a context handoff directory. Python standard library only."""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

REQUIRED = {"START.md", "STATE.md", "INDEX.md", "requirements.json"}
MANIFEST = "manifest.json"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inventory(root):
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError("Bundle links are not supported: " + str(path))
        if not path.resolve().is_relative_to(root):
            raise ValueError("Path escapes bundle: " + str(path))
        if path.is_file() and path.name != MANIFEST:
            name = path.relative_to(root).as_posix()
            result[name] = {"bytes": path.stat().st_size, "sha256": digest(path)}
        elif path.is_file() and path != root / MANIFEST:
            raise ValueError("Nested manifest.json is not supported")
    return result


def required_files(files):
    for name in REQUIRED:
        if name not in files or files[name]["bytes"] == 0:
            raise ValueError("Missing or empty required file: " + name)


def seal(root):
    target = root / MANIFEST
    if target.exists():
        raise ValueError("Already sealed; prepare a new version directory")
    from requirements import check
    check(root)
    files = inventory(root)
    required_files(files)
    data = {"schema": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
            "files": files,
            "scope": "Bundle bytes only; external references and semantic completeness are not verified"}
    # Exclusive creation preserves an existing seal even if another writer races.
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return {"status": "sealed", "manifest_sha256": digest(target), "files": len(files)}


def verify(root, expected=None):
    target = root / MANIFEST
    if target.is_symlink():
        raise ValueError("Manifest must not be a symlink")
    actual_digest = digest(target)
    if expected and actual_digest != expected.lower():
        raise ValueError("Manifest hash differs from the source handoff")
    data = json.loads(target.read_text(encoding="utf-8"))
    if data.get("schema") != 1 or not isinstance(data.get("files"), dict):
        raise ValueError("Unsupported manifest")
    for name in data["files"]:
        p = PurePosixPath(name)
        if not name or "\\" in name or ":" in name or p.is_absolute() or ".." in p.parts:
            raise ValueError("Invalid manifest path")
    required_files(data["files"])
    current = inventory(root)
    expected_files = data["files"]
    changes = {
        "missing": sorted(set(expected_files) - set(current)),
        "added": sorted(set(current) - set(expected_files)),
        "changed": sorted(k for k in set(current) & set(expected_files)
                          if current[k] != expected_files[k]),
    }
    if any(changes.values()):
        raise ValueError("Bundle mismatch: " + json.dumps(changes, ensure_ascii=False))
    return {"status": "verified", "manifest_sha256": actual_digest,
            "source_hash_matched": bool(expected), "files": len(current),
            "semantic_completeness": "not_verified"}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["seal", "verify"])
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--expected-manifest")
    args = parser.parse_args()
    try:
        root = args.bundle.resolve(strict=True)
        if not root.is_dir():
            raise ValueError("Bundle is not a directory")
        if args.action == "seal" and args.expected_manifest:
            raise ValueError("--expected-manifest is only valid for verify")
        result = seal(root) if args.action == "seal" else verify(root, args.expected_manifest)
        print(json.dumps(result, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
