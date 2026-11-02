import json
import csv
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("omega.db")

def import_superenalotto():
    if not Path("venus_history.json").exists():
        print("File venus_history.json non trovato.")
        return
    with open("venus_history.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    count = 0
    with sqlite3.connect(DB_PATH) as conn:
        for item in data:
            date_str = item.get("data")
            nums = item.get("combinazione")
            if date_str and nums and len(nums) == 6:
                try:
                    dt = datetime.strptime(date_str, "%d/%m/%Y").date().isoformat()
                    conn.execute("INSERT OR IGNORE INTO se VALUES (?,?,?,?,?,?,?)", (dt, *nums))
                    count += 1
                except: pass
        conn.commit()
    print(f"Superenalotto: importate {count} estrazioni.")

def import_swfl():
    if not Path("vinci_history.json").exists():
        print("File vinci_history.json non trovato.")
        return
    with open("vinci_history.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    count = 0
    with sqlite3.connect(DB_PATH) as conn:
        for item in data:
            date_str = item.get("data")
            nums = item.get("numeri")
            if date_str and nums and len(nums) == 8:
                try:
                    dt = datetime.strptime(date_str, "%d/%m/%Y").date().isoformat()
                    conn.execute("INSERT OR IGNORE INTO vv VALUES (?,?,?,?,?,?,?,?,?)", (dt, *nums))
                    count += 1
                except: pass
        conn.commit()
    print(f"SWFL: importate {count} estrazioni.")

def import_eurojackpot():
    if not Path("EJ_ab_2022.csv").exists():
        print("File EJ_ab_2022.csv non trovato.")
        return
        
    count = 0
    with open("EJ_ab_2022.csv", mode='r', encoding='utf-8', errors='ignore') as f, \
         sqlite3.connect(DB_PATH) as conn:
        reader = csv.reader(f, delimiter=';')
        for row in reader:
            if len(row) < 8 or not row[0].strip() or row[0].strip() == "Datum":
                continue
            try:
                date_str = row[0].strip()
                dt = datetime.strptime(date_str, "%d.%m.%Y").date().isoformat()
                mains = [int(row[i].strip()) for i in range(1, 6)]
                euros = [int(row[i].strip()) for i in range(6, 8)]
                conn.execute("INSERT OR IGNORE INTO ej VALUES (?,?,?,?,?,?,?,?)", (dt, *mains, *euros))
                count += 1
            except: pass
        conn.commit()
    print(f"Eurojackpot: importate {count} estrazioni.")

if __name__ == "__main__":
    import_superenalotto()
    import_swfl()
    import_eurojackpot()
