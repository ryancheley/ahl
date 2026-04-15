"""Datasette plugin for displaying AHL playoff bracket predictions."""

import sqlite3
from pathlib import Path
from datasette import hookimpl
from datasette.utils.asgi import Response


_docker_db = Path("/data/my_database.db")
DB_PATH = (
    _docker_db
    if _docker_db.exists()
    else Path(__file__).parent.parent / "my_database.db"
)


def get_db_connection():
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@hookimpl
def menu_links(datasette, actor):
    """Add playoff bracket link to menu."""
    return [
        {"href": "/playoffs", "label": "Playoff Bracket"},
    ]


@hookimpl
def register_routes():
    """Register playoff bracket routes."""
    return [
        (r"^/playoffs$", playoffs_view),
        (r"^/playoffs/data$", playoffs_data_api),
    ]


async def playoffs_view(request, datasette):
    """Render main playoff bracket page."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AHL Playoff Bracket</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; }
            .bracket-container { max-width: 1400px; margin: 0 auto; }
            .bracket-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 30px 0; }
            .bracket-round { padding: 15px; background: #f5f5f5; border-radius: 8px; }
            .bracket-round h3 { margin-top: 0; color: #333; }
            .series-card {
                background: white;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 12px;
                margin: 10px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }
            .series-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }
            .series-header strong { flex: 1; }
            .series-format {
                font-size: 0.85em;
                background: #e3f2fd;
                color: #1565c0;
                padding: 2px 8px;
                border-radius: 12px;
                white-space: nowrap;
            }
            .team-row {
                padding: 8px;
                margin: 4px 0;
                border-radius: 4px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .team-row.higher-seed { background: #e8f4f8; }
            .team-row.lower-seed { background: #f8e8e8; }
            .win-pct {
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 3px;
                background: white;
            }
            .prob-high { background: #c8e6c9; color: #1b5e20; }
            .prob-med { background: #fff9c4; color: #f57f17; }
            .prob-low { background: #ffccbc; color: #bf360c; }
            .champion-section {
                margin: 40px 0;
                background: #f0f4f8;
                padding: 20px;
                border-radius: 8px;
            }
            .champion-list { list-style: none; padding: 0; }
            .champion-item {
                padding: 10px;
                margin: 5px 0;
                background: white;
                border-radius: 4px;
                display: flex;
                justify-content: space-between;
            }
            .loading { color: #666; text-align: center; padding: 40px; }
            .error { color: #d32f2f; background: #ffebee; padding: 15px; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="bracket-container">
            <h1>🏒 AHL Playoff Bracket Predictions</h1>
            <div id="projected-banner" style="display:none; background:#fff3cd; border:1px solid #ffc107; padding:12px; border-radius:4px; margin-bottom:20px; color:#856404;">
                <strong>📊 Projected Bracket</strong> — Based on current regular season standings (updates daily as season progresses)
            </div>
            <div id="content" class="loading">Loading bracket data...</div>
        </div>

        <script>
            async function loadBracket() {
                try {
                    const response = await fetch('/playoffs/data');
                    const data = await response.json();

                    if (data.error) {
                        document.getElementById('content').innerHTML =
                            '<div class="error">' + data.error + '</div>';
                        return;
                    }

                    // Show projected bracket banner if applicable
                    if (data.is_projected) {
                        document.getElementById('projected-banner').style.display = 'block';
                    }

                    let html = '<div class="bracket-grid">';

                    // Group series by round
                    const byRound = {};
                    for (const series of data.series) {
                        if (!byRound[series.round_number]) {
                            byRound[series.round_number] = [];
                        }
                        byRound[series.round_number].push(series);
                    }

                    // Render rounds
                    for (const round of Object.keys(byRound).sort()) {
                        html += '<div class="bracket-round">';
                        html += '<h3>Round ' + round + '</h3>';

                        for (const series of byRound[round]) {
                            html += '<div class="series-card">';
                            html += '<div class="series-header">';
                            html += '<strong>' + series.series_label + '</strong>';
                            html += '<span class="series-format">Best of ' + series.max_games + '</span>';
                            html += '</div>';

                            if (series.higher_seed_team_id) {
                                const h_pct = series.prediction ? Math.round(series.prediction.home_series_win_pct) : null;
                                const probClass = h_pct && h_pct >= 70 ? 'prob-high' : (h_pct && h_pct >= 40 ? 'prob-med' : (h_pct ? 'prob-low' : null));

                                html += '<div class="team-row higher-seed">';
                                html += '<span>' + (data.team_names[series.higher_seed_team_id] || 'Team ' + series.higher_seed_team_id) + '</span>';
                                if (h_pct !== null) {
                                    html += '<span class="win-pct ' + probClass + '">' + h_pct + '%</span>';
                                }
                                html += '</div>';
                            } else {
                                html += '<div class="team-row higher-seed"><span style="color: #999;">TBD</span></div>';
                            }

                            if (series.lower_seed_team_id) {
                                const l_pct = series.prediction ? Math.round(series.prediction.away_series_win_pct) : null;
                                const probClass = l_pct && l_pct >= 70 ? 'prob-high' : (l_pct && l_pct >= 40 ? 'prob-med' : (l_pct ? 'prob-low' : null));

                                html += '<div class="team-row lower-seed">';
                                html += '<span>' + (data.team_names[series.lower_seed_team_id] || 'Team ' + series.lower_seed_team_id) + '</span>';
                                if (l_pct !== null) {
                                    html += '<span class="win-pct ' + probClass + '">' + l_pct + '%</span>';
                                }
                                html += '</div>';
                            } else {
                                html += '<div class="team-row lower-seed"><span style="color: #999;">TBD</span></div>';
                            }

                            html += '</div>';
                        }
                        html += '</div>';
                    }
                    html += '</div>';

                    // Add champion probabilities
                    if (data.champion_probs && Object.keys(data.champion_probs).length > 0) {
                        html += '<div class="champion-section">';
                        html += '<h2>🏆 Calder Cup Winner Probability</h2>';
                        html += '<ul class="champion-list">';

                        const sorted = Object.entries(data.champion_probs)
                            .sort((a, b) => b[1] - a[1])
                            .slice(0, 10);

                        for (const [team_id, pct] of sorted) {
                            const team_name = data.team_names[team_id] || 'Team ' + team_id;
                            html += '<li class="champion-item">';
                            html += '<span>' + team_name + '</span>';
                            html += '<strong>' + Math.round(pct * 10) / 10 + '%</strong>';
                            html += '</li>';
                        }
                        html += '</ul>';
                        html += '</div>';
                    }

                    document.getElementById('content').innerHTML = html;
                } catch (error) {
                    document.getElementById('content').innerHTML =
                        '<div class="error">Error loading bracket: ' + error.message + '</div>';
                }
            }

            loadBracket();
        </script>
    </body>
    </html>
    """
    return Response.html(html)


async def playoffs_data_api(request, datasette):
    """API endpoint returning playoff bracket data as JSON.

    Returns the most recent playoff bracket with full bracket projection filled in.
    Prioritizes actual playoffs over projections. Projections use playoff_season_id=999.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get the latest playoff season - prefer projections (999) first, then actual playoffs
        cursor.execute(
            """
            SELECT playoff_season_id
            FROM playoff_brackets
            ORDER BY
              CASE WHEN playoff_season_id = 999 THEN 0 ELSE 1 END ASC,
              playoff_season_id DESC
            LIMIT 1
            """
        )
        season_row = cursor.fetchone()
        playoff_season_id = season_row[0] if season_row else 999

        is_projected = playoff_season_id == 999

        # Get all bracket series
        cursor.execute(
            """
            SELECT
                pb.series_id,
                pb.round_number,
                pb.series_label,
                pb.higher_seed_team_id,
                pb.lower_seed_team_id,
                t1.name as higher_team_name,
                t2.name as lower_team_name
            FROM playoff_brackets pb
            LEFT JOIN team t1 ON pb.higher_seed_team_id = t1.team_id
            LEFT JOIN team t2 ON pb.lower_seed_team_id = t2.team_id
            WHERE pb.playoff_season_id = ?
            ORDER BY pb.round_number, pb.series_label
            """,
            [playoff_season_id],
        )

        all_series = cursor.fetchall()
        series_list = []
        team_names = {}

        # Build maps for quick lookup
        series_by_id = {}  # series_id -> row
        series_predictions = {}  # series_id -> prediction
        expected_winners = {}  # series_id -> team_id

        # Use separate cursor for lookups to avoid state issues
        lookup_cursor = conn.cursor()

        for row in all_series:
            series_by_id[row["series_id"]] = row

            # Get latest prediction for this series
            lookup_cursor.execute(
                """
                SELECT home_series_win_pct, away_series_win_pct, expected_games
                FROM playoff_series_predictions
                WHERE series_id = ?
                ORDER BY snapshot_date DESC
                LIMIT 1
                """,
                [row["series_id"]],
            )
            pred_row = lookup_cursor.fetchone()
            if pred_row:
                series_predictions[row["series_id"]] = {
                    "home_series_win_pct": pred_row[0],
                    "away_series_win_pct": pred_row[1],
                    "expected_games": pred_row[2],
                }

                # Determine expected winner (higher seed if > 50% chance)
                if row["higher_seed_team_id"] and pred_row[0] > 50:
                    expected_winners[row["series_id"]] = row["higher_seed_team_id"]
                elif row["lower_seed_team_id"]:
                    expected_winners[row["series_id"]] = row["lower_seed_team_id"]

        # Get series relationship information to fill TBD slots
        lookup_cursor.execute(
            """
            SELECT series_id, source_series_a_id, source_series_b_id
            FROM playoff_brackets
            WHERE playoff_season_id = ?
            """,
            [playoff_season_id],
        )
        series_sources = {}  # series_id -> (source_a_id, source_b_id)
        for series_id, source_a, source_b in lookup_cursor.fetchall():
            series_sources[series_id] = (source_a, source_b)

        # Build series list with TBD slots filled with expected winners
        for row in all_series:
            series_id = row["series_id"]
            source_a, source_b = series_sources.get(series_id, (None, None))

            # Determine actual teams to display
            higher_team_id = row["higher_seed_team_id"]
            lower_team_id = row["lower_seed_team_id"]
            higher_team_name = row["higher_team_name"]
            lower_team_name = row["lower_team_name"]

            # Fill TBD slots with expected winners from source series
            if not higher_team_id and source_a and source_a in expected_winners:
                higher_team_id = expected_winners[source_a]
                lookup_cursor.execute(
                    "SELECT name FROM team WHERE team_id = ?",
                    [higher_team_id],
                )
                name_row = lookup_cursor.fetchone()
                higher_team_name = name_row[0] if name_row else f"Team {higher_team_id}"

            if not lower_team_id and source_b and source_b in expected_winners:
                lower_team_id = expected_winners[source_b]
                lookup_cursor.execute(
                    "SELECT name FROM team WHERE team_id = ?",
                    [lower_team_id],
                )
                name_row = lookup_cursor.fetchone()
                lower_team_name = name_row[0] if name_row else f"Team {lower_team_id}"

            # Determine max games for this series based on round
            round_num = row["round_number"]
            if round_num == 1:
                max_games = 3
            elif round_num in (2, 3):
                max_games = 5
            else:  # Conference finals and beyond
                max_games = 7

            prediction = series_predictions.get(series_id)

            series_list.append(
                {
                    "series_id": series_id,
                    "round_number": row["round_number"],
                    "series_label": row["series_label"],
                    "higher_seed_team_id": higher_team_id,
                    "lower_seed_team_id": lower_team_id,
                    "prediction": prediction,
                    "max_games": max_games,
                    "is_tbd": not (
                        row["higher_seed_team_id"] or row["lower_seed_team_id"]
                    ),
                }
            )

            # Track team names
            if higher_team_id:
                team_names[higher_team_id] = higher_team_name
            if lower_team_id:
                team_names[lower_team_id] = lower_team_name

        # Compute champion probabilities (simplified)
        champion_probs = {}
        lookup_cursor.execute(
            """
            SELECT away_team_id, AVG(away_series_win_pct) as avg_pct
            FROM playoff_series_predictions psp
            JOIN playoff_brackets pb ON psp.series_id = pb.series_id
            WHERE pb.round_number >= 4
            GROUP BY away_team_id
            """
        )

        for row in lookup_cursor.fetchall():
            champion_probs[row["away_team_id"]] = row["avg_pct"] / 100.0

        lookup_cursor.close()
        conn.close()

        return Response.json(
            {
                "series": series_list,
                "team_names": team_names,
                "champion_probs": champion_probs,
                "is_projected": is_projected,
                "playoff_season_id": playoff_season_id,
            }
        )

    except Exception as e:
        return Response.json({"error": str(e)}, status=500)
