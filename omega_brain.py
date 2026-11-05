import random
from datetime import datetime
from collections import Counter

GAMES = {
    "eurojackpot": {"mains": 5, "euros": 2, "cost": 2.0, "max_pool": 50},
    "superenalotto": {"mains": 6, "euros": 0, "cost": 1.0, "max_pool": 90},
    "swfl": {"mains": 6, "euros": 0, "cost": 2.0, "max_pool": 90},
}

def get_decision(game, jackpot):
    return "PLAY_MAX", 0.0

def generate_ticket(game, recent_draws, seed=None):
    if seed is not None:
        rng = random.Random(seed)
    else:
        today_seed = int(datetime.now().strftime("%Y%m%d"))
        rng = random.Random(today_seed + len(game))

    is_ej = (game == "eurojackpot")
    max_pool = GAMES[game]["max_pool"]
    num_to_pick = GAMES[game]["mains"]

    # --- ANALISI MEMORIA (CALDO/FREDDO) ---
    freq = Counter()
    last_seen = {}
    for i, d in enumerate(recent_draws):
        for k, v in d.items():
            if k.startswith("n") and v:
                freq[v] += 1
                if v not in last_seen:
                    last_seen[v] = i

    hot_nums = [n for n, count in freq.most_common() if n <= max_pool]
    all_nums = list(range(1, max_pool + 1))
    cold_nums = sorted(all_nums, key=lambda n: last_seen.get(n, len(recent_draws)), reverse=True)

    # --- GENERAZIONE CON FILTRI DI VALIDAZIONE (IL MIRINO) ---
    best_mains = []
    attempts = 0
    max_attempts = 20000

    while attempts < max_attempts:
        attempts += 1
        picks = []

        if not hot_nums or not cold_nums:
            mains = sorted(rng.sample(all_nums, num_to_pick))
        else:
            # 1. Prendi 2 Caldi
            hot_picks = rng.sample(hot_nums[:20], min(2, len(hot_nums)))
            picks.extend(hot_picks)

            # 2. Prendi 2 Freddi
            cold_candidates = [n for n in cold_nums if n not in picks]
            cold_picks = rng.sample(cold_candidates, min(2, len(cold_candidates)))
            picks.extend(cold_picks)

            # 3. Prendi il resto Random
            needed_random = num_to_pick - len(picks)
            remaining_pool = [n for n in all_nums if n not in picks]
            if len(remaining_pool) >= needed_random:
                picks.extend(rng.sample(remaining_pool, needed_random))

            picks = list(dict.fromkeys(picks))
            while len(picks) < num_to_pick:
                remaining = list(set(all_nums) - set(picks))
                picks.append(rng.choice(remaining))

            mains = sorted(picks[:num_to_pick])

        # --- APPLICAZIONE DEI FILTRI TATTICI ---
        
        # Filtro 1: Somma
        total_sum = sum(mains)
        if is_ej:
            if not (90 <= total_sum <= 170): continue
        else:
            if not (200 <= total_sum <= 350): continue

        # Filtro 2: Parità (Massimo 4 pari o 4 dispari)
        evens = sum(1 for n in mains if n % 2 == 0)
        if evens < 2 or evens > 4: continue

        # Filtro 3: Decine (Almeno 3 decine diverse)
        decades = set()
        for n in mains:
            if n <= 9: decades.add(1)
            elif n <= 19: decades.add(2)
            elif n <= 29: decades.add(3)
            elif n <= 39: decades.add(4)
            elif n <= 49: decades.add(5)
            elif n <= 59: decades.add(6)
            elif n <= 69: decades.add(7)
            elif n <= 79: decades.add(8)
            else: decades.add(9)
        if len(decades) < 3: continue

        # Filtro 4: Consecutivi (Max 1 coppia consecutiva)
        consec_count = 0
        for i in range(len(mains) - 1):
            if mains[i+1] - mains[i] == 1:
                consec_count += 1
        if consec_count > 1: continue

        # Filtro 5: Unità (Max 2 numeri con la stessa cifra finale)
        last_digits = [n % 10 for n in mains]
        digit_counts = Counter(last_digits)
        if any(count > 2 for count in digit_counts.values()): continue

        # Filtro 6: Ampiezza (Spread)
        spread = mains[-1] - mains[0]
        if is_ej:
            if spread < 25: continue
        else:
            if spread < 40: continue

        # Se supera TUTTI i filtri, è la nostra sestina perfetta
        best_mains = mains
        break

    if not best_mains:
        best_mains = mains # Fallback di sicurezza

    # --- EURONUMERI (Solo Eurojackpot) ---
    if is_ej:
        euro_freq = Counter()
        euro_last_seen = {}
        for i, d in enumerate(recent_draws):
            if d.get("e1"):
                euro_freq[d["e1"]] += 1
                if d["e1"] not in euro_last_seen: euro_last_seen[d["e1"]] = i
            if d.get("e2"):
                euro_freq[d["e2"]] += 1
                if d["e2"] not in euro_last_seen: euro_last_seen[d["e2"]] = i

        euro_hot = [n for n, count in euro_freq.most_common() if n <= 12]
        euro_cold = sorted(list(range(1, 13)), key=lambda n: euro_last_seen.get(n, len(recent_draws)), reverse=True)

        if euro_hot and euro_cold:
            e_hot_pick = rng.choice(euro_hot[:5])
            cold_candidates = [n for n in euro_cold if n != e_hot_pick]
            e_cold_pick = rng.choice(cold_candidates[:5])
            euros = sorted([e_hot_pick, e_cold_pick])
        else:
            euros = sorted(rng.sample(list(range(1, 13)), 2))
            
        return best_mains, euros

    return best_mains, []
