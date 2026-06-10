from pathlib import Path

from il_supermarket_scarper import ScarpingTask, ScraperFactory, FileTypesFilters


# We pull the latest full snapshot per branch plus the store catalogue.
# Update files (PRICE_FILE/PROMO_FILE) are deltas — full files give a complete
# picture in one shot. Promos are needed so the export can apply per-unit sale
# prices on top of the sticker price.
STORE_FILE_TYPES = [
    FileTypesFilters.STORE_FILE.name,
]
PRICE_FILE_TYPES = [
    FileTypesFilters.PRICE_FULL_FILE.name,
    FileTypesFilters.PROMO_FULL_FILE.name,
]
ALL_FILE_TYPES = STORE_FILE_TYPES + PRICE_FILE_TYPES

# When a dev limit is set, store files get their own small budget instead of
# competing with price files for the same N downloads — otherwise a chain's
# store snapshots can crowd out its prices entirely (Good Pharm) or vice
# versa (Carrefour). Store files are small full snapshots; one or two per
# chain is always enough.
DEV_STORE_FILE_LIMIT = 2


def download(chains: list[str], dump_dir: Path, limit: int = 0) -> None:
    """Download supermarket XML dumps for the given ScraperFactory chain names."""
    dump_dir.mkdir(parents=True, exist_ok=True)
    status_dir = dump_dir / "_status"
    status_dir.mkdir(parents=True, exist_ok=True)

    enabled = [getattr(ScraperFactory, name).name for name in chains]

    _run(enabled, STORE_FILE_TYPES, dump_dir, status_dir / "stores",
         limit=DEV_STORE_FILE_LIMIT if limit else 0)
    _run(enabled, PRICE_FILE_TYPES, dump_dir, status_dir / "prices", limit=limit)


def _run(enabled: list[str], file_types: list[str], dump_dir: Path,
         status_dir: Path, limit: int = 0) -> None:
    status_dir.mkdir(parents=True, exist_ok=True)
    task = ScarpingTask(
        enabled_scrapers=enabled,
        files_types=file_types,
        output_configuration={
            "output_mode": "disk",
            "base_storage_path": str(dump_dir),
        },
        status_configuration={
            "database_type": "json",
            "base_path": str(status_dir),
        },
    )
    task.start(limit=limit or None)
    task.join()
