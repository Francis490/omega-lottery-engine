import random
import math
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter

GAMES = {
    "eurojackpot": {"mains": 5, "euros": 2, "cost": 2.0, "max_pool": 50},
    "superenalotto": {"mains": 6, "euros": 0, "cost": 1.0, "max_pool": 90},
    "swfl": {"mains": 6, "euros": 0, "cost": 2.0, "max_pool": 90},
}

C_90_6 = 622_614_630

JACKPOT_PROBABILITY = {
    "eurojackpot": 1 / 139_838_160,
    "superenalotto": 1 / C_90_6,
    "swfl": 28 / C_90_6,
}

LOWER_TIER_RETURN = {
    "eurojackpot": 0.35,
    "superenalotto": 0.50,
    "swfl": 0.55,
}

ENABLE_SKIP = False
SKIP_THRESHOLD = 0.60


def get_decision(game, jackpot):
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


def _find_broken_numbers(recent_draws, max_pool, top_n=3):
    """
    Hacker Mode: Trova i numeri statisticamente più 'rotti' (Z-Score alto).
    Questi sono i numeri che la fisica o il server stanno spingendo fuori dalla norma.
    """
    freq = Counter()
    total_extracted = 0

    for d in recent_draws:
        for k, v in d.items():
            if k.startswith("n") and v:
                freq[v] += 1
                total_extracted += 1

    if total_extracted == 0:
        return []

    expected = total_extracted / max_pool
    std_dev = math.sqrt(expected * (1 - (1 / max_pool)))

    z_scores = {}
    for n in range(1, max_pool + 1):
        uscite = freq.get(n, 0)
        z = (uscite - expected) / std_dev if std_dev > 0 else 0
        z_scores[n] = z

    sorted_anomalies = sorted(z_scores.items(), key=lambda x: abs(x[1]), reverse=True)
    broken = [num for num, z in sorted_anomalies if abs(z) > 2.0][:top_n]
    return broken


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

    if len(set(n // 10 for n in mains)) < 3: return False

    consec_count = 0
    for i in range(len(mains) - 1):
        if mains[i + 1] - mains[i] == 1:
            consec_count += 1
    if consec_count > 1: return False

    if any(c > 2 for c in Counter(n % 10 for n in mains).values()): return False

    spread = mains[-1] - mains[0]
    if is_ej and spread < 25: return False
    if not is_ej and spread < 40: return False

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
    all_nums = list(range(1, max_pool + 1))

    # 1. Hacker Mode
    broken_nums = _find_broken_numbers(recent_draws, max_pool, top_n=3)

    # 2. Decisioni UNA VOLTA FUORI dal loop (fix B4)
    chaos_mode = rng.random() < 0.20
    use_broken = bool(broken_nums) and (chaos_mode or rng.random() < 0.5)

    # 3. Statistiche precalcolate FUORI dal loop (fix perf)
    freq = Counter()
    last_seen = {}
    for i, d in enumerate(recent_draws):
        for k, v in d.items():
            if k.startswith("n") and v:
                freq[v] += 1
                if v not in last_seen:
                    last_seen[v] = i

    hot_nums = [n for n, _ in freq.most_common()]
    cold_nums = sorted(
        all_nums,
        key=lambda n: last_seen.get(n, len(recent_draws)),
        reverse=True,
    )

    # 4. Generazione
    best_mains = None
    fallback_mains = None

    if use_broken:
        # Gioca i numeri rotti ignorando i filtri
        picks = list(broken_nums)
        while len(picks) < num_to_pick:
            n = rng.choice(all_nums)
            if n not in picks:
                picks.append(n)
        best_mains = sorted(picks[:num_to_pick])
    else:
        attempts = 0
        max_attempts = 50000
        while attempts < max_attempts:
            attempts += 1
            picks = []
            if hot_nums and cold_nums:
                picks.extend(rng.sample(hot_nums[:10], min(2, len(hot_nums))))
                cold_candidates = [n for n in cold_nums if n not in picks]
                picks.extend(rng.sample(cold_candidates, min(2, len(cold_candidates))))
            while len(picks) < num_to_pick:
                n = rng.choice(all_nums)
                if n not in picks:
                    picks.append(n)
            mains = sorted(picks[:num_to_pick])
            if fallback_mains is None:
                fallback_mains = mains
            if _passes_filters(mains, is_ej, num_to_pick):
                best_mains = mains
                break
        if best_mains is None:
            best_mains = fallback_mains or sorted(rng.sample(all_nums, num_to_pick))

    # Gestione Euronumeri (invariato)
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
