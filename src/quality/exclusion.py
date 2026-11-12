from src.quality.record_validation import validate_listing


def get_exclusion_reason(listing, rules):
    errors = validate_listing(listing, rules)
    return '; '.join(errors) if errors else None