import os
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import requests

from database import init_db, get_recent
from fetcher import fetch_eurojackpot, fetch_superenalotto, fetch_vinci
from omega_brain import get_decision, generate_ticket
from jackpot_fetcher import get_all_jackpots

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

DRAW_DAYS = {
    "eurojackpot": [1, 4],           # Mar, Ven
    "superenalotto": [1, 3, 4, 5],   # Mar, Gio, Ven, Sab
    "swfl": [0, 1, 2, 3, 4, 5, 6],   # Ogni giorno
}

DISPLAY_NAMES = {
    "eurojackpot": "EUROJACKPOT",
    "superenalotto": "SUPERENALOTTO",
    "swfl": "SUPER WIN FOR LIFE",
}

MAX_STALENESS_DAYS = {
    "eurojackpot": 5,
    "superenalotto": 4,
    "swfl": 2,
}


def send_telegram(msg):
    if TOKEN and CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            requests.post(
                url,
                json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"},
                timeout=10,
            )
        except Exception as e:
            logging.error(f"Errore invio Telegram: {e}")


def _latest_draw_age_days(game: str) -> int:
    try:
        recent = get_recent(game, limit=1)
        if not recent:
            return 9999
        last_date = datetime.strptime(recent[0]["date"], "%Y-%m-%d").date()
        today = datetime.now(ZoneInfo("Europe/Rome")).date()
        return (today - last_date).days
    except Exception:
        return 9999


def _is_fresh_enough(game: str) -> bool:
    age = _latest_draw_age_days(game)
    limit = MAX_STALENESS_DAYS[game]
    if age > limit:
        logging.warning(
            f"{game}: ultimo dato troppo vecchio ({age} giorni fa, max {limit})."
        )
        return False
    return True


def _all_good(data: dict) -> bool:
    games = data.get("games", {})
    if not games:
        return False
    return all(info.get("status") != "STALE" for info in games.values())


def run():
    logging.info("Avvio Omega Engine...")

    now = datetime.now(ZoneInfo("Europe/Rome"))
    oggi = now.weekday()
    today_str = now.strftime("%Y-%m-%d")
    day_names = [
        "Lunedì", "Martedì", "Mercoledì", "Giovedì",
        "Venerdì", "Sabato", "Domenica",
    ]

    pwa_path = Path("docs/latest.json")

    # --- DAILY LOCK ---
    if pwa_path.exists():
        try:
            with open(pwa_path, "r") as f:
                existing_data = json.load(f)

            if (
                existing_data.get("timestamp", "").startswith(today_str)
                and _all_good(existing_data)
            ):
                logging.info("Sestina già generata oggi. Invio promemoria.")
                report = (
                    f"🧠 *OMEGA ENGINE - {day_names[oggi].upper()}* "
                    f"(Promemoria)\n\n"
                )
                for game, info in existing_data.get("games", {}).items():
                    if info.get("status") == "PLAY":
                        nome_gioco = DISPLAY_NAMES.get(game, game.upper())
                        num_str = "-".join(map(str, info["mains"]))
                        if info.get("euros"):
                            num_str += "  |  ⭐ " + "-".join(map(str, info["euros"]))
                        report += f"✅ *{nome_gioco}*\n🎯 `{num_str}`\n\n"
                if not report.endswith("(Promemoria)\n\n"):
                    send_telegram(report)
                return
            else:
                logging.info(
                    "Dati di oggi presenti ma non tutti validi (STALE). Rigenero."
                )
        except Exception as e:
            logging.error(f"Errore lettura latest.json: {e}")

    # --- FETCH PHASE ---
    init_db()

    logging.info("Recupero ultime estrazioni...")
    fetched_ok = {
        "eurojackpot": fetch_eurojackpot(),
        "superenalotto": fetch_superenalotto(),
        "swfl": fetch_vinci(),
    }
    logging.info(f"Stato fetch: {fetched_ok}")

    logging.info("Recupero jackpot in corso...")
    jackpots = get_all_jackpots()

    # --- GENERATION PHASE ---
    report = f"🧠 *OMEGA ENGINE - {day_names[oggi].upper()}*\n\n"
    pwa_data = {"timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "games": {}}
    giocate_oggi = 0

    for game, jackpot in jackpots.items():
        nome_gioco = DISPLAY_NAMES.get(game, game.upper())

        if oggi not in DRAW_DAYS[game]:
            pwa_data["games"][game] = {"status": "NO_DRAW", "ev": 0}
            continue

        if not _is_fresh_enough(game):
            report += f"⚠️ *{nome_gioco}* — dati non aggiornati, salto.\n\n"
            pwa_data["games"][game] = {"status": "STALE", "ev": 0}
            continue

        if not fetched_ok[game]:
            logging.warning(f"{game}: fetch fallito, uso dati recenti dal DB.")

        decision, ev = get_decision(game, jackpot)

        if decision == "SKIP":
            report += f"🛑 *{nome_gioco}* — SKIP (EV: {ev:.2f}€)\n\n"
            pwa_data["games"][game] = {"status": "SKIP", "ev": round(ev, 4)}
            continue

        giocate_oggi += 1
        recent = get_recent(game, limit=200)
        mains, euros = generate_ticket(game, recent)

        num_str = "-".join(map(str, mains))
        if euros:
            num_str += "  |  ⭐ " + "-".join(map(str, euros))

        report += f"✅ *{nome_gioco}*\n🎯 `{num_str}`\n\n"
        pwa_data["games"][game] = {
            "status": "PLAY",
            "ev": round(ev, 4),
            "mains": mains,
            "euros": euros,
        }

    if giocate_oggi == 0:
        report += "Nessuna giocata attiva oggi."

    Path("docs").mkdir(exist_ok=True)
    with open(pwa_path, "w") as f:
        json.dump(pwa_data, f, indent=4)

    send_telegram(report)
    logging.info("Ciclo Omega completato con successo.")


if __name__ == "__main__":
    run()
