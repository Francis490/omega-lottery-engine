import os
import requests
import json
import logging
from datetime import datetime
from pathlib import Path

from database import init_db, get_recent
from fetcher import fetch_eurojackpot, fetch_superenalotto, fetch_vinci
from omega_brain import get_decision, generate_ticket
from jackpot_fetcher import get_all_jackpots

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# CALENDARIO ESTRAZIONI (0=Lun, 1=Mar, 2=Mer, 3=Gio, 4=Ven, 5=Sab, 6=Dom)
DRAW_DAYS = {
    "eurojackpot": [1, 4],                 # Martedì e Venerdì
    "superenalotto": [1, 3, 4, 5],         # Martedì, Giovedì, Venerdì, Sabato
    "vinci_vita": [0, 1, 2, 3, 4, 5, 6]    # Tutti i giorni (incluso Giovedì)
}

def send_telegram(msg):
    if TOKEN and CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        except Exception as e:
            logging.error(f"Errore invio Telegram: {e}")

def run():
    logging.info("Avvio Omega Engine...")
    init_db()
    
    # 1. Fetch di tutti i giochi per mantenere il DB aggiornato
    fetch_eurojackpot()
    fetch_superenalotto()
    fetch_vinci()

    # 2. Recupero AUTOMATICO dei jackpot reali
    logging.info("Recupero jackpot in corso...")
    jackpots = get_all_jackpots()
    
    oggi = datetime.now().weekday()
    day_names = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
    
    report = f"🧠 *OMEGA ENGINE - {day_names[oggi].upper()}*\n\n"
    pwa_data = {"timestamp": "Ultimo aggiornamento", "games": {}}
    giocate_oggi = 0

    # 3. Elaborazione intelligente per ogni gioco
    for game, jackpot in jackpots.items():
        # Controlla se oggi si estrae questo gioco
        if oggi not in DRAW_DAYS[game]:
            pwa_data["games"][game] = {"status": "NO_DRAW", "ev": 0}
            continue
            
        giocate_oggi += 1
        decision, ev = get_decision(game, jackpot)
        
        # Con il nuovo omega_brain, decision sarà sempre PLAY_MAX
        if decision == "SKIP" and game != "eurojackpot":
            report += f"🛑 *{game.upper()}*\nEV: `{ev}` · **SKIP**\nNon giocare. Statisticamente svantaggioso.\n\n"
            pwa_data["games"][game] = {"status": "SKIP", "ev": ev}
            continue
            
        recent = get_recent(game, limit=15)
        mains, euros = generate_ticket(game, recent)
        
        num_str = "-".join(map(str, mains))
        if euros: 
            num_str += "  |  ⭐ " + "-".join(map(str, euros))
        
        report += f"✅ *{game.upper()}*\n🎯 `{num_str}`\n\n"
        pwa_data["games"][game] = {
            "status": "PLAY", 
            "ev": ev,
            "mains": mains, 
            "euros": euros
        }

    if giocate_oggi == 0:
        report += "Nessuna estrazione prevista per oggi. Riposo."

    # 4. Salva per la PWA (GitHub Pages)
    Path("docs").mkdir(exist_ok=True)
    with open("docs/latest.json", "w") as f:
        json.dump(pwa_data, f, indent=4)

    # 5. Invia il report finale
    send_telegram(report)
    logging.info("Ciclo Omega completato con successo.")

if __name__ == "__main__":
    run()
