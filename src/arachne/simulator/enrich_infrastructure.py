from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import random

import polars as pl

"""
enrich_infrastructure.py serves to create infrastructure reference data which is shared between
transaction entities. It generates devices, IPs, cards, and addresses, and then enriches existing
transaction records with references to this infrastructure data.

This introduction of shared infrastructure data simulates a more realistic scenario where multiple
transactions may share the same device, IP address, payment card, or address, reflecting common usage
and potentilal fraud patterns.
"""


@dataclass(frozen=True)
class InfraConfig:
    seed: int = 42
    n_devices: int = 2500
    n_ips: int = 1800
    n_cards: int = 2200
    n_addresses: int = 1600

    # Controls re-use of infra items across transactions
    # Lower => more unique infra per transaction and higher => more re-use
    reuse_strength: float = 0.25

# make IDs with fixed width numeric suffixes
def _make_ids(prefix: str, n: int, width: int) -> list[str]:
    return [f"{prefix}{i:0{width}d}" for i in range(n)]


def _random_ipv4() -> str:
    # Private ranges to avoid accidental use of real-world IPs in examples
    a = random.choice([10, 172, 192])
    if a == 10:
        return f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    if a == 172:
        return f"172.{random.randint(16,31)}.{random.randint(0,255)}.{random.randint(1,254)}"
    return f"192.168.{random.randint(0,255)}.{random.randint(1,254)}"


def _sample_with_reuse(pool: list[str], n: int, reuse_strength: float) -> list[str]:
    """
    Returns n samples from pool with controllable re-use.
    reuse_strength ~ 0 => near-uniform random
    reuse_strength ~ 1 => heavy preference for a smaller concentrated "hot" subset
    more reuse means more shared infra between transactions and more actionable fraud patterns to emerge
    """
    if not pool:
        raise ValueError("empty pool")

    hot_k = max(10, int(len(pool) * max(0.02, min(0.2, reuse_strength))))
    hot = pool[:hot_k]

    out: list[str] = []
    for _ in range(n):
        if random.random() < reuse_strength:
            out.append(random.choice(hot))
        else:
            out.append(random.choice(pool))
    return out


def main() -> None:
    cfg = InfraConfig()
    random.seed(cfg.seed)

    bronze_dir = Path("data/bronze")
    tx_path = bronze_dir / "transactions.parquet"
    if not tx_path.exists():
        raise FileNotFoundError("Expected data/bronze/transactions.parquet to exist. Run generate_bronze first.")

    tx = pl.read_parquet(tx_path)

    # Build infrastructure reference tables
    device_ids = _make_ids("D", cfg.n_devices, 7)
    ip_values = [_random_ipv4() for _ in range(cfg.n_ips)]
    card_hashes = _make_ids("C", cfg.n_cards, 8)
    address_hashes = _make_ids("A", cfg.n_addresses, 7)

    devices = pl.DataFrame({"device_id": device_ids, "device_type": ["mobile"] * cfg.n_devices})
    ips = pl.DataFrame({"ip": ip_values})
    cards = pl.DataFrame({"card_hash": card_hashes})
    addresses = pl.DataFrame({"address_hash": address_hashes, "postcode": ["UK"] * cfg.n_addresses})

    # Enrich transactions with infra references 
    n = tx.height
    tx_enriched = tx.with_columns(
        pl.Series("device_id", _sample_with_reuse(device_ids, n, cfg.reuse_strength)),
        pl.Series("ip", _sample_with_reuse(ip_values, n, cfg.reuse_strength)),
        pl.Series("card_hash", _sample_with_reuse(card_hashes, n, cfg.reuse_strength)),
        pl.Series("address_hash", _sample_with_reuse(address_hashes, n, cfg.reuse_strength)),
    )

    # Write to parquet
    devices.write_parquet(bronze_dir / "devices.parquet")
    ips.write_parquet(bronze_dir / "ips.parquet")
    cards.write_parquet(bronze_dir / "cards.parquet")
    addresses.write_parquet(bronze_dir / "addresses.parquet")
    tx_enriched.write_parquet(tx_path)

    print("Wrote devices/ips/cards/addresses and updated transactions.parquet")


if __name__ == "__main__":
    main()
