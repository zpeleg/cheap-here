import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd


# CSV cells that originally were empty in the XML are written as "''" by the
# parsers package (CSVOutputWriter.EMPTY_STRING) so they can be distinguished
# from dedup-masked cells. Normalise them to NULL on load.
EMPTY_SENTINEL = "''"

# Strings the parsers write into per-item promo fields when the source XML had
# the element but with no body (e.g. <discountedprice/>). We treat both as NULL
# when computing per-unit sale prices.
PROMO_MISSING_VALUES = {"", "NO_BODY", EMPTY_SENTINEL}


@dataclass
class BranchItem:
    chain_id: str
    sub_chain_id: str
    store_id: str
    item_code: str
    item_name: str
    manufacturer: str
    unit_qty: str
    quantity: str
    unit_of_measure: str
    price: float
    unit_of_measure_price: float | None
    price_update_date: str


@dataclass
class StoreInfo:
    chain_id: str
    sub_chain_id: str
    store_id: str
    store_name: str
    address: str
    city: str


@dataclass
class PromoItem:
    """Best active promo for a single (chain, store, item) on the run date.

    `per_unit_price` is `total_price / min_qty` — matches the reference site's
    "מחיר ליחידה" figure shown in the popup.
    """
    chain_id: str
    store_id: str
    item_code: str
    description: str
    min_qty: float
    total_price: float
    per_unit_price: float
    end_date: str  # YYYY-MM-DD


class Store:
    def __init__(self, path: str = ":memory:") -> None:
        self.conn = duckdb.connect(path)

    def create_schema(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                chain_id              VARCHAR NOT NULL,
                sub_chain_id          VARCHAR,
                store_id              VARCHAR NOT NULL,
                item_code             VARCHAR NOT NULL,
                item_name             VARCHAR,
                manufacturer          VARCHAR,
                unit_qty              VARCHAR,
                quantity              VARCHAR,
                unit_of_measure       VARCHAR,
                price                 DOUBLE  NOT NULL,
                unit_of_measure_price DOUBLE,
                price_update_date     VARCHAR
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS stores (
                chain_id     VARCHAR NOT NULL,
                sub_chain_id VARCHAR,
                store_id     VARCHAR NOT NULL,
                store_name   VARCHAR,
                address      VARCHAR,
                city         VARCHAR
            )
        """)
        # One row per (promotion × item-in-promotion). The original promo XML
        # nests promotion items inside <Groups><Group><PromotionItems>, which
        # the parsers package emits as a single JSON-stringified `groups` cell.
        # We flatten that here so we can compute per-unit sale prices in SQL.
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS promos (
                chain_id        VARCHAR NOT NULL,
                store_id        VARCHAR NOT NULL,
                item_code       VARCHAR NOT NULL,
                description     VARCHAR,
                start_date      VARCHAR,
                end_date        VARCHAR,
                min_qty         DOUBLE,
                total_price     DOUBLE,
                per_unit_price  DOUBLE
            )
        """)

    def load_price_csv(self, path: Path) -> int:
        df = self._read_csv(path)
        if df is None or df.empty:
            return 0

        df = _select_columns(df, {
            "chainid":            "chain_id",
            "subchainid":         "sub_chain_id",
            "storeid":            "store_id",
            "itemcode":           "item_code",
            "itemname":           "item_name",
            "manufacturername":   "manufacturer",
            "unitqty":            "unit_qty",
            "quantity":           "quantity",
            "unitofmeasure":      "unit_of_measure",
            "itemprice":          "price",
            "unitofmeasureprice": "unit_of_measure_price",
            "priceupdatedate":    "price_update_date",
        })

        df["price"] = pd.to_numeric(df["price"], errors="coerce")
        df["unit_of_measure_price"] = pd.to_numeric(df["unit_of_measure_price"], errors="coerce")
        # Drop rows missing any dedup key — without them latest_per_branch can't
        # group correctly. Also drop non-positive prices, which upstream uses as
        # a sentinel for "not for sale / placeholder".
        df = df.dropna(subset=["chain_id", "store_id", "item_code", "price"])
        df = df[df["price"] > 0]

        if df.empty:
            return 0

        self.conn.register("_prices_df", df)
        self.conn.execute("INSERT INTO prices SELECT * FROM _prices_df")
        self.conn.unregister("_prices_df")
        return len(df)

    def load_promo_csv(self, path: Path) -> int:
        df = self._read_csv(path)
        if df is None or df.empty:
            return 0

        required = {"chainid", "storeid", "groups"}
        if not required.issubset(df.columns):
            return 0

        flattened = _flatten_promo_rows(df)
        if not flattened:
            return 0

        out = pd.DataFrame(flattened)
        self.conn.register("_promos_df", out)
        self.conn.execute("INSERT INTO promos SELECT * FROM _promos_df")
        self.conn.unregister("_promos_df")
        return len(out)

    def active_promos_per_branch(self, as_of: datetime | None = None) -> list[PromoItem]:
        """Best (cheapest per-unit) active promo per (chain, store, item).

        A promo is "active" when its start/end window contains `as_of`. Rows
        with missing dates are treated as open-ended on the missing side, which
        matches what the upstream feeds seem to do for evergreen membership
        prices.
        """
        as_of = as_of or datetime.now()
        as_of_str = as_of.strftime("%Y-%m-%d")
        rows = self.conn.execute(
            """
            SELECT chain_id, store_id, item_code,
                   description, min_qty, total_price, per_unit_price, end_date
            FROM promos
            WHERE per_unit_price IS NOT NULL AND per_unit_price > 0
              AND (start_date IS NULL OR start_date <= ?)
              AND (end_date   IS NULL OR end_date   >= ?)
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY chain_id, store_id, item_code
                ORDER BY per_unit_price ASC
            ) = 1
            """,
            [as_of_str, as_of_str],
        ).fetchall()
        return [
            PromoItem(
                chain_id=r[0], store_id=r[1], item_code=r[2],
                description=r[3], min_qty=r[4], total_price=r[5],
                per_unit_price=r[6], end_date=r[7],
            )
            for r in rows
        ]

    def load_store_csv(self, path: Path) -> int:
        df = self._read_csv(path)
        if df is None or df.empty:
            return 0

        df = _select_columns(df, {
            "chainid":     "chain_id",
            "subchainid":  "sub_chain_id",
            "storeid":     "store_id",
            "storename":   "store_name",
            "address":     "address",
            "city":        "city",
        })
        df = df.dropna(subset=["chain_id", "store_id"])

        if df.empty:
            return 0

        self.conn.register("_stores_df", df)
        self.conn.execute("INSERT INTO stores SELECT * FROM _stores_df")
        self.conn.unregister("_stores_df")
        return len(df)

    def latest_per_branch(self) -> list[BranchItem]:
        # A single ETL run typically ingests multiple per-snapshot CSVs per
        # chain, so the same (chain, store, item) appears many times. Keep
        # only the row with the newest price_update_date; NULL dates sort
        # last so a real timestamp always beats a missing one.
        rows = self.conn.execute("""
            SELECT chain_id, sub_chain_id, store_id, item_code, item_name,
                   manufacturer, unit_qty, quantity, unit_of_measure,
                   price, unit_of_measure_price, price_update_date
            FROM prices
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY chain_id, store_id, item_code
                ORDER BY price_update_date DESC NULLS LAST
            ) = 1
        """).fetchall()
        return [BranchItem(*r) for r in rows]

    def branches(self) -> list[StoreInfo]:
        # The same store appears in every stores.xml snapshot, sometimes with
        # minor metadata drift (renamed branch, address typo fix). We don't
        # need to reconcile those — ANY_VALUE picks one deterministically per
        # (chain_id, store_id) so each branch shows up exactly once.
        rows = self.conn.execute("""
            SELECT chain_id,
                   ANY_VALUE(sub_chain_id) AS sub_chain_id,
                   store_id,
                   ANY_VALUE(store_name)   AS store_name,
                   ANY_VALUE(address)      AS address,
                   ANY_VALUE(city)         AS city
            FROM stores
            GROUP BY chain_id, store_id
            ORDER BY chain_id, store_id
        """).fetchall()
        return [StoreInfo(*r) for r in rows]

    def close(self) -> None:
        self.conn.close()

    @staticmethod
    def _read_csv(path: Path) -> pd.DataFrame | None:
        # Equivalent to il_supermarket_parsers.read_data_rows(ffill=True,
        # as_records=False), except ragged lines are skipped instead of
        # raising ParserError — the upstream promo feeds occasionally emit
        # rows with stray delimiters, and one bad line must not abort a run.
        # ffill restores values the parsers blanked out for dedup (repeated
        # chain/store/sub_chain on consecutive rows). Without it most rows
        # would drop in load_price_csv's dropna step above.
        try:
            df = pd.read_csv(path, dtype=str, on_bad_lines="skip")
        except pd.errors.EmptyDataError:
            return None
        if df.empty:
            return None
        df = df.ffill()
        df.columns = [c.lower() for c in df.columns]
        # Replace the parsers' empty sentinel with None so DuckDB stores SQL NULL.
        return df.replace({EMPTY_SENTINEL: None}).where(df.notna(), None)


def _select_columns(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """Project + rename to the canonical schema; missing source columns become None."""
    selected = pd.DataFrame()
    for src, dst in mapping.items():
        selected[dst] = df[src] if src in df.columns else None
    return selected


def _promo_number(value) -> float | None:
    """Coerce a promo cell to float, returning None for the parsers' sentinels."""
    if value is None:
        return None
    s = str(value).strip()
    if s in PROMO_MISSING_VALUES:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _promo_date(value) -> str | None:
    """Extract YYYY-MM-DD from a promotion start/end timestamp."""
    if not value:
        return None
    s = str(value).strip()
    if s in PROMO_MISSING_VALUES:
        return None
    # Format observed: "2026-05-30T23:58:00.000" — splitting on T is enough.
    return s.split("T", 1)[0][:10] or None


def _coerce_list(value) -> list:
    """Promo XML emits a single child as a dict and many children as a list.
    Normalise both to a list so callers don't have to branch every time."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _flatten_promo_rows(df: pd.DataFrame) -> list[dict]:
    """Explode the nested `groups` JSON into one row per item-in-promotion.

    Skips items missing both `discountedprice` and `discountedpricepermida` —
    without a price we can't show a sale to the user. The reference site
    derives "מחיר ליחידה" as discountedprice / minqty, which we replicate here
    when possible and fall back to the per-mida value otherwise.
    """
    out: list[dict] = []
    for row in df.itertuples(index=False):
        groups_raw = getattr(row, "groups", None)
        if not groups_raw or groups_raw in PROMO_MISSING_VALUES:
            continue
        try:
            parsed = json.loads(groups_raw)
        except (TypeError, ValueError):
            continue

        chain_id = str(getattr(row, "chainid", "") or "")
        store_id = str(getattr(row, "storeid", "") or "")
        if not chain_id or not store_id:
            continue

        description = getattr(row, "promotiondescription", None) or ""
        start_date = _promo_date(getattr(row, "promotionstartdatetime", None))
        end_date = _promo_date(getattr(row, "promotionenddatetime", None))

        for group in _coerce_list(parsed.get("group")):
            if not isinstance(group, dict):
                continue
            promotionitems = group.get("promotionitems")
            if not isinstance(promotionitems, dict):
                continue
            items = _coerce_list(promotionitems.get("promotionitem"))
            for item in items:
                if not isinstance(item, dict):
                    continue
                code = item.get("itemcode")
                if not code or str(code).strip() in PROMO_MISSING_VALUES:
                    continue

                min_qty = _promo_number(item.get("minqty")) or 1.0
                total = _promo_number(item.get("discountedprice"))
                per_mida = _promo_number(item.get("discountedpricepermida"))

                # Prefer total/qty (matches the reference site's "מחיר ליחידה");
                # only fall back to per-mida when there's no total price.
                if total is not None and min_qty > 0:
                    per_unit = total / min_qty
                elif per_mida is not None:
                    per_unit = per_mida
                    total = per_mida * min_qty
                else:
                    continue

                out.append({
                    "chain_id":       chain_id,
                    "store_id":       store_id,
                    "item_code":      str(code).strip(),
                    "description":    description,
                    "start_date":     start_date,
                    "end_date":       end_date,
                    "min_qty":        min_qty,
                    "total_price":    total,
                    "per_unit_price": per_unit,
                })

    return out
