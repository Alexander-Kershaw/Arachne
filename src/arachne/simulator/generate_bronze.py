from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import random
from datetime import datetime, timedelta, timezone

import polars as pl

"""
Generate bronze data parquet files for a simple financial transactions simulation

Creates:
- people.parquet table
- merchants.parquet table
- transactions.parquet table


"""

@dataclass(frozen=True)
class SimConfig:
    seed: int = 42
    n_people: int = 2_000
    n_merchants: int = 120
    n_transactions: int = 50_000

"""
the generate_people method creates a dataframe with fixed-width person IDs and
a created_at timestamp for each person that later can be randomized for realism
"""

def generate_people(cfg: SimConfig) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "person_id": [f"P{idx:06d}" for idx in range(cfg.n_people)],
            "created_at": [datetime(2024, 1, 1, tzinfo=timezone.utc)] * cfg.n_people,
        }
    )

"""
the generate_merchants method creates a dataframe with fixed-width merchant IDs and
a simple distribution of merchant category codes (MCCs)
"""

def generate_merchants(cfg: SimConfig) -> pl.DataFrame:
    # Simple MCC (merchant category code) distribution placeholder
    mccs = ["5411", "5812", "5999", "5732", "4111", "4814", "6011"] # Grocery, Restaurant, Misc Retail, Electronics, Gas Station, Telecom, ATM
    return pl.DataFrame(
        {
            "merchant_id": [f"M{idx:05d}" for idx in range(cfg.n_merchants)],
            "mcc": [random.choice(mccs) for _ in range(cfg.n_merchants)],
            "country": ["GB"] * cfg.n_merchants,
        }
    )

"""
generate_transactions returns a dataframe of simulated transactions inside a 30 day window 
from January 1st, 2025. Transactions occur at random seconds within the time window, creating 
random timestamps across the month. 

Transaction amounts are randomly generated between £1.50 and £400.00. Each transaction is linked to
a random person ID and merchant ID from the previously generated dataframes.
"""

def generate_transactions(cfg: SimConfig, people: pl.DataFrame, merchants: pl.DataFrame) -> pl.DataFrame:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    person_ids = people["person_id"].to_list()
    merchant_ids = merchants["merchant_id"].to_list()

    tx_ids = [f"T{idx:08d}" for idx in range(cfg.n_transactions)]
    ts = [start + timedelta(seconds=random.randint(0, 60 * 60 * 24 * 30)) for _ in range(cfg.n_transactions)]
    amounts = [round(random.uniform(1.5, 400.0), 2) for _ in range(cfg.n_transactions)]

    return pl.DataFrame(
        {
            "tx_id": tx_ids,
            "ts": ts,
            "amount": amounts,
            "currency": ["GBP"] * cfg.n_transactions,
            "person_id": [random.choice(person_ids) for _ in range(cfg.n_transactions)],
            "merchant_id": [random.choice(merchant_ids) for _ in range(cfg.n_transactions)],
        }
    )


def write_bronze(out_dir: Path, people: pl.DataFrame, merchants: pl.DataFrame, tx: pl.DataFrame) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    people.write_parquet(out_dir / "people.parquet")
    merchants.write_parquet(out_dir / "merchants.parquet")
    tx.write_parquet(out_dir / "transactions.parquet")


def main() -> None:
    cfg = SimConfig()
    random.seed(cfg.seed)

    people = generate_people(cfg)
    merchants = generate_merchants(cfg)
    tx = generate_transactions(cfg, people, merchants)

    write_bronze(Path("data/bronze"), people, merchants, tx)
    print("Wrote bronze parquet files to data/bronze")


if __name__ == "__main__":
    main()
