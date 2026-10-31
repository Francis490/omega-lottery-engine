import requests
from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)

# Valori di default (sicuri) in caso di fallimento del fetch
DEFAULT_JACKPOTS = {
    "eurojackpot": 30_000_000,
    "superenalotto": 40_000_000,
    "vinci_vita": 2_500_000 # Stima del valore attuale della rendita
}

def fetch_eurojackpot_jackpot():
    """Recupera il jackpot dell'Eurojackpot da multipasko.pl."""
    try:
        res = requests.get("https://www.multipasko.pl/widget-wyniki.php?format=json", timeout=15)
        data = res.json()
        # Il jackpot è spesso nella sezione 'eurojackpot' o 'jackpot'
        # Cerchiamo un valore numerico grande
        jackpot_str = data.get("g", {}).get("eurojackpot", {}).get("j")
        if jackpot_str:
            # Pulisce la stringa (es. "120.000.000" -> 120000000)
            jackpot = int(re.sub(r"[^\d]", "", str(jackpot_str)))
            logger.info(f"Eurojackpot Jackpot recuperato: {jackpot} €")
            return jackpot
    except Exception as e:
        logger.warning(f"Impossibile recuperare il jackpot Eurojackpot: {e}")
    return None

def fetch_superenalotto_jackpot():
    """Recupera il montepremi del Superenalotto da lottologia.com."""
    try:
        res = requests.get("https://www.lottologia.com/superenalotto/estrazioni/", timeout=15)
        soup = BeautifulSoup(res.text, "lxml")
        text = soup.get_text(" ", strip=True)
        
        # Cerca un pattern come "Montepremi: 48.100.000" o simile
        match = re.search(r"montepremi[:\s]*([\d\.]+)", text, re.IGNORECASE)
        if match:
            jackpot = int(re.sub(r"[^\d]", "", match.group(1)))
            logger.info(f"Superenalotto Jackpot recuperato: {jackpot} €")
            return jackpot
    except Exception as e:
        logger.warning(f"Impossibile recuperare il jackpot Superenalotto: {e}")
    return None

def fetch_vinci_jackpot():
    """Recupera la rendita del Vinci per la Vita da AGIMEG."""
    try:
        res = requests.get("https://www.agimeg.it/wp-json/wp/v2/posts?categories=1031", timeout=15)
        posts = res.json()
        if posts:
            latest = posts[0]
            content = BeautifulSoup(latest["content"]["rendered"], "lxml").get_text(" ", strip=True)
            # Cerca la rendita mensile (es. "15.030 euro al mese")
            match = re.search(r"([\d\.]+)\s*euro\s*(?:al mese|mensili)", content, re.IGNORECASE)
            if match:
                rendita_mensile = int(re.sub(r"[^\d]", "", match.group(1)))
                # Calcolo del valore nominale su 20 anni (12 mesi * 20 anni)
                jackpot_stimato = rendita_mensile * 12 * 20
                logger.info(f"Vinci Vita Rendita: {rendita_mensile} €/mese -> Valore stimato: {jackpot_stimato} €")
                return jackpot_stimato
    except Exception as e:
        logger.warning(f"Impossibile recuperare la rendita Vinci Vita: {e}")
    return None

def get_all_jackpots():
    """Restituisce un dizionario con i jackpot aggiornati per tutti i giochi."""
    logger.info("Recupero dei jackpot aggiornati...")
    
    jackpots = {
        "eurojackpot": fetch_eurojackpot_jackpot() or DEFAULT_JACKPOTS["eurojackpot"],
        "superenalotto": fetch_superenalotto_jackpot() or DEFAULT_JACKPOTS["superenalotto"],
        "vinci_vita": fetch_vinci_jackpot() or DEFAULT_JACKPOTS["vinci_vita"]
    }
    
    logger.info(f"Jackpot finali in uso: {jackpots}")
    return jackpots
