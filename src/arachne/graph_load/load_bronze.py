from __future__ import annotations

from pathlib import Path
import polars as pl # because polars is faster than pandas for parquet I/O
from neo4j import GraphDatabase


# Chunking lists into smaller batches since Neo4j performs better with smaller UNWINDs
# and the transaction data is quite large
def chunked(seq, size: int):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def main() -> None:
    # Match configs/arachne.yml defaults
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "password123"
    database = "neo4j"

    # Load bronze parquet files
    bronze = Path("data/bronze")
    people = pl.read_parquet(bronze / "people.parquet")
    merchants = pl.read_parquet(bronze / "merchants.parquet")
    devices = pl.read_parquet(bronze / "devices.parquet")
    ips = pl.read_parquet(bronze / "ips.parquet")
    cards = pl.read_parquet(bronze / "cards.parquet")
    addrs = pl.read_parquet(bronze / "addresses.parquet")
    tx = pl.read_parquet(bronze / "transactions.parquet")

    # Convert polars dataframes into rows (list of dicts) needed for Neo4j UNWIND
    people_rows = people.select(["person_id"]).to_dicts()
    merchant_rows = merchants.select(["merchant_id", "mcc", "country"]).to_dicts()
    device_rows = devices.select(["device_id", "device_type"]).to_dicts()
    ip_rows = ips.select(["ip"]).to_dicts()
    card_rows = cards.select(["card_hash"]).to_dicts()
    addr_rows = addrs.select(["address_hash", "postcode"]).to_dicts()

    # Selecting only the necessary fields for transactions
    tx_rows = tx.select(
        [
            "tx_id",
            "ts",
            "amount",
            "currency",
            "person_id",
            "merchant_id",
            "device_id",
            "ip",
            "card_hash",
            "address_hash",
            "is_fraud",
        ]
    ).to_dicts()

    # Connect to Neo4j
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        driver.verify_connectivity()
        print("Connected to Neo4j")

        with driver.session(database=database) as session:
            # Defining merge nodes
            # Basically: if the node exists, reuse it, else create it
            # Since uniqueness constraints are already created (uniqueness cypher), MERGE should be safe and prevent duplicates
            def merge_nodes(query: str, rows: list[dict], batch_size: int = 5000):
                for batch in chunked(rows, batch_size):
                    session.run(query, rows=batch)

            merge_nodes(
                """
                UNWIND $rows AS r
                MERGE (:Person {person_id: r.person_id})
                """,
                people_rows,
            )
            print(f"Loaded Person: {len(people_rows)}")

            merge_nodes(
                """
                UNWIND $rows AS r
                MERGE (m:Merchant {merchant_id: r.merchant_id})
                SET m.mcc = r.mcc, m.country = r.country
                """,
                merchant_rows,
            )
            print(f"Loaded Merchant: {len(merchant_rows)}")

            merge_nodes(
                """
                UNWIND $rows AS r
                MERGE (d:Device {device_id: r.device_id})
                SET d.device_type = r.device_type
                """,
                device_rows,
            )
            print(f"Loaded Device: {len(device_rows)}")

            merge_nodes(
                """
                UNWIND $rows AS r
                MERGE (:IP {ip: r.ip})
                """,
                ip_rows,
            )
            print(f"Loaded IP: {len(ip_rows)}")

            merge_nodes(
                """
                UNWIND $rows AS r
                MERGE (:Card {card_hash: r.card_hash})
                """,
                card_rows,
            )
            print(f"Loaded Card: {len(card_rows)}")

            merge_nodes(
                """
                UNWIND $rows AS r
                MERGE (a:Address {address_hash: r.address_hash})
                SET a.postcode = r.postcode
                """,
                addr_rows,
            )
            print(f"Loaded Address: {len(addr_rows)}")
            """
            #Transactions + relationships
             Creates transaction nodes (or reuses existing ones) and sets properties:
             - Python datetime -> Neo4j datetime conversion
             - amount is casted to float
             - is_fraud is casted to integeric binary flag (0/1)

             Also creates relationships using MATCH to find existing nodes,
             this should ensure the correct links are established for persons, merchants, devices, IPs, cards, and addresses

             SUMMARY:
             - MATCH ensures nodes exist before creating relationships
             - MERGE ensures the relationship isn't duplicated on multiple runs
            """
            tx_query = """
            UNWIND $rows AS r

            // Transaction node
            MERGE (t:Transaction {tx_id: r.tx_id})
            SET t.ts = datetime(r.ts),
                t.amount = toFloat(r.amount),
                t.currency = r.currency,
                t.is_fraud = toInteger(r.is_fraud)

            WITH r, t

            // Match all referenced nodes in one clause
            MATCH (p:Person   {person_id: r.person_id}),
                (m:Merchant {merchant_id: r.merchant_id}),
                (d:Device   {device_id: r.device_id}),
                (ip:IP      {ip: r.ip}),
                (c:Card     {card_hash: r.card_hash}),
                (a:Address  {address_hash: r.address_hash})

            // Relationships
            MERGE (p)-[:MADE]->(t)
            MERGE (t)-[:TO_MERCHANT]->(m)
            MERGE (t)-[:USED_DEVICE]->(d)
            MERGE (t)-[:FROM_IP]->(ip)
            MERGE (t)-[:PAID_WITH]->(c)
            MERGE (t)-[:BILLED_TO]->(a)
            """

            # Since the transaction query covers many labels, rows, and creats many relationships
            # Chunking into smaller batches to avoid transaction timeouts / memory issues
            for batch in chunked(tx_rows, 1500):
                session.run(tx_query, rows=batch)

            print(f"Loaded Transaction + rels: {len(tx_rows)}")
            print("Done")

    finally:
        driver.close()


if __name__ == "__main__":
    main()
