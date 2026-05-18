import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    chains: list[str]
    output_dir: Path
    limit: int


def load_config() -> Config:
    path = Path(os.environ.get("CONFIG_PATH", Path(__file__).parent / "stores.json"))
    data = json.loads(path.read_text(encoding="utf-8"))
    return Config(
        chains=data.get("chains", []),
        output_dir=Path(data.get("output_dir", "../frontend/public/data")),
        limit=int(data.get("limit", 0)),
    )
