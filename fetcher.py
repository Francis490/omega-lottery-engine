import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import logging
from models import EurojackpotDraw, SuperenalottoDraw, VinciDraw
from database import save_ej, save_se, save_vv

logger = logging.getLogger(__name__)

def fetch_eurojackpot():
    try:
        res = requests.get("https://www.multipasko.pl/widget-wyniki.php?format=json", timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        data = res.json()["g"]["eurojackpot"]
        draw = EurojackpotDraw(
            draw_date=datetime.strptime(data["d"].strip(), "%d.%m.%Y").date(),
            mains=data["l"], euros=data["x"]
        )
        save_ej(draw)
        logger.info("Eurojackpot OK")
    except Exception as e:
        logger.error(f"Errore Fetch Eurojackpot: {e}")

def fetch_superenalotto():
    try:
        res = requests.get("https://www.lottologia.com/superenalotto/estrazioni/", timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "lxml")
        text = soup.get_text(" ", strip=True)
        
        match = re.search(r"Numeri\s+((?:\d{1,2}\s+){5}\d{1,2})", text, re.IGNORECASE)
        if not match:
            logger.warning("Superenalotto: Numeri non trovati.")
            return

        nums = [int(n) for n in match.group(1).split()]
        date_match = re.search(r"(\d{1,2})\s+(Gen|Feb|Mar|Apr|Mag|Giu|Lug|Ago|Set|Ott|Nov|Dic)\s+(\d{4})", text, re.IGNORECASE)
        mesi = {"gen":1, "feb":2, "mar":3, "apr":4, "mag":5, "giu":6, "lug":7, "ago":8, "set":9, "ott":10, "nov":11, "dic":12}
        
        if date_match:
            day = int(date_match.group(1))
            month = mesi[date_match.group(2).lower()]
            year = int(date_match.group(3))
            draw_date = datetime(year, month, day).date()
        else:
            draw_date = datetime.now().date()

        draw = SuperenalottoDraw(draw_date=draw_date, mains=nums)
        save_se(draw)
        logger.info(f"Superenalotto OK: {nums}")
    except Exception as e:
        logger.error(f"Errore Fetch Superenalotto: {e}")

def fetch_vinci():
    try:
        res = requests.get("https://www.agimeg.it/wp-json/wp/v2/posts?categories=1031", timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        posts = res.json()
        
        if not posts:
            logger.warning("SWFL: Nessun post trovato.")
            return
            
        latest = posts[0]
        content = BeautifulSoup(latest["content"]["rendered"], "lxml").get_text(" ", strip=True)
        
        # CERCA TUTTI I NUMERI DA 1 A 90 NEL TESTO
        all_nums = re.findall(r"\b(?:[1-9]|[1-8][0-9]|90)\b", content)
        
        # Filtra per avere solo numeri unici, mantenendo l'ordine
        unique_nums = list(dict.fromkeys([int(n) for n in all_nums]))
        
        # Se troviamo almeno 8 numeri, li salviamo
        if len(unique_nums) >= 8:
            date_str = latest["date"][:10]
            draw_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            draw = VinciDraw(draw_date=draw_date, mains=unique_nums[:8])
            save_vv(draw)
            logger.info(f"SWFL OK: {unique_nums[:8]}")
        else:
            logger.warning("SWFL: Numeri non trovati nel post (trovati meno di 8).")
    except Exception as e:
        logger.error(f"Errore Fetch SWFL: {e}")
