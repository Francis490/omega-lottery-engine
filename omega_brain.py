import random
from datetime import datetime
from collections import Counter

GAMES = {
    "eurojackpot": {"mains": 5, "euros": 2, "cost": 2.0, "max_pool": 50},
    "superenalotto": {"mains": 6, "euros": 0, "cost": 1.0, "max_pool": 90},
    "swfl": {"mains": 6, "euros": 0, "cost": 2.0, "max_pool": 90}
}

def get_decision(game, jackpot):
    return "PLAY_MAX", 0.0 

def generate_ticket(game, recent_draws, seed=42):
    today_seed = int(datetime.now().strftime("%Y%m%d"))
    # Seme unico per gioco per evitare sestine identiche
    rng = random.Random(today_seed + len(game))
    
    is_ej = (game == "eurojackpot")
    max_pool = GAMES[game]["max_pool"]
    num_to_pick = 5 if is_ej else 6
    
    # --- ANALISI MEMORIA ---
    freq = Counter()
    all_numbers_in_history = set()
    
    for d in recent_draws:
        for k, v in d.items():
            if k.startswith("n") and v:
                freq[v] += 1
                all_numbers_in_history.add(v)
                
    # Caldi (più frequenti) e Freddi (non usciti di recente)
    hot_nums = [n for n, count in freq.most_common() if n <= max_pool]
    cold_nums = [n for n in range(1, max_pool + 1) if n not in all_numbers_in_history]
    
    if not hot_nums or not cold_nums:
        pool = list(range(1, max_pool + 1))
        mains = sorted(rng.sample(pool, num_to_pick))
    else:
        picks = []
        
        # 1. Prendi 2 Caldi
        hot_picks = rng.sample(hot_nums[:20], min(2, len(hot_nums)))
        picks.extend(hot_picks)
        
        # 2. Prendi 2 Freddi
        cold_picks = rng.sample(cold_nums, min(2, len(cold_nums)))
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
