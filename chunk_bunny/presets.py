from chunk_bunny.chunking_models import *


DefaultRulesForCodeBase = [
    RecursiveLevel(delimiter="class", include_delim="prev", mode="python"),
    RecursiveLevel(delimiter="def", include_delim="prev", mode="python"),
    RecursiveLevel(delimiter="if", include_delim="prev", mode="python"),
    RecursiveLevel(delimiter="for", include_delim="prev", mode="python"),
]


DefaultRulesForMarkdownChunking = [
    RecursiveLevel(delimiter="#", include_delim="prev", mode="header"),
    RecursiveLevel(delimiter="##", include_delim="prev", mode="header"),
    RecursiveLevel(delimiter="###", include_delim="prev", mode="header"),
    RecursiveLevel(delimiter="\n\n", include_delim="prev", mode="literal"),
    RecursiveLevel(delimiter="\n", include_delim="prev", mode="literal"),
    RecursiveLevel(delimiter=" ", include_delim="prev", mode="literal"),
]
