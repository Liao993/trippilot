from src.ingestion.silver import clean_price, is_rejected_listing


def test_clean_price_parses_currency_string():
    assert clean_price("$1,234.00") == 1234.0


def test_clean_price_returns_none_for_empty_value():
    assert clean_price("") is None


def test_clean_price_returns_none_for_invalid_value():
    assert clean_price("not-a-price") is None


def test_listing_without_usable_id_is_rejected():
    assert is_rejected_listing(None) is True
    assert is_rejected_listing("") is True
    assert is_rejected_listing("   ") is True


def test_listing_with_id_is_not_rejected():
    assert is_rejected_listing("12345") is False


def test_missing_price_does_not_reject_listing():
    # Documents the revised Silver contract: a valid ID is enough
    # for a listing to remain in Silver.
    assert is_rejected_listing("12345") is False