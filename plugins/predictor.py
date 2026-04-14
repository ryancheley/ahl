"""Datasette plugin for Monte Carlo game outcome prediction.

Provides routes and UI for predicting AHL game outcomes using cached team stats
and official bias computations.
"""

import json
import sqlite3
import sys
import urllib.parse
from datetime import datetime, UTC
from pathlib import Path

# Import from parent directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from datasette import hookimpl
from datasette.utils.asgi import Response

from monte_carlo import SimConfig, GameParams, run_simulation, compute_official_bias


# Use /data/my_database.db in Docker/Coolify, otherwise use local path
_docker_db = Path("/data/my_database.db")
DB_PATH = (
    _docker_db
    if _docker_db.exists()
    else Path(__file__).parent.parent / "my_database.db"
)

LEAGUE_HOME_WIN_PCT = 0.5361


def get_db_connection():
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


async def _check_stats_freshness(datasette):
    """Check if cached team stats are stale (> 24h). If so, trigger retrain."""
    try:
        db = datasette.get_database("my_database")
        result = await db.execute(
            "SELECT MAX(computed_at) as latest FROM mc_team_stats"
        )
        row = result.rows[0] if result.rows else None

        if not row or not row["latest"]:
            # No stats yet, run init and train
            _run_retrain(datasette)
            return

        latest_str = row["latest"]
        latest = datetime.fromisoformat(latest_str.replace("Z", "+00:00"))
        now = datetime.now(UTC)
        hours_ago = (now - latest).total_seconds() / 3600

        if hours_ago > 24:
            _run_retrain(datasette)
    except Exception as e:
        # Silently fail on startup check - don't crash datasette
        print(f"[MC] Stats freshness check failed: {e}")


def _run_retrain(datasette):
    """Run retrain subprocess (simplified version)."""
    import subprocess

    try:
        subprocess.run(
            ["uv", "run", "retrain.py", "train"],
            cwd=str(Path(__file__).parent.parent),
            timeout=60,
            capture_output=True,
        )
    except Exception as e:
        print(f"[MC] Retrain failed: {e}")


@hookimpl
def menu_links(datasette, actor):
    """Add Game Predictor link to main navigation menu."""
    return [{"href": "/predict", "label": "Game Predictor"}]


@hookimpl
def startup(datasette):
    """Check stats freshness on startup."""

    async def _startup():
        await _check_stats_freshness(datasette)

    return _startup()


@hookimpl
def register_routes():
    """Register custom routes for the predictor."""
    return [
        (r"^/predict$", predict_view),
        (r"^/predict/run$", predict_run_view),
        (r"^/predict/games$", predict_games_api),
    ]


async def predict_view(request, datasette):
    """GET /predict - Render the game selection form."""
    db = datasette.get_database("my_database")

    # Fetch seasons (career=1, playoff=0, regular season only)
    seasons_result = await db.execute(
        """
        SELECT season_id, season_name
        FROM season
        WHERE career = 1 AND playoff = 0
        ORDER BY season_id DESC
        """
    )
    seasons = seasons_result.rows

    # Default to season 90 if available
    default_season_id = 90
    if not seasons:
        default_season_id = None
    else:
        # Check if season 90 exists
        season_90 = [s for s in seasons if s["season_id"] == 90]
        if season_90:
            default_season_id = 90
        else:
            default_season_id = seasons[0]["season_id"]

    # Fetch games for default season (both completed and upcoming)
    games = []
    teams = []
    if default_season_id:
        # Get season date range
        season_info = await db.execute(
            """
            SELECT start_date, end_date FROM season WHERE season_id = ?
            """,
            [default_season_id],
        )
        season_dates = season_info.rows[0] if season_info.rows else None

        # Fetch teams active in this season (from both completed and scheduled games)
        teams_result = await db.execute(
            """
            SELECT DISTINCT t.team_id, t.name
            FROM team t
            WHERE t.team_id IN (
                SELECT DISTINCT home_team_id FROM gamedata WHERE season_id = ?
                UNION
                SELECT DISTINCT away_team_id FROM gamedata WHERE season_id = ?
                UNION
                SELECT DISTINCT home_team_id FROM scheduled_games sg
                WHERE sg.game_date >= (SELECT start_date FROM season WHERE season_id = ?)
                  AND sg.game_date <= (SELECT end_date FROM season WHERE season_id = ?)
                UNION
                SELECT DISTINCT away_team_id FROM scheduled_games sg
                WHERE sg.game_date >= (SELECT start_date FROM season WHERE season_id = ?)
                  AND sg.game_date <= (SELECT end_date FROM season WHERE season_id = ?)
            )
            ORDER BY t.name
            """,
            [
                default_season_id,
                default_season_id,
                default_season_id,
                default_season_id,
                default_season_id,
                default_season_id,
            ],
        )
        teams = teams_result.rows

        # Completed games
        completed = await db.execute(
            """
            SELECT
                g.game_id,
                g.season_id,
                g.game_date,
                g.game_status,
                g.home_team_id,
                g.away_team_id,
                ht.name as home_team,
                at.name as away_team,
                g.home_team_score,
                g.away_team_score,
                'completed' as game_type
            FROM gamedata g
            LEFT JOIN team ht ON g.home_team_id = ht.team_id
            LEFT JOIN team at ON g.away_team_id = at.team_id
            WHERE g.season_id = ?
            ORDER BY g.game_date DESC
            LIMIT 100
            """,
            [default_season_id],
        )

        # Upcoming games (scheduled but not yet played)
        # Use the season date range to find games instead of LEFT JOIN
        # Exclude games that are already in gamedata (have been played)
        upcoming_games = []
        if season_dates:
            upcoming = await db.execute(
                """
                SELECT
                    sg.game_id,
                    sg.game_date,
                    sg.home_team_id,
                    sg.away_team_id,
                    ht.name as home_team,
                    at.name as away_team
                FROM scheduled_games sg
                LEFT JOIN team ht ON sg.home_team_id = ht.team_id
                LEFT JOIN team at ON sg.away_team_id = at.team_id
                WHERE sg.game_date >= ? AND sg.game_date <= ?
                  AND sg.game_id NOT IN (SELECT DISTINCT game_id FROM gamedata)
                ORDER BY sg.game_date ASC
                """,
                [season_dates["start_date"], season_dates["end_date"]],
            )

            upcoming_games = [
                {
                    "game_id": row["game_id"],
                    "season_id": default_season_id,
                    "game_date": row["game_date"],
                    "game_status": "Upcoming",
                    "home_team_id": row["home_team_id"],
                    "away_team_id": row["away_team_id"],
                    "home_team": row["home_team"],
                    "away_team": row["away_team"],
                    "home_team_score": None,
                    "away_team_score": None,
                    "game_type": "upcoming",
                }
                for row in upcoming.rows
            ]

        # Put upcoming games first (in ascending order), then completed games (most recent first)
        games = upcoming_games + completed.rows

    html = await datasette.render_template(
        "predictor.html",
        {
            "seasons": seasons,
            "default_season_id": default_season_id,
            "games": games,
            "teams": teams,
        },
        request=request,
    )
    return Response.html(html)


async def predict_games_api(request, datasette):
    """GET /predict/games?season_id=X - Return games and teams for a season as JSON."""
    try:
        query_string = request.scope.get("query_string", b"").decode("utf-8")
        params = urllib.parse.parse_qs(query_string)
        season_id = int(params.get("season_id", [""])[0])

        if not season_id:
            return Response.json({"error": "Missing season_id"}, status=400)
    except (ValueError, IndexError):
        return Response.json({"error": "Invalid season_id"}, status=400)

    db = datasette.get_database("my_database")

    # Get season date range
    season_info = await db.execute(
        """
        SELECT start_date, end_date FROM season WHERE season_id = ?
        """,
        [season_id],
    )
    season_dates = season_info.rows[0] if season_info.rows else None

    if not season_dates:
        return Response.json({"error": "Season not found"}, status=404)

    # Fetch completed games
    completed = await db.execute(
        """
        SELECT
            g.game_id,
            g.season_id,
            g.game_date,
            g.game_status,
            g.home_team_id,
            g.away_team_id,
            ht.name as home_team,
            at.name as away_team,
            g.home_team_score,
            g.away_team_score,
            'completed' as game_type
        FROM gamedata g
        LEFT JOIN team ht ON g.home_team_id = ht.team_id
        LEFT JOIN team at ON g.away_team_id = at.team_id
        WHERE g.season_id = ?
        ORDER BY g.game_date DESC
        LIMIT 100
        """,
        [season_id],
    )

    # Fetch upcoming games
    upcoming = await db.execute(
        """
        SELECT
            sg.game_id,
            sg.game_date,
            sg.home_team_id,
            sg.away_team_id,
            ht.name as home_team,
            at.name as away_team
        FROM scheduled_games sg
        LEFT JOIN team ht ON sg.home_team_id = ht.team_id
        LEFT JOIN team at ON sg.away_team_id = at.team_id
        WHERE sg.game_date >= ? AND sg.game_date <= ?
          AND sg.game_id NOT IN (SELECT DISTINCT game_id FROM gamedata)
        ORDER BY sg.game_date ASC
        """,
        [season_dates["start_date"], season_dates["end_date"]],
    )

    # Compile games list
    games_list = []
    for row in upcoming.rows:
        games_list.append(
            {
                "game_id": row["game_id"],
                "game_date": row["game_date"],
                "home_team_id": row["home_team_id"],
                "away_team_id": row["away_team_id"],
                "home_team": row["home_team"],
                "away_team": row["away_team"],
                "home_team_score": None,
                "away_team_score": None,
                "game_status": "Upcoming",
                "game_type": "upcoming",
            }
        )

    for row in completed.rows:
        games_list.append(
            {
                "game_id": row["game_id"],
                "game_date": row["game_date"],
                "home_team_id": row["home_team_id"],
                "away_team_id": row["away_team_id"],
                "home_team": row["home_team"],
                "away_team": row["away_team"],
                "home_team_score": row["home_team_score"],
                "away_team_score": row["away_team_score"],
                "game_status": row["game_status"],
                "game_type": row["game_type"],
            }
        )

    # Fetch teams active in this season
    teams_result = await db.execute(
        """
        SELECT DISTINCT t.team_id, t.name
        FROM team t
        WHERE t.team_id IN (
            SELECT DISTINCT home_team_id FROM gamedata WHERE season_id = ?
            UNION
            SELECT DISTINCT away_team_id FROM gamedata WHERE season_id = ?
            UNION
            SELECT DISTINCT home_team_id FROM scheduled_games sg
            WHERE sg.game_date >= ? AND sg.game_date <= ?
            UNION
            SELECT DISTINCT away_team_id FROM scheduled_games sg
            WHERE sg.game_date >= ? AND sg.game_date <= ?
        )
        ORDER BY t.name
        """,
        [
            season_id,
            season_id,
            season_dates["start_date"],
            season_dates["end_date"],
            season_dates["start_date"],
            season_dates["end_date"],
        ],
    )

    teams = [
        {"team_id": row["team_id"], "name": row["name"]} for row in teams_result.rows
    ]

    return Response.json(
        {
            "games": games_list,
            "teams": teams,
        }
    )


async def predict_run_view(request, datasette):
    """GET /predict/run - Run simulation and return results."""
    try:
        # Parse query parameters from URL
        query_string = request.scope.get("query_string", b"").decode("utf-8")
        params = urllib.parse.parse_qs(query_string)

        game_id_list = params.get("game_id", [])
        if not game_id_list:
            return Response.html("<p>Missing game_id</p>", status=400)

        game_id = int(game_id_list[0])
        n_sims = int(params.get("n_simulations", ["1000"])[0])
        decay_preset = params.get("decay", ["medium"])[0]
        lookback = int(params.get("lookback", ["20"])[0])
    except ValueError as e:
        return Response.html(f"<p>Invalid parameters: {str(e)}</p>", status=400)
    except Exception as e:
        return Response.html(f"<p>Error: {str(e)}</p>", status=500)

    # Map decay preset to rate
    decay_rates = {"slow": 0.05, "medium": 0.1, "fast": 0.25}
    decay_rate = decay_rates.get(decay_preset, 0.1)

    # Fetch game info - try gamedata first, then scheduled_games
    db = datasette.get_database("my_database")

    # Try to find in completed games
    game_result = await db.execute(
        "SELECT game_id, season_id, home_team_id, away_team_id, game_date FROM gamedata WHERE game_id = ?",
        [game_id],
    )

    game = None
    season_id = None

    if game_result.rows:
        game = game_result.rows[0]
        season_id = game["season_id"]
    else:
        # Try scheduled games
        scheduled = await db.execute(
            """
            SELECT sg.game_id, sg.home_team_id, sg.away_team_id, sg.game_date,
                   s.season_id
            FROM scheduled_games sg
            LEFT JOIN season s ON (
                sg.game_date >= s.start_date AND
                sg.game_date <= s.end_date AND
                s.career = 1 AND s.playoff = 0
            )
            WHERE sg.game_id = ?
            """,
            [game_id],
        )
        if scheduled.rows:
            game = scheduled.rows[0]
            season_id = game["season_id"]

    if not game:
        return Response.html("<p>Game not found</p>", status=404)
    home_team_id = game["home_team_id"]
    away_team_id = game["away_team_id"]
    game_date = game["game_date"]

    # Fetch team names
    team_names_result = await db.execute(
        "SELECT team_id, name FROM team WHERE team_id IN (?, ?)",
        [home_team_id, away_team_id],
    )
    team_names = {row["team_id"]: row["name"] for row in team_names_result.rows}
    home_team_name = team_names.get(home_team_id, "Unknown")
    away_team_name = team_names.get(away_team_id, "Unknown")

    # Fetch game details (scores and status if completed)
    game_details = None
    game_status = "Upcoming"
    home_score = None
    away_score = None
    gamedata = await db.execute(
        """
        SELECT game_status, home_team_score, away_team_score
        FROM gamedata WHERE game_id = ?
        """,
        [game_id],
    )
    if gamedata.rows:
        game_details = gamedata.rows[0]
        game_status = game_details["game_status"] or "Unknown"
        home_score = game_details["home_team_score"]
        away_score = game_details["away_team_score"]

    # Load team stats
    team_stats_result = await db.execute(
        """
        SELECT team_id, attack_rate, defense_rate, so_win_rate
        FROM mc_team_stats
        WHERE season_id = ? AND team_id IN (?, ?)
        """,
        [season_id, home_team_id, away_team_id],
    )

    team_stats = {row["team_id"]: row for row in team_stats_result.rows}

    if home_team_id not in team_stats or away_team_id not in team_stats:
        return Response.html(
            "<p>Team stats not available for this season. Run retraining.</p>",
            status=400,
        )

    home_ts = team_stats[home_team_id]
    away_ts = team_stats[away_team_id]

    # Load officials and compute bias
    officials_result = await db.execute(
        """
        SELECT DISTINCT go.person_id, mos.home_win_pct
        FROM gameofficial go
        LEFT JOIN mc_official_stats mos ON go.person_id = mos.person_id
        WHERE go.game_id = ?
        """,
        [game_id],
    )

    official_biases = []
    for official in officials_result.rows:
        if official["home_win_pct"]:
            official_biases.append(official["home_win_pct"])

    official_bias = compute_official_bias(official_biases) if official_biases else 0.0

    # Build game parameters
    params_obj = GameParams(
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_attack=home_ts["attack_rate"],
        home_defense=home_ts["defense_rate"],
        away_attack=away_ts["attack_rate"],
        away_defense=away_ts["defense_rate"],
        official_bias=official_bias,
        home_so_win_rate=home_ts["so_win_rate"],
        away_so_win_rate=away_ts["so_win_rate"],
    )

    config = SimConfig(
        n_simulations=n_sims, decay_rate=decay_rate, lookback_games=lookback
    )

    # Run simulation
    result = run_simulation(params_obj, config)

    # Save result to cache
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO mc_predictions
            (game_id, n_simulations, decay_rate, lookback_games, home_win_pct,
             away_win_pct, ot_pct, so_pct, avg_home_goals, avg_away_goals,
             score_dist_json, computed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                game_id,
                n_sims,
                decay_rate,
                lookback,
                result.home_win_pct,
                result.away_win_pct,
                result.ot_pct,
                result.so_pct,
                result.avg_home_goals,
                result.avg_away_goals,
                json.dumps(result.score_distribution),
                datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[MC] Error saving prediction: {e}")

    # Prepare data for chart - filter out matching scores (they go to OT/SO)
    filtered_scores = {}
    for score, pct in result.score_distribution.items():
        # Parse "X-Y" format and skip if matching
        parts = score.split("-")
        if len(parts) == 2 and parts[0] != parts[1]:
            filtered_scores[score] = pct

    scores = list(filtered_scores.keys())
    percentages = list(filtered_scores.values())

    # Render results HTML with Chart.js
    chart_data_json = json.dumps({"scores": scores, "percentages": percentages})

    # Format game info
    game_info_html = f"""
    <div class="game-info">
        <h4>Game Information</h4>
        <table class="results-table">
            <tr>
                <td><strong>Date</strong></td>
                <td>{game_date}</td>
            </tr>
            <tr>
                <td><strong>Status</strong></td>
                <td>{game_status}</td>
            </tr>
    """
    if home_score is not None and away_score is not None:
        game_info_html += f"""
            <tr>
                <td><strong>Final Score</strong></td>
                <td>{home_team_name} {home_score} - {away_score} {away_team_name}</td>
            </tr>
        """
    game_info_html += """
        </table>
    </div>
    """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Prediction Results</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 900px; margin: 0 auto; }}
            .mc-results {{ background: #fff; padding: 20px; border-radius: 8px; border: 2px solid #0066cc; }}
            .mc-results h3 {{ color: #0066cc; margin-top: 0; }}
            .mc-results h4 {{ margin-top: 20px; color: #333; }}
            .game-info {{ background: #f0f7ff; padding: 15px; border-radius: 6px; margin: 20px 0; }}
            .game-info h4 {{ margin-top: 0; }}
            .results-grid {{ display: flex; gap: 30px; margin: 20px 0; align-items: start; }}
            .outcome-boxes {{ display: flex; gap: 15px; }}
            .outcome-box {{ padding: 15px 20px; border-radius: 6px; text-align: center; min-width: 140px; }}
            .outcome-box.home-win {{ background: #e6f3ff; border: 2px solid #0066cc; }}
            .outcome-box.away-win {{ background: #ffe6e6; border: 2px solid #cc0000; }}
            .outcome-label {{ font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 8px; }}
            .team-name {{ font-size: 14px; font-weight: 600; margin-bottom: 8px; }}
            .outcome-percent {{ font-size: 28px; font-weight: bold; color: #333; }}
            .results-table {{ border-collapse: collapse; }}
            .results-table td {{ padding: 10px 15px; border-bottom: 1px solid #eee; }}
            .results-table tr:nth-child(even) {{ background-color: #f9f9f9; }}
            #scoreChart {{ max-height: 300px; }}
            .back-link {{ margin: 20px 0; }}
            .back-link a {{ color: #0066cc; text-decoration: none; }}
            .back-link a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="back-link">
                <a href="/predict">← Back to Predictor</a>
            </div>

            <div class="mc-results">
                <h3>Prediction Results</h3>

                {game_info_html}

                <div class="results-grid">
                    <div class="outcome-boxes">
                        <div class="outcome-box home-win">
                            <div class="outcome-label">Home Win</div>
                            <div class="team-name">{home_team_name}</div>
                            <div class="outcome-percent">{result.home_win_pct}%</div>
                        </div>
                        <div class="outcome-box away-win">
                            <div class="outcome-label">Away Win</div>
                            <div class="team-name">{away_team_name}</div>
                            <div class="outcome-percent">{result.away_win_pct}%</div>
                        </div>
                    </div>

                    <table class="results-table">
                        <tr>
                            <td><strong>Regulation</strong></td>
                            <td>{result.home_reg_win_pct + result.away_reg_win_pct}%</td>
                        </tr>
                        <tr>
                            <td><strong>Overtime</strong></td>
                            <td>{result.ot_pct}%</td>
                        </tr>
                        <tr>
                            <td><strong>Shootout</strong></td>
                            <td>{result.so_pct}%</td>
                        </tr>
                        <tr>
                            <td colspan="2">&nbsp;</td>
                        </tr>
                        <tr>
                            <td><strong>Avg Home Goals</strong></td>
                            <td>{result.avg_home_goals}</td>
                        </tr>
                        <tr>
                            <td><strong>Avg Away Goals</strong></td>
                            <td>{result.avg_away_goals}</td>
                        </tr>
                    </table>
                </div>

                <h4>Top Score Lines</h4>
                <div style="position: relative; width: 100%; height: 300px; margin: 20px 0;">
                    <canvas id="scoreChart"></canvas>
                </div>

                <p><small>Simulations: {result.n_simulations}</small></p>
            </div>
        </div>

        <script>
            const chartData = {chart_data_json};
            const ctx = document.getElementById('scoreChart').getContext('2d');
            const chart = new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: chartData.scores,
                    datasets: [{{
                        label: 'Probability (%)',
                        data: chartData.percentages,
                        backgroundColor: '#0066cc',
                        borderColor: '#0052a3',
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: true, position: 'top' }},
                        title: {{ display: true, text: 'Most Likely Final Scores' }}
                    }},
                    scales: {{
                        y: {{ beginAtZero: true, title: {{ display: true, text: 'Probability (%)' }} }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """

    return Response.html(html)
