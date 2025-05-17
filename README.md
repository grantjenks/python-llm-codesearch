# python-llm-codesearch

This package provides a `llm` extension implementing a simple
code search tool. It splits a repository into large text chunks,
queries each chunk in parallel using your configured LLM model,
and merges any positive findings into a concise result.

Install the package in the same environment as `llm` and run:

```
llm codesearch "How is authentication implemented?"
```

Refer to the module docstrings for details on the implementation.
