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
        if res.status_code != 200:
            print(f"Impossibile scaricare {file_name}.")
            return
        data = res.json()
    except Exception as e:
        print(f"Errore download: {e}")
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
                except:
                    pass
        conn.commit()
    print(f"Importate {count} estrazioni per {table_name.upper()}.")

def import_eurojackpot_csv():
    print("Cerco file EJ_ab_2018.csv...")
    if not Path("EJ_ab_2018.csv").exists():
        print("ERRORE: File EJ_ab_2018.csv non trovato nella root del repository!")
        return

    count = 0
    with open("EJ_ab_2018.csv", mode='r', encoding='utf-8', errors='ignore') as f, \
         sqlite3.connect(DB_PATH) as conn:
        reader = csv.reader(f, delimiter=';')
        for row in reader:
            # Salta intestazioni e righe vuote
            if len(row) < 8 or not row[0].strip() or row[0].strip() == "Datum":
                continue
            try:
                # Esempio riga: 05.01.2018;40; 2;38;45; 7;10; ...
                date_str = row[0].strip()
                dt = datetime.strptime(date_str, "%d.%m.%Y").date().isoformat()
                
                # Estrae i 5 numeri principali (colonne 1-5)
                mains = [int(row[i].strip()) for i in range(1, 6)]
                # Estrae i 2 euronumeri (colonne 6-7)
                euros = [int(row[i].strip()) for i in range(6, 8)]
                
                conn.execute("INSERT OR IGNORE INTO ej VALUES (?,?,?,?,?,?,?,?)", (dt, *mains, *euros))
                count += 1
            except Exception as e:
                pass
        conn.commit()
    print(f"Importate {count} estrazioni per EUROJACKPOT dal CSV.")

if __name__ == "__main__":
    import_from_github("superenalotto-venus-vortex", "venus_history.json", "se", 6)
    import_from_github("aurora-engine", "vinci_history.json", "vv", 8)
    import_eurojackpot_csv()
