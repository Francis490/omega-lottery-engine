import sqlite3
from collections import Counter
from pathlib import Path

DB_PATH = Path("omega.db")

def generate_report(table_name, game_name, max_pool):
    if not DB_PATH.exists():
        print(f"Database non trovato. Esegui prima il bot per creare omega.db")
        return

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        # Prende le ultime 200 estrazioni
        rows = conn.execute(f"SELECT * FROM {table_name} ORDER BY date DESC LIMIT 200").fetchall()
        
    if not rows:
        print(f"Nessun dato nel database per {game_name}.")
        return

    freq = Counter()
    recent_count = len(rows)
    last_seen = {n: None for n in range(1, max_pool + 1)}
    
    # Calcolo frequenze e ritardi
    for i, row in enumerate(rows):
        d = dict(row)
        for k, v in d.items():
            if k.startswith("n") and v:
                freq[v] += 1
                if last_seen[v] is None:
                    last_seen[v] = i # Salva quante estrazioni fa è uscito l'ultima volta

    print(f"\n=============================================")
    print(f" REPORT VORTEX: {game_name.upper()} (Ultime {recent_count} estrazioni)")
    print(f"=============================================")
    
    # Top 10 Caldi
    top_hot = freq.most_common(10)
    print("\n🔥 TOP 10 CALDI (I più frequenti):")
    for num, count in top_hot:
        print(f"  Numero {num:02d}: {count} volte")
        
    # Top 10 Freddi (Mancanti o rari)
    print("\n❄️ TOP 10 FREDDI (I meno frequenti):")
    all_nums = [(n, freq.get(n, 0)) for n in range(1, max_pool + 1)]
    all_nums.sort(key=lambda x: x[1])
    for num, count in all_nums[:10]:
        print(f"  Numero {num:02d}: {count} volte")

    # Numeri in "Buco" (Non usciti da più estrazioni)
    print("\n🕳️ NUMERI IN RITARDO (Non escono da più estrazioni):")
    gaps = [(n, last_seen[n] if last_seen[n] is not None else recent_count) for n in range(1, max_pool + 1)]
    gaps.sort(key=lambda x: x[1], reverse=True)
    
    for num, gap in gaps[:10]:
        if gap >= 15: # Mostra solo quelli che non escono da almeno 15 estrazioni
            print(f"  Numero {num:02d}: non esce da {gap} estrazioni")
            
    print("\n=============================================\n")

if __name__ == "__main__":
    # Genera il report per tutti e 3 i giochi
    generate_report("vv", "Super Win for Life", 90)
    generate_report("se", "Superenalotto", 90)
    generate_report("ej", "Eurojackpot", 50)
