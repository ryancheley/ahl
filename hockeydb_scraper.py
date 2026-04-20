"""
HockeyDB Franchise Scraper

Scrapes historical franchise data from HockeyDB.com (league 112, AHL) and populates
the franchise and franchise_history tables in my_database.db.

Each franchise represents a lineage (e.g., Maine Mariners → ... → Calgary Wranglers),
and each franchise_history entry captures one era (city, name, years active).
"""

import re
import sqlite3
import sys
import time
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, model_validator
from rich.console import Console

sys.path.insert(0, "/Users/ryan/Documents/github/ahl")
from program import get_db_connection

console = Console()

# Constants
HOCKEYDB_BASE = "https://www.hockeydb.com"
LEAGUE_112_URL = "https://www.hockeydb.com/ihdb/stats/leagues/112.html"
HTTP_TIMEOUT = 10
REQUEST_DELAY = 0.5  # seconds between requests


# ============================================================================
# Pydantic Models
# ============================================================================


class FranchiseHistoryEntry(BaseModel):
    """One era in a franchise's history."""

    name: str  # full team name, e.g. "Maine Mariners"
    city: str  # city portion, e.g. "Maine"
    nickname: str  # nickname portion, e.g. "Mariners"
    team_code: str  # 2-4 uppercase letters
    active: bool  # True only if this era is still current
    start_year: int
    end_year: Optional[int]  # None = currently active
    matched_team_id: Optional[int] = None  # FK to team table; None if no match found

    @model_validator(mode="after")
    def check_years(self) -> "FranchiseHistoryEntry":
        """Validate year ordering."""
        if self.end_year is not None and self.end_year < self.start_year:
            raise ValueError(
                f"end_year ({self.end_year}) must be >= start_year ({self.start_year})"
            )
        if self.start_year < 1900:
            raise ValueError(f"start_year ({self.start_year}) must be >= 1900")
        return self

    @model_validator(mode="after")
    def check_team_code(self) -> "FranchiseHistoryEntry":
        """Validate team_code format: 2-4 uppercase letters."""
        if not (2 <= len(self.team_code) <= 4):
            raise ValueError(f"team_code must be 2-4 chars, got '{self.team_code}'")
        if not self.team_code.isupper() or not self.team_code.isalpha():
            raise ValueError(
                f"team_code must be uppercase letters only, got '{self.team_code}'"
            )
        return self


class Franchise(BaseModel):
    """Top-level franchise entity."""

    hockeydb_id: int  # numeric ID from URL, e.g. 6716
    hockeydb_url: str  # full URL on hockeydb.com, e.g. /stte/maine-mariners-6716.html
    current_name: str  # most recent team name
    history: list[FranchiseHistoryEntry]

    @model_validator(mode="after")
    def history_not_empty(self) -> "Franchise":
        """Ensure at least one history entry."""
        if not self.history:
            raise ValueError("Franchise must have at least one history entry")
        return self


# ============================================================================
# Helper Functions
# ============================================================================


def parse_team_name(full_name: str) -> tuple[str, str]:
    """
    Split a full team name into (city, nickname).

    Examples:
        "Maine Mariners" → ("Maine", "Mariners")
        "Quad City Flames" → ("Quad City", "Flames")
        "Saint John Flames" → ("Saint John", "Flames")
        "Wilkes-Barre/Scranton Penguins" → ("Wilkes-Barre/Scranton", "Penguins")
    """
    full_name = full_name.strip()
    parts = full_name.split()

    if len(parts) == 1:
        # Single word: use it as both city and nickname
        return full_name, full_name

    # Last word is nickname, everything before is city
    nickname = parts[-1]
    city = " ".join(parts[:-1])

    return city, nickname


def generate_team_code(city: str) -> str:
    """
    Generate a team code from city name.

    Examples:
        "Maine" → "MAI"
        "Grand Rapids" → "GR"
        "Wilkes-Barre/Scranton" → "WBS"
        "Quad City" → "QC"
    """
    city = city.strip()

    # Split on spaces, slashes, and hyphens
    parts = re.split(r"[\s/\-]+", city)
    parts = [p for p in parts if p]  # remove empty strings

    if len(parts) == 1:
        # Single word: first 3 letters
        return city[:3].upper()
    else:
        # Multi-word: take first letter of each word
        code = "".join(p[0].upper() for p in parts if p)
        return code


def find_matching_team(
    conn: sqlite3.Connection, name: str, city: str, nickname: str
) -> tuple[Optional[int], Optional[str]]:
    """
    Find a matching team in the team table.

    Returns (team_id, team_code) if found, else (None, None).

    Match strategy (in order):
      1. Exact match on team.name
      2. Match on team.city AND team.nickname
      3. Match on team.nickname in team.name
    """
    cursor = conn.cursor()

    # Strategy 1: exact name match
    cursor.execute("SELECT team_id, team_code FROM team WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        return row[0], row[1]

    # Strategy 2: city + nickname match
    cursor.execute(
        "SELECT team_id, team_code FROM team WHERE city = ? AND nickname = ?",
        (city, nickname),
    )
    row = cursor.fetchone()
    if row:
        return row[0], row[1]

    # Strategy 3: nickname in name (partial match)
    cursor.execute(
        "SELECT team_id, team_code FROM team WHERE name LIKE ?",
        (f"%{nickname}%",),
    )
    row = cursor.fetchone()
    if row:
        # Verify city is in the team name
        cursor.execute("SELECT name FROM team WHERE team_id = ?", (row[0],))
        actual_row = cursor.fetchone()
        if actual_row and city.lower() in actual_row[0].lower():
            return row[0], row[1]

    return None, None


def fetch_franchise_urls() -> list[str]:
    """
    Fetch league 112 page and extract all franchise URLs from cities divs.

    Returns list of full URLs.
    """
    console.print(f"[cyan]Fetching league 112 page: {LEAGUE_112_URL}[/cyan]")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    resp = httpx.get(LEAGUE_112_URL, timeout=HTTP_TIMEOUT, headers=headers)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Find all divs with class "cities"
    cities_divs = soup.find_all("div", class_="cities")
    console.print(f"[cyan]Found {len(cities_divs)} cities divs[/cyan]")

    urls = []
    for div in cities_divs:
        links = div.find_all("a")
        for link in links:
            href = link.get("href")
            if href:
                full_url = HOCKEYDB_BASE + href if href.startswith("/") else href
                urls.append(full_url)

    console.print(f"[cyan]Extracted {len(urls)} franchise URLs[/cyan]")
    return urls


def parse_franchise_page(url: str, conn: sqlite3.Connection) -> Optional[Franchise]:
    """
    Fetch a franchise page and parse its Franchise History section.

    Returns Franchise object if valid, else None.
    """
    try:
        time.sleep(REQUEST_DELAY)  # Be courteous to HockeyDB
        console.print(f"[dim]Scraping: {url}[/dim]")

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        resp = httpx.get(url, timeout=HTTP_TIMEOUT, headers=headers)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract hockeydb_id from URL
        match = re.search(r"(\d+)\.html$", url)
        if not match:
            console.print(f"[yellow]Could not extract ID from {url}[/yellow]")
            return None
        hockeydb_id = int(match.group(1))

        # Find the "Franchise History" div with class "team_header"
        franchise_header = None
        for div in soup.find_all("div", class_="team_header"):
            if "Franchise History" in div.get_text():
                franchise_header = div
                break

        if not franchise_header:
            console.print(
                f"[yellow]No Franchise History section found in {url}[/yellow]"
            )
            return None

        # Collect all cellpad divs that follow until we hit another section
        # (identified by another team_header div or similar)
        cellpad_divs = []
        sibling = franchise_header.find_next_sibling("div")
        while sibling:
            if sibling.get("class") and "team_header" in sibling.get("class"):
                # Hit another section, stop
                break
            if sibling.get("class") and "cellpad" in sibling.get("class"):
                cellpad_divs.append(sibling)
            elif "cellpad" in str(sibling.get("class", [])):
                cellpad_divs.append(sibling)
            sibling = sibling.find_next_sibling("div")

        if not cellpad_divs:
            console.print(
                f"[yellow]No franchise history entries found in {url}[/yellow]"
            )
            return None

        # Parse history entries
        # Format: "Team Name (YYYY-YYYY)" or "Team Name (YYYY-present)"
        history_entries = []
        current_year = 2026  # Update if needed

        for cellpad in cellpad_divs:
            text = cellpad.get_text()

            # Skip "Expansion franchise..." etc.
            if "(" not in text or "-" not in text:
                continue

            # Find the <a> tag (team name)
            link = cellpad.find("a")
            if link:
                team_name = link.get_text().strip()
            else:
                # For current team (wrapped in <b>), extract from text
                # Format: "» Team Name «"
                team_match = re.search(r"»\s*(.+?)\s*«", text)
                if team_match:
                    team_name = team_match.group(1).strip()
                else:
                    # Fall back to text before the year
                    team_match = re.search(r"^(.+?)\s*\(", text)
                    if team_match:
                        team_name = team_match.group(1).strip()
                    else:
                        continue

            # Extract years from text like "(1977-1987)" or "(2022-present)" or "(2022-2026)"
            year_match = re.search(r"\((\d{4})-(\d{4}|present)\)", text)
            if not year_match:
                continue

            start_year = int(year_match.group(1))
            end_year_str = year_match.group(2)

            # If marked as "present" or is the current year, it's active with no end_year
            if end_year_str == "present":
                end_year = None
                active = True
            else:
                end_year_int = int(end_year_str)
                if end_year_int == current_year:
                    # Current year means still active, so no end_year
                    end_year = None
                    active = True
                else:
                    end_year = end_year_int
                    active = False

            # Parse city and nickname
            city, nickname = parse_team_name(team_name)

            # Find matching team or generate code
            matched_team_id, matched_code = find_matching_team(
                conn, team_name, city, nickname
            )
            if matched_code:
                team_code = matched_code
                console.print(
                    f"  ✓ Matched: {team_name} → {team_code} (team_id={matched_team_id})"
                )
            else:
                team_code = generate_team_code(city)
                console.print(f"  • Generated: {team_name} → {team_code}")

            # Create history entry
            try:
                entry = FranchiseHistoryEntry(
                    name=team_name,
                    city=city,
                    nickname=nickname,
                    team_code=team_code,
                    active=active,
                    start_year=start_year,
                    end_year=end_year,
                    matched_team_id=matched_team_id,
                )
                history_entries.append(entry)
            except Exception as e:
                console.print(f"[yellow]Validation error for {team_name}: {e}[/yellow]")
                continue

        if not history_entries:
            console.print(f"[yellow]No history entries parsed from {url}[/yellow]")
            return None

        # Get current name from most recent entry
        current_name = history_entries[-1].name

        # Create Franchise
        try:
            franchise = Franchise(
                hockeydb_id=hockeydb_id,
                hockeydb_url=url,
                current_name=current_name,
                history=history_entries,
            )
            return franchise
        except Exception as e:
            console.print(f"[red]Franchise validation error for {url}: {e}[/red]")
            return None

    except Exception as e:
        console.print(f"[red]Error scraping {url}: {e}[/red]")
        return None


def init_franchise_tables(conn: sqlite3.Connection) -> None:
    """Create franchise and franchise_history tables if they don't exist."""
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS franchise (
            franchise_id INTEGER PRIMARY KEY AUTOINCREMENT,
            hockeydb_id INTEGER UNIQUE NOT NULL,
            hockeydb_url TEXT NOT NULL,
            current_name TEXT NOT NULL
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS franchise_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            franchise_id INTEGER NOT NULL REFERENCES franchise(franchise_id),
            team_id INTEGER REFERENCES team(team_id),
            team_code TEXT NOT NULL,
            active BOOLEAN NOT NULL,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            nickname TEXT NOT NULL,
            start_year INTEGER NOT NULL,
            end_year INTEGER
        )
    """
    )

    conn.commit()
    console.print("[green]✓ Franchise tables initialized[/green]")


def save_franchise(conn: sqlite3.Connection, franchise: Franchise) -> None:
    """Save franchise and its history entries to the database."""
    cursor = conn.cursor()

    # Check if franchise already exists
    cursor.execute(
        "SELECT franchise_id FROM franchise WHERE hockeydb_id = ?",
        (franchise.hockeydb_id,),
    )
    existing = cursor.fetchone()

    if existing:
        # Franchise already exists, skip to avoid duplicates
        franchise_id = existing[0]
        console.print("[dim]  (already in database, skipping history entries)[/dim]")
        return

    # INSERT franchise (or ignore if hockeydb_id already exists)
    cursor.execute(
        """
        INSERT OR IGNORE INTO franchise (hockeydb_id, hockeydb_url, current_name)
        VALUES (?, ?, ?)
    """,
        (franchise.hockeydb_id, franchise.hockeydb_url, franchise.current_name),
    )

    # Retrieve franchise_id (either just inserted or already existing)
    cursor.execute(
        "SELECT franchise_id FROM franchise WHERE hockeydb_id = ?",
        (franchise.hockeydb_id,),
    )
    row = cursor.fetchone()
    if not row:
        console.print(
            f"[red]Failed to retrieve franchise_id for hockeydb_id={franchise.hockeydb_id}[/red]"
        )
        return

    franchise_id = row[0]

    # INSERT history entries
    for entry in franchise.history:
        cursor.execute(
            """
            INSERT OR IGNORE INTO franchise_history
            (franchise_id, team_id, team_code, active, name, city, nickname, start_year, end_year)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                franchise_id,
                entry.matched_team_id,
                entry.team_code,
                entry.active,
                entry.name,
                entry.city,
                entry.nickname,
                entry.start_year,
                entry.end_year,
            ),
        )

    conn.commit()


def scrape_all_franchises() -> None:
    """Orchestrator: scrape all franchises from league 112."""
    conn = get_db_connection()

    try:
        # Initialize tables
        init_franchise_tables(conn)

        # Fetch all franchise URLs
        urls = fetch_franchise_urls()
        if not urls:
            console.print("[yellow]No franchise URLs found[/yellow]")
            return

        # Scrape each franchise
        total_parsed = 0
        total_matched = 0
        total_history_entries = 0

        for i, url in enumerate(urls, 1):
            console.print(f"\n[cyan]{i}/{len(urls)}[/cyan]")
            franchise = parse_franchise_page(url, conn)

            if franchise:
                save_franchise(conn, franchise)
                total_parsed += 1
                total_history_entries += len(franchise.history)
                total_matched += sum(1 for e in franchise.history if e.matched_team_id)

        # Print summary
        console.print("\n" + "=" * 60)
        console.print("[green]✓ Scraping complete[/green]")
        console.print(f"  Total franchises parsed: {total_parsed}/{len(urls)}")
        console.print(f"  Total history entries: {total_history_entries}")
        console.print(f"  Matched to existing teams: {total_matched}")
        console.print(f"  Generated codes: {total_history_entries - total_matched}")

    finally:
        conn.close()


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    scrape_all_franchises()
