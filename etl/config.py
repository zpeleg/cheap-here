import json
import os
from dataclasses import dataclass
from pathlib import Path

from il_supermarket_scarper import ScraperFactory


@dataclass
class Config:
    profile: str
    chains: list[str]
    output_dir: Path
    limit: int


def _resolve_chains(chains) -> list[str]:
    # "all" expands to every stable chain the scraper supports (excludes
    # ones the library flags as unstable, e.g. VICTORY / QUIK).
    if chains == "all":
        return ScraperFactory.all_scrapers_name()
    return list(chains)


def load_config() -> Config:
    path = Path(os.environ.get("CONFIG_PATH", Path(__file__).parent / "stores.json"))
    data = json.loads(path.read_text(encoding="utf-8"))

    profiles = data["profiles"]
    profile = os.environ.get("PROFILE", data.get("default_profile", "local"))
    if profile not in profiles:
        raise SystemExit(f"Unknown PROFILE {profile!r}; available: {sorted(profiles)}")
    selected = profiles[profile]

    return Config(
        profile=profile,
        chains=_resolve_chains(selected.get("chains", [])),
        output_dir=Path(data.get("output_dir", "../frontend/public/data")),
        limit=int(selected.get("limit", 0)),
    )
