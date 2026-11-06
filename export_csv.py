"""
Esporta i CSV storici dal database SQLite in formato unificato:

    data;n1;n2;...;nk[;extra...]

- EJ   -> data;n1;n2;n3;n4;n5;e1;e2
- SE   -> data;n1;n2;n3;n4;n5;n6;jolly;superstar
- SWFL -> data;n1;n2;n3;n4;n5;n6;n7;n8

I file vengono sovrascritti ad ogni run: restano sempre allineati
all'ultima estrazione presente nel DB (fonte di verità).
"""
import csv
import sqlite3
from pathlib import Path

DB_PATH = Path("omega.db")

EJ_CSV = Path("EJ_ab_2018.csv")
SE_CSV = Path("superenalotto_storico.csv")
SWFL_CSV = Path("swfl_storico.csv")


def export_eurojackpot(conn):
    rows = conn.execute(
        "SELECT date, n1, n2, n3, n4, n5, e1, e2 FROM ej ORDER BY date"
    ).fetchall()
    with open(EJ_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["data", "n1", "n2", "n3", "n4", "n5", "e1", "e2"])
        w.writerows(rows)
    print(f"[EXPORT] Eurojackpot: {len(rows)} righe")


def export_superenalotto(conn):
    rows = conn.execute(
        "SELECT date, n1, n2, n3, n4, n5, n6, jolly, superstar "
        "FROM se ORDER BY date"
    ).fetchall()
    with open(SE_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["data", "n1", "n2", "n3", "n4", "n5", "n6", "jolly", "superstar"])
        for r in rows:
            jolly = r[7] if r[7] is not None else ""
            superstar = r[8] if r[8] is not None else ""
            w.writerow([r[0], *r[1:7], jolly, superstar])
    print(f"[EXPORT] Superenalotto: {len(rows)} righe")


def export_swfl(conn):
    rows = conn.execute(
        "SELECT date, n1, n2, n3, n4, n5, n6, n7, n8 FROM vv ORDER BY date"
    ).fetchall()
    with open(SWFL_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["data", "n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8"])
        w.writerows(rows)
    print(f"[EXPORT] SWFL: {len(rows)} righe")


def main():
    if not DB_PATH.exists():
        print("omega.db non trovato. Esegui prima il bot.")
        return
    with sqlite3.connect(DB_PATH) as conn:
        export_eurojackpot(conn)
        export_superenalotto(conn)
        export_swfl(conn)


if __name__ == "__main__":
    main()
