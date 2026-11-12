import sys
from pathlib import Path

start = Path.cwd().resolve()
ROOT = next(
    (p for p in [start, *start.parents]
     if (p / 'src').is_dir() and (p / 'config/project.yml').is_file()),
    None,
)
if ROOT is None:
    raise RuntimeError('Cannot locate repository root. Open this notebook inside the Databricks Git folder.')
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
print('Repository root:', ROOT)


from src.common.city_registry import get_enabled_cities


def test_returns_only_enabled_cities():
    registry = {
        "cities": [
            {"city": "Toronto", "enabled": True},
            {"city": "Vancouver", "enabled": False},
            {"city": "Montreal", "enabled": True},
        ]
    }

    assert get_enabled_cities(registry) == ["Toronto", "Montreal"]


def test_missing_enabled_flag_means_disabled():
    registry = {
        "cities": [
            {"city": "Toronto"},
        ]
    }

    assert get_enabled_cities(registry) == []


def test_empty_registry_returns_empty_list():
    registry = {"cities": []}

    assert get_enabled_cities(registry) == []
