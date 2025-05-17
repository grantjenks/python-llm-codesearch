"""Command-line helpers for the codesearch plugin."""

from __future__ import annotations

import asyncio
import hashlib
import os
import json
from pathlib import Path
from typing import List

import click

from .chunker import iter_chunks

SEARCH_SYSTEM_PROMPT = (
    "You are a senior software engineer helping a colleague find information in a codebase."
)

SEARCH_USER_TEMPLATE = """Question: "{query}"

Below is a portion of the repository (≤1M tokens).
If this portion contains information that answers the question, respond with:

  FOUND
  Lines: <comma-separated line numbers or ranges>
  Snippets: |
    ```<language>
    ...relevant lines...
    ```
  Explanation: <≤120 words explaining relevance>

If irrelevant, respond exactly:
  NOT_FOUND
"""

REDUCE_SYSTEM_PROMPT = "Merge partial findings into a single helpful answer."

REDUCE_USER_TEMPLATE = """Question: "{query}"

Partial findings:
---
{findings}
"""

CACHE_FILE = Path.home() / ".llm_codesearch_cache.json"


def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_cache(cache: dict):
    try:
        CACHE_FILE.write_text(json.dumps(cache))
    except Exception:
        pass


def chunk_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def query_chunk(llm, model: str, chunk: str, query: str, cache: dict) -> str:
    h = chunk_hash(chunk + query)
    if h in cache:
        return cache[h]
    response = await llm.complete(
        system=SEARCH_SYSTEM_PROMPT,
        prompt=SEARCH_USER_TEMPLATE.format(query=query, chunk=chunk),
        model=model,
    )
    cache[h] = response
    return response


async def gather_queries(llm, model: str, chunks: List[str], query: str, concurrency: int, cache: dict) -> List[str]:
    sem = asyncio.Semaphore(concurrency)

    async def worker(chunk):
        async with sem:
            return await query_chunk(llm, model, chunk, query, cache)

    tasks = [asyncio.create_task(worker(c)) for c in chunks]
    return await asyncio.gather(*tasks)


def reduce_results(llm, model: str, query: str, results: List[str]) -> str:
    findings = "\n---\n".join(r for r in results if "FOUND" in r)
    if not findings:
        return "No results found."
    response = llm.complete(
        system=REDUCE_SYSTEM_PROMPT,
        prompt=REDUCE_USER_TEMPLATE.format(query=query, findings=findings),
        model=model,
    )
    return response


@click.command()
@click.option("--json", "json_output", is_flag=True, help="Return machine-readable JSON")
@click.option("--files", is_flag=True, help="Show only file paths that matched")
@click.option("--concurrency", default=None, type=int, help="Parallel worker count")
@click.option("--model", default=None, help="Model to use for answering")
@click.option("--cost-estimate", is_flag=True, help="Show cost estimate and abort")
@click.argument("query")
@click.pass_obj
def cli(llm, json_output, files, concurrency, model, cost_estimate, query):
    """Run ad-hoc search across the current repository."""
    repo_root = Path.cwd()
    model = model or llm.default_model
    chunks = list(iter_chunks(repo_root))
    cache = load_cache()

    if cost_estimate:
        total_tokens = sum(len(c) // 4 for c in chunks)
        click.echo(f"Would send ~{total_tokens} tokens")
        return

    results = asyncio.run(gather_queries(llm, model, chunks, query, concurrency or os.cpu_count(), cache))

    save_cache(cache)

    reduced = reduce_results(llm, model, query, results)

    if json_output:
        click.echo(json.dumps({"answer": reduced, "matches": results}))
    else:
        click.echo(reduced)

