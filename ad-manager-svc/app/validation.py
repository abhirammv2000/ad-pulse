"""Checks the JSON fields of ads and campaigns before they are stored.

Postgres checks the columns it has a type for. The JSONB columns (bid, budget,
ad units, targeting, frequency caps) take any JSON at all, and ad-server-svc
decodes them into typed Go structs. A value of the wrong type there makes the ad
server skip the ad without telling anyone. So these fields are checked here, and
a wrong one is a 400 that names it.

Only the key names the ad server reads are accepted, so a misspelt key is refused
instead of being stored and ignored. A field that is missing or null is fine: the
ad server reads it as "not set".
"""

from decimal import Decimal

BID_TYPES = ('CPM', 'CPC')
CURRENCIES = ('USD',)
ENTITY_TYPES = ('AD', 'CAMPAIGN')
EVENT_TYPES = ('CSC', 'CLK')  # a render and a click, named like the engagement service's endpoints
WINDOW_SECONDS = {'MINUTE': 60, 'HOUR': 3600, 'DAY': 86400, 'WEEK': 604800}

# The ad server counts money in micros (a millionth of a unit) in an int64.
MAX_DECIMAL_PLACES = 6
MAX_AMOUNT = 1_000_000_000

# Each cap costs a Redis read on every ad request, and the ad server keeps one week of events per user.
MAX_FREQUENCY_CAPS = 5
MAX_CAP_WINDOW_SECONDS = WINDOW_SECONDS['WEEK']

# Days are 1 to 7 with Sunday as 1. Hours are 0 to 23, in UTC.
TARGETING_RANGES = {'dayTargeting': (1, 7), 'timeTargeting': (0, 23)}


class ValidationError(Exception):
    """One field of the request body is wrong. The API answers 400 and names the field."""

    def __init__(self, field, message):
        super().__init__(f'{field} {message}')
        self.field = field
        self.message = message


def validate_ad(body):
    """Raise ValidationError if a JSON field of an ad body is wrong."""
    _check_if_set(body, 'bidinfo', _check_bid_info)
    _check_if_set(body, 'budget', _check_budget)
    _check_if_set(body, 'ad_unit_targeted', _check_ad_units)
    _check_if_set(body, 'targetinginfo', _check_targeting)
    _check_if_set(body, 'frequencycaps', _check_frequency_caps)


def validate_campaign(body):
    """Raise ValidationError if a JSON field of a campaign body is wrong."""
    _check_if_set(body, 'budget', _check_budget)
    _check_if_set(body, 'frequencycaps', _check_frequency_caps)


def _check_if_set(body, field, check):
    value = body.get(field)
    if value is not None:
        check(value, field)


def _check_bid_info(value, field):
    _check_object(value, field, ('bid', 'bidType'), required=('bid', 'bidType'))
    _check_amount(value['bid'], f'{field}.bid')
    _check_choice(value['bidType'], f'{field}.bidType', BID_TYPES)


def _check_budget(value, field):
    _check_object(value, field, ('dailyBudget', 'totalBudget', 'currencyCode'))
    for key in ('dailyBudget', 'totalBudget'):
        if value.get(key) is not None:
            _check_amount(value[key], f'{field}.{key}')
    if value.get('currencyCode') is not None:
        _check_choice(value['currencyCode'], f'{field}.currencyCode', CURRENCIES)


def _check_ad_units(value, field):
    _check_list(value, field)
    for i, unit in enumerate(value):
        if not isinstance(unit, str) or not unit:
            raise ValidationError(f'{field}[{i}]', 'must be an ad unit id')


def _check_targeting(value, field):
    _check_object(value, field, tuple(TARGETING_RANGES))
    for key, (low, high) in TARGETING_RANGES.items():
        rule = value.get(key)
        if rule is None:
            continue
        rule_field = f'{field}.{key}'
        _check_object(rule, rule_field, ('type', 'values'))
        if rule.get('type') is not None and rule['type'] != 'equal':
            raise ValidationError(f'{rule_field}.type', 'must be "equal", the only rule the ad server applies')
        values = rule.get('values')
        if values is None:
            continue
        _check_list(values, f'{rule_field}.values')
        for i, number in enumerate(values):
            _check_whole_number(number, f'{rule_field}.values[{i}]', low, high)


def _check_frequency_caps(value, field):
    _check_object(value, field, ('frequencyCapList',))
    caps = value.get('frequencyCapList')
    if caps is None:
        return
    list_field = f'{field}.frequencyCapList'
    _check_list(caps, list_field)
    if len(caps) > MAX_FREQUENCY_CAPS:
        raise ValidationError(list_field, f'can have at most {MAX_FREQUENCY_CAPS} caps')
    for i, cap in enumerate(caps):
        _check_frequency_cap(cap, f'{list_field}[{i}]')


def _check_frequency_cap(cap, field):
    keys = ('entityType', 'eventType', 'timeFrame', 'userCap')
    _check_object(cap, field, keys, required=keys)
    _check_choice(cap['entityType'], f'{field}.entityType', ENTITY_TYPES)
    _check_choice(cap['eventType'], f'{field}.eventType', EVENT_TYPES)
    if cap['userCap'] is not True:
        raise ValidationError(f'{field}.userCap', 'must be true, only caps per user are supported')

    frame_field = f'{field}.timeFrame'
    frame_keys = ('value', 'maxCount', 'timeWindowType')
    frame = cap['timeFrame']
    _check_object(frame, frame_field, frame_keys, required=frame_keys)
    _check_choice(frame['timeWindowType'], f'{frame_field}.timeWindowType', tuple(WINDOW_SECONDS))
    _check_whole_number(frame['maxCount'], f'{frame_field}.maxCount', 1)
    _check_whole_number(frame['value'], f'{frame_field}.value', 1)
    if frame['value'] * WINDOW_SECONDS[frame['timeWindowType']] > MAX_CAP_WINDOW_SECONDS:
        raise ValidationError(f'{frame_field}.value', 'makes the window longer than one week')


def _check_object(value, field, allowed, required=()):
    if not isinstance(value, dict):
        raise ValidationError(field, 'must be an object')
    for key in value:
        if key not in allowed:
            raise ValidationError(f'{field}.{key}', f"is not a known field, use one of: {', '.join(allowed)}")
    for key in required:
        if value.get(key) is None:
            raise ValidationError(f'{field}.{key}', 'is required')


def _check_list(value, field):
    if not isinstance(value, list):
        raise ValidationError(field, 'must be a list')


def _check_choice(value, field, choices):
    if not isinstance(value, str) or value not in choices:
        raise ValidationError(field, f"must be one of: {', '.join(choices)}")


def _check_whole_number(value, field, low, high=None):
    # bool is a subclass of int in Python, and 3.0 is a float that Go would not read into an int.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(field, 'must be a whole number')
    if value < low or (high is not None and value > high):
        bounds = f'from {low} to {high}' if high is not None else f'at least {low}'
        raise ValidationError(field, f'must be {bounds}')


def _check_amount(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(field, 'must be a number')
    amount = Decimal(str(value))
    if not amount.is_finite():
        raise ValidationError(field, 'must be a number')
    if amount <= 0:
        raise ValidationError(field, 'must be more than 0')
    if amount > MAX_AMOUNT:
        raise ValidationError(field, f'must be at most {MAX_AMOUNT}')
    if -amount.as_tuple().exponent > MAX_DECIMAL_PLACES:
        raise ValidationError(field, f'can have at most {MAX_DECIMAL_PLACES} decimal places')
