"""ETL entry point for the cheap-here price dataset.

Pipeline stages, in order:

1. Load configuration from ``etl/stores.json`` (chain list, row limit, output dir).
2. Download per-chain XML dumps from the upstream price-transparency portals
   into a temporary ``dumps/`` directory.
3. Convert the raw XML dumps into normalized CSVs (prices + stores) under a
   temporary ``csv/`` directory.
4. Load the CSVs into a SQLite ``Store``, computing the latest price snapshot
   per (branch, product) pair.
5. Export per-branch JSON files to the configured output directory for the
   frontend to consume.

The temporary working directory is always removed on exit, even on failure.
Exits non-zero if no chains are configured or if zero price rows are ingested
(typically a network or upstream-format issue worth surfacing loudly).

Run directly: ``python etl/main.py``.
"""

import shutil
import sys
import tempfile
from pathlib import Path

from config import load_config
from scraper import download
from convert import convert, price_csvs, store_csvs, promo_csvs
from db import Store
from export import export_json


def _load_all(label: str, paths: list[Path], loader) -> int:
    """Load every CSV through `loader`, returning total rows ingested.

    A single corrupt upstream feed must not abort the multi-hour run, so
    per-file failures are reported and skipped. Systemic failure is still
    caught by the zero-price-rows check in main().
    """
    total = 0
    for path in paths:
        try:
            n = loader(path)
        except Exception as exc:
            print(f"[{label}] {path.name} — skipped: {exc}")
            continue
        print(f"[{label}] {path.name} — {n} rows")
        total += n
    return total


def main() -> None:
    """Run the full download → convert → load → export pipeline.

    Side effects:
        - Creates and deletes a temp directory under the system tempdir.
        - Writes JSON files under ``cfg.output_dir`` (resolved relative to
          this file when not absolute).
        - Writes to the SQLite database backing ``Store``.

    Exits:
        - Code 1 if ``cfg.chains`` is empty.
        - Code 1 if the pipeline ingests zero price rows.
    """
    cfg = load_config()

    if not cfg.chains:
        sys.exit("No chains configured — populate etl/stores.json")

    print(f"Profile: {cfg.profile} — {len(cfg.chains)} chains, limit={cfg.limit or 'none'}")

    workdir = Path(tempfile.mkdtemp(prefix="cheap_here_"))
    dump_dir = workdir / "dumps"
    csv_dir = workdir / "csv"

    try:
        print(f"Downloading XMLs for chains: {cfg.chains}")
        download(cfg.chains, dump_dir, limit=cfg.limit)

        print(f"Converting XMLs → CSV in {csv_dir}")
        convert(cfg.chains, dump_dir, csv_dir)

        store = Store()
        store.create_schema()

        total_prices = _load_all("prices", price_csvs(csv_dir), store.load_price_csv)
        total_stores = _load_all("stores", store_csvs(csv_dir), store.load_store_csv)
        total_promos = _load_all("promos", promo_csvs(csv_dir), store.load_promo_csv)

        if total_prices == 0:
            sys.exit("No price rows ingested — verify chains and network access")

        latest = store.latest_per_branch()
        branches = store.branches()
        promos = store.active_promos_per_branch()
        print(f"Loaded {total_prices} price rows, {total_stores} store rows, {total_promos} promo-item rows")
        print(f"Latest snapshot: {len(latest)} (branch × product) pairs across {len(branches)} branches")
        print(f"Active promos: {len(promos)} (branch × product) pairs with a current sale price")

        output_dir = cfg.output_dir
        if not output_dir.is_absolute():
            output_dir = Path(__file__).parent / output_dir

        keys = export_json(latest, branches, promos, output_dir)
        print(f"Exported {len(keys)} branch files → {output_dir}")

        store.close()

    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
