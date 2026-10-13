"""Strict path resolution via lstat/readlink, including Windows junctions.

The managed Windows sandbox can deny GetFinalPathName directory handles while
allowing the actual files. Never replace strict containment with lexical abspath.
"""
import os
from pathlib import Path
import stat


def canonical_path(path):
    pending = list(Path(path).absolute().parts)
    resolved = Path(pending.pop(0))
    links = 0
    while pending:
        part = pending.pop(0)
        if part in ('', '.'):
            continue
        if part == '..':
            resolved = resolved.parent
            continue
        current = resolved / part
        info = current.lstat()  # Missing/inaccessible components fail closed.
        reparse = bool(getattr(info, 'st_file_attributes', 0) & 0x400)
        if stat.S_ISLNK(info.st_mode) or reparse:
            links += 1
            if links > 40:
                raise ValueError('Symlink/junction cycle or excessive indirection')
            target = os.readlink(current)  # Unknown reparse tags are rejected by the OS.
            if target.startswith('\\\\?\\'):
                target = target[4:]
            elif target.startswith('\\??\\'):
                target = target[4:]
            expanded = Path(target)
            if expanded.is_absolute():
                parts = list(expanded.parts)
                resolved = Path(parts.pop(0))
                pending = parts + pending
            else:
                pending = list(expanded.parts) + pending
        else:
            resolved = current
    return resolved
