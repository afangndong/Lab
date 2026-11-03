import pytest

import netmodel


@pytest.fixture
def data():
    """Echte Standortdaten aus data/sites.yml, bei jedem Test frisch geladen."""
    return netmodel.load()