"""Migracions lleugeres de schema SQLite (compartides entre Flask i scripts)."""
import sqlite3

_correction_lgm_drop_done = False


def ensure_correction_drop_live_game_manager(conn: sqlite3.Connection) -> None:
    """
    Elimina la columna legacy Correction.live_game_manager (el LGM és Game.live_game_manager).
    Requereix SQLite 3.35+ (ALTER TABLE ... DROP COLUMN). Si falla, la columna pot quedar
    però el codi ja no l'escriu.
    """
    global _correction_lgm_drop_done
    if _correction_lgm_drop_done:
        return
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(Correction)")
    cols = {row[1] for row in cur.fetchall()}
    if "live_game_manager" not in cols:
        _correction_lgm_drop_done = True
        return
    try:
        cur.execute("ALTER TABLE Correction DROP COLUMN live_game_manager")
        conn.commit()
    except sqlite3.OperationalError:
        conn.rollback()
    _correction_lgm_drop_done = True
