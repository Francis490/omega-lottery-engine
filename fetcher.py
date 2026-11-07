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
    """
    Fetch SWFL da Agimeg (brute-force robusto).

    Regole di sicurezza:
    - La data viene estratta PRIMA di rimuovere date/anni/orari dal testo,
      altrimenti i numeri della data finiscono tra gli "estratti".
    - Cerchiamo solo sequenze consecutive di 8 numeri unici 1-90.
    - Se non troviamo una sequenza valida, NON salviamo: meglio nessun dato
      che un dato sbagliato (con INSERT OR REPLACE il record verrà corretto
      al prossimo fetch riuscito).
    """
    try:
        res = requests.get(
            "https://www.agimeg.it/wp-json/wp/v2/posts?categories=1031",
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        res.raise_for_status()
        posts = res.json()

        if not posts:
            logger.warning("SWFL: Nessun post trovato.")
            return False

        latest = posts[0]
        content = BeautifulSoup(
            latest["content"]["rendered"], "lxml"
        ).get_text(" ", strip=True)

        # 1) Data PRIMA del cleanup
        draw_date = _parse_italian_date(content)
        if not draw_date:
            try:
                draw_date = datetime.strptime(
                    latest["date"][:10], "%Y-%m-%d"
                ).date()
            except (KeyError, ValueError):
                logger.warning("SWFL: data non determinabile.")
                return False

        # 2) Cleanup: rimuovi date, anni, orari
        cleaned = content
        cleaned = re.sub(DATE_MONTH_REGEX, " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b\d{4}\b", " ", cleaned)  # anni
        cleaned = re.sub(
            r"\b\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}\b", " ", cleaned
        )  # date numeriche
        cleaned = re.sub(r"\b\d{1,2}[:.]\d{2}\b", " ", cleaned)  # orari

        # 3) Cerca SOLO sequenze consecutive di 8 numeri
        seq_pattern = re.compile(
            r"(?:\b\d{1,2}\b[\s,;|/\-]+){7}\b\d{1,2}\b"
        )

        for seq_text in seq_pattern.findall(cleaned):
            nums = [int(n) for n in re.findall(r"\b\d{1,2}\b", seq_text)]
            if (
                len(nums) == 8
                and len(set(nums)) == 8
                and all(1 <= n <= 90 for n in nums)
            ):
                draw = VinciDraw(draw_date=draw_date, mains=nums)
                save_vv(draw)
                logger.info(f"SWFL OK: {nums} ({draw_date})")
                return True

        logger.warning("SWFL: nessuna sequenza valida di 8 numeri unici 1-90.")
        return False
    except Exception as e:
        logger.error(f"Errore Fetch SWFL: {e}")
        return False
