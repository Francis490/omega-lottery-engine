import random
from datetime import datetime
from collections import Counter

GAMES = {
    "eurojackpot": {"mains": 5, "euros": 2, "cost": 2.0, "max_pool": 50},
    "superenalotto": {"mains": 6, "euros": 0, "cost": 1.0, "max_pool": 90},
    "swfl": {"mains": 8, "euros": 0, "cost": 2.0, "max_pool": 90} # FIX: SWFL gioca 8 numeri
}

def get_decision(game, jackpot):
    return "PLAY_MAX", 0.0 

def generate_ticket(game, recent_draws, seed=42):
    today_seed = int(datetime.now().strftime("%Y%m%d"))
    rng = random.Random(today_seed + len(game))
    
    is_ej = (game == "eurojackpot")
    max_pool = GAMES[game]["max_pool"]
    
    # FIX: Usa il numero corretto di mains per ogni gioco
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
    
    if not hot_nums or not cold_nums:
        pool = list(range(1, max_pool + 1))
        mains = sorted(rng.sample(pool, num_to_pick))
    else:
        picks = []
        
        # 1. Prendi 2 Caldi (dai top 20)
        hot_picks = rng.sample(hot_nums[:20], min(2, len(hot_nums)))
        picks.extend(hot_picks)
        
        # 2. Prendi 2 Freddi
        cold_candidates = [n for n in cold_nums if n not in picks]
        cold_picks = rng.sample(cold_candidates, min(2, len(cold_candidates)))
        picks.extend(cold_picks)
        
        # 3. Prendi il resto Random
        needed_random = num_to_pick - len(picks)
        pool = list(range(1, max_pool + 1))
        remaining_pool = [n for n in pool if n not in picks]
        
        if len(remaining_pool) >= needed_random:
            random_picks = rng.sample(remaining_pool, needed_random)
            picks.extend(random_picks)
            
        picks = list(dict.fromkeys(picks))
        while len(picks) < num_to_pick:
            remaining = list(set(pool) - set(picks))
            picks.append(rng.choice(remaining))
            
        mains = sorted(picks[:num_to_pick])

    if is_ej:
        euro_pool = list(range(1, 13))
        euros = sorted(rng.sample(euro_pool, 2))
        return mains, euros
    
    return mains, []
