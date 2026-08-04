# 🐰 Chunk Bunny

A chunking module for a RAG pipeline targeting the [vLLM](https://github.com/vllm-project/vllm) codebase. It splits `.py` and `.md` files into semantically meaningful chunks, stores them in SQLite, and tracks file changes via a hash-based manifest — so unchanged files don't get reprocessed.

## Core idea

Naive "split every N characters" chunking cuts code and text in the middle of functions/paragraphs. Instead, Chunk Bunny uses **recursive chunking**: text is split by a hierarchy of delimiters from "coarse" to "fine", and if a piece is still too big, the recursion drops down a level.

For Python files, instead of text delimiters, chunking is driven by the **AST** — code is split along real syntactic node boundaries (classes, functions, etc.) rather than arbitrary lines.

## How it works

### Markdown / text files — `get_next_chunk_md`

A recursive splitter walks through a prioritized list of rules (`RecursiveLevel`):

```
# → ## → ### → \n\n → \n → " "
```

At each level:
- if a piece fits within `chunk_size`, it's accumulated into a buffer;
- if it doesn't fit, it's recursively split by the next (finer) delimiter;
- if all rules are exhausted and the piece is still too big, it's hard-split by character count.

Header delimiters (`#`, `##`, `###`) are matched with a regex that avoids `#` matching as part of `##`. Literal delimiters (`\n\n`, `\n`, `" "`) use plain `str.split`.

Each chunk is returned as `(start_char, end_char, text)` — coordinates are kept relative to the source file, so context around a retrieved chunk can be reconstructed later.

### Python files — `get_next_cuhnk_code`

1. The file is parsed with `ast.parse`.
2. Top-level nodes (`tree.body`) — classes, functions, plain statements — are accumulated into a chunk as long as they fit within `chunk_size`.
3. If a single node (e.g. a huge function) is bigger than the limit on its own, it isn't recursively split by nested nodes — instead it falls back to a line-by-line split (`_split_lines`), using the same "fits / doesn't fit" logic.
4. If the file fails to parse (`SyntaxError`), the pipeline (`Chunker.run`) falls back to the markdown chunker.

### Storage — `ChunkStorage` (SQLite)

A simple `Chunks` table: file path, character boundaries, text, type (`python`/`markdown`), metadata and breadcrumbs (not actively used yet). Chunks can be inserted and deleted per file — when a file is reindexed, its old chunks are deleted before the new ones are inserted.

### Incremental indexing — `ManifestFile`

`manifest.json` stores an MD5 hash and chunk count for each file:

```json
{
  "MAX_CHUNK_SIZE": 1000,
  "src/model.py": {
    "content_hash": "96b961029bac67c84acc67aabfba545e",
    "chunk_count": 12
  }
}
```

On each `Chunker.run`:
- if `MAX_CHUNK_SIZE` in the manifest doesn't match the current config, the whole chunk database is wiped (old chunks were sized differently, so they're invalid);
- if a file's hash hasn't changed, it's skipped entirely, saving reparsing and re-embedding time.

## Project structure

```
chunking.py          # Chunker — entry point, directory walk, pipeline orchestration
chunking_models.py    # Pydantic models: Chunk, RecursiveLevel, chunking settings
chunk_storage.py       # ChunkStorage — SQLite persistence
manifest.py            # ManifestFile — file hashes, incremental indexing
presets.py              # Ready-made rule sets (DefaultRulesForMarkdownChunking, etc.)
tools.py                 # Low-level algorithms: spliter, get_next_chunk_md, get_next_cuhnk_code
```

## Usage

```python
from pathlib import Path
from chunking import Chunker

chunker = Chunker(max_chunk_size=1000)
chunker.run(Path("vllm-0.10.1"))
```

This creates (or updates) `index.db` and `manifest.json` in the current directory.

## Known limitations / TODO

- **The AST chunker only splits top-level nodes** — recursive descent into `node.body` to re-split oversized nested constructs (e.g. a class with dozens of methods) isn't implemented yet; it falls back to line-by-line splitting instead. #ADD but need to test
- `ChunkStorage.get_all_chunks` and `get_chunks_by_ids` are stubs, not implemented.
- `breadcrumbs` and `metadata` on `Chunk` are currently populated with empty defaults — intended for future context (e.g. "which class/section this chunk belongs to").

## Dependencies

`pydantic`, `tqdm`

## License

MIT
