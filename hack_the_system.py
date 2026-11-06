import sqlite3
from collections import Counter
from scipy import stats
from pathlib import Path

DB_PATH = Path("omega.db")

def analizza_teoria_3_e_2(tabella, nome_gioco, max_pool):
    print(f"\n==================================================")
    print(f" 🔎 ANALISI PROFONDA: {nome_gioco.upper()}")
    print(f"==================================================")
    
    if not DB_PATH.exists():
        print("Database non trovato.")
        return

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        # Prendi TUTTO lo storico, non solo gli ultimi 200
        rows = conn.execute(f"SELECT * FROM {tabella} ORDER BY date DESC").fetchall()

    if not rows:
        print("Nessun dato.")
        return

    freq = Counter()
    total_numeri_estratti = 0

    for row in rows:
        d = dict(row)
        for k, v in d.items():
            if k.startswith("n") and v:
                freq[v] += 1
                total_numeri_estratti += 1

    # CALCOLO Z-SCORE (Teoria 3: Difetti fisici)
    # Lo Z-Score misura quanto un numero si discosta dalla media.
    # Se un numero ha uno Z-Score > 3 o < -3, c'è un'anomalia statistica forte.
    print("\n--- TEORIA 3 (Difetti Fisici / Caldo-Freddo estremo) ---")
    media_attesa = total_numeri_estratti / max_pool
    dev_std_attesa = (media_attesa * (1 - (1/max_pool))) ** 0.5

    z_scores = {}
    for n in range(1, max_pool + 1):
        uscite = freq.get(n, 0)
        z = (uscite - media_attesa) / dev_std_attesa
        z_scores[n] = z

    # Ordina per Z-Score per trovare i numeri anomali
    numeri_anomali = sorted(z_scores.items(), key=lambda x: abs(x[1]), reverse=True)

    print(f"Totale estrazioni analizzate: {len(rows)}")
    print(f"Uscite attese per numero: {media_attesa:.1f}")
    print("\nI 5 numeri con la deviazione statistica più alta (se Z > 2.5 o < -2.5 è sospetto):")
    for n, z in numeri_anomali[:5]:
        direzione = "CALDO (esce troppo)" if z > 0 else "FREDDO (esce troppo poco)"
        print(f"  Numero {n:02d}: Uscito {freq.get(n, 0)} volte | Z-Score: {z:.2f} ({direzione})")

    # CALCOLO CHI-QUADRO (Teoria 2: Sequenze nascoste)
    # Il test del Chi-Quadro verifica se la distribuzione è casuale.
    # Se il p-value è < 0.05, c'è una probabilità del 5% che il sistema NON sia casuale.
    print("\n--- TEORIA 2 (Sequenze Occulte / Non-casualità) ---")
    osservati = [freq.get(n, 0) for n in range(1, max_pool + 1)]
    attesi = [media_attesa] * max_pool
    
    chi2, p_value = stats.chisquare(osservati, attesi)
    print(f"Test del Chi-Quadro: {chi2:.2f}")
    print(f"P-Value: {p_value:.4f}")
    
    if p_value < 0.05:
        print("🚨 ALLARME: La distribuzione NON è casuale! Potrebbe esserci un pattern o un RNG truccato.")
    else:
        print("✅ La distribuzione è statisticamente casuale. Nessuna prova di RNG truccato o sequenze nascoste.")

def main():
    # Analizziamo tutti e tre i giochi
    analizza_teoria_3_e_2("ej", "Eurojackpot", 50)
    analizza_teoria_3_e_2("se", "Superenalotto", 90)
    analizza_teoria_3_e_2("vv", "Super Win For Life", 90)

if __name__ == "__main__":
    main()
