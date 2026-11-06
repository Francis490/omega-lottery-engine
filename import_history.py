import csv
import io
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from database import DB_PATH, init_db, save_ej, save_se, save_vv
from models import EurojackpotDraw, SuperenalottoDraw, VinciDraw
from pydantic import ValidationError


EJ_CSV = Path("EJ_ab_2018.csv")
SN_CSV_CANDIDATES = [
    Path("superenalotto_storico.csv"),
    Path("Estrazioni del Superenalotto dal 03 Dicembre 1997 al 31 Ottobre 2026 _ Superenalottooggi.it.csv"),
]
SWFL_CSV = Path("swfl_storico.csv")

EJ_DATE_REGEX = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")


def table_count(table: str) -> int:
    """Numero di righe in una tabella (0 se DB o tabella assenti)."""
    if not DB_PATH.exists():
        return 0
    try:
        with sqlite3.connect(DB_PATH) as conn:
            return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        return 0


def db_is_populated() -> bool:
    """True se TUTTE e tre le tabelle hanno almeno una riga."""
    return table_count("ej") > 0 and table_count("se") > 0 and table_count("vv") > 0


def _detect_format(path: Path) -> str:
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        first = f.readline().strip().lower()
    if first.startswith("data;"):
        return "new"
    return "old"


def _read_semicolon(path: Path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        yield from csv.reader(f, delimiter=";")


# ---------------- EUROJACKPOT ----------------
def _import_ej_new(path: Path) -> int:
    count = 0
    for i, row in enumerate(_read_semicolon(path)):
        if i == 0 or len(row) < 8:
            continue
        try:
            date = datetime.strptime(row[0].strip(), "%Y-%m-%d").date()
            mains = [int(row[k].strip()) for k in range(1, 6)]
            euros = [int(row[k].strip()) for k in range(6, 8)]
            save_ej(EurojackpotDraw(draw_date=date, mains=mains, euros=euros))
            count += 1
        except (ValueError, ValidationError, IndexError):
            continue
    return count


def _import_ej_old(path: Path) -> int:
    count, errors = 0, 0
    with open(path, "r", encoding="cp1252", newline="") as fp:
        for lineno, row in enumerate(csv.reader(fp, delimiter=";"), 1):
            if len(row) < 9 or not row[0].strip():
                continue
            first = row[0].strip()
            # Salta header, footer e commenti: elabora solo righe che iniziano
            # con una data tedesca dd.mm.yyyy (robusto al mojibake del CSV).
            if not EJ_DATE_REGEX.match(first):
                continue
            try:
                draw_date = datetime.strptime(first, "%d.%m.%Y").date()
                mains = [int(row[i].strip()) for i in range(1, 6)]
                euros = [int(row[i].strip()) for i in range(6, 8)]
                save_ej(EurojackpotDraw(draw_date=draw_date, mains=mains, euros=euros))
                count += 1
            except (ValueError, ValidationError, IndexError) as exc:
                errors += 1
                if errors <= 3:
                    print(f"[EJ lineno {lineno}] skip: {exc}")
    print(f"[EJ] Errori: {errors}")
    return count


def import_eurojackpot_csv() -> int:
    if not EJ_CSV.exists():
        print(f"[EJ] File non trovato: {EJ_CSV}")
        return 0
    fmt = _detect_format(EJ_CSV)
    if fmt == "new":
        n = _import_ej_new(EJ_CSV)
        print(f"[EJ] Importate {n} estrazioni (formato nuovo)")
        return n
    n = _import_ej_old(EJ_CSV)
    print(f"[EJ] Importate {n} estrazioni (formato originale)")
    return n


# ---------------- SUPERENALOTTO ----------------
def _opt_int_1_90(s) -> Optional[int]:
    s = (s or "").strip() if isinstance(s, str) else ""
    if not s:
        return None
    try:
        n = int(s)
    except ValueError:
        return None
    return n if 1 <= n <= 90 else None


def _import_se_new(path: Path) -> int:
    count = 0
    for i, row in enumerate(_read_semicolon(path)):
        if i == 0 or len(row) < 7:
            continue
        try:
            date = datetime.strptime(row[0].strip(), "%Y-%m-%d").date()
            mains = [int(row[k].strip()) for k in range(1, 7)]
            jolly = _opt_int_1_90(row[7]) if len(row) > 7 else None
            superstar = _opt_int_1_90(row[8]) if len(row) > 8 else None
            save_se(SuperenalottoDraw(
                draw_date=date, mains=mains,
                jolly=jolly, superstar=superstar,
            ))
            count += 1
        except (ValueError, ValidationError, IndexError):
            continue
    return count


def _import_se_old(path: Path) -> int:
    with open(path, "r", encoding="utf-8") as fp:
        lines = fp.readlines()
    if lines and lines[0].startswith("\ufeff"):
        lines[0] = lines[0].lstrip("\ufeff")
    start = next(
        (i for i, ln in enumerate(lines) if ln.lstrip().startswith("N. conc.")),
        None,
    )
    if start is None:
        print(f"[SE] Header 'N. conc.' non trovato in {path.name}")
        return 0
    count, errors = 0, 0
    reader = csv.DictReader(io.StringIO("".join(lines[start:])))
    for row in reader:
        n_conc = (row.get("N. conc.") or "").strip()
        if not n_conc.isdigit():
            continue
        try:
            draw_date = datetime.strptime(
                (row.get("Data estr.") or "").strip(), "%d/%m/%Y"
            ).date()
            mains = [int(row[f"{i}°"]) for i in range(1, 7)]
            save_se(SuperenalottoDraw(
                draw_date=draw_date, mains=mains,
                jolly=_opt_int_1_90(row.get("J", "")),
                superstar=_opt_int_1_90(row.get("SS", "")),
            ))
            count += 1
        except (ValueError, KeyError, ValidationError) as exc:
            errors += 1
            if errors <= 3:
                print(f"[SE concorso {n_conc}] skip: {exc}")
    print(f"[SE] Errori: {errors}")
    return count


def _find_sn_csv() -> Optional[Path]:
    for p in SN_CSV_CANDIDATES:
        if p.exists():
            return p
    return None


def import_superenalotto_csv() -> int:
    path = _find_sn_csv()
    if not path:
        print(f"[SE] File non trovato. Cercati: {[p.name for p in SN_CSV_CANDIDATES]}")
        return 0
    fmt = _detect_format(path)
    if fmt == "new":
        n = _import_se_new(path)
        print(f"[SE] Importate {n} estrazioni (formato nuovo)")
        return n
    n = _import_se_old(path)
    print(f"[SE] Importate {n} estrazioni (formato originale)")
    return n


# ---------------- SWFL ----------------
def _import_swfl_new(path: Path) -> int:
    count = 0
    for i, row in enumerate(_read_semicolon(path)):
        if i == 0 or len(row) < 9:
            continue
        try:
            date = datetime.strptime(row[0].strip(), "%Y-%m-%d").date()
            nums = [int(row[k].strip()) for k in range(1, 9)]
            save_vv(VinciDraw(draw_date=date, mains=nums))
            count += 1
        except (ValueError, ValidationError, IndexError):
            continue
    return count


def _import_swfl_old(path: Path) -> int:
    count, errors = 0, 0
    with open(path, "r", encoding="utf-8", newline="") as fp:
        for row in csv.reader(fp):
            if len(row) < 3 or row[0].strip().lower() == "concorso":
                continue
            try:
                dt = datetime.strptime(row[1].strip(), "%d/%m/%Y").date()
                nums = [int(n) for n in row[2].replace('"', "").strip().split()]
                if len(nums) != 8:
                    raise ValueError(f"attesi 8 numeri, trovati {len(nums)}")
                save_vv(VinciDraw(draw_date=dt, mains=nums))
                count += 1
            except (ValueError, ValidationError) as exc:
                errors += 1
                if errors <= 3:
                    print(f"[SWFL] skip: {exc}")
    print(f"[SWFL] Errori: {errors}")
    return count


def import_swfl_csv() -> int:
    if not SWFL_CSV.exists():
        print(f"[SWFL] File non trovato: {SWFL_CSV}")
        return 0
    fmt = _detect_format(SWFL_CSV)
    if fmt == "new":
        n = _import_swfl_new(SWFL_CSV)
        print(f"[SWFL] Importate {n} estrazioni (formato nuovo)")
        return n
    n = _import_swfl_old(SWFL_CSV)
    print(f"[SWFL] Importate {n} estrazioni (formato originale)")
    return n


if __name__ == "__main__":
    init_db()

    ej_count = table_count("ej")
    se_count = table_count("se")
    vv_count = table_count("vv")

    print(f"[DB] Stato attuale: EJ={ej_count}, SE={se_count}, SWFL={vv_count}")

    if ej_count > 0 and se_count > 0 and vv_count > 0:
        print("[SKIP] omega.db già popolato su tutte le tabelle, salto import CSV.")
    else:
        print("=" * 62)
        print(" Import mirato: solo le tabelle vuote")
        print("=" * 62)

        if ej_count == 0:
            import_eurojackpot_csv()
        else:
            print(f"[EJ] Già {ej_count} righe, salto import.")

        if se_count == 0:
            import_superenalotto_csv()
        else:
            print(f"[SE] Già {se_count} righe, salto import.")

        if vv_count == 0:
            import_swfl_csv()
        else:
            print(f"[SWFL] Già {vv_count} righe, salto import.")

    print("=" * 62)
    with sqlite3.connect(DB_PATH) as conn:
        for table, label in [("ej", "Eurojackpot"), ("se", "Superenalotto"), ("vv", "SWFL")]:
            try:
                total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                rng = conn.execute(f"SELECT MIN(date), MAX(date) FROM {table}").fetchone()
                print(f"  {label:14s} {total:>6} righe   [{rng[0]} → {rng[1]}]")
            except sqlite3.OperationalError:
                print(f"  {label:14s} tabella assente")
    print("=" * 62)
