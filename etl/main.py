import shutil
import sys
import tempfile
from pathlib import Path

from config import load_config
from scraper import download
from convert import convert, price_csvs, store_csvs
from db import Store
from export import export_json


def main() -> None:
    cfg = load_config()

    if not cfg.chains:
        sys.exit("No chains configured — populate etl/stores.json")

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

        total_prices = 0
        for path in price_csvs(csv_dir):
            n = store.load_price_csv(path)
            print(f"[prices] {path.name} — {n} rows")
            total_prices += n

        total_stores = 0
        for path in store_csvs(csv_dir):
            n = store.load_store_csv(path)
            print(f"[stores] {path.name} — {n} rows")
            total_stores += n

        if total_prices == 0:
            sys.exit("No price rows ingested — verify chains and network access")

        latest = store.latest_per_branch()
        branches = store.branches()
        print(f"Loaded {total_prices} price rows, {total_stores} store rows")
        print(f"Latest snapshot: {len(latest)} (branch × product) pairs across {len(branches)} branches")

        output_dir = cfg.output_dir
        if not output_dir.is_absolute():
            output_dir = Path(__file__).parent / output_dir

        keys = export_json(latest, branches, output_dir)
        print(f"Exported {len(keys)} branch files → {output_dir}")

        store.close()

    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
