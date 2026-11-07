import sqlite3
from pathlib import Path
from models import EurojackpotDraw, SuperenalottoDraw, VinciDraw

DB_PATH = Path("omega.db")

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS ej "
            "(date TEXT PRIMARY KEY, n1 INT, n2 INT, n3 INT, n4 INT, n5 INT, e1 INT, e2 INT)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS se "
            "(date TEXT PRIMARY KEY, n1 INT, n2 INT, n3 INT, n4 INT, n5 INT, n6 INT, jolly INT, superstar INT)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS vv "
            "(date TEXT PRIMARY KEY, n1 INT, n2 INT, n3 INT, n4 INT, n5 INT, n6 INT, n7 INT, n8 INT)"
        )
        # Assicuriamoci che le colonne esistano per DB creati in precedenza
        for col in ("jolly", "superstar"):
            try:
                conn.execute(f"ALTER TABLE se ADD COLUMN {col} INT")
            except sqlite3.OperationalError:
                pass
        conn.commit()

def save_ej(draw: EurojackpotDraw):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO ej (date, n1, n2, n3, n4, n5, e1, e2)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(date) DO UPDATE SET
               n1=excluded.n1, n2=excluded.n2, n3=excluded.n3,
               n4=excluded.n4, n5=excluded.n5, e1=excluded.e1, e2=excluded.e2""",
            (draw.draw_date.isoformat(), *draw.mains, *draw.euros),
        )
        conn.commit()

def save_se(draw: SuperenalottoDraw):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO se (date, n1, n2, n3, n4, n5, n6, jolly, superstar)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(date) DO UPDATE SET
               n1=excluded.n1, n2=excluded.n2, n3=excluded.n3,
               n4=excluded.n4, n5=excluded.n5, n6=excluded.n6,
               jolly=COALESCE(excluded.jolly, se.jolly),
               superstar=COALESCE(excluded.superstar, se.superstar)""",
            (draw.draw_date.isoformat(), *draw.mains, draw.jolly, draw.superstar),
        )
        conn.commit()

def save_vv(draw: VinciDraw):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO vv (date, n1, n2, n3, n4, n5, n6, n7, n8)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(date) DO UPDATE SET
               n1=excluded.n1, n2=excluded.n2, n3=excluded.n3,
               n4=excluded.n4, n5=excluded.n5, n6=excluded.n6,
               n7=excluded.n7, n8=excluded.n8""",
            (draw.draw_date.isoformat(), *draw.mains),
        )
        conn.commit()

def get_recent(game: str, limit=15) -> list:
    table_map = {
        "eurojackpot": "ej",
        "superenalotto": "se",
        "swfl": "vv",
    }
    table_name = table_map.get(game, "ej")
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"SELECT * FROM {table_name} ORDER BY date DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
