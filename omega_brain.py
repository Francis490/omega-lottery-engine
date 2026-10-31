import random
from datetime import datetime

GAMES = {
    "eurojackpot": {"mains": 5, "euros": 2, "cost": 2.0, "max_pool": 50},
    "superenalotto": {"mains": 6, "euros": 0, "cost": 1.0, "max_pool": 90},
    "swfl": {"mains": 6, "euros": 0, "cost": 2.0, "max_pool": 90}
}

def get_decision(game, jackpot):
    # Giochiamo sempre. Colpo secco.
    return "PLAY_MAX", 0.0 

def generate_ticket(game, recent_draws, seed=42):
    # Usiamo la data come seed per garantire che la sestina rimanga 
    # la stessa per tutto il giorno (se rilanci il bot, non cambiano i numeri).
    today_seed = int(datetime.now().strftime("%Y%m%d"))
    random.seed(today_seed)
    
    is_ej = (game == "eurojackpot")
    max_pool = GAMES[game]["max_pool"]
    num_to_pick = 5 if is_ej else 6
    
    # --- GENERAZIONE PURA E SPUDORATA ---
    # Nessun filtro. Peschiamo dal range completo.
    pool = list(range(1, max_pool + 1))
    mains = sorted(random.sample(pool, num_to_pick))
    
    if is_ej:
        # Euronumeri: peschiamo da TUTTI i 12 numeri. 
        euro_pool = list(range(1, 13))
        euros = sorted(random.sample(euro_pool, 2))
        return mains, euros
    
    return mains, []
