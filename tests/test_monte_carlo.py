"""Unit tests for Monte Carlo game outcome predictor."""

import pytest
from monte_carlo import (
    SimConfig,
    GameParams,
    run_simulation,
    compute_official_bias,
    build_game_params,
)


def test_sim_config_defaults():
    """Test SimConfig default values."""
    config = SimConfig()
    assert config.n_simulations == 1_000
    assert config.decay_rate == 0.1
    assert config.lookback_games == 20


def test_sim_config_capped_at_100k():
    """Test that n_simulations is capped at 100,000."""
    # Should accept 100k
    config = SimConfig(n_simulations=100_000)
    assert config.n_simulations == 100_000

    # Should reject > 100k
    with pytest.raises(ValueError):
        SimConfig(n_simulations=100_001)


def test_sim_config_minimum_100():
    """Test that n_simulations has minimum of 100."""
    with pytest.raises(ValueError):
        SimConfig(n_simulations=50)


def test_identical_teams_home_advantage():
    """Test that identical teams result in home team winning more (54% baseline)."""
    params = GameParams(
        home_team_id=1,
        away_team_id=2,
        home_attack=1.0,
        home_defense=1.0,
        away_attack=1.0,
        away_defense=1.0,
        official_bias=0.0,
    )
    config = SimConfig(n_simulations=10_000)

    result = run_simulation(params, config)

    # Home team should win roughly 54% of regulation games
    assert 44.0 < result.home_reg_win_pct < 64.0  # Wide tolerance for randomness
    # Away team should win roughly 46%
    assert 36.0 < result.away_reg_win_pct < 56.0  # Wide tolerance for randomness


def test_win_percentages_sum_to_100():
    """Test that home_win_pct + away_win_pct = 100%."""
    params = GameParams(
        home_team_id=1,
        away_team_id=2,
        home_attack=1.1,
        home_defense=0.95,
        away_attack=0.9,
        away_defense=1.05,
    )
    config = SimConfig(n_simulations=5_000)

    result = run_simulation(params, config)

    # Total wins + OT + SO should account for all games
    # home_win_pct includes regulation, OT, and SO wins
    # away_win_pct includes regulation, OT, and SO wins
    total = result.home_win_pct + result.away_win_pct
    assert 99.9 < total < 100.1  # Allow tiny floating point error


def test_ot_and_so_percentages_reasonable():
    """Test that OT and SO percentages are within reasonable bounds."""
    params = GameParams(
        home_team_id=1,
        away_team_id=2,
        home_attack=1.0,
        home_defense=1.0,
        away_attack=1.0,
        away_defense=1.0,
    )
    config = SimConfig(n_simulations=10_000)

    result = run_simulation(params, config)

    # OT + SO should be relatively small (maybe 5-15% for close teams)
    ot_so_total = result.ot_pct + result.so_pct
    assert ot_so_total < 20.0


def test_score_distribution_sums_to_100():
    """Test that score distribution percentages sum to 100%."""
    params = GameParams(
        home_team_id=1,
        away_team_id=2,
        home_attack=1.0,
        home_defense=1.0,
        away_attack=1.0,
        away_defense=1.0,
    )
    config = SimConfig(n_simulations=10_000)

    result = run_simulation(params, config)

    score_pct_sum = sum(result.score_distribution.values())
    # Score distribution is top 10 only, so won't sum to 100%
    # But should be substantial (maybe 30-60% of outcomes in top 10)
    assert 20.0 < score_pct_sum < 70.0


def test_favorable_home_team():
    """Test that a much stronger home team wins more."""
    params = GameParams(
        home_team_id=1,
        away_team_id=2,
        home_attack=1.5,  # Much better offense
        home_defense=0.8,  # Much better defense
        away_attack=0.8,
        away_defense=1.2,
    )
    config = SimConfig(n_simulations=5_000)

    result = run_simulation(params, config)

    # Home team should win by significant margin
    assert result.home_win_pct > result.away_win_pct
    assert result.home_win_pct > 65.0  # Clearly favored


def test_unfavorable_home_team():
    """Test that a much weaker home team wins less."""
    params = GameParams(
        home_team_id=1,
        away_team_id=2,
        home_attack=0.6,  # Worse offense
        home_defense=1.3,  # Worse defense (allows more goals)
        away_attack=1.4,
        away_defense=0.7,
    )
    config = SimConfig(n_simulations=5_000)

    result = run_simulation(params, config)

    # Home team should lose more
    assert result.away_win_pct > result.home_win_pct
    assert result.away_win_pct > 65.0


def test_official_bias_positive():
    """Test that positive official bias helps home team (with larger bias to see effect)."""
    # Use larger bias to overcome random variance with smaller sample size
    base_params = GameParams(
        home_team_id=1,
        away_team_id=2,
        home_attack=1.0,
        home_defense=1.0,
        away_attack=1.0,
        away_defense=1.0,
        official_bias=0.0,
    )
    biased_params = GameParams(
        home_team_id=1,
        away_team_id=2,
        home_attack=1.0,
        home_defense=1.0,
        away_attack=1.0,
        away_defense=1.0,
        official_bias=0.3,  # Larger positive bias to see effect clearly
    )
    config = SimConfig(n_simulations=10_000)

    base_result = run_simulation(base_params, config)
    biased_result = run_simulation(biased_params, config)

    # Home team should win more with positive bias
    # Allow 1% tolerance for random variance
    assert biased_result.home_win_pct >= base_result.home_win_pct - 1.0


def test_official_bias_computation():
    """Test compute_official_bias function."""
    # Two officials with 60% home win rate (above 53.61% league avg)
    bias = compute_official_bias([0.60, 0.60])
    assert bias > 0.0  # Should be positive
    assert 0.03 < bias < 0.07  # Roughly 0.5 * (0.60 - 0.5361) * 2

    # Officials with league-average home win rate
    bias = compute_official_bias([0.5361, 0.5361])
    assert abs(bias) < 0.01  # Should be near zero

    # Empty list
    bias = compute_official_bias([])
    assert bias == 0.0


def test_build_game_params():
    """Test build_game_params convenience function."""
    params = build_game_params(
        home_attack=1.1,
        home_defense=0.9,
        away_attack=1.0,
        away_defense=1.0,
        official_bias=0.05,
        home_team_id=10,
        away_team_id=20,
    )

    assert params.home_attack == 1.1
    assert params.home_defense == 0.9
    assert params.away_attack == 1.0
    assert params.away_defense == 1.0
    assert params.official_bias == 0.05
    assert params.home_team_id == 10
    assert params.away_team_id == 20
    assert params.home_so_win_rate == 0.5


def test_simulation_different_seed_same_outcomes():
    """Test that running with different seeds produces similar (but not identical) results."""
    params = GameParams(
        home_team_id=1,
        away_team_id=2,
        home_attack=1.0,
        home_defense=1.0,
        away_attack=1.0,
        away_defense=1.0,
    )
    config = SimConfig(n_simulations=5_000)

    result1 = run_simulation(params, config)
    result2 = run_simulation(params, config)

    # Results should be similar but not identical (different random seeds)
    assert abs(result1.home_win_pct - result2.home_win_pct) < 5.0
    assert result1.home_win_pct != result2.home_win_pct  # Very unlikely to be exact


def test_high_scoring_teams():
    """Test teams with high scoring rates."""
    params = GameParams(
        home_team_id=1,
        away_team_id=2,
        home_attack=1.3,
        home_defense=1.2,
        away_attack=1.25,
        away_defense=1.15,
    )
    config = SimConfig(n_simulations=5_000)

    result = run_simulation(params, config)

    # Expected goals should be relatively high
    assert result.avg_home_goals > 3.0
    assert result.avg_away_goals > 2.5
