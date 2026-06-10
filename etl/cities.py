"""Resolve raw city fields to Hebrew city names.

Several chains fill the stores-file ``<City>`` with a CBS settlement code
(e.g. 7400 = נתניה, 6500 = חדרה) or a junk placeholder (``0``) instead of a
name. ``cbs_cities.json`` is a committed snapshot of the CBS settlements
table (data.gov.il resource 5c78e9fa-c2e2-4771-93ff-7f400a12f7ba) mapping
code → Hebrew name.
"""

import json
from pathlib import Path


CITY_CODES_PATH = Path(__file__).parent / "cbs_cities.json"


def load_city_names() -> dict[str, str]:
    return json.loads(CITY_CODES_PATH.read_text(encoding="utf-8"))


def resolve_city(raw: str | None, city_names: dict[str, str]) -> str | None:
    """Map a CBS code to its city name; pass real names through unchanged.

    Numeric values not in the table are kept as-is (still searchable);
    ``0`` is a known "no city" placeholder and becomes None.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s.isdigit():
        code = str(int(s))
        if code == "0":
            return None
        return city_names.get(code, s)
    return s
