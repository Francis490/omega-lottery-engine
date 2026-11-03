import csv
import io
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from database import DB_PATH, init_db, save_ej, save_se, save_vv
from models import EurojackpotDraw, SuperenalottoDraw, VinciDraw
from pydantic import ValidationError


EJ_CSV = Path("EJ_ab_2018.csv")
SN_CSV_CANDIDATES = [
    Path("Estrazioni del Superenalotto dal 03 Dicembre 1997 al 31 Ottobre 2026 _ Superenalottooggi.it.csv"),
    Path("superenalotto_storico.csv"),
]
SWFL_CSV = Path("swfl_storico.csv")


def _find_sn_csv() -> Optional[Path]:
    for p in SN_CSV_CANDIDATES:
        if p.exists():
            return p
    return None


def import_eurojackpot_csv() -> int:
    if not EJ_CSV.exists():
        print(f"[EJ] File non trovato: {EJ_CSV}")
        return 0
    count, errors = 0, 0
    with open(EJ_CSV, "r", encoding="cp1252", newline="") as fp:
        for lineno, row in enumerate(csv.reader(fp, delimiter=";"), 1):
            if len(row) < 9 or not row[0].strip():
                continue
            first = row[0].strip()
            if first == "Datum" or first.startswith("Spieleinsätze") or first.startswith("Alle Angaben"):
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
    print(f"[EJ] Importate {count} estrazioni (errori: {errors})")
    return count


def _opt_int_1_90(s: str) -> Optional[int]:
    s = (s or "").strip()
    if not s:
        return None
    try:
        n = int(s)
    except ValueError:
        return None
    return n if 1 <= n <= 90 else None


def import_superenalotto_csv() -> int:
    path = _find_sn_csv()
    if not path:
        print(f"[SE] File non trovato. Cercati: {[p.name for p in SN_CSV_CANDIDATES]}")
        return 0
    with open(path, "r", encoding="utf-8") as fp:
        lines = fp.readlines()
    if lines and lines[0].startswith("\ufeff"):
        lines[0] = lines[0].lstrip("\ufeff")
    start = next((i for i, ln in enumerate(lines) if ln.lstrip().startswith("N. conc.")), None)
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
            draw_date = datetime.strptime((row.get("Data estr.") or "").strip(), "%d/%m/%Y").date()
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
    print(f"[SE] Importate {count} estrazioni (errori: {errors})")
    return count


def import_swfl_csv() -> int:
    if not SWFL_CSV.exists():
        print(f"[SWFL] File non trovato: {SWFL_CSV}")
        return 0
    count, errors = 0, 0
    with open(SWFL_CSV, "r", encoding="utf-8", newline="") as fp:
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
    print(f"[SWFL] Importate {count} estrazioni (errori: {errors})")
    return count


if __name__ == "__main__":
    init_db()
    print("=" * 62)
    print(" Import storico Omega Engine")
    print("=" * 62)
    ej = import_eurojackpot_csv()
    se = import_superenalotto_csv()
    swfl = import_swfl_csv()
    print("=" * 62)
    with sqlite3.connect(DB_PATH) as conn:
        for table, label in [("ej", "Eurojackpot"), ("se", "Superenalotto"), ("vv", "SWFL")]:
            try:
                total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                rng = conn.execute(f"SELECT MIN(date), MAX(date) FROM {table}").fetchone()
                print(f"  {label:14s} {total:>6} righe   [{rng[0]} → {rng[1]}]")
            except sqlite3.OperationalError:
                print(f"  {label:14s} tabella assente")
        try:
            n_j = conn.execute("SELECT COUNT(*) FROM se WHERE jolly IS NOT NULL").fetchone()[0]
            n_s = conn.execute("SELECT COUNT(*) FROM se WHERE superstar IS NOT NULL").fetchone()[0]
            print(f"  Jolly/Superstar: {n_j} / {n_s} draw popolati")
        except sqlite3.OperationalError:
            pass
    print("=" * 62)
