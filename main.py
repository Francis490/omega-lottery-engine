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

# Calendario estrazioni (0=Lun, 1=Mar, 2=Mer, 3=Gio, 4=Ven, 5=Sab, 6=Dom)
DRAW_DAYS = {
    "eurojackpot": [1, 4],                 # Martedì, Venerdì
    "superenalotto": [1, 3, 4, 5],         # Martedì, Giovedì, Venerdì, Sabato
    "swfl": [0, 1, 2, 3, 4, 5, 6]          # Tutti i giorni
}

DISPLAY_NAMES = {
    "eurojackpot": "EUROJACKPOT",
    "superenalotto": "SUPERENALOTTO",
    "swfl": "SUPER WIN FOR LIFE"
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
    
    # Fetch di tutti i giochi
    fetch_eurojackpot()
    fetch_superenalotto()
    fetch_vinci()

    logging.info("Recupero jackpot in corso...")
    jackpots = get_all_jackpots()
    
    oggi = datetime.now().weekday()
    day_names = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
    
    report = f"🧠 *OMEGA ENGINE - {day_names[oggi].upper()}*\n\n"
    pwa_data = {"timestamp": "Ultimo aggiornamento", "games": {}}
    giocate_oggi = 0

    for game, jackpot in jackpots.items():
        if oggi not in DRAW_DAYS[game]:
            pwa_data["games"][game] = {"status": "NO_DRAW", "ev": 0}
            continue
            
        giocate_oggi += 1
        decision, ev = get_decision(game, jackpot)
        
        # IL MIX PERFETTO: Leggiamo le ultime 200 estrazioni
        recent = get_recent(game, limit=200)
        mains, euros = generate_ticket(game, recent)
        
        num_str = "-".join(map(str, mains))
        if euros: 
            num_str += "  |  ⭐ " + "-".join(map(str, euros))
        
        nome_gioco = DISPLAY_NAMES.get(game, game.upper())
        
        report += f"✅ *{nome_gioco}*\n🎯 `{num_str}`\n\n"
        pwa_data["games"][game] = {
            "status": "PLAY", 
            "ev": ev,
            "mains": mains, 
            "euros": euros
        }

    if giocate_oggi == 0:
        report += "Nessuna estrazione prevista per oggi. Riposo."

    Path("docs").mkdir(exist_ok=True)
    with open("docs/latest.json", "w") as f:
        json.dump(pwa_data, f, indent=4)

    send_telegram(report)
    logging.info("Ciclo Omega completato con successo.")

if __name__ == "__main__":
    run()
