import pytest
from tennis.models import players

@pytest.fixture(autouse=True)
def clear_players():
    players.clear()
    yield
    players.clear()
