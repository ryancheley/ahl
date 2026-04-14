"""Monte Carlo game outcome predictor.

Pure simulation engine for predicting AHL game outcomes using Poisson distribution
scoring model with exponential decay recency weighting and official bias adjustment.

No datasette imports — this module can be tested independently.
"""

from pydantic import BaseModel, Field
import numpy as np
from collections import Counter


# Empirical statistics from historical data
LEAGUE_HOME_WIN_PCT = 0.5361
OT_RESOLUTION_PCT = 0.5596  # % of tied games resolved in OT (vs SO)
HOME_OT_WIN_PCT = 0.54  # Home team advantage in OT
LEAGUE_AVG_GOALS = 2.94  # Regulation home team goals per game


class SimConfig(BaseModel):
    """Configuration for Monte Carlo simulation."""

    n_simulations: int = Field(ge=100, le=100_000, default=1_000)
    decay_rate: float = Field(ge=0.01, le=1.0, default=0.1)
    lookback_games: int = Field(ge=5, le=82, default=20)


class GameParams(BaseModel):
    """Pre-computed parameters for a specific game matchup."""

    home_team_id: int
    away_team_id: int
    home_attack: float  # Normalized: team goals_for / league_avg
    home_defense: float  # Normalized: team goals_against / league_avg
    away_attack: float
    away_defense: float
    home_advantage: float = 1.1  # Multiplicative factor for home ice
    league_avg_goals: float = LEAGUE_AVG_GOALS
    official_bias: float = 0.0  # Additive lambda adjustment from officials
    home_so_win_rate: float = 0.5
    away_so_win_rate: float = 0.5


class SimResult(BaseModel):
    """Results from a Monte Carlo simulation."""

    home_win_pct: float
    away_win_pct: float
    ot_pct: float  # Went to OT (one team won)
    so_pct: float  # Went to shootout
    avg_home_goals: float
    avg_away_goals: float
    home_reg_win_pct: float  # Regulation only (ties don't count)
    away_reg_win_pct: float  # Regulation only
    score_distribution: dict[str, float]  # Top 10 score lines, {score: pct}
    goal_diff_distribution: dict[
        int, float
    ]  # Final-score diff: +N=home win by N, -N=away win by N; ±5 caps "5+"
    n_simulations: int


def run_simulation(params: GameParams, config: SimConfig) -> SimResult:
    """
    Run Monte Carlo simulation for a game matchup.

    Uses numpy vectorization for efficiency. With 100k simulations, runtime is ~50-200ms.

    Args:
        params: Game parameters (team stats, official bias, etc.)
        config: Simulation config (n_simulations, decay_rate, lookback_games)

    Returns:
        SimResult with outcome probabilities and score distribution.
    """
    rng = np.random.default_rng()

    # Poisson lambdas for home and away scoring (regulation)
    lambda_home = (
        params.home_attack
        * params.away_defense
        * params.home_advantage
        * params.league_avg_goals
    )
    lambda_home += params.official_bias

    lambda_away = params.away_attack * params.home_defense * params.league_avg_goals

    # Sample goals for regulation (vectorized across all simulations)
    home_goals = rng.poisson(lambda_home, config.n_simulations)
    away_goals = rng.poisson(lambda_away, config.n_simulations)

    # Determine which games are tied (regulation)
    tied_mask = home_goals == away_goals

    # OT/SO resolution: if tied, some go to OT, rest go to SO
    ot_mask = tied_mask & (rng.uniform(size=config.n_simulations) < OT_RESOLUTION_PCT)
    so_mask = tied_mask & ~ot_mask

    # OT: home team has slight advantage (54%)
    ot_home_wins = ot_mask & (rng.uniform(size=config.n_simulations) < HOME_OT_WIN_PCT)
    ot_away_wins = ot_mask & ~ot_home_wins

    # SO: use team-specific SO win rates
    so_home_wins = so_mask & (
        rng.uniform(size=config.n_simulations) < params.home_so_win_rate
    )
    so_away_wins = so_mask & ~so_home_wins

    # Total wins by outcome type
    reg_home_wins = home_goals > away_goals
    reg_away_wins = away_goals > home_goals

    total_home_wins = reg_home_wins | ot_home_wins | so_home_wins
    total_away_wins = reg_away_wins | ot_away_wins | so_away_wins

    # Compute probabilities
    home_win_pct = np.sum(total_home_wins) / config.n_simulations * 100
    away_win_pct = np.sum(total_away_wins) / config.n_simulations * 100
    ot_pct = np.sum(ot_mask) / config.n_simulations * 100
    so_pct = np.sum(so_mask) / config.n_simulations * 100
    home_reg_win_pct = np.sum(reg_home_wins) / config.n_simulations * 100
    away_reg_win_pct = np.sum(reg_away_wins) / config.n_simulations * 100

    # Score distribution (top 10 final scores)
    scores = [f"{h}-{a}" for h, a in zip(home_goals, away_goals)]
    score_counts = Counter(scores)
    top_scores = score_counts.most_common(10)
    score_dist = {
        score: (count / config.n_simulations * 100) for score, count in top_scores
    }

    # Goal differential distribution based on final scores.
    # Regulation wins keep their actual margin (clipped to ±5).
    # OT/SO games are always decided by 1 goal: +1 for home win, -1 for away win.
    reg_diff = home_goals - away_goals
    final_diff = np.where(
        reg_diff != 0,
        np.clip(reg_diff, -5, 5),
        np.where(total_home_wins, 1, -1),
    )
    diff_values, diff_counts = np.unique(final_diff, return_counts=True)
    goal_diff_dist: dict[int, float] = {
        int(d): round(float(c) / config.n_simulations * 100, 1)
        for d, c in zip(diff_values, diff_counts)
    }

    return SimResult(
        home_win_pct=round(home_win_pct, 1),
        away_win_pct=round(away_win_pct, 1),
        ot_pct=round(ot_pct, 1),
        so_pct=round(so_pct, 1),
        avg_home_goals=round(float(np.mean(home_goals)), 2),
        avg_away_goals=round(float(np.mean(away_goals)), 2),
        home_reg_win_pct=round(home_reg_win_pct, 1),
        away_reg_win_pct=round(away_reg_win_pct, 1),
        score_distribution=score_dist,
        goal_diff_distribution=goal_diff_dist,
        n_simulations=config.n_simulations,
    )


def compute_official_bias(
    ref_home_win_pcts: list[float],
    league_home_win_pct: float = LEAGUE_HOME_WIN_PCT,
    adjustment_factor: float = 0.5,
) -> float:
    """
    Compute average official bias from a list of referee home-win percentages.

    The bias is scaled down so it contributes at most ~0.1-0.15 goals to lambda,
    preventing officials from dominating the model.

    Args:
        ref_home_win_pcts: Home win percentages for each official (as decimals, 0.0-1.0)
        league_home_win_pct: League baseline home win rate (default 0.5361)
        adjustment_factor: Scale factor for bias (default 0.5)

    Returns:
        Official bias (additive lambda adjustment)
    """
    if not ref_home_win_pcts:
        return 0.0

    avg_pct = sum(ref_home_win_pcts) / len(ref_home_win_pcts)
    bias_delta = avg_pct - league_home_win_pct
    official_bias = bias_delta * adjustment_factor

    return official_bias


def build_game_params(
    home_attack: float,
    home_defense: float,
    away_attack: float,
    away_defense: float,
    official_bias: float = 0.0,
    league_avg_goals: float = LEAGUE_AVG_GOALS,
    home_so_win_rate: float = 0.5,
    away_so_win_rate: float = 0.5,
    home_team_id: int = 0,
    away_team_id: int = 0,
) -> GameParams:
    """Convenience builder for GameParams."""
    return GameParams(
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_attack=home_attack,
        home_defense=home_defense,
        away_attack=away_attack,
        away_defense=away_defense,
        official_bias=official_bias,
        league_avg_goals=league_avg_goals,
        home_so_win_rate=home_so_win_rate,
        away_so_win_rate=away_so_win_rate,
    )
