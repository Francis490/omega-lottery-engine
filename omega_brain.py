import random
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter

GAMES = {
    "eurojackpot": {"mains": 5, "euros": 2, "cost": 2.0, "max_pool": 50},
    "superenalotto": {"mains": 6, "euros": 0, "cost": 1.0, "max_pool": 90},
    # SWFL: 8 numeri estratti, il giocatore ne sceglie 6 (Sisal).
    "swfl": {"mains": 6, "euros": 0, "cost": 2.0, "max_pool": 90},
}

C_90_6 = 622_614_630  # C(90, 6)

JACKPOT_PROBABILITY = {
    "eurojackpot": 1 / 139_838_160,  # C(50,5) * C(12,2)
    "superenalotto": 1 / C_90_6,
    "swfl": 28 / C_90_6,             # C(8,6) / C(90,6)
}

# Ritorno atteso dei premi minori (frazione del costo biglietto).
# Calibrati sui payout ufficiali dichiarati dai gestori:
#   - Eurojackpot: payout totale ~50% delle giocate, jackpot ~15% -> minori ~35%
#   - Superenalotto: payout totale ~60%, jackpot ~10% -> minori ~50%
#   - SWFL: payout totale ~65%, jackpot (rendita) ~10% -> minori ~55%
# Per ricalibrare EJ sui dati storici reali, esegui `python calibrate_ev.py`.
LOWER_TIER_RETURN = {
    "eurojackpot": 0.35,
    "superenalotto": 0.50,
    "swfl": 0.55,
}

# SKIP è disabilitato di default: il bot genera sempre le sestine nei giorni
# di estrazione. Metti ENABLE_SKIP=True se vuoi che salti le giocate con
# EV/costo < SKIP_THRESHOLD (es. quando il jackpot è basso e non compensa).
ENABLE_SKIP = False
SKIP_THRESHOLD = 0.60


def get_decision(game, jackpot):
    """
    Restituisce (decisione, EV in euro per biglietto).
    decisione ∈ {"PLAY_MAX", "SKIP"}
    """
    config = GAMES.get(game)
    if config is None:
        return "SKIP", 0.0

    cost = config["cost"]
    p_jackpot = JACKPOT_PROBABILITY[game]
    lower_return = LOWER_TIER_RETURN[game] * cost
    jackpot_ev = jackpot * p_jackpot
    ev_total = jackpot_ev + lower_return
    ev_ratio = ev_total / cost if cost else 0.0

    if ENABLE_SKIP and ev_ratio < SKIP_THRESHOLD:
        return "SKIP", ev_total
    return "PLAY_MAX", ev_total


def _decade(n):
    if n <= 9: return 1
    if n <= 19: return 2
    if n <= 29: return 3
    if n <= 39: return 4
    if n <= 49: return 5
    if n <= 59: return 6
    if n <= 69: return 7
    if n <= 79: return 8
    return 9


def _passes_filters(mains, is_ej, num_to_pick):
    total_sum = sum(mains)
    if is_ej:
        if not (90 <= total_sum <= 170): return False
    else:
        if not (200 <= total_sum <= 350): return False

    evens = sum(1 for n in mains if n % 2 == 0)
    if num_to_pick == 5:
        if evens < 2 or evens > 3: return False
    else:
        if evens < 2 or evens > 4: return False

    decades = {_decade(n) for n in mains}
    if len(decades) < 3: return False

    consec_count = 0
    for i in range(len(mains) - 1):
        if mains[i + 1] - mains[i] == 1:
            consec_count += 1
    if consec_count > 1: return False

    last_digits = Counter(n % 10 for n in mains)
    if any(c > 2 for c in last_digits.values()): return False

    spread = mains[-1] - mains[0]
    if is_ej:
        if spread < 25: return False
    else:
        if spread < 40: return False

    return True


def generate_ticket(game, recent_draws, seed=None):
    if seed is not None:
        rng = random.Random(seed)
    else:
        now_rome = datetime.now(ZoneInfo("Europe/Rome"))
        today_seed = int(now_rome.strftime("%Y%m%d"))
        rng = random.Random(today_seed + len(game))

    is_ej = game == "eurojackpot"
    max_pool = GAMES[game]["max_pool"]
    num_to_pick = GAMES[game]["mains"]

    freq = Counter()
    last_seen = {}
    for i, d in enumerate(recent_draws):
        for k, v in d.items():
            if k.startswith("n") and v:
                freq[v] += 1
                if v not in last_seen:
                    last_seen[v] = i

    hot_nums = [n for n, _ in freq.most_common() if n <= max_pool]
    all_nums = list(range(1, max_pool + 1))
    cold_nums = sorted(
        all_nums,
        key=lambda n: last_seen.get(n, len(recent_draws)),
        reverse=True,
    )

    best_mains = None
    fallback_mains = None
    attempts = 0
    max_attempts = 40000

    while attempts < max_attempts:
        attempts += 1
        picks = []

        if not hot_nums or not cold_nums:
            mains = sorted(rng.sample(all_nums, num_to_pick))
        else:
            hot_picks = rng.sample(hot_nums[:20], min(2, len(hot_nums)))
            picks.extend(hot_picks)

            cold_candidates = [n for n in cold_nums if n not in picks]
            cold_picks = rng.sample(
                cold_candidates, min(2, len(cold_candidates))
            )
            picks.extend(cold_picks)

            needed_random = num_to_pick - len(picks)
            remaining_pool = [n for n in all_nums if n not in picks]
            if needed_random > 0 and len(remaining_pool) >= needed_random:
                picks.extend(rng.sample(remaining_pool, needed_random))

            picks = list(dict.fromkeys(picks))
            while len(picks) < num_to_pick:
                remaining = list(set(all_nums) - set(picks))
                picks.append(rng.choice(remaining))

            mains = sorted(picks[:num_to_pick])

        if fallback_mains is None:
            fallback_mains = mains

        if _passes_filters(mains, is_ej, num_to_pick):
            best_mains = mains
            break

    if best_mains is None:
        best_mains = fallback_mains or sorted(rng.sample(all_nums, num_to_pick))

    if is_ej:
        euro_freq = Counter()
        euro_last_seen = {}
        for i, d in enumerate(recent_draws):
            if d.get("e1"):
                euro_freq[d["e1"]] += 1
                if d["e1"] not in euro_last_seen:
                    euro_last_seen[d["e1"]] = i
            if d.get("e2"):
                euro_freq[d["e2"]] += 1
                if d["e2"] not in euro_last_seen:
                    euro_last_seen[d["e2"]] = i

        euro_hot = [n for n, _ in euro_freq.most_common() if n <= 12]
        euro_cold = sorted(
            list(range(1, 13)),
            key=lambda n: euro_last_seen.get(n, len(recent_draws)),
            reverse=True,
        )

        if euro_hot and euro_cold:
            e_hot_pick = rng.choice(euro_hot[:5])
            cold_candidates = [n for n in euro_cold if n != e_hot_pick]
            e_cold_pick = rng.choice(cold_candidates[:5])
            euros = sorted([e_hot_pick, e_cold_pick])
        else:
            euros = sorted(rng.sample(list(range(1, 13)), 2))

        return best_mains, euros

    return best_mains, []
