import random
import math
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter

# ==========================================
# ☢️ CONFIGURAZIONE ARMAGEDDON ☢️
# ==========================================
ARMAGEDDON_MODE = True  # Metti False se vuoi tornare al bot "normale"

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


def _get_quantum_randomness(count):
    """Oracolo Quantistico (ANU) per il Seed di Armageddon."""
    try:
        url = f"https://qrng.anu.edu.au/API/jsonI.php?length={count}&type=uint8"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json().get('data')
    except Exception:
        pass
    return None


def _find_broken_numbers(recent_draws, max_pool, top_n=5):
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
    Fitness Armageddon: Esponenziale. 
    I numeri estremi valgono il quadrato del loro Z-Score.
    """
    score = 0.0
    for num in ticket:
        z = abs(z_scores.get(num, 0))
        if z > 2.0:
            score += (z ** 2) * 100  # ESPLOSIONE DI PUNTEGGIO
        else:
            score += z * 10
            
    total_sum = sum(ticket)
    if is_ej:
        score -= abs(total_sum - 127.5) * 0.1
    else:
        score -= abs(total_sum - 273.0) * 0.1

    evens = sum(1 for n in ticket if n % 2 == 0)
    if (is_ej and evens in (2, 3)) or (not is_ej and evens == 3):
        score += 50

    decades = len(set(n // 10 for n in ticket))
    score += decades * 20

    return score


def _crossover(parent1, parent2, num_to_pick, all_nums):
    combined = list(set(parent1 + parent2))
    if len(combined) < num_to_pick:
        return sorted(random.sample(all_nums, num_to_pick))
    return sorted(random.sample(combined, num_to_pick))


def _mutate(ticket, all_nums, mutation_rate=0.6):
    """Mutazione Nucleare: il 60% dei geni viene alterato."""
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
        # Armageddon usa il tempo esatto o il caos quantistico
        if ARMAGEDDON_MODE:
            q_data = _get_quantum_randomness(1)
            if q_data:
                rng = random.Random(q_data[0])
            else:
                rng = random.Random(datetime.now(ZoneInfo("Europe/Rome")).timestamp())
        else:
            today_seed = int(datetime.now(ZoneInfo("Europe/Rome")).strftime("%Y%m%d"))
            rng = random.Random(today_seed + len(game))

    is_ej = game == "eurojackpot"
    max_pool = GAMES[game]["max_pool"]
    num_to_pick = GAMES[game]["mains"]
    all_nums = list(range(1, max_pool + 1))

    # Calcolo Z-Score globale
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

    broken_nums = _find_broken_numbers(recent_draws, max_pool, top_n=5)

    # Modalità Caos (solo se non siamo in Armageddon)
    chaos_mode = rng.random() < 0.20 if not ARMAGEDDON_MODE else False
    use_broken = bool(broken_nums) and (chaos_mode or rng.random() < 0.4)

    if use_broken:
        # Gioca i numeri estremamente rotti
        picks = list(broken_nums)
        while len(picks) < num_to_pick:
            n = rng.choice(all_nums)
            if n not in picks: picks.append(n)
        best_mains = sorted(picks[:num_to_pick])
    else:
        # ALGORITMO GENETICO ARMAGEDDON
        pop_size = 1000 if ARMAGEDDON_MODE else 300
        generations = 500 if ARMAGEDDON_MODE else 150
        mut_rate = 0.60 if ARMAGEDDON_MODE else 0.15

        # Genesi
        population = [sorted(rng.sample(all_nums, num_to_pick)) for _ in range(pop_size)]

        for _ in range(generations):
            scored_pop = [(_calculate_fitness(t, z_scores, is_ej, num_to_pick), t) for t in population]
            scored_pop.sort(key=lambda x: x[0], reverse=True)
            
            # I top 10% sopravvivono alla distruzione
            survivors = [t for _, t in scored_pop[:int(pop_size * 0.10)]]

            new_population = survivors[:50] # Elitismo puro
            
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
