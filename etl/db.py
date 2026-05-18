from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd
from il_supermarket_parsers import read_data_rows


# CSV cells that originally were empty in the XML are written as "''" by the
# parsers package (CSVOutputWriter.EMPTY_STRING) so they can be distinguished
# from dedup-masked cells. Normalise them to NULL on load.
EMPTY_SENTINEL = "''"


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
        # ffill=True restores values the parsers blanked out for dedup
        # (repeated chain/store/sub_chain on consecutive rows). Without it
        # most rows would drop in load_price_csv's dropna step above.
        df = read_data_rows(str(path), ffill=True, as_records=False)
        if df is None or df.empty:
            return None
        df.columns = [c.lower() for c in df.columns]
        # Replace the parsers' empty sentinel with None so DuckDB stores SQL NULL.
        return df.replace({EMPTY_SENTINEL: None}).where(df.notna(), None)


def _select_columns(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """Project + rename to the canonical schema; missing source columns become None."""
    selected = pd.DataFrame()
    for src, dst in mapping.items():
        selected[dst] = df[src] if src in df.columns else None
    return selected
