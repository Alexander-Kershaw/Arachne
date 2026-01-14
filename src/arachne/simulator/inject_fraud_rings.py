from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
import random

import polars as pl

"""
inject_fraud_rings.py serves to modify an existing transactions dataset by injecting synthetic
fraud rings. Fraud rings are groups of individuals who collaborate to commit fraudulent activities,
often sharing resources like devices, IP addresses, payment methods, and addresses.

Here are the key functionalities of the script:

- Creates N number of fraud rings, each consisting of a random number of members within specified size limits.
- Selects a fraction of existing transactions to be modified into fraud ring transactions
- For each selected transaction: enforces that the person_id belongs to a ring member,
    makes adjustments to the transaction timestamps to create burst window patterns,
    forces shared infrastructure usage (device, IP, card, address) among ring members based on configurable probabilities.
- Adds an is_fraud label column to the transactions dataset to indicate which transactions were modified as
synthetic ground truth for evaluation.
"""

@dataclass(frozen=True)
class RingConfig:
    seed: int = 42

    n_rings: int = 12
    ring_size_min: int = 6
    ring_size_max: int = 20

    # Fraction of all transactions that will be coerced into fraud rings
    fraud_tx_share: float = 0.08

    # Strengths of rings shared infrastructure (0..1)
    shared_device_prob: float = 0.70
    shared_ip_prob: float = 0.55
    shared_card_prob: float = 0.35
    shared_address_prob: float = 0.45

    # Defining burst window
    burst_hours_window: int = 48


def _choose_hot(pool: list[str], k: int) -> list[str]:
    # biased towards first slice
    k = max(1, min(k, len(pool)))
    return pool[:k]


def main() -> None:
    cfg = RingConfig()
    random.seed(cfg.seed)

    bronze = Path("data/bronze")
    people = pl.read_parquet(bronze / "people.parquet")
    tx = pl.read_parquet(bronze / "transactions.parquet")

    devices = pl.read_parquet(bronze / "devices.parquet")["device_id"].to_list()
    ips = pl.read_parquet(bronze / "ips.parquet")["ip"].to_list()
    cards = pl.read_parquet(bronze / "cards.parquet")["card_hash"].to_list()
    addrs = pl.read_parquet(bronze / "addresses.parquet")["address_hash"].to_list()

    person_ids = people["person_id"].to_list()

    # Choosing ring membership
    random.shuffle(person_ids)
    rings: list[list[str]] = []
    cursor = 0
    for ring_id in range(cfg.n_rings):
        size = random.randint(cfg.ring_size_min, cfg.ring_size_max)
        if cursor + size > len(person_ids):
            break
        rings.append(person_ids[cursor : cursor + size])
        cursor += size

    if not rings:
        raise RuntimeError("No rings created; increase n_people or reduce ring sizes.")

    # Determine how many transaction rows will be converted into fraud ring transactions
    n_total = tx.height
    n_fraud = int(n_total * cfg.fraud_tx_share)
    if n_fraud <= 0:
        raise ValueError("fraud_tx_share too small; yields 0 fraud transactions.")

    # Pick transaction indices to modify
    fraud_idx = random.sample(range(n_total), k=min(n_fraud, n_total))

    tx_person = tx["person_id"].to_list()
    tx_ts = tx["ts"].to_list()
    tx_device = tx["device_id"].to_list()
    tx_ip = tx["ip"].to_list()
    tx_card = tx["card_hash"].to_list()
    tx_addr = tx["address_hash"].to_list()

    # Predetermine “hot pools” so ring infrastructure feature reuse is obvious
    hot_devices = _choose_hot(devices, k=max(30, int(len(devices) * 0.03)))
    hot_ips = _choose_hot(ips, k=max(40, int(len(ips) * 0.04)))
    hot_cards = _choose_hot(cards, k=max(30, int(len(cards) * 0.03)))
    hot_addrs = _choose_hot(addrs, k=max(25, int(len(addrs) * 0.03)))

    # Create shared infrastructure per ring
    ring_shared = []
    for _ in rings:
        ring_shared.append(
            {
                "device": random.choice(hot_devices),
                "ip": random.choice(hot_ips),
                "card": random.choice(hot_cards),
                "addr": random.choice(hot_addrs),
            }
        )

    # Anchor burst windows for each ring using existing transaction timestamps
    # This anchoring ensures a temporal distribution within bounds of transaction data
    anchor_times = random.sample(tx_ts, k=len(rings))

    # Modify selected transactions
    for idx in fraud_idx:
        r_i = random.randrange(len(rings))
        ring_members = rings[r_i]
        shared = ring_shared[r_i]
        anchor = anchor_times[r_i]

        # Force transaction to be made by a ring member
        tx_person[idx] = random.choice(ring_members)

        # Make burst window around anchor time
        jitter = timedelta(hours=random.randint(-cfg.burst_hours_window, cfg.burst_hours_window))
        tx_ts[idx] = anchor + jitter

        # Shared infrastructure with configured probabilities
        if random.random() < cfg.shared_device_prob:
            tx_device[idx] = shared["device"]
        if random.random() < cfg.shared_ip_prob:
            tx_ip[idx] = shared["ip"]
        if random.random() < cfg.shared_card_prob:
            tx_card[idx] = shared["card"]
        if random.random() < cfg.shared_address_prob:
            tx_addr[idx] = shared["addr"]

    # Add is_fraud label column
    # This is for synthetic ground truth to evaluate fraud detection models (not IRL data)
    is_fraud = [0] * n_total
    for idx in fraud_idx:
        is_fraud[idx] = 1

    tx_out = tx.with_columns(
        pl.Series("person_id", tx_person),
        pl.Series("ts", tx_ts),
        pl.Series("device_id", tx_device),
        pl.Series("ip", tx_ip),
        pl.Series("card_hash", tx_card),
        pl.Series("address_hash", tx_addr),
        pl.Series("is_fraud", is_fraud),
    )

    tx_out.write_parquet(bronze / "transactions.parquet")
    print(f"Injected {len(fraud_idx)} fraud-ring transactions across {len(rings)} rings")


if __name__ == "__main__":
    main()
