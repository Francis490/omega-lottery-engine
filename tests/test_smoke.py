"""
Smoke test eseguiti in CI dopo main.py, prima del commit.
"""
import json
import random
from pathlib import Path

import pytest

from models import EurojackpotDraw, SuperenalottoDraw, VinciDraw
from omega_brain import (
    ENABLE_SKIP,
    GAMES,
    JACKPOT_PROBABILITY,
    LOWER_TIER_RETURN,
    SKIP_THRESHOLD,
    generate_ticket,
    get_decision,
)


def _fake_draws(n=30, pool=90, seed=0):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        nums = sorted(rng.sample(range(1, pool + 1), 8))
        out.append(
            {
                "n1": nums[0], "n2": nums[1], "n3": nums[2], "n4": nums[3],
                "n5": nums[4], "n6": nums[5], "n7": nums[6], "n8": nums[7],
                "e1": rng.randint(1, 12), "e2": rng.randint(1, 12),
            }
        )
    return out


# ---------------- Models ----------------
def test_eurojackpot_model_cardinality():
    d = EurojackpotDraw(draw_date="2026-11-06", mains=[1, 2, 3, 4, 5], euros=[1, 2])
    assert len(d.mains) == 5
    assert len(d.euros) == 2


def test_superenalotto_model_cardinality():
    d = SuperenalottoDraw(draw_date="2026-11-06", mains=[1, 2, 3, 4, 5, 6])
    assert len(d.mains) == 6


def test_vinci_model_cardinality():
    d = VinciDraw(draw_date="2026-11-06", mains=[1, 2, 3, 4, 5, 6, 7, 8])
    assert len(d.mains) == 8


# ---------------- generate_ticket ----------------
@pytest.mark.parametrize(
    "game, expected_mains, expected_euros",
    [
        ("eurojackpot", 5, 2),
        ("superenalotto", 6, 0),
        ("swfl", 6, 0),
    ],
)
def test_generate_ticket_cardinality(game, expected_mains, expected_euros):
    pool = GAMES[game]["max_pool"]
    draws = _fake_draws(pool=pool)
    mains, euros = generate_ticket(game, draws, seed=42)

    assert len(mains) == expected_mains, (
        f"{game}: attesi {expected_mains} numeri, trovati {len(mains)}"
    )
    assert len(euros) == expected_euros
    assert len(set(mains)) == len(mains)
    assert all(1 <= n <= pool for n in mains)
    assert all(1 <= n <= 12 for n in euros)


def test_generate_ticket_deterministic():
    draws = _fake_draws()
    a = generate_ticket("superenalotto", draws, seed=123)
    b = generate_ticket("superenalotto", draws, seed=123)
    assert a == b


# ---------------- get_decision / EV ----------------
@pytest.mark.parametrize("game", ["eurojackpot", "superenalotto", "swfl"])
def test_decision_valid(game):
    decision, ev = get_decision(game, 50_000_000)
    assert decision in ("PLAY_MAX", "SKIP")
    assert ev >= 0
    assert isinstance(ev, float)


def test_ev_grows_with_jackpot():
    _, ev_low = get_decision("eurojackpot", 10_000_000)
    _, ev_high = get_decision("eurojackpot", 100_000_000)
    assert ev_high > ev_low


@pytest.mark.parametrize("game", ["eurojackpot", "superenalotto", "swfl"])
def test_lower_tier_return_in_range(game):
    """LOWER_TIER_RETURN deve essere una frazione plausibile (0.20–0.80)."""
    v = LOWER_TIER_RETURN[game]
    assert 0.20 <= v <= 0.80, (
        f"{game}: LOWER_TIER_RETURN={v} fuori range plausibile"
    )


def test_skip_disabled_by_default():
    """Con ENABLE_SKIP=False, get_decision non deve mai tornare SKIP."""
    if ENABLE_SKIP:
        pytest.skip("ENABLE_SKIP=True, test non applicabile")
    for game in ("eurojackpot", "superenalotto", "swfl"):
        decision, _ = get_decision(game, 0)
        assert decision == "PLAY_MAX", (
            f"{game}: con ENABLE_SKIP=False e jackpot=0 atteso PLAY_MAX"
        )


# ---------------- latest.json ----------------
def test_latest_json_shape():
    p = Path("docs/latest.json")
    if not p.exists():
        pytest.skip("latest.json non presente")

    data = json.loads(p.read_text(encoding="utf-8"))
    assert "timestamp" in data
    assert "games" in data
    assert isinstance(data["games"], dict)

    valid_statuses = {"PLAY", "SKIP", "NO_DRAW", "STALE"}
    for game, info in data["games"].items():
        assert "status" in info
        assert info["status"] in valid_statuses
        assert "ev" in info
        if info["status"] == "PLAY":
            assert isinstance(info.get("mains"), list)
            expected = 5 if game == "eurojackpot" else 6
            assert len(info["mains"]) == expected


# ---------------- _all_good helper ----------------
def test_all_good_helper():
    from main import _all_good

    assert _all_good({"games": {"a": {"status": "PLAY"}, "b": {"status": "NO_DRAW"}}})
    assert not _all_good({"games": {"a": {"status": "STALE"}, "b": {"status": "PLAY"}}})
    assert not _all_good({"games": {}})
