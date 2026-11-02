import requests
import json
import sqlite3
import csv
from datetime import datetime
from pathlib import Path

DB_PATH = Path("omega.db")

def import_from_github(repo_name, file_name, table_name, num_cols):
    print(f"Scarico storico {file_name} da {repo_name}...")
    url = f"https://raw.githubusercontent.com/Francis490/{repo_name}/main/{file_name}"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code != 200: return
        data = res.json()
    except Exception:
        return

    count = 0
    with sqlite3.connect(DB_PATH) as conn:
        for item in data:
            date_str = item.get("data")
            nums = item.get("combinazione") if "combinazione" in item else item.get("numeri")
            if date_str and nums and len(nums) >= num_cols:
                try:
                    dt = datetime.strptime(date_str, "%d/%m/%Y").date().isoformat()
                    final_nums = nums[:num_cols]
                    placeholders = ",".join(["?"] * (num_cols + 1))
                    conn.execute(f"INSERT OR IGNORE INTO {table_name} VALUES ({placeholders})", (dt, *final_nums))
                    count += 1
                except: pass
        conn.commit()
    print(f"Importate {count} estrazioni per {table_name.upper()} (da JSON).")

def import_eurojackpot_csv():
    filename = "EJ_ab_2018.csv"
    if not Path(filename).exists():
        print(f"ERRORE: File {filename} non trovato!")
        return

    count = 0
    with open(filename, mode='r', encoding='utf-8', errors='ignore') as f, \
         sqlite3.connect(DB_PATH) as conn:
        reader = csv.reader(f, delimiter=';')
        for row in reader:
            if len(row) < 8 or not row[0].strip() or row[0].strip() == "Datum":
                continue
            try:
                dt = datetime.strptime(row[0].strip(), "%d.%m.%Y").date().isoformat()
                mains = [int(row[i].strip()) for i in range(1, 6)]
                euros = [int(row[i].strip()) for i in range(6, 8)]
                conn.execute("INSERT OR IGNORE INTO ej VALUES (?,?,?,?,?,?,?,?)", (dt, *mains, *euros))
                count += 1
            except: pass
        conn.commit()
    print(f"Importate {count} estrazioni per EUROJACKPOT (da CSV).")

def import_superenalotto_csv():
    filename = "superenalotto_storico.csv"
    if not Path(filename).exists():
        print(f"ERRORE: File {filename} non trovato!")
        return

    count = 0
    with open(filename, mode='r', encoding='utf-8', errors='ignore') as f, \
         sqlite3.connect(DB_PATH) as conn:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 8:
                continue
            try:
                date_str = row[1].strip()
                dt = datetime.strptime(date_str, "%d/%m/%Y").date().isoformat()
                nums = [int(row[i].strip()) for i in range(2, 8)]
                if len(nums) == 6 and all(1 <= n <= 90 for n in nums):
                    conn.execute("INSERT OR IGNORE INTO se VALUES (?,?,?,?,?,?,?)", (dt, *nums))
                    count += 1
            except (ValueError, IndexError):
                pass
        conn.commit()
    print(f"Importate {count} estrazioni per SUPERENALOTTO (da CSV gigante).")

if __name__ == "__main__":
    import_from_github("superenalotto-venus-vortex", "venus_history.json", "se", 6)
    import_from_github("aurora-engine", "vinci_history.json", "vv", 8)
    import_eurojackpot_csv()
    import_superenalotto_csv()
