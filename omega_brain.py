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

    # --- ANALISI MEMORIA (MAINS) ---
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

    if not hot_nums or not cold_nums:
        mains = sorted(rng.sample(all_nums, num_to_pick))
    else:
        picks = []
        hot_picks = rng.sample(hot_nums[:20], min(2, len(hot_nums)))
        picks.extend(hot_picks)
        
        cold_candidates = [n for n in cold_nums if n not in picks]
        cold_picks = rng.sample(cold_candidates, min(2, len(cold_candidates)))
        picks.extend(cold_picks)
        
        needed_random = num_to_pick - len(picks)
        remaining_pool = [n for n in all_nums if n not in picks]
        if len(remaining_pool) >= needed_random:
            picks.extend(rng.sample(remaining_pool, needed_random))
        
        picks = list(dict.fromkeys(picks))
        while len(picks) < num_to_pick:
            remaining = list(set(all_nums) - set(picks))
            picks.append(rng.choice(remaining))
        
        mains = sorted(picks[:num_to_pick])

    # --- EURONUMERI (Solo per Eurojackpot) ---
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
        all_euros = list(range(1, 13))
        euro_cold = sorted(all_euros, key=lambda n: euro_last_seen.get(n, len(recent_draws)), reverse=True)

        # 1 Caldo + 1 Freddo per gli Euronumeri
        if euro_hot and euro_cold:
            e_hot_pick = rng.choice(euro_hot[:5]) # Scegli tra i top 5 caldi
            cold_candidates = [n for n in euro_cold if n != e_hot_pick]
            e_cold_pick = rng.choice(cold_candidates[:5]) # Scegli tra i top 5 freddi
            euros = sorted([e_hot_pick, e_cold_pick])
        else:
            euros = sorted(rng.sample(all_euros, 2))
            
        return mains, euros

    return mains, []
