def get_enabled_cities(registry):
    """Return names of cities explicitly enabled in the registry."""
    return [
        entry["city"] for entry in registry["cities"] if entry.get("enabled", False)
    ]
