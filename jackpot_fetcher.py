import requests
from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)

DEFAULT_JACKPOTS = {
    "eurojackpot": 30_000_000,
    "superenalotto": 40_000_000,
    "swfl": 2_500_000 # Nome aggiornato
}

# ... (le funzioni fetch_eurojackpot_jackpot e fetch_superenalotto_jackpot rimangono identiche) ...

def fetch_vinci_jackpot():
    try:
        res = requests.get("https://www.agimeg.it/wp-json/wp/v2/posts?categories=1031", timeout=15)
        posts = res.json()
        if posts:
            latest = posts[0]
            content = BeautifulSoup(latest["content"]["rendered"], "lxml").get_text(" ", strip=True)
            match = re.search(r"([\d\.]+)\s*euro\s*(?:al mese|mensili)", content, re.IGNORECASE)
            if match:
                rendita_mensile = int(re.sub(r"[^\d]", "", match.group(1)))
                jackpot_stimato = rendita_mensile * 12 * 20
                logger.info(f"SWFL Rendita: {rendita_mensile} €/mese -> Valore: {jackpot_stimato} €")
                return jackpot_stimato
    except Exception as e:
        logger.warning(f"Impossibile recuperare la rendita SWFL: {e}")
    return None

def get_all_jackpots():
    logger.info("Recupero dei jackpot aggiornati...")
    jackpots = {
        "eurojackpot": fetch_eurojackpot_jackpot() or DEFAULT_JACKPOTS["eurojackpot"],
        "superenalotto": fetch_superenalotto_jackpot() or DEFAULT_JACKPOTS["superenalotto"],
        "swfl": fetch_vinci_jackpot() or DEFAULT_JACKPOTS["swfl"] # Nome aggiornato
    }
    logger.info(f"Jackpot finali in uso: {jackpots}")
    return jackpots
