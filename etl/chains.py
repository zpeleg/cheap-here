"""Chain display names, keyed by the barcode prefix (``chainId``) that the
price feeds report.

This is the single source of truth for chain names: ``export.py`` writes the
subset present in a run into ``stores.json`` so the frontend can render labels
without hardcoding its own copy. A chain may have more than one prefix (e.g.
Victory), all mapping to the same display name.
"""

CHAIN_NAMES = {
    "7290027600007": "Shufersal",
    "7290058140886": "Rami Levy",
    "7290873255550": "Tiv Taam",
    "7290803800003": "Yohananof",
    "7290103152017": "Osher Ad",
    "7290696200003": "Victory",
    "7290058103393": "Victory",
    "7290058249350": "Wolt Market",
    "7290058197699": "Good Pharm",
    "7290055700007": "Carrefour",
    "7290700100008": "Hazi Hinam",
    "7290492000005": "am:pm",
}
