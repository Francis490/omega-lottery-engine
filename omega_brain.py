import random
import math
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter

# ==========================================
# ☢️ CONFIGURAZIONE ARMAGEDDON MODERATO ☢️
# ==========================================
ARMAGEDDON_MODE = True  # Lasciamolo True, ma con fitness bilanciata

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
    if config is None: return "SKIP", 0.0
    cost = config["cost"]
    p_jackpot = JACKPOT_PROBABILITY[game]
    lower_return = LOWER_TIER_RETURN[game] * cost
    ev_total = (jackpot * p_jackpot) + lower_return
    ev_ratio = ev_total / cost if cost else 0.0

    if ENABLE_SKIP and ev_ratio < SKIP_THRESHOLD: return "SKIP", ev_total
    return "PLAY_MAX", ev_total


def _find_broken_numbers(recent_draws, max_pool, top_n=3):
    freq = Counter()
    total_extracted = 0

    for d in recent_draws:
        for k, v in d.items():
            if k.startswith("n") and v:
                freq[v] += 1
                total_extracted += 1

    if total_extracted == 0: return []

    expected = total_extracted / max_pool
    std_dev = math.sqrt(expected * (1 - (1 / max_pool)))

    z_scores = {}
    for n in range(1, max_pool + 1):
        uscite = freq.get(n, 0)
        z_scores[n] = (uscite - expected) / std_dev if std_dev > 0 else 0

    sorted_anomalies = sorted(z_scores.items(), key=lambda x: abs(x[1]), reverse=True)
    return [num for num, z in sorted_anomalies if abs(z) > 2.0][:top_n]


def _calculate_fitness(ticket, z_scores, is_ej, num_to_pick):
    """
    Fitness Bilanciata: Premia gli Z-Score alti ma punisce le schedine 'brutte'.
    """
    score = 0.0
    
    # 1. Premia i numeri con Z-Score alto (ma senza esplosioni nucleari)
    for num in ticket:
        z = abs(z_scores.get(num, 0))
        score += z * 40 # Premio lineare, non più esponenziale
        if z > 2.0: score += 20 # Bonus extra per l'anomalia

    total_sum = sum(ticket)
    
    # 2. Forte premio per le somme che rispettano i canoni classici
    if is_ej:
        if 90 <= total_sum <= 170: score += 150
        score -= abs(total_sum - 130) * 0.2
    else:
        if 200 <= total_sum <= 350: score += 150
        score -= abs(total_sum - 275) * 0.2

    # 3. Premia il giusto mix di Pari/Dispari (no a 5 pari e 1 dispari)
    evens = sum(1 for n in ticket if n % 2 == 0)
    if is_ej:
        if evens in [2, 3]: score += 80
    else:
        if evens in [2, 3, 4]: score += 80 # 2/4, 3/3, 4/2 sono ok

    # 4. Premia l'eterogeneità (numeri sparsi su più decine)
    decades = len(set(n // 10 for n in ticket))
    score += decades * 25

    # 5. Penalizza pesantemente i consecutivi
    consec_count = sum(1 for i in range(len(ticket) - 1) if ticket[i + 1] - ticket[i] == 1)
    if consec_count > 1: score -= 100

    return score


def _crossover(parent1, parent2, num_to_pick, all_nums):
    combined = list(set(parent1 + parent2))
    if len(combined) < num_to_pick:
        return sorted(random.sample(all_nums, num_to_pick))
    return sorted(random.sample(combined, num_to_pick))


def _mutate(ticket, all_nums, mutation_rate=0.3):
    # Mutazione ridotta al 30% per non distruggere l'equilibrio
    ticket = list(ticket)
    if random.random() < mutation_rate:
        idx = random.randint(0, len(ticket) - 1)
        new_num = random.choice(all_nums)
        while new_num in ticket:
            new_num = random.choice(all_nums)
        ticket[idx] = new_num
    return sorted(ticket)


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

    freq = Counter()
    total_extracted = 0
    for d in recent_draws:
        for k, v in d.items():
            if k.startswith("n") and v:
                freq[v] += 1
                total_extracted += 1

    expected = total_extracted / max_pool if total_extracted else 0
    std_dev = math.sqrt(expected * (1 - (1 / max_pool))) if expected else 1
    z_scores = {n: (freq.get(n, 0) - expected) / std_dev if std_dev > 0 else 0 for n in range(1, max_pool + 1)}

    broken_nums = _find_broken_numbers(recent_draws, max_pool, top_n=3)
    chaos_mode = rng.random() < 0.20
    use_broken = bool(broken_nums) and (chaos_mode or rng.random() < 0.5)

    if use_broken:
        picks = list(broken_nums)
        while len(picks) < num_to_pick:
            n = rng.choice(all_nums)
            if n not in picks: picks.append(n)
        best_mains = sorted(picks[:num_to_pick])
    else:
        # ALGORITMO GENETICO MODERATO
        pop_size = 500
        generations = 200
        mut_rate = 0.3

        population = [sorted(rng.sample(all_nums, num_to_pick)) for _ in range(pop_size)]

        for _ in range(generations):
            scored_pop = [(_calculate_fitness(t, z_scores, is_ej, num_to_pick), t) for t in population]
            scored_pop.sort(key=lambda x: x[0], reverse=True)
            
            survivors = [t for _, t in scored_pop[:int(pop_size * 0.20)]] # Top 20%

            new_population = survivors[:50]
            
            while len(new_population) < pop_size:
                p1, p2 = rng.choice(survivors), rng.choice(survivors)
                child = _crossover(p1, p2, num_to_pick, all_nums)
                child = _mutate(child, all_nums, mutation_rate=mut_rate)
                new_population.append(child)
                
            population = new_population

        scored_pop = [(_calculate_fitness(t, z_scores, is_ej, num_to_pick), t) for t in population]
        scored_pop.sort(key=lambda x: x[0], reverse=True)
        best_mains = scored_pop[0][1]

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

        euro_hot = [n for n, _ in euro_freq.most_common() if n <= 12]
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
