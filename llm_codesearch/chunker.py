"""Utilities for scanning a repository and yielding large text chunks."""

from __future__ import annotations

import os
from pathlib import Path
import hashlib

__all__ = ["iter_chunks", "estimate_tokens", "all_source_files"]

EXCLUDE_DIRS = {".git", "__pycache__"}


def all_source_files(root: Path) -> list[Path]:
    """Yield all file paths under *root* in lexical order."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in sorted(dirnames) if d not in EXCLUDE_DIRS]
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            if path.is_file():
                yield path


def estimate_tokens(text: str) -> int:
    """Rough token estimator with optional tiktoken support."""
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
    except Exception:
        return len(text) // 4
    else:
        return len(enc.encode(text))


def iter_chunks(repo_root: Path, max_tokens: int = 950_000):
    """Yield repository chunks up to *max_tokens* tokens."""
    buf = []
    count = 0
    for path in sorted(all_source_files(repo_root)):
        try:
            text = path.read_text("utf-8")
        except Exception:
            # Skip binary or unreadable files
            continue
        tokens = estimate_tokens(text)
        if count + tokens > max_tokens and buf:
            yield "\n".join(buf)
            buf = []
            count = 0
        buf.append(f"// FILE: {path.relative_to(repo_root)}\n{text}")
        count += tokens
    if buf:
        yield "\n".join(buf)

