# AI-hint: In-process SQLite vector store (sqlite-vec) scratchpad module for ephemeral tool outputs (CONV-08).
# Gated to no-op stubs when MIOS_CONV_MEMORY_SQLITE_VEC_ENABLE=false.
# usr/lib/mios/agent-pipe/mios_scratchpad.py

import os
from pathlib import Path

SQLITE_VEC_ENABLE = os.environ.get("MIOS_CONV_MEMORY_SQLITE_VEC_ENABLE", "false").lower() in ("true", "1", "yes", "on")

if SQLITE_VEC_ENABLE:
    import sqlite3
    import sqlite_vec

    def create_scratchpad(session_id: str, scratchpad_dir: str) -> tuple:
        db_dir = Path(scratchpad_dir or "/tmp")
        db_dir.mkdir(parents=True, exist_ok=True)
        path = db_dir / f"mios-session-{session_id}.sqlite"
        
        conn = sqlite3.connect(str(path), check_same_thread=False)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS vec_scratch USING vec0(content TEXT, embedding float[768])")
        conn.commit()
        return conn, path

    def destroy_scratchpad(conn, path: Path) -> None:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass

    def vec_insert(conn, content: str, embedding: list[float]) -> None:
        if not conn:
            return
        serialized = sqlite_vec.serialize_float32(embedding)
        conn.execute("INSERT INTO vec_scratch(content, embedding) VALUES (?, ?)", (content, serialized))
        conn.commit()

    def vec_search(conn, query_embedding: list[float], k: int = 5) -> list[dict]:
        if not conn:
            return []
        serialized = sqlite_vec.serialize_float32(query_embedding)
        cursor = conn.execute(
            "SELECT content, distance FROM vec_scratch WHERE embedding MATCH ? ORDER BY distance LIMIT ?",
            (serialized, k)
        )
        return [{"content": row[0], "distance": row[1]} for row in cursor.fetchall()]

else:
    # Stubs when disabled: no sqlite3/sqlite_vec imports, empty returns
    def create_scratchpad(session_id: str, scratchpad_dir: str) -> tuple:
        return None, None

    def destroy_scratchpad(conn, path) -> None:
        pass

    def vec_insert(conn, content: str, embedding: list[float]) -> None:
        pass

    def vec_search(conn, query_embedding: list[float], k: int = 5) -> list[dict]:
        return []
