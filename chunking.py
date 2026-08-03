from collections.abc import Generator
from pathlib import Path
from pydantic import BaseModel, Field
from chunking_models import *
from tqdm import tqdm
from presets import DefaultRulesForMarkdownChunking
from tools import *
from manifest import ManifestFile
from chunk_storage import ChunkStorage
import sqlite3

# TODO add overlap


class Chunker(BaseModel):
    max_chunk_size: int = Field(ge=0, default=500)
    markdown_settings: MarkdownChunkingSettings = Field(
        default_factory=lambda: MarkdownChunkingSettings(
            chunk_overlap=200, recursive_rules=DefaultRulesForMarkdownChunking
        )
    )
    code_settings: CodeChunkingSettings = Field(
        default_factory=lambda: CodeChunkingSettings(chunk_overlap=200)
    )
    data_base_name: str = "index.db"
    manifest_json: str = "manifest.json"

    @staticmethod
    def get_next_file(dir: Path) -> Generator[Path]:
        for item in dir.iterdir():
            if item.is_dir():
                yield from Chunker.get_next_file(item)
            else:
                if item.suffix in [".py", ".md"]:
                    yield item


    def chunk_code_base(
        self, file_path: Path
    ) -> list[Chunk]:
        chunks = []
        try:
            with open(file=file_path, encoding="utf-8") as f:
                conntent = f.read()
                get_chunk = get_next_cuhnk_code(conntent, self.max_chunk_size)
                for chunk in get_chunk:
                    data = {
                        "file_path": file_path,
                        "first_chunk_char": chunk[0],
                        "last_chunk_char": chunk[1],
                        "text": chunk[2],
                        "type": "python",
                    }
                    chunks.append(Chunk.model_validate(data))
                return chunks
        except OSError as e:
            raise ChunkingError(f"Problem with file {file_path}: {e}")


    def chunk_markdown(
        self, file_path: Path
    ) -> list[Chunk]:
        chunks = []
        try:
            rules = self.markdown_settings.recursive_rules
            with open(file_path, "r", encoding="utf-8") as f:
                conntent = f.read()
            get_chunk = get_next_chunk_md(conntent, rules, self.max_chunk_size)
            for chunk in get_chunk:
                data = {
                    "file_path": file_path,
                    "first_chunk_char": chunk[0],
                    "last_chunk_char": chunk[1],
                    "text": chunk[2],
                    "type": "markdown",
                }
                chunks.append(Chunk.model_validate(data))
        except OSError as e:
            raise ChunkingError(f"Problem with file {file_path}: {e}")
        return chunks


    def run(self, source_dir: Path) -> None:
        """Main chunking pipeline"""

        if not source_dir.exists() or not source_dir.is_dir():
            raise ChunkingError(f"{source_dir} is not a dir or not exist")

        errors = []
        all_files = list(self.get_next_file(source_dir))
        db_state = ChunkStorage.create(self.data_base_name)
        manifest_rules = ManifestFile(
            manifest_json=self.manifest_json, max_chunk_size=self.max_chunk_size
        )
        connection = sqlite3.connect(self.data_base_name)
        if not db_state or not manifest_rules.check_max_chunk_size():
            ChunkStorage.clear_all_chunks(connection)
        for file in tqdm(all_files, desc="Chunking files", unit="file"):
            hash_res = manifest_rules.check_file_hash(file)

            if hash_res[0]:
                continue

            if file.suffix == ".py":
                try:
                    chunks = self.chunk_code_base(file)
                except SyntaxError:
                    chunks = self.chunk_markdown(
                        file, manifest_rules
                    )  # TODO test it
                except ChunkingError as e:
                    errors.append(e)
            else:
                try:
                    chunks = self.chunk_markdown(file)
                except ChunkingError as e:
                    errors.append(e)
            with connection:
                ChunkStorage.delete_chunks_by_file(connection, str(file))
                ChunkStorage.insert_chunks(connection,chunks)
                manifest_rules.update_chunk_count(file, len(chunks))
        connection.close()


if __name__ == "__main__":
    chunker = Chunker(max_chunk_size=1000)
    chunker.run(Path("vllm-0.10.1"))
