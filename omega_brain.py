import random
from datetime import datetime

GAMES = {
    "eurojackpot": {"mains": 5, "euros": 2, "cost": 2.0, "max_pool": 50},
    "superenalotto": {"mains": 6, "euros": 0, "cost": 1.0, "max_pool": 90},
    "swfl": {"mains": 6, "euros": 0, "cost": 2.0, "max_pool": 90} # Nome cambiato in swfl
}

def get_decision(game, jackpot):
    # Colpo secco: giochiamo sempre
    return "PLAY_MAX", 0.0 

def generate_ticket(game, recent_draws, seed=42):
    today_seed = int(datetime.now().strftime("%Y%m%d"))
    random.seed(today_seed) 
    
    is_ej = (game == "eurojackpot")
    max_pool = GAMES[game]["max_pool"]
    num_to_pick = 5 if is_ej else 6
    
    recent_nums = set()
    for d in recent_draws:
        for k, v in d.items():
            if k.startswith("n") and v: 
                recent_nums.add(v)
                
    cold_pool = [n for n in range(1, max_pool + 1) if n not in recent_nums]
    hot_pool = list(recent_nums)
    
    if len(cold_pool) < 3:
        cold_pool = list(range(1, max_pool + 1))
        
    cold_picks = random.sample(cold_pool, 3)
    hot_pool = [n for n in hot_pool if n not in cold_picks]
    if len(hot_pool) < (num_to_pick - 3):
        hot_pool = [n for n in range(1, max_pool + 1) if n not in cold_picks]
        
    hot_picks = random.sample(hot_pool, num_to_pick - 3)
    mains = sorted(cold_picks + hot_picks)
    
    if is_ej:
        euro_pool = list(range(2, 12))
        euros = sorted(random.sample(euro_pool, 2))
        return mains, euros
    
    return mains, []
