from pathlib import Path

from il_supermarket_scarper import ScarpingTask, ScraperFactory, FileTypesFilters


# We pull the latest full snapshot per branch plus the store catalogue.
# Update files (PRICE_FILE/PROMO_FILE) are deltas — full files give a complete
# picture in one shot. Promos are needed so the export can apply per-unit sale
# prices on top of the sticker price.
PRICE_FILE_TYPES = [
    FileTypesFilters.STORE_FILE.name,
    FileTypesFilters.PRICE_FULL_FILE.name,
    FileTypesFilters.PROMO_FULL_FILE.name,
]


def download(chains: list[str], dump_dir: Path, limit: int = 0) -> None:
    """Download supermarket XML dumps for the given ScraperFactory chain names."""
    dump_dir.mkdir(parents=True, exist_ok=True)
    status_dir = dump_dir / "_status"
    status_dir.mkdir(parents=True, exist_ok=True)

    enabled = [getattr(ScraperFactory, name).name for name in chains]

    task = ScarpingTask(
        enabled_scrapers=enabled,
        files_types=PRICE_FILE_TYPES,
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
