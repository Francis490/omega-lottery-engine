import re
import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DEFAULT_JACKPOTS = {
    "eurojackpot": 30_000_000,
    "superenalotto": 40_000_000,
    "swfl": 960_000,
}


def _parse_money(s):
    """
    Converte una stringa monetaria in intero euro.
    Supporta: "30.000.000", "30.000.000,00", "30000000", "30,000,000.00".
    """
    s = str(s).strip()
    if not s:
        return 0
    if re.search(r",\d{1,2}$", s):
        s = re.sub(r",\d{1,2}$", "", s)
        s = s.replace(".", "").replace(",", "")
    else:
        s = re.sub(r"[^\d]", "", s)
    return int(s) if s else 0


def fetch_eurojackpot_jackpot():
    try:
        res = requests.get(
            "https://www.multipasko.pl/widget-wyniki.php?format=json",
            timeout=15,
        )
        data = res.json()
        jackpot_str = data.get("g", {}).get("eurojackpot", {}).get("j")
        if jackpot_str:
            jackpot = _parse_money(jackpot_str)
            if jackpot > 0:
                logger.info(f"Eurojackpot Jackpot: {jackpot} €")
                return jackpot
    except Exception as e:
        logger.warning(f"Eurojackpot jackpot non disponibile: {e}")
    return None


def fetch_superenalotto_jackpot():
    try:
        res = requests.get(
            "https://www.lottologia.com/superenalotto/estrazioni/",
            timeout=15,
        )
        soup = BeautifulSoup(res.text, "lxml")
        text = soup.get_text(" ", strip=True)
        match = re.search(r"montepremi[:\s]*([\d\.,]+)", text, re.IGNORECASE)
        if match:
            jackpot = _parse_money(match.group(1))
            if jackpot > 0:
                logger.info(f"Superenalotto Jackpot: {jackpot} €")
                return jackpot
    except Exception as e:
        logger.warning(f"Superenalotto jackpot non disponibile: {e}")
    return None


def fetch_vinci_jackpot():
    try:
        res = requests.get(
            "https://www.agimeg.it/wp-json/wp/v2/posts?categories=1031",
            timeout=15,
        )
        posts = res.json()
        if posts:
            latest = posts[0]
            content = BeautifulSoup(
                latest["content"]["rendered"], "lxml"
            ).get_text(" ", strip=True)
            match = re.search(
                r"([\d\.,]+)\s*(?:euro|€)\s*(?:al mese|mensili)",
                content,
                re.IGNORECASE,
            )
            if match:
                rendita_mensile = _parse_money(match.group(1))
                if rendita_mensile > 0:
                    jackpot_stimato = rendita_mensile * 12 * 20
                    logger.info(
                        f"SWFL rendita {rendita_mensile} €/mese "
                        f"-> valore stimato {jackpot_stimato} €"
                    )
                    return jackpot_stimato
    except Exception as e:
        logger.warning(f"SWFL jackpot non disponibile: {e}")
    return None


def get_all_jackpots():
    logger.info("Recupero jackpot aggiornati...")
    jackpots = {
        "eurojackpot": fetch_eurojackpot_jackpot() or DEFAULT_JACKPOTS["eurojackpot"],
        "superenalotto": fetch_superenalotto_jackpot() or DEFAULT_JACKPOTS["superenalotto"],
        "swfl": fetch_vinci_jackpot() or DEFAULT_JACKPOTS["swfl"],
    }
    logger.info(f"Jackpot in uso: {jackpots}")
    return jackpots
