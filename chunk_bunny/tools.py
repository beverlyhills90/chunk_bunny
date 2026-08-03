from chunking_models import RecursiveLevel, Literal, CodeBase
from typing import Generator
from pathlib import Path
import re
import hashlib
import ast



class ChunkingError(Exception):
    def __init__(self, msg="Unknow chunking ERROR"):
        super().__init__(msg)


def hash_generator(file_path: Path) -> str:
    try:
        with open(file_path, "rb") as file:
            content = file.read()
            md5 = hashlib.md5()
            md5.update(content)
        return md5.hexdigest()
    except OSError as e:
        raise ChunkingError(f"Problem with file:{file_path}:{e}")


def spliter(text: str, delimiter: str, mode: Literal | CodeBase) -> list[str]:
    if mode == "header":
        esc_delim = re.escape(delimiter)
        char = re.escape(delimiter[0])
        pattern = rf"(?=(?:^|\n){esc_delim}(?!{char})\s)"
        return [c for c in re.split(pattern, text) if c]
    elif mode == "literal" or mode == "python":
        return text.split(delimiter)


def get_next_chunk_md(
    text: str, rules: list[RecursiveLevel], chunk_size: int
) -> Generator[tuple]:
    char_counter = 0
    level_idx = 0

    # TODO add prev next logic
    def _recursive_split(
        text: str,
        rules: list[RecursiveLevel],
        level_idx: int,
        chunk_size: int,
        char_counter: int,
    ) -> Generator[tuple]:
        current_chunk = []
        start_char = char_counter
        if level_idx == len(rules):
            while len(text) > chunk_size:
                yield (start_char, char_counter, text[:chunk_size])
                char_counter += chunk_size
                start_char = char_counter
                text = text[chunk_size:]
            if text.strip():
                yield (char_counter, char_counter + len(text), text)
            return
        


        delimiter = rules[level_idx].delimiter
        r_mode = rules[level_idx].mode
        chunks = spliter(text, delimiter, r_mode)
        for i, chunk in enumerate(chunks):
            delim_len = (
                len(delimiter)
                if (r_mode == "literal" and i < len(chunks) - 1)
                else 0
            )
            if len(chunk) > chunk_size:
                if current_chunk:
                    yield (start_char, char_counter, "".join(current_chunk))
                    current_chunk = []
                yield from _recursive_split(
                    chunk, rules, level_idx + 1, chunk_size, char_counter
                )
                char_counter += len(chunk) + delim_len
                start_char = char_counter
            elif (
                len(chunk)
                + sum(len(t) for t in current_chunk)
                + (len(current_chunk) * delim_len)
                <= chunk_size
            ):
                if not chunk:
                    start_char = char_counter

                current_chunk += [chunk]
                char_counter += len(chunk) + delim_len
            else:
                yield (
                    start_char,
                    char_counter,
                    f"{delimiter}".join(current_chunk),
                )
                start_char = char_counter
                char_counter += len(chunk) + delim_len
                current_chunk = [chunk]
        if current_chunk:
            join_str = delimiter if r_mode == "literal" else ""

            yield (start_char, char_counter, join_str.join(current_chunk))

    return _recursive_split(text, rules, level_idx, chunk_size, char_counter)


def _split_lines(
    meta_lines: list[tuple],
    line_start: int,
    line_end: int,
    chunk_size: int,
    char_counter: int,
) -> Generator[tuple]:

    chunk = []
    start_char = char_counter
    for size, line in meta_lines[line_start - 1 : line_end]:
        if len(line) > chunk_size:
            if chunk:
                yield (start_char, char_counter, "".join(chunk))
                chunk = []
                start_char = char_counter
            while len(line) > chunk_size:
                yield (start_char, char_counter, line[:chunk_size])
                char_counter += len(line[:chunk_size])
                line = line[chunk_size:]

                start_char = char_counter
            else:
                if len("".join(chunk)) + len(line) <= chunk_size:
                    chunk.append(line)
                    char_counter += len(line)
                else:
                    yield (start_char, char_counter, "".join(chunk))
                    start_char = char_counter
                    char_counter += len(line)
        else:
            chunk.append(line)
            char_counter += size

    if chunk:
        yield (start_char, char_counter, "".join(chunk))


def get_next_cuhnk_code(text: str, chunk_size: int) -> Generator[tuple]:
    char_counter = 0

    clear_lines = text.splitlines(keepends=True)
    char_counter = 0
    meta_lines = []
    for line in clear_lines:
        meta_lines.append((len(line), line))
        char_counter += len(line)
    if char_counter <= chunk_size:
        yield (0, char_counter, text)
        return

    char_counter = 0
    try:
        tree = ast.parse(text)
    except SyntaxError:
        raise SyntaxError

    def _split_nodes(
        nodes: list[ast.AST],
        meta_lines: list[tuple],
        clear_lines: list[str],
        chunk_size: int,
        char_counter: int,
    ):
        current_chunk = []
        start_chunk = char_counter

        for node in nodes:
            line_start, line_end = node.lineno, node.end_lineno
            if (
                len("".join(current_chunk))
                + sum(l[0] for l in meta_lines[line_start - 1 : line_end])
                <= chunk_size
            ):
                current_chunk.extend(clear_lines[line_start - 1 : line_end])
                char_counter += sum(
                    l[0] for l in meta_lines[line_start - 1 : line_end]
                )
            else:
                if current_chunk:
                    yield (start_chunk, char_counter, "".join(current_chunk))
                yield from _split_lines(
                    meta_lines, line_start, line_end, chunk_size, char_counter
                )
                char_counter += sum(
                    l[0] for l in meta_lines[line_start - 1 : line_end]
                )
                start_chunk = char_counter
                current_chunk = []
        if current_chunk:
            yield (start_chunk, char_counter, "".join(current_chunk))

    yield from _split_nodes(
        tree.body, meta_lines, clear_lines, chunk_size, char_counter
    )
