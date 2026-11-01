from src.city_registry import get_enabled_cities


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
