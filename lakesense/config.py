from dataclasses import dataclass
from pathlib import Path


@dataclass
class Paths:
    root: Path = Path(".")

    def __post_init__(self):
        self.root = Path(self.root)

    @property
    def raw(self): return self.root / "data" / "raw"
    @property
    def db(self): return self.root / "data" / "warehouse.duckdb"
    @property
    def out(self): return self.root / "outputs"

    def ensure(self):
        self.raw.mkdir(parents=True, exist_ok=True)
        self.out.mkdir(parents=True, exist_ok=True)
        return self
