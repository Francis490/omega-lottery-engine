import random

GAMES = {
    "eurojackpot": {"mains": 5, "euros": 2, "cost": 2.0, "prob": 1/139838160, "max_pool": 50},
    "superenalotto": {"mains": 6, "euros": 0, "cost": 1.0, "prob": 1/622614630, "max_pool": 90},
    "vinci_vita": {"mains": 6, "euros": 0, "cost": 2.0, "prob": 1/622614630, "max_pool": 90}
}

def calculate_ev(game, jackpot):
    prob = GAMES[game]["prob"]
    cost = GAMES[game]["cost"]
    # Stima dei giocatori (più il jackpot è alto, più gente gioca)
    players = 50_000_000 if jackpot > 40_000_000 else 10_000_000
    expected_winners = max(1.0, players * prob)
    
    # EV del jackpot diviso per i possibili vincitori
    ev_jackpot = prob * (jackpot / expected_winners)
    
    # Stima dei premi minori (approssimativa)
    ev_other = 0.35 
    
    return round(ev_jackpot + ev_other - cost, 4)

def get_decision(game, jackpot):
    """Questa è la funzione che mancava!"""
    ev = calculate_ev(game, jackpot)
    if ev < -0.7:
        return "SKIP", ev
    elif ev < -0.3:
        return "PLAY_MIN", ev
    else:
        return "PLAY_MAX", ev

def generate_ticket(game, recent_draws, seed=42):
    random.seed(seed)
    is_ej = (game == "eurojackpot")
    max_pool = GAMES[game]["max_pool"]
    
    # 1. Estraiamo i numeri usciti di recente (per evitarli)
    recent_nums = set()
    for d in recent_draws:
        for k, v in d.items():
            if k.startswith("n") and v: 
                recent_nums.add(v)

    # 2. Logica Anti-Crowd: Numeri alti (> 31 per evitare compleanni), no multipli di 7
    pool = [n for n in range(32, max_pool + 1) if n not in recent_nums and n % 7 != 0]
    
    # Fallback di sicurezza
    if len(pool) < (5 if is_ej else 6):
        pool = [n for n in range(32, max_pool + 1) if n % 7 != 0]

    # 3. Euronumeri
    if is_ej:
        recent_euros = set()
        for d in recent_draws:
            if d.get("e1"): recent_euros.add(d["e1"])
            if d.get("e2"): recent_euros.add(d["e2"])
        
        euro_pool = [n for n in range(1, 13) if n not in (1, 7, 12) and n not in recent_euros]
        if len(euro_pool) < 2: 
            euro_pool = [2, 3, 4, 5, 6, 8, 9, 10, 11]
            
        return sorted(random.sample(pool, 5)), sorted(random.sample(euro_pool, 2))
    
    return sorted(random.sample(pool, 6)), []
