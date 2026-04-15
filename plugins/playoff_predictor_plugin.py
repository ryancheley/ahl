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
        (r"^/playoffs/dates$", playoffs_dates_api),
    ]


async def playoffs_view(request, datasette):
    """Render main playoff bracket page using template."""
    return Response.html(await datasette.render_template("playoffs.html", {}))


async def playoffs_data_api(request, datasette):
    """API endpoint returning playoff bracket data as JSON.

    Returns the most recent playoff bracket with full bracket projection filled in.
    Prioritizes actual playoffs over projections. Projections use playoff_season_id=999.
    Supports ?date=YYYY-MM-DD to get historical snapshots.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get requested date from query params (default to today or latest snapshot)
        requested_date = None
        if hasattr(request, "query_string") and request.query_string:
            # Parse query string manually
            query_str = (
                request.query_string
                if isinstance(request.query_string, str)
                else request.query_string.decode()
            )
            for param in query_str.split("&"):
                if param.startswith("date="):
                    requested_date = param.split("=", 1)[1]
                    break

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

        # Check if we should load from snapshot
        use_snapshot = False
        champion_probs = {}
        if requested_date:
            cursor.execute(
                "SELECT bracket_json, champion_probs_json FROM playoff_prediction_snapshots WHERE playoff_season_id = ? AND snapshot_date = ? LIMIT 1",
                [playoff_season_id, requested_date],
            )
            snapshot_row = cursor.fetchone()
            if snapshot_row:
                use_snapshot = True
                import json

                # Load snapshot data
                snapshot_bracket = json.loads(snapshot_row[0])
                champion_probs = json.loads(snapshot_row[1])

        is_projected = playoff_season_id == 999

        # If loading from snapshot, build response from snapshot data
        if use_snapshot:
            # Build series list from snapshot bracket data
            series_list = []
            team_names = {}

            # Convert snapshot data back to series format
            for bracket_item in snapshot_bracket:
                series_id = bracket_item.get("series_id")

                # Get team names
                cursor.execute(
                    "SELECT name FROM team WHERE team_id = ?",
                    [bracket_item.get("higher_id")],
                )
                higher_name_row = cursor.fetchone()
                higher_name = (
                    higher_name_row[0]
                    if higher_name_row
                    else f"Team {bracket_item.get('higher_id')}"
                )

                if bracket_item.get("higher_id"):
                    team_names[bracket_item.get("higher_id")] = higher_name

                cursor.execute(
                    "SELECT name FROM team WHERE team_id = ?",
                    [bracket_item.get("lower_id")],
                )
                lower_name_row = cursor.fetchone()
                lower_name = (
                    lower_name_row[0]
                    if lower_name_row
                    else f"Team {bracket_item.get('lower_id')}"
                )

                if bracket_item.get("lower_id"):
                    team_names[bracket_item.get("lower_id")] = lower_name

                # Get prediction for this series if available
                prediction = None
                if bracket_item.get("higher_pct") is not None:
                    # Probabilities in snapshot are stored as percentages (0-100)
                    prediction = {
                        "home_series_win_pct": bracket_item.get("higher_pct", 50),
                        "away_series_win_pct": bracket_item.get("lower_pct", 50),
                        "expected_games": bracket_item.get("expected_games"),
                        "games_dist": bracket_item.get("games_dist"),
                    }

                # Determine max games
                round_num = bracket_item.get("round", 1)
                if round_num == 1:
                    max_games = 3
                elif round_num in (2, 3):
                    max_games = 5
                else:
                    max_games = 7

                series_list.append(
                    {
                        "series_id": series_id,
                        "round_number": bracket_item.get("round"),
                        "series_label": bracket_item.get("label"),
                        "higher_seed_team_id": bracket_item.get("higher_id"),
                        "lower_seed_team_id": bracket_item.get("lower_id"),
                        "prediction": prediction,
                        "max_games": max_games,
                        "is_tbd": False,
                    }
                )

            conn.close()
            return Response.json(
                {
                    "series": series_list,
                    "team_names": team_names,
                    "champion_probs": champion_probs,
                    "is_projected": is_projected,
                    "playoff_season_id": playoff_season_id,
                    "snapshot_date": requested_date,
                }
            )

        # Get all bracket series (current data, not snapshot)
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
                SELECT home_series_win_pct, away_series_win_pct, expected_games, games_dist_json
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
                    "games_dist": pred_row[3],  # JSON string
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

        # Compute champion probabilities by tracing each team's bracket path
        # Only show if all 23 playoff teams can be calculated; otherwise show nothing
        # (6 Atlantic + 5 Central + 5 North + 7 Pacific = 23 teams)
        champion_probs = {}

        # Load all series into memory for fast lookups
        lookup_cursor.execute(
            """
            SELECT pb.series_id, pb.round_number, pb.series_label, pb.higher_seed_team_id, pb.lower_seed_team_id,
                   pb.source_series_a_id, pb.source_series_b_id,
                   psp.home_series_win_pct, psp.away_series_win_pct
            FROM playoff_brackets pb
            LEFT JOIN playoff_series_predictions psp ON pb.series_id = psp.series_id
            WHERE pb.playoff_season_id = ?
            ORDER BY pb.round_number
            """,
            [playoff_season_id],
        )

        series_by_id = {}
        series_by_round = {}  # round -> list of series

        for row in lookup_cursor.fetchall():
            series_id = row["series_id"]
            series_by_id[series_id] = {
                "round": row["round_number"],
                "label": row["series_label"],
                "higher_id": row["higher_seed_team_id"],
                "lower_id": row["lower_seed_team_id"],
                "source_a": row["source_series_a_id"],
                "source_b": row["source_series_b_id"],
                "higher_prob": (row["home_series_win_pct"] or 50.0) / 100.0,
                "lower_prob": (row["away_series_win_pct"] or 50.0) / 100.0,
            }
            if row["round_number"] not in series_by_round:
                series_by_round[row["round_number"]] = []
            series_by_round[row["round_number"]].append(series_id)

        # Get all playoff teams (from R1)
        all_teams = set()
        for series_id in series_by_round.get(1, []):
            series = series_by_id[series_id]
            if series["higher_id"]:
                all_teams.add(series["higher_id"])
            if series["lower_id"]:
                all_teams.add(series["lower_id"])

        # Also add R2 bye teams (those not in R1)
        for series_id in series_by_round.get(2, []):
            series = series_by_id[series_id]
            if series["higher_id"]:
                all_teams.add(series["higher_id"])
            if series["lower_id"]:
                all_teams.add(series["lower_id"])

        # Helper: find which series a team plays in during a given round
        def find_team_series_in_round(team_id, round_num):
            """Find the series_id where team_id plays in round_num."""
            for series_id in series_by_round.get(round_num, []):
                series = series_by_id[series_id]
                if team_id == series["higher_id"] or team_id == series["lower_id"]:
                    return series_id

            return None

        # Trace championship path for each team
        for team_id in sorted(all_teams):
            prob = 1.0

            # Find starting round (R1 or R2 if bye)
            current_round = 1
            if not find_team_series_in_round(team_id, 1):
                current_round = 2

            # Trace through each round from current_round to Cup Final
            for round_num in range(current_round, 6):
                series_id = find_team_series_in_round(team_id, round_num)
                if not series_id:
                    prob = None
                    break

                series = series_by_id[series_id]

                # Multiply by win probability based on seed
                if team_id == series["higher_id"]:
                    prob *= series["higher_prob"]
                elif team_id == series["lower_id"]:
                    prob *= series["lower_prob"]
                else:
                    # Team should be in this series
                    prob = None
                    break

            if prob is not None and prob > 0:
                champion_probs[team_id] = prob

        # Only display if we have all 23 playoff teams
        if len(champion_probs) != 23:
            champion_probs = {}

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


async def playoffs_dates_api(request, datasette):
    """API endpoint returning available snapshot dates for historical comparison."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get the latest playoff season
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

        # Get all available snapshot dates
        cursor.execute(
            """
            SELECT snapshot_date, snapshot_type, n_simulations, computed_at
            FROM playoff_prediction_snapshots
            WHERE playoff_season_id = ?
            ORDER BY snapshot_date DESC
            """,
            [playoff_season_id],
        )

        dates = []
        for row in cursor.fetchall():
            dates.append(
                {
                    "date": row["snapshot_date"],
                    "type": row["snapshot_type"],
                    "simulations": row["n_simulations"],
                    "computed_at": row["computed_at"],
                }
            )

        conn.close()
        return Response.json(
            {
                "dates": dates,
                "playoff_season_id": playoff_season_id,
            }
        )

    except Exception as e:
        return Response.json({"error": str(e)}, status=500)
