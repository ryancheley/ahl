"""Monte Carlo simulation functions for AHL playoff predictions."""

import sqlite3
import numpy as np
from monte_carlo import GameParams, SimConfig, run_simulation

# Constants
HOME_ICE_SCHEDULES = {
    "R1_close": {1: True, 2: False, 3: True},
    "R1_far": {1: True, 2: True, 3: True},
    "R23_close": {1: True, 2: True, 3: False, 4: False, 5: True},
    "R23_far_A": {1: True, 2: True, 3: False, 4: False, 5: False},
    "R23_far_B": {1: False, 2: False, 3: True, 4: True, 5: True},
    "finals": {1: True, 2: True, 3: False, 4: False, 5: False, 6: True, 7: True},
}


def get_series_win_probability(
    conn: sqlite3.Connection,
    higher_seed_id: int,
    lower_seed_id: int,
    schedule_key: str,
    n_simulations: int = 1000,
) -> tuple[float, float, dict, float]:
    """Simulate a playoff series and return win probabilities.

    Args:
        conn: Database connection.
        higher_seed_id: Higher seeded team.
        lower_seed_id: Lower seeded team.
        schedule_key: Home ice format (R1_close, R23_far_A, finals, etc).
        n_simulations: Number of Monte Carlo simulations.

    Returns:
        Tuple of (higher_seed_win_pct, lower_seed_win_pct, games_distribution)
    """
    cursor = conn.cursor()

    # Get team stats from mc_team_stats (fallback to averages if not available)
    cursor.execute(
        "SELECT attack_rate, defense_rate FROM mc_team_stats WHERE team_id = ? ORDER BY season_id DESC LIMIT 1",
        [higher_seed_id],
    )
    h_row = cursor.fetchone()
    h_attack = h_row[0] if h_row else 1.0
    h_defense = h_row[1] if h_row else 1.0

    cursor.execute(
        "SELECT attack_rate, defense_rate FROM mc_team_stats WHERE team_id = ? ORDER BY season_id DESC LIMIT 1",
        [lower_seed_id],
    )
    l_row = cursor.fetchone()
    l_attack = l_row[0] if l_row else 1.0
    l_defense = l_row[1] if l_row else 1.0

    # Create game parameters (home = higher seed for stats purposes)
    game_params = GameParams(
        home_team_id=higher_seed_id,
        away_team_id=lower_seed_id,
        home_attack=h_attack,
        home_defense=h_defense,
        away_attack=l_attack,
        away_defense=l_defense,
        home_advantage=1.1,
        home_so_win_rate=0.5,
        away_so_win_rate=0.5,
    )

    config = SimConfig(n_simulations=n_simulations)

    # Get per-game win probability from existing Monte Carlo
    result = run_simulation(game_params, config)
    per_game_higher_win_pct = result.home_win_pct / 100.0

    # Determine series length from schedule
    schedule = HOME_ICE_SCHEDULES.get(schedule_key, HOME_ICE_SCHEDULES["finals"])
    max_games = max(schedule.keys())
    wins_needed = (max_games + 1) // 2  # Best of 3, 5, or 7

    # Simulate series using vectorized numpy
    rng = np.random.default_rng()
    higher_wins = np.zeros(n_simulations, dtype=int)
    lower_wins = np.zeros(n_simulations, dtype=int)
    series_lengths = np.zeros(n_simulations, dtype=int)

    for game_num in range(1, max_games + 1):
        # Determine who has home ice this game
        h_is_home = schedule.get(game_num, True)

        # Adjust per-game probability: home team has slight advantage
        game_p = per_game_higher_win_pct
        if not h_is_home:
            game_p = 1.0 - per_game_higher_win_pct

        # Draw game outcomes for all simulations
        # Only for series that aren't decided yet
        active = (higher_wins < wins_needed) & (lower_wins < wins_needed)
        game_outcomes = rng.uniform(size=n_simulations) < game_p
        higher_wins[active & game_outcomes] += 1
        lower_wins[active & ~game_outcomes] += 1
        series_lengths[active] += 1

        # Stop if all series are decided
        if np.all((higher_wins >= wins_needed) | (lower_wins >= wins_needed)):
            break

    # Compute results
    higher_win_count = np.sum(higher_wins >= wins_needed)
    lower_win_count = np.sum(lower_wins >= wins_needed)

    higher_pct = (higher_win_count / n_simulations) * 100.0
    lower_pct = (lower_win_count / n_simulations) * 100.0

    # Games distribution
    unique, counts = np.unique(series_lengths, return_counts=True)
    games_dist = {
        int(g): float(c / n_simulations * 100) for g, c in zip(unique, counts)
    }
    expected_games = float(np.mean(series_lengths))

    return (
        round(higher_pct, 1),
        round(lower_pct, 1),
        games_dist,
        round(expected_games, 1),
    )
