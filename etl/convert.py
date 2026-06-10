from pathlib import Path

from il_supermarket_parsers import ConvertingTask, FileTypesFilters

from scraper import ALL_FILE_TYPES


def convert(chains: list[str], dump_dir: Path, csv_dir: Path) -> None:
    """Convert downloaded XML dumps into per-(parser, file-type) CSV files.

    Output filenames follow `{file_type}_{parser_name}.csv` (e.g.
    `price_full_file_bareket.csv`, `store_file_bareket.csv`).
    """
    csv_dir.mkdir(parents=True, exist_ok=True)
    status_dir = csv_dir / "_status"
    status_dir.mkdir(parents=True, exist_ok=True)

    task = ConvertingTask(
        source_configuration={"folder": str(dump_dir)},
        output_configuration=[
            {"output_mode": "csv", "output_folder": str(csv_dir)},
        ],
        status_configuration={
            "database_type": "json",
            "base_path": str(status_dir),
        },
        enabled_parsers=chains,
        files_types=ALL_FILE_TYPES,
    )
    task.start()
    task.join()


def price_csvs(csv_dir: Path) -> list[Path]:
    return sorted(csv_dir.glob(f"{FileTypesFilters.PRICE_FULL_FILE.name.lower()}_*.csv"))


def store_csvs(csv_dir: Path) -> list[Path]:
    return sorted(csv_dir.glob(f"{FileTypesFilters.STORE_FILE.name.lower()}_*.csv"))


def promo_csvs(csv_dir: Path) -> list[Path]:
    return sorted(csv_dir.glob(f"{FileTypesFilters.PROMO_FULL_FILE.name.lower()}_*.csv"))
