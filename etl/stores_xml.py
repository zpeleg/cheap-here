"""Parse nested-format ``Stores*.xml`` dumps directly into store rows.

Several chains publish their store list as one ``<Stores>`` block per
sub-chain (Chain/Root > SubChains > SubChain > Stores > Store). The
il_supermarket_parsers store parser keeps only the last such block, so for
Shufersal (10 sub-chains) ~93% of branches are silently dropped, and for
Carrefour the store CSV comes out empty. Until that's fixed upstream, we
parse these chains' XML ourselves and skip the package's store CSV for
them. Good Pharm currently has a single sub-chain (the upstream bug is
only latent there) but uses the same format, so it goes through this path
too.

Tag casing varies by chain (``ChainID``/``StoreID`` vs ``ChainId``/
``StoreId``), hence the case-insensitive lookups. ``<City>`` may be a CBS
settlement code — left raw here, resolved chain-agnostically at export
time (see cities.py).
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from db import normalize_store_id


# Dump folder name → stores-file glob, for chains whose store CSV we bypass.
NESTED_STORES_DUMPS = {
    "Shufersal":               "Stores*.xml",
    "YaynotBitanAndCarrefour": "Stores*.xml",
    "GoodPharm":               "StoresFull*.xml",
}

# Upstream store CSVs superseded by the direct XML parse above.
SKIPPED_STORE_CSV_STEMS = {
    "store_file_shufersal",
    "store_file_yayno_bitan_and_carrefour",
    "store_file_good_pharm",
}


def _findtext_ci(elem, tag: str) -> str | None:
    """Case-insensitive findtext over direct children."""
    want = tag.lower()
    for child in elem:
        if child.tag.lower() == want:
            return child.text
    return None


def _clean(value: str | None) -> str | None:
    return value.strip() if value and value.strip() else None


def store_xml_paths(dump_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for folder, pattern in NESTED_STORES_DUMPS.items():
        paths.extend(sorted(dump_dir.glob(f"{folder}/{pattern}")))
    return paths


def parse_stores_xml(path: Path) -> list[dict]:
    """One row per branch, matching the ``stores`` table columns."""
    root = ET.parse(path).getroot()
    chain_id = _clean(_findtext_ci(root, "ChainID"))
    if not chain_id:
        return []

    rows: list[dict] = []
    for sub_chains in root:
        if sub_chains.tag.lower() != "subchains":
            continue
        for sub_chain in sub_chains:
            sub_chain_id = _clean(_findtext_ci(sub_chain, "SubChainID"))
            for stores in sub_chain:
                if stores.tag.lower() != "stores":
                    continue
                for store in stores:
                    store_id = _clean(_findtext_ci(store, "StoreID"))
                    if not store_id:
                        continue
                    rows.append({
                        "chain_id":     chain_id,
                        "sub_chain_id": sub_chain_id,
                        "store_id":     normalize_store_id(store_id),
                        "store_name":   _clean(_findtext_ci(store, "StoreName")),
                        "address":      _clean(_findtext_ci(store, "Address")),
                        "city":         _clean(_findtext_ci(store, "City")),
                    })
    return rows


def load_stores_from_xml(dump_dir: Path, store) -> int:
    """Parse every nested-format stores dump into ``store``. Returns rows loaded."""
    total = 0
    for path in store_xml_paths(dump_dir):
        rows = parse_stores_xml(path)
        total += store.load_store_rows(rows)
        print(f"[stores] {path.name} — {len(rows)} rows (direct XML parse)")
    return total
