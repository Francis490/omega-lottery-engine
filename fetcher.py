import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import logging
from models import EurojackpotDraw, SuperenalottoDraw, VinciDraw
from database import save_ej, save_se, save_vv

logger = logging.getLogger(__name__)

MESI = {"gen": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "giu": 6,
        "lug": 7, "ago": 8, "set": 9, "ott": 10, "nov": 11, "dic": 12}


def fetch_eurojackpot():
    try:
        res = requests.get(
            "https://www.multipasko.pl/widget-wyniki.php?format=json",
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        data = res.json()["g"]["eurojackpot"]
        draw = EurojackpotDraw(
            draw_date=datetime.strptime(data["d"].strip(), "%d.%m.%Y").date(),
            mains=data["l"],
            euros=data["x"],
        )
        save_ej(draw)
        logger.info("Eurojackpot OK")
    except Exception as e:
        logger.error(f"Errore Fetch Eurojackpot: {e}")


def fetch_superenalotto():
    try:
        res = requests.get(
            "https://www.lottologia.com/superenalotto/estrazioni/",
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        soup = BeautifulSoup(res.text, "lxml")
        text = soup.get_text(" ", strip=True)

        match = re.search(r"Numeri\s+((?:\d{1,2}\s+){5}\d{1,2})", text, re.IGNORECASE)
        if not match:
            logger.warning("Superenalotto: Numeri non trovati.")
            return

        nums = [int(n) for n in match.group(1).split()]
        if len(set(nums)) != 6 or any(not (1 <= n <= 90) for n in nums):
            logger.warning(f"Superenalotto: numeri non validi: {nums}")
            return

        date_match = re.search(
            r"(\d{1,2})\s+(Gen|Feb|Mar|Apr|Mag|Giu|Lug|Ago|Set|Ott|Nov|Dic)\s+(\d{4})",
            text,
            re.IGNORECASE,
        )
        if not date_match:
            logger.warning("Superenalotto: data non trovata, salto il salvataggio.")
            return

        day = int(date_match.group(1))
        month = MESI[date_match.group(2).lower()]
        year = int(date_match.group(3))
        draw_date = datetime(year, month, day).date()

        draw = SuperenalottoDraw(draw_date=draw_date, mains=nums)
        save_se(draw)
        logger.info(f"Superenalotto OK: {nums} ({draw_date})")
    except Exception as e:
        logger.error(f"Errore Fetch Superenalotto: {e}")


def fetch_vinci():
    try:
        res = requests.get(
            "https://www.agimeg.it/wp-json/wp/v2/posts?categories=1031",
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        posts = res.json()

        if not posts:
            logger.warning("SWFL: Nessun post trovato.")
            return

        latest = posts[0]
        content = BeautifulSoup(latest["content"]["rendered"], "lxml").get_text(" ", strip=True)

        # Pattern ancorato: cerca "combinazione/numeri vincenti/estratti" seguiti da 8 numeri.
        match = re.search(
            r"(?:combinazione|numeri)\s*(?:vincent[ei]|estratti)[:\s]*"
            r"((?:\d{1,2}[\s,]+){7}\d{1,2})",
            content,
            re.IGNORECASE,
        )
        if not match:
            logger.warning("SWFL: combinazione vincente non trovata nel post.")
            return

        nums = [int(n) for n in re.split(r"[\s,]+", match.group(1).strip())]
        if (len(nums) != 8 or len(set(nums)) != 8
                or any(not (1 <= n <= 90) for n in nums)):
            logger.warning(f"SWFL: numeri non validi: {nums}")
            return

        date_str = latest["date"][:10]
        draw_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        draw = VinciDraw(draw_date=draw_date, mains=nums)
        save_vv(draw)
        logger.info(f"SWFL OK: {nums} ({draw_date})")
    except Exception as e:
        logger.error(f"Errore Fetch SWFL: {e}")
