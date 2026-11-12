def contract_error_count(df, rules):
    from pyspark.sql import functions as F

    required = set(rules.get('required_columns', []))
    required.update(rules.get('rules', {}).keys())
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f'Missing contract columns: {sorted(missing)}')
    invalid = F.lit(False)
    for name, rule in rules.get('rules', {}).items():
        c = F.col(name)
        blank = c.isNull() | (F.trim(c.cast('string')) == '')
        if rule.get('required'):
            invalid = invalid | blank
        if 'allowed_values' in rule:
            invalid = invalid | (~blank & ~c.isin(rule['allowed_values']))
        kind = rule.get('type')
        if kind in {'decimal', 'double', 'float'}:
            n = F.expr(f'try_cast(`{name}` AS DOUBLE)')
            bad = n.isNull() | F.isnan(n) | (F.abs(n) == F.lit(float('inf')))
            if 'minimum' in rule:
                bad = bad | (n < F.lit(rule['minimum']))
            if 'maximum' in rule:
                bad = bad | (n > F.lit(rule['maximum']))
            invalid = invalid | (~blank & bad)
        elif kind == 'date':
            invalid = invalid | (~blank & F.expr(f'try_cast(`{name}` AS DATE)').isNull())
        elif kind not in {None, 'string'}:
            raise ValueError(f'Unsupported contract type: {kind}')
    return df.filter(F.coalesce(invalid, F.lit(False))).count()