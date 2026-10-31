import sqlite3
from pathlib import Path
from models import EurojackpotDraw, SuperenalottoDraw, VinciDraw

DB_PATH = Path("omega.db")

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("CREATE TABLE IF NOT EXISTS ej (date TEXT PRIMARY KEY, n1 INT, n2 INT, n3 INT, n4 INT, n5 INT, e1 INT, e2 INT)")
        conn.execute("CREATE TABLE IF NOT EXISTS se (date TEXT PRIMARY KEY, n1 INT, n2 INT, n3 INT, n4 INT, n5 INT, n6 INT)")
        # La tabella del database rimane 'vv' per non perdere i dati, ma la mappatura sotto cambia
        conn.execute("CREATE TABLE IF NOT EXISTS vv (date TEXT PRIMARY KEY, n1 INT, n2 INT, n3 INT, n4 INT, n5 INT, n6 INT, n7 INT, n8 INT)")
        conn.commit()

def save_ej(draw: EurojackpotDraw):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR IGNORE INTO ej VALUES (?,?,?,?,?,?,?,?)", 
                     (draw.draw_date.isoformat(), *draw.mains, *draw.euros))
        conn.commit()

def save_se(draw: SuperenalottoDraw):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR IGNORE INTO se VALUES (?,?,?,?,?,?,?)", 
                     (draw.draw_date.isoformat(), *draw.mains))
        conn.commit()

def save_vv(draw: VinciDraw):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR IGNORE INTO vv VALUES (?,?,?,?,?,?,?,?,?)", 
                     (draw.draw_date.isoformat(), *draw.mains))
        conn.commit()

def get_recent(game: str, limit=15) -> list:
    table_map = {
        "eurojackpot": "ej",
        "superenalotto": "se",
        "swfl": "vv" # Mappato 'swfl' alla tabella 'vv'
    }
    table_name = table_map.get(game, "ej")
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(f"SELECT * FROM {table_name} ORDER BY date DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
