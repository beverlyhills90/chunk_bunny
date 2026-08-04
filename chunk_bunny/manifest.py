import json
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Any
from tools import hash_generator, ChunkingError


class ManifestUnit(BaseModel):
    content_hash: str
    chunk_count: int


class ManifestFile(BaseModel):
    manifest_json: Path
    max_chunk_size: int = Field(ge=0)
    """
    JSON FILE FORMAT:
    {
    "MAX_CHUNK_SIZE": 2000,
    "file_path": [
        "96b961029bac67c84acc67aabfba545e", #content hash
        0                                   #chunk counter
    ],
    "file_path": [
        "76e5d5b14e98957d8201f1689d21eb76",
        0
    ]
    }
    """

    def check_max_chunk_size(self) -> bool:
        """Verify if the chunk size in the manifest matches the current configuration.

        If the size has changed or the manifest is newly initialized, resets the
        manifest content with the updated MAX_CHUNK_SIZE.

        Returns:
            bool: True if MAX_CHUNK_SIZE matches the configured size,
            False otherwise.

        Raises:
            ChunkingError: If the manifest file contains invalid JSON.
        """
        res = False
        try:
            with open(self.manifest_json, "r+") as manifest:
                raw_json = manifest.read()
                if raw_json.strip():
                    content = json.loads(raw_json)
        except FileNotFoundError:
            content = {}
        except json.JSONDecodeError as e:
            raise ChunkingError(f"Problem with {self.manifest_json}: {e}")

        if content.get("MAX_CHUNK_SIZE") != self.max_chunk_size:
            new_max_cs = {"MAX_CHUNK_SIZE": self.max_chunk_size}
            content = new_max_cs
            with open(self.manifest_json, "w") as manifest:
                json.dump(content, manifest, ensure_ascii=False, indent=4)
        else:
            res = True

        return res

    def check_file_hash(self, file_path: Path) -> tuple[bool, Any]:
        """Check whether a file has already been processed with an unchanged hash.

        If the file is missing or its hash has changed, updates the manifest with
        an initial ManifestUnit entry.

        Args:
            file_path (Path): Path to the file being checked.

        Returns:
            tuple[bool, Any]: A tuple where the first element is True if the file
            is cached and unchanged (False otherwise), and the second element is
            the newly calculated hash (or None if cached).

        Raises:
            ChunkingError: If the manifest cannot be read or written.
        """
        str_path = str(file_path)
        current_hash = hash_generator(file_path)
        content = {}
        try:
            with open(self.manifest_json, "r") as manifest:
                raw_json = manifest.read()
                if raw_json.strip():
                    content = json.loads(raw_json)
        except json.JSONDecodeError as e:
            raise ChunkingError(f"Problem with {self.manifest_json}: {e}")
        if (
            str_path in content.keys()
            and content[str_path].get("content_hash") == current_hash
        ):
            return (True, None)
        content[str_path] = vars(
            ManifestUnit(chunk_count=0, content_hash=current_hash)
        )
        try:
            with open(self.manifest_json, "w") as manifest:
                json.dump(content, manifest, ensure_ascii=False, indent=4)
            return (False, current_hash)
        except OSError as e:
            raise ChunkingError(f"Unknow error with manifest.json")

    def update_chunk_count(self, file_path: Path, chunk_counter: int) -> None:
        """Update the chunk count for a specific file entry in the manifest.

        Args:
            file_path (Path): Path to the target file.
            chunk_counter (int): The number of generated chunks for this file.

        Raises:
            ChunkingError: If the manifest file is missing, empty, invalid JSON,
                or fails to write.
        """
        str_path = str(file_path)
        content = {}
        try:
            with open(self.manifest_json, "r") as manifest:
                raw_json = manifest.read()
                if raw_json.strip():
                    content = json.loads(raw_json)
                else:
                    raise ChunkingError("Update chunk Error")
            value = ManifestUnit.model_validate(content.get(str_path))
            value.chunk_count = chunk_counter
            content[str_path] = value.model_dump()
        except FileNotFoundError as e:
            raise ChunkingError(f"Problem with {self.manifest_json}: {e}")
        except json.JSONDecodeError as e:
            raise ChunkingError(f"Problem with {self.manifest_json}: {e}")
        with open(self.manifest_json, "w") as manifest:
            json.dump(content, manifest, ensure_ascii=False, indent=4)

    def clear(self) -> None:
        """Clear all entries in the manifest file, resetting it to an empty JSON object.

        Raises:
            ChunkingError: If the manifest file does not exist, is empty, contains
                invalid JSON, or fails to write.
        """
        try:
            with open(self.manifest_json, "r") as manifest:
                raw_json = manifest.read()
                if raw_json.strip():
                    content = json.loads(raw_json)
                else:
                    raise ChunkingError("Update chunk Error")
            content = {}
        except FileNotFoundError as e:
            raise ChunkingError(f"Problem with {self.manifest_json}: {e}")
        except json.JSONDecodeError as e:
            raise ChunkingError(f"Problem with {self.manifest_json}: {e}")
        with open(self.manifest_json, "w") as manifest:
            json.dump(content, manifest, ensure_ascii=False, indent=4)
