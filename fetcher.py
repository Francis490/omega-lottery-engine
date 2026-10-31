import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
from models import EurojackpotDraw, SuperenalottoDraw, VinciDraw
from database import save_ej, save_se, save_vv

logger = logging.getLogger(__name__)

def fetch_eurojackpot():
    try:
        # Fonte primaria JSON (multipasko.pl)
        res = requests.get("https://www.multipasko.pl/widget-wyniki.php?format=json", 
                           timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        data = res.json()["g"]["eurojackpot"]
        
        draw = EurojackpotDraw(
            draw_date=datetime.strptime(data["d"].strip(), "%d.%m.%Y").date(),
            mains=data["l"], 
            euros=data["x"]
        )
        save_ej(draw)
        logger.info("Eurojackpot OK")
    except Exception as e:
        logger.error(f"Errore Fetch Eurojackpot: {e}")

def fetch_superenalotto():
    try:
        # Fonte Lottologia
        res = requests.get("https://www.lottologia.com/superenalotto/estrazioni/", 
                           timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "lxml")
        # Logica semplificata per non far crashare se il sito cambia
        # In produzione andrebbe affinato il regex, ma qui mettiamo un blocco di sicurezza
        text = soup.get_text(" ", strip=True)
        
        # Esempio di logica (da adattare se il sito cambia)
        # In questo step, ci limitiamo a loggare che il fetch è stato tentato
        logger.info("Superenalotto HTML scaricato (parser in standby)")
    except Exception as e:
        logger.error(f"Errore Fetch Superenalotto: {e}")

def fetch_vinci():
    try:
        # Fonte AGIMEG (WordPress REST API)
        res = requests.get("https://www.agimeg.it/wp-json/wp/v2/posts?categories=1031", 
                           timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        posts = res.json()
        logger.info("Vinci Vita API scaricata (parser in standby)")
    except Exception as e:
        logger.error(f"Errore Fetch Vinci Vita: {e}")
