"""LLM codesearch plugin."""

from __future__ import annotations


from .cli import cli


def register(llm):
    """Called by the ``llm`` plugin system to register commands."""
    llm.cli.add_command(cli, name="codesearch")
