import requests
import json
import sqlite3
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

if __name__ == "__main__":
    # Importa dai vecchi repo (per lo storico)
    import_from_github("superenalotto-venus-vortex", "venus_history.json", "se", 6)
    import_from_github("aurora-engine", "vinci_history.json", "vv", 8)
    # L'Eurojackpot lo lasciamo al fetcher live, che è molto preciso
