import re
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from models import EurojackpotDraw, SuperenalottoDraw, VinciDraw
from database import save_ej, save_se, save_vv

logger = logging.getLogger(__name__)

MESI = {
    "gen": 1, "gennaio": 1,
    "feb": 2, "febbraio": 2,
    "mar": 3, "marzo": 3,
    "apr": 4, "aprile": 4,
    "mag": 5, "maggio": 5,
    "giu": 6, "giugno": 6,
    "lug": 7, "luglio": 7,
    "ago": 8, "agosto": 8,
    "set": 9, "settembre": 9,
    "ott": 10, "ottobre": 10,
    "nov": 11, "novembre": 11,
    "dic": 12, "dicembre": 12,
}

DATE_MONTH_REGEX = (
    r"(\d{1,2})\s+"
    r"(Gen(?:naio)?|Feb(?:braio)?|Mar(?:zo)?|Apr(?:ile)?|Mag(?:gio)?|"
    r"Giu(?:gno)?|Lug(?:lio)?|Ago(?:sto)?|Set(?:tembre)?|Ott(?:obre)?|"
    r"Nov(?:embre)?|Dic(?:embre)?)"
    r"\s+(\d{4})"
)


def _parse_italian_date(text: str):
    """Estrae la prima data italiana dal testo (rifiuta date future)."""
    m = re.search(DATE_MONTH_REGEX, text, re.IGNORECASE)
    if not m:
        return None
    try:
        day = int(m.group(1))
        month = MESI[m.group(2).lower()]
        year = int(m.group(3))
        candidate = datetime(year, month, day).date()
        today = datetime.now(ZoneInfo("Europe/Rome")).date()
        if candidate > today:
            return None
        return candidate
    except (KeyError, ValueError):
        return None


def fetch_eurojackpot() -> bool:
    try:
        res = requests.get(
            "https://www.multipasko.pl/widget-wyniki.php?format=json",
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        res.raise_for_status()
        data = res.json()["g"]["eurojackpot"]
        draw = EurojackpotDraw(
            draw_date=datetime.strptime(data["d"].strip(), "%d.%m.%Y").date(),
            mains=[int(n) for n in data["l"]],
            euros=[int(n) for n in data["x"]],
        )
        save_ej(draw)
        logger.info(f"Eurojackpot OK: {draw.mains} | {draw.euros} ({draw.draw_date})")
        return True
    except Exception as e:
        logger.error(f"Errore Fetch Eurojackpot: {e}")
        return False


def fetch_superenalotto() -> bool:
    try:
        res = requests.get(
            "https://www.lottologia.com/superenalotto/estrazioni/",
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "lxml")
        text = soup.get_text(" ", strip=True)

        match = re.search(
            r"Numeri[:\s]+((?:\d{1,2}[\s,]+){5}\d{1,2})",
            text,
            re.IGNORECASE,
        )
        if not match:
            logger.warning("Superenalotto: Numeri non trovati.")
            return False

        nums = [int(n) for n in re.split(r"[\s,]+", match.group(1).strip())]
        if len(set(nums)) != 6 or any(not (1 <= n <= 90) for n in nums):
            logger.warning(f"Superenalotto: numeri non validi: {nums}")
            return False

        draw_date = _parse_italian_date(text)
        if not draw_date:
            logger.warning("Superenalotto: data non trovata, salto il salvataggio.")
            return False

        jolly = None
        superstar = None
        jolly_match = re.search(r"[Jj]olly[:\s]+(\d{1,2})", text)
        if jolly_match:
            val = int(jolly_match.group(1))
            if 1 <= val <= 90:
                jolly = val
        superstar_match = re.search(r"[Ss]uperstar[:\s]+(\d{1,2})", text)
        if superstar_match:
            val = int(superstar_match.group(1))
            if 1 <= val <= 90:
                superstar = val

        draw = SuperenalottoDraw(
            draw_date=draw_date,
            mains=nums,
            jolly=jolly,
            superstar=superstar,
        )
        save_se(draw)
        logger.info(
            f"Superenalotto OK: {nums} | J={jolly} SS={superstar} ({draw_date})"
        )
        return True
    except Exception as e:
        logger.error(f"Errore Fetch Superenalotto: {e}")
        return False


def fetch_vinci() -> bool:
    # Usiamo Lottologia, ma cerchiamo la tabella HTML invece del testo
    try:
        res = requests.get(
            "https://www.lottologia.com/super-win-for-life/estrazioni/",
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "lxml")
        
        # Trova la tabella che contiene "Data" o "Concorso"
        table = None
        for t in soup.find_all("table"):
            if "Data" in t.get_text() or "Concorso" in t.get_text():
                table = t
                break
                
        if not table:
            logger.warning("SWFL: Tabella non trovata su Lottologia.")
            return False
            
        rows = table.find_all("tr")
        if len(rows) < 2:
            logger.warning("SWFL: Righe insufficienti nella tabella.")
            return False
            
        # La riga 1 (dopo l'header) è l'estrazione più recente
        row_text = rows[1].get_text(" ", strip=True)
        
        # Estrai la data (cerca un formato dd/mm/yyyy)
        date_match = re.search(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", row_text)
        if not date_match:
            logger.warning("SWFL: Data non trovata nella riga.")
            return False
            
        d, m, y = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
        draw_date = datetime(y, m, d).date()
        
        # Estrai gli 8 numeri validi (da 1 a 90)
        all_nums = [int(n) for n in re.findall(r"\b\d{1,2}\b", row_text)]
        valid_nums = []
        for n in all_nums:
            if 1 <= n <= 90 and n not in valid_nums:
                valid_nums.append(n)
                
        if len(valid_nums) < 8:
            logger.warning(f"SWFL: trovati solo {len(valid_nums)} numeri validi: {valid_nums}")
            return False
            
        nums = valid_nums[:8]
        
        draw = VinciDraw(draw_date=draw_date, mains=nums)
        save_vv(draw)
        logger.info(f"SWFL OK: {nums} ({draw_date})")
        return True
    except Exception as e:
        logger.error(f"Errore Fetch SWFL: {e}")
        return False
