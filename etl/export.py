import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from cities import load_city_names, resolve_city
from db import BranchItem, PromoItem, StoreInfo


# A branch lists an item only when buying it there is the national best price,
# or close enough not to matter (within 5% of the cheapest effective price).
NEAR_CHEAPEST_TOLERANCE = 0.05


def export_json(
    items: list[BranchItem],
    stores: list[StoreInfo],
    promos: list[PromoItem],
    output_dir: Path,
) -> list[str]:
    """Write per-branch JSON files plus a stores index. Returns the list of branch keys."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for stale in output_dir.glob("store_*.json"):
        stale.unlink()

    store_meta = {(s.chain_id, s.store_id): s for s in stores}
    city_names = load_city_names()
    # PromoItem is already best-per-branch-item — see Store.active_promos_per_branch.
    promo_by_branch_item: dict[tuple[str, str, str], PromoItem] = {
        (p.chain_id, p.store_id, p.item_code): p for p in promos
    }

    # Effective price honours active promos: a "3 for ₪14" sale beats the
    # sticker price even when sticker prices look similar across branches.
    # This matches the reference site's "מבצע" column.
    def effective_price(it: BranchItem) -> float:
        promo = promo_by_branch_item.get((it.chain_id, it.store_id, it.item_code))
        if promo is None:
            return it.price
        return min(it.price, promo.per_unit_price)

    # Build a "best price" filter per item_code:
    #   1. item appears in >=2 chains (cross-chain comparison must be meaningful)
    #   2. effective prices are not all identical across stores (some real variation exists)
    #   3. this branch's effective price is within NEAR_CHEAPEST_TOLERANCE of the
    #      cheapest national effective price (cheapest in the country, or almost)
    chain_prices_per_item: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    # Some chains publish prices with a blank item name (e.g. Good Pharm);
    # borrow the name another chain reports for the same barcode.
    item_names: dict[str, str] = {}
    for it in items:
        chain_prices_per_item[it.item_code][it.chain_id].append(effective_price(it))
        if it.item_name and it.item_code not in item_names:
            item_names[it.item_code] = it.item_name

    # (min, median, max) of cross-store effective prices, for items worth
    # exporting. min drives the inclusion filter; median/max are shown by the
    # frontend next to the local price so the deal is visible.
    item_stats: dict[str, tuple[float, float, float]] = {}
    # Per-chain price summary, cheapest chain first. Kept as bare
    # [chain_id, min_price, branch_count] arrays rather than objects: this
    # repeats for every exported item (~40k rows) and the verbose form would
    # roughly double the JSON payload.
    item_chain_prices: dict[str, list[list]] = {}
    for code, per_chain in chain_prices_per_item.items():
        if len(per_chain) < 2:
            continue
        prices = [p for chain_ps in per_chain.values() for p in chain_ps]
        if min(prices) == max(prices):
            continue
        item_stats[code] = (min(prices), median(prices), max(prices))
        item_chain_prices[code] = sorted(
            ([chain, round(min(ps), 2), len(ps)] for chain, ps in per_chain.items()),
            key=lambda entry: entry[1],
        )

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for it in items:
        eff = effective_price(it)
        stats = item_stats.get(it.item_code)
        if stats is None:
            continue
        min_price, median_price, max_price = stats
        if eff > min_price * (1 + NEAR_CHEAPEST_TOLERANCE):
            continue
        promo = promo_by_branch_item.get((it.chain_id, it.store_id, it.item_code))
        groups[(it.chain_id, it.store_id)].append({
            "barcode":  it.item_code,
            "name":     it.item_name,
            "manufacturer": it.manufacturer,
            "unitQty":  it.unit_qty,
            "quantity": it.quantity,
            "unit":     it.unit_of_measure,
            "price":    it.price,
            "effectivePrice": eff,
            "medianPrice": round(median_price, 2),
            "maxPrice": round(max_price, 2),
            "chainPrices": item_chain_prices[it.item_code],
            "unitPrice": it.unit_of_measure_price,
            "updatedAt": it.price_update_date,
            "sale":     _sale_payload(promo) if promo else None,
        })

    updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    branch_keys: list[str] = []
    index_entries: list[dict] = []

    for (chain_id, store_id), products in sorted(groups.items()):
        products.sort(key=lambda p: p["effectivePrice"])
        key = f"{chain_id}_{store_id}"
        branch_keys.append(key)

        meta = store_meta.get((chain_id, store_id))
        store_name = meta.store_name if meta else None
        city = resolve_city(meta.city, city_names) if meta else None
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
            "address":   address,
            "itemCount": len(products),
        })

    (output_dir / "stores.json").write_text(
        json.dumps({"updatedAt": updated_at, "stores": index_entries}, ensure_ascii=False),
        encoding="utf-8",
    )

    return branch_keys


def _sale_payload(promo: PromoItem) -> dict:
    return {
        "minQty":       promo.min_qty,
        "totalPrice":   promo.total_price,
        "perUnitPrice": promo.per_unit_price,
        "description":  promo.description,
        "endDate":      promo.end_date,
    }
