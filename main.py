import os
import requests
import json
import logging
from pathlib import Path
from database import init_db, get_recent
from fetcher import fetch_eurojackpot, fetch_superenalotto, fetch_vinci
from omega_brain import get_decision, generate_ticket

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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
    
    # 1. Fetch di tutti i giochi
    fetch_eurojackpot()
    fetch_superenalotto()
    fetch_vinci()

    # Jackpot attuali (stime)
    jackpots = {
        "eurojackpot": 120_000_000, 
        "superenalotto": 45_000_000, 
        "vinci_vita": 2_500_000
    }
    
    report = "🧠 *OMEGA ENGINE - ANALISI QUANTITATIVA*\n\n"
    pwa_data = {"timestamp": "Ultimo aggiornamento", "games": {}}

    # 3. Elaborazione di ogni gioco
    for game, jackpot in jackpots.items():
        decision, ev = get_decision(game, jackpot)
        
        if decision == "SKIP":
            report += f"🛑 *{game.upper()}*\nEV: `{ev}` · Decisione: **SKIP**\nNon giocare. Statisticamente svantaggioso.\n\n"
            pwa_data["games"][game] = {"status": "SKIP", "ev": ev}
            continue
            
        recent = get_recent(game, limit=15)
        mains, euros = generate_ticket(game, recent)
        
        num_str = "-".join(map(str, mains))
        if euros: 
            num_str += "  |  ⭐ " + "-".join(map(str, euros))
        
        report += f"✅ *{game.upper()}*\nEV: `{ev}`\n🎯 `{num_str}`\n\n"
        pwa_data["games"][game] = {
            "status": "PLAY", 
            "ev": ev,
            "mains": mains, 
            "euros": euros
        }

    # 4. Salva per la PWA (GitHub Pages)
    Path("docs").mkdir(exist_ok=True)
    with open("docs/latest.json", "w") as f:
        json.dump(pwa_data, f, indent=4)

    # 5. Invia il report
    send_telegram(report)
    logging.info("Ciclo Omega completato con successo.")

if __name__ == "__main__":
    run()
