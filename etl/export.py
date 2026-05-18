import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from db import BranchItem, StoreInfo


def export_json(items: list[BranchItem], stores: list[StoreInfo], output_dir: Path) -> list[str]:
    """Write per-branch JSON files plus a stores index. Returns the list of branch keys."""
    output_dir.mkdir(parents=True, exist_ok=True)

    store_meta = {(s.chain_id, s.store_id): s for s in stores}

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for it in items:
        groups[(it.chain_id, it.store_id)].append({
            "barcode":  it.item_code,
            "name":     it.item_name,
            "manufacturer": it.manufacturer,
            "unitQty":  it.unit_qty,
            "quantity": it.quantity,
            "unit":     it.unit_of_measure,
            "price":    it.price,
            "unitPrice": it.unit_of_measure_price,
            "updatedAt": it.price_update_date,
        })

    updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    branch_keys: list[str] = []
    index_entries: list[dict] = []

    for (chain_id, store_id), products in sorted(groups.items()):
        products.sort(key=lambda p: p["price"])
        key = f"{chain_id}_{store_id}"
        branch_keys.append(key)

        meta = store_meta.get((chain_id, store_id))
        store_name = meta.store_name if meta else None
        city = meta.city if meta else None
        address = meta.address if meta else None

        (output_dir / f"store_{key}.json").write_text(
            json.dumps({
                "chainId":  chain_id,
                "storeId":  store_id,
                "storeName": store_name,
                "city":     city,
                "address":  address,
                "updatedAt": updated_at,
                "itemCount": len(products),
                "items":    products,
            }, ensure_ascii=False),
            encoding="utf-8",
        )

        index_entries.append({
            "key":       key,
            "chainId":   chain_id,
            "storeId":   store_id,
            "storeName": store_name,
            "city":      city,
            "itemCount": len(products),
        })

    (output_dir / "stores.json").write_text(
        json.dumps({"updatedAt": updated_at, "stores": index_entries}, ensure_ascii=False),
        encoding="utf-8",
    )

    return branch_keys
