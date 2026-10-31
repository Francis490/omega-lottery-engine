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
        text = soup.get_text(" ", strip=True)
        
        # 1. Estrazione dei 6 numeri
        match = re.search(r"Numeri\s+((?:\d{1,2}\s+){5}\d{1,2})", text, re.IGNORECASE)
        if not match:
            logger.warning("Superenalotto: Numeri non trovati nel testo.")
            return

        nums = [int(n) for n in match.group(1).split()]
        
        # 2. Estrazione della data (es. "3 Ott 2026")
        date_match = re.search(r"(\d{1,2})\s+(Gen|Feb|Mar|Apr|Mag|Giu|Lug|Ago|Set|Ott|Nov|Dic)\s+(\d{4})", text, re.IGNORECASE)
        mesi = {"gen":1, "feb":2, "mar":3, "apr":4, "mag":5, "giu":6, "lug":7, "ago":8, "set":9, "ott":10, "nov":11, "dic":12}
        
        if date_match:
            day = int(date_match.group(1))
            month = mesi[date_match.group(2).lower()]
            year = int(date_match.group(3))
            draw_date = datetime(year, month, day).date()
        else:
            draw_date = datetime.now().date() # Fallback

        draw = SuperenalottoDraw(draw_date=draw_date, mains=nums)
        save_se(draw)
        logger.info(f"Superenalotto OK: {nums}")
        
    except Exception as e:
        logger.error(f"Errore Fetch Superenalotto: {e}")

def fetch_vinci():
    try:
        # Fonte AGIMEG (WordPress REST API)
        res = requests.get("https://www.agimeg.it/wp-json/wp/v2/posts?categories=1031", 
                           timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        posts = res.json()
        
        if not posts:
            logger.warning("Vinci Vita: Nessun post trovato.")
            return
            
        latest = posts[0]
        content = BeautifulSoup(latest["content"]["rendered"], "lxml").get_text(" ", strip=True)
        
        # 1. Estrazione degli 8 numeri
        match = re.search(r"((?:\b\d{1,2}\b[\s,·]+){7}\b\d{1,2}\b)", content)
        if match:
            nums = [int(n) for n in re.findall(r"\b(\d{1,2})\b", match.group(1))]
            nums = [n for n in nums if 1 <= n <= 90]
            unique_nums = list(dict.fromkeys(nums)) # Rimuove doppioni
            
            if len(unique_nums) >= 8:
                date_str = latest["date"][:10] # YYYY-MM-DD
                draw_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                draw = VinciDraw(draw_date=draw_date, mains=unique_nums[:8])
                save_vv(draw)
                logger.info(f"Vinci Vita OK: {unique_nums[:8]}")
                return
                
        logger.warning("Vinci Vita: Numeri non trovati nel post.")
    except Exception as e:
        logger.error(f"Errore Fetch Vinci Vita: {e}")
