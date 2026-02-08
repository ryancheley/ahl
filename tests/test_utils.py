from datetime import datetime
from unittest.mock import Mock
import pytest
import requests

from program import (
    get_game_details,
    get_attendance,
    get_date,
    get_game_status,
    get_home_team_score,
    get_away_team_score,
    get_home_team,
    get_away_team,
    get_team,
)
from .parameters import (
    RESPONSE_TEXT,
    RESPONSE_GAME_NOT_PLAYED_TEXT,
    RESPONSE_NOT_YET_AVAILABLE_TEXT,
    RESPONSE,
    RESPONSE_GAME_NOT_PLAYED,
    RESPONSE_NOT_YET_AVAILABLE,
    home_team,
    away_team,
    home_score,
    away_score,
    game_status,
)


def test_get_home_team():
    actual = get_home_team(RESPONSE_TEXT)
    expected = home_team
    assert actual == expected


def test_get_away_team():
    actual = get_away_team(RESPONSE_TEXT)
    expected = away_team
    assert actual == expected


def test_get_home_team_score():
    actual = get_home_team_score(RESPONSE_TEXT)
    expected = home_score
    assert actual == expected


def test_get_away_team_score():
    actual = get_away_team_score(RESPONSE_TEXT)
    expected = away_score
    assert actual == expected


def test_get_game_status():
    actual = get_game_status(RESPONSE_TEXT)
    expected = game_status
    assert actual == expected


def test_get_date():
    actual = get_date(RESPONSE_TEXT)
    expected = datetime(2023, 5, 13, 0, 0)
    assert actual == expected


def test_get_attendance():
    actual = get_attendance(RESPONSE_TEXT)
    expected = 6212
    assert actual == expected


@pytest.mark.parametrize(
    "response_text,expected",
    [
        (RESPONSE, RESPONSE_TEXT),
        (RESPONSE_GAME_NOT_PLAYED, RESPONSE_GAME_NOT_PLAYED_TEXT),
        (RESPONSE_NOT_YET_AVAILABLE, RESPONSE_NOT_YET_AVAILABLE_TEXT),
    ],
)
def test_get_game_details(response_text, expected):
    response = Mock(spec=requests.Response)
    response.status_code = 200
    response.text = response_text
    actual = get_game_details(response)
    assert actual == expected


@pytest.mark.parametrize(
    "team_type,expected",
    [
        ("home", home_team),
        ("away", away_team),
    ],
)
def test_get_team(team_type, expected):
    actual = get_team(RESPONSE_TEXT, team_type)
    assert actual == expected
