"""
Enhanced game scraper for handling different hockey game types.

Supports:
- Regular season games
- Post-season games
- All-star games
- Games with varying overtime periods (1-8+)
- Games with shootouts
- Detailed parsing of goals, penalties, referees, and linespersons
- HTML official game report parsing
"""

import re
import yaml
import sqlite3
import time
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from program import (
    get_game_details,
    get_away_team,
    get_home_team,
    get_away_team_score,
    get_home_team_score,
    get_date,
    get_attendance,
    get_shots_on_goal,
)


class GameType(Enum):
    """Enumeration of different hockey game types."""
    REGULAR = "regular"
    POST_SEASON = "post"
    ALL_STAR = "all-star"


class GameFormat(Enum):
    """Enumeration of game formats (regulation, overtime, shootout)."""
    REGULATION = "regulation"
    OVERTIME = "overtime"
    SHOOTOUT = "shootout"


@dataclass
class Goal:
    """Container for goal information."""
    goal_number: int
    player_name: str
    player_number: int
    team: str
    assists: List[str]
    time: str
    period: int
    power_play: bool = False
    empty_net: bool = False
    short_handed: bool = False

    def __str__(self) -> str:
        return f"Goal {self.goal_number}: {self.player_name} #{self.player_number} ({self.team}) at {self.time} in {self.period} period"


@dataclass
class Penalty:
    """Container for penalty information."""
    player_name: str
    team: str
    penalty_type: str
    time: str
    period: int
    duration_minutes: int = 2  # Default to 2 minutes

    def __str__(self) -> str:
        return f"{self.player_name} ({self.team}) - {self.penalty_type} at {self.time} in {self.period} period"


@dataclass
class Official:
    """Container for official information."""
    name: str
    number: int

    def __str__(self) -> str:
        return f"{self.name} ({self.number})"


@dataclass
class GameInfo:
    """Container for game information extracted from game report."""
    game_id: int
    game_type: GameType
    game_format: GameFormat
    away_team: str
    home_team: str
    away_score: int
    home_score: int
    game_status: str
    game_date: str
    attendance: int
    home_shots: int
    away_shots: int
    overtime_periods: int = 0
    decided_by_shootout: bool = False
    referees: List[Official] = field(default_factory=list)
    linespersons: List[Official] = field(default_factory=list)
    goals: List[Goal] = field(default_factory=list)
    penalties: List[Penalty] = field(default_factory=list)


def load_game_examples(yaml_path: str = "game_examples.yaml") -> Dict:
    """
    Load game examples from YAML file.

    Args:
        yaml_path: Path to the game_examples.yaml file

    Returns:
        Dictionary with game type keys containing game format URLs
    """
    try:
        with open(yaml_path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: {yaml_path} not found")
        return {}


def detect_overtime_periods(game_status: str) -> int:
    """
    Detect the number of overtime periods from game status string.

    Handles formats like:
    - "Final" (0 OT periods)
    - "Final/OT" (1 OT period)
    - "Final/2OT" (2 OT periods)
    - "Final/3OT" (3 OT periods)
    - etc.

    Args:
        game_status: The game status string from the report

    Returns:
        Number of overtime periods (0 for regulation)
    """
    if "OT" not in game_status:
        return 0

    match = re.search(r"(\d+)OT", game_status)
    if match:
        return int(match.group(1))
    elif "OT" in game_status:
        return 1

    return 0


def detect_shootout(game_status: str) -> bool:
    """
    Detect if a game was decided by shootout.

    Args:
        game_status: The game status string from the report

    Returns:
        True if game was decided by shootout, False otherwise
    """
    return "SO" in game_status or "shootout" in game_status.lower()


def determine_game_format(game_status: str) -> GameFormat:
    """
    Determine the game format (regulation, overtime, or shootout).

    Args:
        game_status: The game status string from the report

    Returns:
        GameFormat enum value
    """
    if detect_shootout(game_status):
        return GameFormat.SHOOTOUT
    elif detect_overtime_periods(game_status) > 0:
        return GameFormat.OVERTIME
    else:
        return GameFormat.REGULATION


def parse_officials(detail_line: str) -> List[Official]:
    """
    Parse officials (referees or linespersons) from a detail line.

    Expected format: "Referees-Name1 (123), Name2 (456)."
                     "Linesmen-Name1 (123), Name2 (456)."

    Args:
        detail_line: The detail line containing official information

    Returns:
        List of Official objects
    """
    officials = []

    if "-" not in detail_line:
        return officials

    officials_str = detail_line.split("-", 1)[1].strip().rstrip(".")

    for official_entry in officials_str.split(","):
        official_entry = official_entry.strip()

        match = re.match(r"^(.+?)\s+\((\d+)\)$", official_entry)
        if match:
            name = match.group(1).strip()
            number = int(match.group(2))
            officials.append(Official(name=name, number=number))

    return officials


def parse_goals_and_penalties_from_periods(game_details: List[str]) -> Tuple[List[Goal], List[Penalty]]:
    """
    Parse goals and penalties from period detail lines.

    Period lines contain goals and penalties mixed together.
    Example: "1st Period-1, Rochester, Kulich 5 (Jobst, Prow), 9:57 (PP). Penalties-Shaw Tor (tripping), 8:00; ..."

    Args:
        game_details: List of game detail strings

    Returns:
        Tuple of (goals list, penalties list)
    """
    goals = []
    penalties = []

    period = 0

    for detail in game_details:
        detail = detail.strip()

        period_match = re.match(r"^(\d+)(?:st|nd|rd|th)\s+Period", detail)
        if period_match:
            period = int(period_match.group(1))

        if "Period-" not in detail:
            continue

        period_str, rest = detail.split("Period-", 1)

        period_match = re.match(r"^(\d+)(?:st|nd|rd|th)$", period_str)
        if period_match:
            period = int(period_match.group(1))

        goals_section, _, penalties_section = rest.partition("Penalties-")

        goals.extend(parse_goals_from_section(goals_section, period))
        penalties.extend(parse_penalties_from_section(penalties_section, period))

    return goals, penalties


def parse_goals_from_section(goals_section: str, period: int) -> List[Goal]:
    """
    Parse goals from a period's goals section.

    Expected format: "1, Rochester, Kulich 5 (Jobst, Prow), 9:57 (PP). 2, Toronto, ..."

    Args:
        goals_section: The section containing goals
        period: The period number

    Returns:
        List of Goal objects
    """
    goals = []

    if not goals_section.strip():
        return goals

    goal_pattern = r"(\d+),\s+(\w+),\s+(\w+)\s+(\d+)\s+\(([^)]*)\),\s+(\d+:\d+)\s*((?:\([^)]*\))*)"

    for match in re.finditer(goal_pattern, goals_section):
        goal_number = int(match.group(1))
        team = match.group(2)
        player_name = match.group(3)
        player_number = int(match.group(4))
        assists_str = match.group(5)
        time = match.group(6)
        flags = match.group(7)

        assists = [a.strip() for a in assists_str.split(",") if a.strip()]

        power_play = "(PP)" in flags
        empty_net = "(EN)" in flags
        short_handed = "(SH)" in flags

        goal = Goal(
            goal_number=goal_number,
            player_name=player_name,
            player_number=player_number,
            team=team,
            assists=assists,
            time=time,
            period=period,
            power_play=power_play,
            empty_net=empty_net,
            short_handed=short_handed,
        )
        goals.append(goal)

    return goals


def parse_penalties_from_section(penalties_section: str, period: int) -> List[Penalty]:
    """
    Parse penalties from a period's penalties section.

    Expected format: "Shaw Tor (tripping), 8:00; Clifford Tor (roughing), 15:09; ..."

    Args:
        penalties_section: The section containing penalties
        period: The period number

    Returns:
        List of Penalty objects
    """
    penalties = []

    if not penalties_section.strip():
        return penalties

    penalty_section = penalties_section.split(".")[0]

    penalty_pattern = r"(\w+)\s+(\w+)\s+\(([^)]+)\),\s+(\d+:\d+)"

    for match in re.finditer(penalty_pattern, penalty_section):
        player_name = match.group(1)
        team_abbrev = match.group(2)
        penalty_type = match.group(3)
        time = match.group(4)

        penalty = Penalty(
            player_name=player_name,
            team=team_abbrev,
            penalty_type=penalty_type,
            time=time,
            period=period,
        )
        penalties.append(penalty)

    return penalties


def parse_html_game_report(html_content: str) -> Optional[Dict]:
    """
    Parse an official game report HTML document.

    Args:
        html_content: The HTML content of the official game report

    Returns:
        Dictionary with extracted game data or None if parsing fails
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        game_data = {}

        # Extract game header information
        game_data["teams"] = extract_teams_from_html(soup)
        game_data["scores"] = extract_scores_from_html(soup)
        game_data["officials"] = extract_officials_from_html(soup)
        game_data["goals"] = extract_goals_from_html(soup)
        game_data["penalties"] = extract_penalties_from_html(soup)
        game_data["game_info"] = extract_game_info_from_html(soup)

        return game_data

    except Exception as e:
        print(f"Error parsing HTML game report: {e}")
        return None


def extract_teams_from_html(soup: BeautifulSoup) -> Dict:
    """Extract team information from HTML."""
    teams = {"away": None, "home": None}

    all_text = soup.get_text()

    # Look for pattern like "Team1 at Team2" in the text
    match = re.search(r"Gamesheet:\s*(\w+[\w\s]*?)\s+at\s+(\w+[\w\s]*?)\s*-", all_text)
    if match:
        teams["away"] = match.group(1).strip()
        teams["home"] = match.group(2).strip()
        return teams

    # Fallback: Look for score line like "Team1 # at Team2 #"
    score_match = re.search(r"(\w+[\w\s]*?)\s+\d+\s+at\s+(\w+[\w\s]*?)\s+\d+", all_text)
    if score_match:
        teams["away"] = score_match.group(1).strip()
        teams["home"] = score_match.group(2).strip()

    return teams


def extract_scores_from_html(soup: BeautifulSoup) -> Dict:
    """Extract score information from HTML."""
    scores = {"away": 0, "home": 0}

    all_text = soup.get_text()

    # Look for pattern like "Team1 # at Team2 #"
    match = re.search(r"(\w+[\w\s]*?)\s+(\d+)\s+at\s+(\w+[\w\s]*?)\s+(\d+)", all_text)
    if match:
        scores["away"] = int(match.group(2))
        scores["home"] = int(match.group(4))

    return scores


def extract_officials_from_html(soup: BeautifulSoup) -> Dict[str, List[Official]]:
    """Extract referees and linespersons from HTML."""
    officials = {"referees": [], "linespersons": []}

    all_text = soup.get_text()

    # Extract referees - format: "Referee:Name1 (Number1)Name2 (Number2)"
    # Look for content between "Referee:" and the next newline (or end of string)
    ref_match = re.search(r"Referee\s*:(.+?)(?=\n|$)", all_text, re.IGNORECASE | re.DOTALL)
    if ref_match:
        ref_text = ref_match.group(1).strip()
        # Remove trailing linesperson info if present on same line (shouldn't happen but just in case)
        ref_text = re.sub(r"(?i)linesperson.*", "", ref_text).strip()
        officials["referees"] = parse_officials_from_text(ref_text)

    # Extract linespersons - format: "linespersons: Name1 (Number1)Name2 (Number2)"
    line_match = re.search(r"linesperson[s]?\s*:(.+?)(?=\n|$)", all_text, re.IGNORECASE)
    if line_match:
        line_text = line_match.group(1).strip()
        officials["linespersons"] = parse_officials_from_text(line_text)

    return officials


def parse_officials_from_text(text: str) -> List[Official]:
    """
    Parse officials from text format like "Mike Sullivan (47)Jordan Samuels-Thomas (42)".

    Args:
        text: Text containing official names and numbers

    Returns:
        List of Official objects
    """
    officials = []

    # Pattern: Match official names and numbers
    # Name can contain letters, spaces, hyphens, and periods
    # followed by (number)
    pattern = r"([A-Za-z\.\s\-]+?)\s*\((\d+)\)"

    for match in re.finditer(pattern, text):
        name = match.group(1).strip()
        number = int(match.group(2))

        if name:  # Only add if we have a name
            officials.append(Official(name=name, number=number))

    return officials


def extract_goals_from_html(soup: BeautifulSoup) -> List[Goal]:
    """Extract goal information from HTML tables (Goals table)."""
    goals = []

    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")

        # Check for goals table - looks for "V-H", "Per", "Goals", "Assists" headers
        if len(rows) > 0:
            header_text = rows[0].get_text(strip=True)
            if "V-H" in header_text and "Per" in header_text and "Goals" in header_text and "Assists" in header_text:

                # Found the goals table
                for row in rows[1:]:  # Skip header row
                    cells = row.find_all(["td", "th"])

                    if len(cells) >= 7:  # V-H, #, Per, Team, Time, Goals, Assists
                        try:
                            goal_num_text = cells[1].get_text(strip=True)
                            period_text = cells[2].get_text(strip=True)
                            team_text = cells[3].get_text(strip=True)
                            time_text = cells[4].get_text(strip=True)
                            goals_text = cells[5].get_text(strip=True)
                            assists_text = cells[6].get_text(strip=True) if len(cells) > 6 else ""

                            # Extract period number
                            if not period_text or not goal_num_text:
                                continue

                            period_match = re.search(r"(\d+)(?:st|nd|rd|th)", period_text)
                            period = int(period_match.group(1)) if period_match else 0

                            if not period or not goals_text:
                                continue

                            # Parse goal: "J. Hayden (1)" -> name, number
                            goal_match = re.match(r"([A-Za-z\.\s]+)\s+\((\d+)\)", goals_text)
                            if goal_match:
                                player_name = goal_match.group(1).strip()
                                player_number = int(goal_match.group(2))

                                # Parse assists
                                assists = []
                                if assists_text:
                                    assists = [a.strip() for a in assists_text.split(",")]

                                # Check for special circumstances
                                power_play = "(PP)" in goals_text or cells[7].get_text() == "PP" if len(cells) > 7 else False
                                empty_net = "(EN)" in goals_text
                                short_handed = "(SH)" in goals_text

                                goal = Goal(
                                    goal_number=int(goal_num_text),
                                    player_name=player_name,
                                    player_number=player_number,
                                    team=team_text,
                                    assists=assists,
                                    time=time_text,
                                    period=period,
                                    power_play=power_play,
                                    empty_net=empty_net,
                                    short_handed=short_handed,
                                )
                                goals.append(goal)
                        except Exception:
                            continue

                break  # Found and processed goals table

    return goals


def parse_goal_from_row(cells: List, period: int) -> Optional[Goal]:
    """Parse a single goal from an HTML table row."""
    try:
        row_text = "".join([cell.get_text(strip=True) for cell in cells])

        # Extract goal information using regex
        # Expected patterns vary by site, but generally: Player# (Assist1, Assist2) Time

        # Try to extract player name and number
        player_match = re.search(r"(\w+)\s+(\d+)", row_text)
        if not player_match:
            return None

        player_name = player_match.group(1)
        player_number = int(player_match.group(2))

        # Extract assists
        assists = []
        assists_match = re.search(r"\(([^)]+)\)", row_text)
        if assists_match:
            assists = [a.strip() for a in assists_match.group(1).split(",")]

        # Extract time
        time_match = re.search(r"(\d+:\d+)", row_text)
        time = time_match.group(1) if time_match else "0:00"

        # Extract team (look at earlier cells or context)
        team = "Unknown"

        # Check for special circumstances
        power_play = "(PP)" in row_text or "Power Play" in row_text
        empty_net = "(EN)" in row_text or "Empty" in row_text
        short_handed = "(SH)" in row_text or "Short" in row_text

        return Goal(
            goal_number=0,  # Will be set by caller
            player_name=player_name,
            player_number=player_number,
            team=team,
            assists=assists,
            time=time,
            period=period,
            power_play=power_play,
            empty_net=empty_net,
            short_handed=short_handed,
        )
    except Exception as e:
        return None


def extract_penalties_from_html(soup: BeautifulSoup) -> List[Penalty]:
    """Extract penalty information from HTML tables (Penalties table)."""
    penalties = []

    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")

        # Check for standalone penalties table
        # First row should be just "PENALTIES", second row should be column headers
        if len(rows) > 2:
            first_row_text = rows[0].get_text(strip=True)
            second_row_text = rows[1].get_text(strip=True)

            # Look for table that has "PENALTIES" as first row and column headers as second
            if first_row_text == "PENALTIES" and "Player" in second_row_text and "Offense" in second_row_text:

                # Found the penalties table
                for row in rows[2:]:  # Skip header rows (PENALTIES + column headers)
                    cells = row.find_all(["td", "th"])

                    if len(cells) >= 6:  # P, T, Player, M, Offense, Time
                        try:
                            period_text = cells[0].get_text(strip=True)
                            team_text = cells[1].get_text(strip=True)
                            player_text = cells[2].get_text(strip=True)
                            minutes_text = cells[3].get_text(strip=True)
                            offense_text = cells[4].get_text(strip=True)
                            time_text = cells[5].get_text(strip=True)

                            if not period_text or not player_text or not offense_text:
                                continue

                            # Extract period number from text like "1st", "2nd", "3rd", "OT"
                            period = 0
                            if "1st" in period_text:
                                period = 1
                            elif "2nd" in period_text:
                                period = 2
                            elif "3rd" in period_text:
                                period = 3
                            elif "OT" in period_text and "2OT" not in period_text and "3OT" not in period_text:
                                period = 4  # First OT
                            elif "2OT" in period_text:
                                period = 5  # Second OT
                            elif "3OT" in period_text:
                                period = 6  # Third OT

                            # Team abbreviation (V/H for visitor/home)
                            team_abbrev = team_text if team_text else "UNK"

                            # Extract duration in minutes
                            duration_minutes = 2  # Default
                            if minutes_text:
                                match = re.search(r"(\d+)", minutes_text)
                                if match:
                                    duration_minutes = int(match.group(1))

                            penalty = Penalty(
                                player_name=player_text,
                                team=team_abbrev,
                                penalty_type=offense_text,
                                time=time_text,
                                period=period,
                                duration_minutes=duration_minutes,
                            )
                            penalties.append(penalty)
                        except Exception:
                            continue

                break  # Found and processed penalties table

    return penalties


def parse_penalty_from_row(cells: List, period: int) -> Optional[Penalty]:
    """Parse a single penalty from an HTML table row."""
    try:
        row_text = "".join([cell.get_text(strip=True) for cell in cells])

        # Extract player name (first column usually)
        player_match = re.search(r"^(\w+)", row_text)
        if not player_match:
            return None

        player_name = player_match.group(1)

        # Extract team abbreviation
        team_match = re.search(r"(\w{2,3})\s+\(", row_text)
        team = team_match.group(1) if team_match else "Unknown"

        # Extract penalty type
        penalty_match = re.search(r"\(([^)]+)\)", row_text)
        penalty_type = penalty_match.group(1) if penalty_match else "Unknown"

        # Extract time
        time_match = re.search(r"(\d+:\d+)", row_text)
        time = time_match.group(1) if time_match else "0:00"

        return Penalty(
            player_name=player_name,
            team=team,
            penalty_type=penalty_type,
            time=time,
            period=period,
        )
    except Exception as e:
        return None


def extract_game_info_from_html(soup: BeautifulSoup) -> Dict:
    """Extract general game information from HTML."""
    info = {
        "date": None,
        "attendance": 0,
        "status": "Final",
        "away_shots": 0,
        "home_shots": 0,
    }

    all_text = soup.get_text()
    status = "Final"
    lines = all_text.split("\n")

    # Look for SCORING section to detect OT/SO
    # SCORING section has period headers: 1, 2, 3, [OT], T
    for i, line in enumerate(lines):
        if line.strip() == "SCORING":
            # Check lines after SCORING header for period columns
            has_ot = False
            has_so = False

            for j in range(i + 1, min(i + 10, len(lines))):
                next_line = lines[j].strip()
                if next_line == "OT":
                    has_ot = True
                elif next_line == "SO":
                    has_so = True
                elif next_line == "T":  # Total column, end of period headers
                    break
                elif next_line == "SHOOTOUT":
                    has_so = True

            # Build status string (SO takes priority)
            if has_so:
                status = "Final/SO"
            elif has_ot:
                status = "Final/OT"

            info["status"] = status
            break

    # Extract date - look for "Apr 22, 2025" or similar patterns
    date_match = re.search(r"(\w+\s+\d{1,2},?\s+\d{4})", all_text)
    if date_match:
        try:
            info["date"] = datetime.strptime(date_match.group(1), "%b %d, %Y")
        except:
            try:
                info["date"] = datetime.strptime(date_match.group(1), "%B %d, %Y")
            except:
                pass

    # Extract attendance - look for "Attendance: 4330" or similar
    attendance_match = re.search(r"Attendance[:\s]+(\d+(?:,\d+)*)", all_text)
    if attendance_match:
        info["attendance"] = int(attendance_match.group(1).replace(",", ""))

    # Extract shots on goal from SHOTS section
    # Pattern: SHOTS header -> column headers -> empty line -> team1 name -> period shots (8 lines) -> total -> empty line -> team2 data
    try:
        lines = all_text.split("\n")

        shots_index = -1
        for i, line in enumerate(lines):
            if line.strip() == "SHOTS":
                shots_index = i
                break

        if shots_index >= 0:
            # After SHOTS header (line 0), column headers (lines 1-8), empty line (9),
            # team name (10), period shots (lines 11-17), total (line 18)
            # Repeat for second team

            away_total_idx = shots_index + 17  # Approximate position of first team's total
            home_total_idx = away_total_idx + 9  # Approximate position of second team's total

            # Search for the actual lines with 2+ digit numbers that could be totals
            totals = []
            for i in range(shots_index + 10, min(shots_index + 50, len(lines))):
                line = lines[i].strip()
                # Look for 2-3 digit numbers that stand alone (likely totals)
                if line.isdigit() and 20 <= int(line) < 60:  # Reasonable shot count range
                    totals.append(int(line))
                    if len(totals) == 2:
                        break

            if len(totals) == 2:
                info["away_shots"] = totals[0]
                info["home_shots"] = totals[1]
    except Exception:
        pass  # If parsing fails, keep default values

    return info


def parse_penalties_from_section(penalties_section: str, period: int) -> List[Penalty]:
    """
    Parse penalties from a period's penalties section.

    Expected format: "Shaw Tor (tripping), 8:00; Clifford Tor (roughing), 15:09; ..."

    Args:
        penalties_section: The section containing penalties
        period: The period number

    Returns:
        List of Penalty objects
    """
    penalties = []

    if not penalties_section.strip():
        return penalties

    penalty_section = penalties_section.split(".")[0]

    penalty_pattern = r"(\w+)\s+(\w+)\s+\(([^)]+)\),\s+(\d+:\d+)"

    for match in re.finditer(penalty_pattern, penalty_section):
        player_name = match.group(1)
        team_abbrev = match.group(2)
        penalty_type = match.group(3)
        time = match.group(4)

        penalty = Penalty(
            player_name=player_name,
            team=team_abbrev,
            penalty_type=penalty_type,
            time=time,
            period=period,
        )
        penalties.append(penalty)

    return penalties


def extract_game_info(
    game_id: int,
    game_type: GameType,
    game_details: List[str]
) -> Optional[GameInfo]:
    """
    Extract game information from parsed game details.

    Args:
        game_id: The ID of the game
        game_type: The type of game (regular, post-season, all-star)
        game_details: List of game detail strings from program.get_game_details()

    Returns:
        GameInfo object if successful, None if extraction fails
    """
    try:
        away_team = get_away_team(game_details)
        home_team = get_home_team(game_details)
        away_score = int(get_away_team_score(game_details))
        home_score = int(get_home_team_score(game_details))
        game_status = game_details[0].split(" - Status: ")[1]
        game_date = str(get_date(game_details))
        attendance = get_attendance(game_details)
        home_shots = int(get_shots_on_goal(game_details, "home"))
        away_shots = int(get_shots_on_goal(game_details, "away"))

        overtime_periods = detect_overtime_periods(game_status)
        decided_by_shootout = detect_shootout(game_status)
        game_format = determine_game_format(game_status)

        referees = []
        linespersons = []
        for detail in game_details:
            if detail.startswith("Referees-"):
                referees = parse_officials(detail)
            elif detail.startswith("Linesmen-") or detail.startswith("Linesman-"):
                linespersons = parse_officials(detail)

        goals, penalties = parse_goals_and_penalties_from_periods(game_details)

        return GameInfo(
            game_id=game_id,
            game_type=game_type,
            game_format=game_format,
            away_team=away_team,
            home_team=home_team,
            away_score=away_score,
            home_score=home_score,
            game_status=game_status,
            game_date=game_date,
            attendance=attendance,
            home_shots=home_shots,
            away_shots=away_shots,
            overtime_periods=overtime_periods,
            decided_by_shootout=decided_by_shootout,
            referees=referees,
            linespersons=linespersons,
            goals=goals,
            penalties=penalties,
        )
    except (IndexError, ValueError, AttributeError) as e:
        print(f"Error extracting game info for game {game_id}: {e}")
        return None


def scrape_game_from_url(game_id: int, url: str, game_type: GameType) -> Optional[GameInfo]:
    """
    Scrape a game from a given URL (supports both text and HTML formats).

    Args:
        game_id: The ID of the game
        url: The URL to scrape
        game_type: The type of game (regular, post-season, all-star)

    Returns:
        GameInfo object if successful, None otherwise
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Detect if this is an official game report (HTML) or text report
        if "official-game-report" in url:
            return scrape_official_game_report(game_id, url, game_type, response)
        else:
            # Fallback to text report parsing
            game_details = get_game_details(response)

            if not game_details or game_details == ['{"error": "No such game"}']:
                print(f"Game {game_id} not found or no data available")
                return None

            if game_details == ["This game is not available."]:
                print(f"Game {game_id} is scheduled but not yet played")
                return None

            return extract_game_info(game_id, game_type, game_details)

    except requests.RequestException as e:
        print(f"Error fetching game {game_id}: {e}")
        return None


def scrape_official_game_report(
    game_id: int, url: str, game_type: GameType, response: requests.Response
) -> Optional[GameInfo]:
    """
    Scrape game information from an official game report HTML page.

    Args:
        game_id: The ID of the game
        url: The URL being scraped
        game_type: The type of game
        response: The HTTP response object

    Returns:
        GameInfo object if successful, None otherwise
    """
    try:
        html_data = parse_html_game_report(response.text)

        if not html_data:
            print(f"Could not parse game {game_id}")
            return None

        teams = html_data.get("teams", {})
        scores = html_data.get("scores", {})
        officials = html_data.get("officials", {})
        goals = html_data.get("goals", [])
        penalties = html_data.get("penalties", [])
        game_info = html_data.get("game_info", {})

        away_team = teams.get("away", "Unknown")
        home_team = teams.get("home", "Unknown")
        away_score = scores.get("away", 0)
        home_score = scores.get("home", 0)

        # Get game status from HTML (e.g., "Final", "Final/OT", "Final/OT/SO")
        game_status = game_info.get("status", "Final")

        # Determine overtime periods and shootout from game status
        decided_by_shootout = "SO" in game_status

        # Determine number of overtime periods:
        # 1. Check if status indicates OT
        # 2. Fall back to checking max goal period
        overtime_periods = 0
        if "OT" in game_status:
            # Status indicates at least 1 OT period
            overtime_periods = 1
            # If there are goals in period > 3, count them to get exact OT count
            if goals:
                max_period = max((goal.period for goal in goals), default=3)
                if max_period > 3:
                    overtime_periods = max_period - 3
        elif goals:
            # Fallback: check if goals went to overtime
            max_period = max(goal.period for goal in goals)
            if max_period > 3:
                overtime_periods = max_period - 3

        game_format = determine_game_format(game_status)

        return GameInfo(
            game_id=game_id,
            game_type=game_type,
            game_format=game_format,
            away_team=away_team,
            home_team=home_team,
            away_score=away_score,
            home_score=home_score,
            game_status=game_status,
            game_date=str(game_info.get("date", "")),
            attendance=game_info.get("attendance", 0),
            home_shots=game_info.get("home_shots", 0),
            away_shots=game_info.get("away_shots", 0),
            overtime_periods=overtime_periods,
            decided_by_shootout=decided_by_shootout,
            referees=officials.get("referees", []),
            linespersons=officials.get("linespersons", []),
            goals=goals,
            penalties=penalties,
        )

    except Exception as e:
        print(f"Error scraping official game report for game {game_id}: {e}")
        return None


def write_game_to_database(game_info: GameInfo, db_path: str = "games.db") -> bool:
    """
    Write game information to the database, including goals and penalties.

    Args:
        game_info: GameInfo object to write
        db_path: Path to the database file (default: games.db)

    Returns:
        True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create games_extended table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS games_extended (
                game_id TEXT PRIMARY KEY,
                game_type TEXT,
                game_format TEXT,
                away_team TEXT,
                home_team TEXT,
                away_score INTEGER,
                home_score INTEGER,
                game_status TEXT,
                game_date TEXT,
                attendance INTEGER,
                home_shots INTEGER,
                away_shots INTEGER,
                overtime_periods INTEGER,
                decided_by_shootout INTEGER
            )
        """)

        cursor.execute("""
            INSERT OR REPLACE INTO games_extended
            (game_id, game_type, game_format, away_team, home_team, away_score,
             home_score, game_status, game_date, attendance, home_shots,
             away_shots, overtime_periods, decided_by_shootout)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game_info.game_id,
            game_info.game_type.value,
            game_info.game_format.value,
            game_info.away_team,
            game_info.home_team,
            game_info.away_score,
            game_info.home_score,
            game_info.game_status,
            game_info.game_date,
            game_info.attendance,
            game_info.home_shots,
            game_info.away_shots,
            game_info.overtime_periods,
            int(game_info.decided_by_shootout),
        ))

        # Create and populate goals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT,
                goal_number INTEGER,
                player_name TEXT,
                player_number INTEGER,
                team TEXT,
                assists TEXT,
                time TEXT,
                period INTEGER,
                power_play INTEGER,
                empty_net INTEGER,
                short_handed INTEGER,
                FOREIGN KEY(game_id) REFERENCES games_extended(game_id)
            )
        """)

        cursor.execute("DELETE FROM goals WHERE game_id = ?", (game_info.game_id,))

        for goal in game_info.goals:
            cursor.execute("""
                INSERT INTO goals
                (game_id, goal_number, player_name, player_number, team, assists,
                 time, period, power_play, empty_net, short_handed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                game_info.game_id,
                goal.goal_number,
                goal.player_name,
                goal.player_number,
                goal.team,
                ",".join(goal.assists),
                goal.time,
                goal.period,
                int(goal.power_play),
                int(goal.empty_net),
                int(goal.short_handed),
            ))

        # Create and populate penalties table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS penalties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT,
                player_name TEXT,
                team TEXT,
                penalty_type TEXT,
                time TEXT,
                period INTEGER,
                duration_minutes INTEGER,
                FOREIGN KEY(game_id) REFERENCES games_extended(game_id)
            )
        """)

        cursor.execute("DELETE FROM penalties WHERE game_id = ?", (game_info.game_id,))

        for penalty in game_info.penalties:
            cursor.execute("""
                INSERT INTO penalties
                (game_id, player_name, team, penalty_type, time, period, duration_minutes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                game_info.game_id,
                penalty.player_name,
                penalty.team,
                penalty.penalty_type,
                penalty.time,
                penalty.period,
                penalty.duration_minutes,
            ))

        # Create and populate officials table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS officials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT,
                official_type TEXT,
                name TEXT,
                number INTEGER,
                FOREIGN KEY(game_id) REFERENCES games_extended(game_id)
            )
        """)

        cursor.execute("DELETE FROM officials WHERE game_id = ?", (game_info.game_id,))

        for referee in game_info.referees:
            cursor.execute("""
                INSERT INTO officials
                (game_id, official_type, name, number)
                VALUES (?, ?, ?, ?)
            """, (game_info.game_id, "referee", referee.name, referee.number))

        for linesperson in game_info.linespersons:
            cursor.execute("""
                INSERT INTO officials
                (game_id, official_type, name, number)
                VALUES (?, ?, ?, ?)
            """, (game_info.game_id, "linesperson", linesperson.name, linesperson.number))

        conn.commit()
        conn.close()
        print(f"✓ Wrote game {game_info.game_id} with {len(game_info.goals)} goals and {len(game_info.penalties)} penalties")
        return True

    except sqlite3.Error as e:
        print(f"Database error for game {game_info.game_id}: {e}")
        return False


def game_exists_in_database(game_id: int, db_path: str = "games.db") -> bool:
    """
    Check if a game already exists in the database.

    Args:
        game_id: The game ID to check
        db_path: Path to the database file

    Returns:
        True if game exists, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM games_extended WHERE game_id = ? LIMIT 1", (game_id,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except sqlite3.Error:
        return False


def scrape_game_id_range(
    start_game_id: int,
    num_games: int = 50,
    db_path: str = "games.db",
    delay: float = 1.0
) -> List[GameInfo]:
    """
    Scrape a range of game IDs sequentially.

    Args:
        start_game_id: Starting game ID
        num_games: Number of games to scrape
        db_path: Path to the database file
        delay: Delay in seconds between requests

    Returns:
        List of GameInfo objects for successful scrapes
    """
    results = []
    base_url = "https://lscluster.hockeytech.com/game_reports/official-game-report.php?client_code=ahl&game_id={}&lang_id=1"

    for i in range(num_games):
        game_id = start_game_id + i
        url = base_url.format(game_id)

        print(f"[{i+1}/{num_games}] Scraping game {game_id}...", end=" ")

        # Skip games that are already in the database
        if game_exists_in_database(game_id, db_path):
            print("↻ Already in database")
            time.sleep(delay)
            continue

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Detect game type (simplified - assume REGULAR by default)
            game_type = GameType.REGULAR

            if "official-game-report" in url:
                game_info = scrape_official_game_report(game_id, url, game_type, response)
            else:
                game_details = get_game_details(response)
                game_info = extract_game_info(game_id, game_type, game_details)

            if game_info:
                # Skip games that haven't been played yet (both teams would be None)
                if game_info.away_team is None or game_info.home_team is None:
                    print("⊘ Game not yet played")
                else:
                    results.append(game_info)
                    write_game_to_database(game_info, db_path)
                    print(f"✓ {game_info.away_team} vs {game_info.home_team}")
            else:
                print("✗ No data")

        except requests.exceptions.RequestException as e:
            print(f"✗ Error: {e}")

        time.sleep(delay)

    # Filter for Coachella Valley games
    cv_games = [g for g in results if 'Coachella' in g.away_team or 'Coachella' in g.home_team]

    if cv_games:
        print(f"\n✓ Found {len(cv_games)} Coachella Valley games in this batch:")
        for game in cv_games:
            print(f"  - Game {game.game_id}: {game.away_team} vs {game.home_team} ({game.away_score}-{game.home_score})")

    return results


def scrape_examples_from_yaml(
    yaml_path: str = "game_examples.yaml",
    game_id_base: int = 1000000,
    db_path: str = "games.db"
) -> List[GameInfo]:
    """
    Scrape all game examples from the YAML file.

    Args:
        yaml_path: Path to the game_examples.yaml file
        game_id_base: Base game ID to use for examples (incremented for each game)
        db_path: Path to the database file

    Returns:
        List of GameInfo objects for successful scrapes
    """
    examples = load_game_examples(yaml_path)
    results = []

    if not examples:
        return results

    for game_type_name, formats in examples.items():
        try:
            game_type = GameType(game_type_name)
        except ValueError:
            print(f"Unknown game type: {game_type_name}")
            continue

        for format_name, url in formats.items():
            if not isinstance(url, str):
                continue

            game_id = game_id_base
            game_id_base += 1

            print(f"Scraping {game_type_name}.{format_name} from {url}")

            game_info = scrape_game_from_url(game_id, url, game_type)

            if game_info:
                results.append(game_info)
                write_game_to_database(game_info, db_path)

            time.sleep(1)

    return results


def print_game_summary(game_info: GameInfo) -> None:
    """
    Print a comprehensive summary of game information.

    Args:
        game_info: GameInfo object to print
    """
    print(f"\n{'='*70}")
    print(f"Game ID: {game_info.game_id}")
    print(f"Type: {game_info.game_type.value.upper()} | Format: {game_info.game_format.value.upper()}")
    if game_info.overtime_periods > 0:
        print(f"Overtime Periods: {game_info.overtime_periods}")
    if game_info.decided_by_shootout:
        print(f"Decided by: Shootout")

    print(f"\n{game_info.away_team} ({game_info.away_shots} shots) vs {game_info.home_team} ({game_info.home_shots} shots)")
    print(f"Final Score: {game_info.away_score} - {game_info.home_score}")
    print(f"Date: {game_info.game_date} | Attendance: {game_info.attendance:,}")

    if game_info.referees:
        refs = ", ".join(str(r) for r in game_info.referees)
        print(f"\nReferees: {refs}")

    if game_info.linespersons:
        lines = ", ".join(str(l) for l in game_info.linespersons)
        print(f"Linespersons: {lines}")

    if game_info.goals:
        print(f"\nGoals ({len(game_info.goals)} total):")
        for goal in game_info.goals:
            special_flags = []
            if goal.power_play:
                special_flags.append("PP")
            if goal.empty_net:
                special_flags.append("EN")
            if goal.short_handed:
                special_flags.append("SH")
            flag_str = f" ({', '.join(special_flags)})" if special_flags else ""

            assists_str = f" (Assists: {', '.join(goal.assists)})" if goal.assists else ""
            print(f"  {goal.goal_number}. {goal.player_name} #{goal.player_number} ({goal.team}) at {goal.time} in {goal.period} period{assists_str}{flag_str}")

    if game_info.penalties:
        print(f"\nPenalties ({len(game_info.penalties)} total):")
        for penalty in game_info.penalties:
            print(f"  {penalty.player_name} ({penalty.team}): {penalty.penalty_type} at {penalty.time} in {penalty.period} period")

    print(f"{'='*70}")


if __name__ == "__main__":
    games = scrape_examples_from_yaml()

    print(f"\n\nSuccessfully scraped {len(games)} games")
    for game in games:
        print_game_summary(game)
