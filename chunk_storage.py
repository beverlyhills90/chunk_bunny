import sqlite3
from chunking_models import Chunk
from pathlib import Path


class ChunkStorage:
    @staticmethod
    def create(db_name: str) -> bool:
        db_path = Path(f"{db_name}")
        db_exist = db_path.exists()
        connection = sqlite3.connect(db_name)
        cursor = connection.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Chunks (
        chunk_id INTEGER PRIMARY KEY,
        file_path TEXT NOT NULL,
        first_character_index INTEGER NOT NULL,
        last_character_index INTEGER NOT NULL,
        text TEXT NOT NULL,
        type TEXT NOT NULL,
        metadata TEXT NOT NULL,
        breadcrumbs TEXT NOT NULL
        )
        """)
        connection.commit()
        connection.close()
        return db_exist

    @staticmethod
    def insert_chunks(
        connection: sqlite3.Connection, chunks: list[Chunk]
    ) -> None:
        cursor = connection.cursor()

        for chunk in chunks:
            cursor.execute(
                f"INSERT INTO Chunks (file_path, first_character_index, last_character_index, text, type, metadata, breadcrumbs) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    str(chunk.file_path),
                    chunk.first_chunk_char,
                    chunk.last_chunk_char,
                    chunk.text,
                    chunk.type,
                    str(chunk.metadata),
                    str(chunk.breadcrumbs),
                ),
            )


    @staticmethod
    def delete_chunks_by_file(
        connection: sqlite3.Connection, file_path: str
    ) -> None:
        cursor = connection.cursor()
        cursor.execute(
            "DELETE FROM Chunks WHERE file_path = ?", (str(file_path),)
        )

    @staticmethod
    def clear_all_chunks(connection: sqlite3.Connection) -> None:
        cursor = connection.cursor()
        cursor.execute("""DELETE FROM Chunks""")
        connection.commit()

    @staticmethod
    def get_all_chunks(connection: sqlite3.Connection) -> None:
        pass

    @staticmethod
    def get_chunks_by_ids(ids: list[int]) -> None:
        pass
